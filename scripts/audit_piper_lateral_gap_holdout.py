"""Evaluate a frozen causal gap marker on a conditional lateral holdout."""

import argparse
import json
from pathlib import Path

from audit_piper_hand_contact_success_controls import file_sha256
from audit_piper_lateral_online_gap_event import first_crossing, project


LAYOUTS = ("center", "minus012", "plus012")


def audit(protocol_path, cohort_path, report_dir):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    frozen = protocol["analysis_frozen_before_run"]
    if (cohort["protocol_sha256"] != file_sha256(protocol_path)
            or cohort["center_screen_denominator"] != len(protocol["seeds_in_order"])
            or cohort["complete_run_denominator"] != len(cohort["records"])
            or frozen["gap_m"] != 0.04
            or frozen["warning_height_m"] != 0.058
            or frozen["warning_vertical_speed_m_s"] != 0.20):
        raise ValueError("Cohort or frozen marker differs")
    expected = {(seed, "center") for seed in protocol["seeds_in_order"]}
    expected.update((seed, tag) for seed in cohort["qualified_seeds"]
                    for tag in LAYOUTS[1:])
    records = {(row["seed"], row["layout_tag"]): row for row in cohort["records"]}
    if (set(records) != expected
            or len(cohort["qualified_seeds"]) != cohort["qualified_pair_denominator"]):
        raise ValueError("Incomplete center screen or conditional pair grid")
    stems = {f"seed{seed}-{tag}" for seed, tag in expected}
    for suffix in ("json", "log"):
        if {path.stem for path in report_dir.glob(f"seed*.{suffix}")} != stems:
            raise ValueError(f"Unexpected {suffix} original set")

    projections = []
    for seed in protocol["seeds_in_order"]:
        tags = LAYOUTS if seed in cohort["qualified_seeds"] else LAYOUTS[:1]
        for tag in tags:
            row = records[(seed, tag)]
            stem = f"seed{seed}-{tag}"
            path = report_dir / f"{stem}.json"
            log = report_dir / f"{stem}.log"
            if (file_sha256(path) != row["report_sha256"]
                    or file_sha256(log) != row["log_sha256"]):
                raise ValueError(f"Changed original for {stem}")
            report = json.loads(path.read_text(encoding="utf-8"))
            substeps = report["hand_contact_substeps"]
            dt = report["scene_runtime_observation"]["physics_dt_s"]
            front_x = -report["scene_runtime_observation"]["box_size_m"][0] / 2
            if (report["seed"] != seed or len(substeps) != 4 * report["push_executed_steps"]
                    or abs(dt - 0.005) > 1e-9 or abs(front_x + 0.6) > 1e-9):
                raise ValueError(f"Clock, box or seed differs for {stem}")
            for index, sample in enumerate(substeps):
                if (sample["push_control_step"] != index // 4 + 1
                        or sample["physics_substep"] != index % 4 + 1):
                    raise ValueError(f"Incomplete substep clock for {stem}")
            first_contact = next((index for index, sample in enumerate(substeps)
                                  if sample["hand_contact"]["force_norm_n"] > 1.0), None)
            event_index, prior = first_crossing(substeps, range(3, len(substeps), 4), front_x)
            event = None
            warning = False
            if event_index is not None:
                event = project(substeps[event_index], event_index,
                                dict(substeps[prior], index=prior), dt, front_x)
                warning = (event["hand_origin_height_box_m"] >= frozen["warning_height_m"]
                           and event["hand_height_speed_m_s"]
                           >= frozen["warning_vertical_speed_m_s"])
                event["before_first_loaded_contact"] = (
                    None if first_contact is None else event_index < first_contact)
                event["retrospective_time_to_first_loaded_contact_s"] = (
                    None if first_contact is None else (first_contact - event_index) * dt)
            projections.append({
                "seed": seed,
                "layout_tag": tag,
                "terminal_reasons": row["terminal_reasons"],
                "outcome": row["outcome"],
                "report_sha256": row["report_sha256"],
                "first_loaded_contact_s": (None if first_contact is None
                                           else (first_contact + 1) * dt),
                "control_step_end_gap_event": event,
                "frozen_exploratory_warning": warning,
            })
    return {
        "schema_version": 1,
        "scope": "independent_seed_falsification_only_conditional_lateral_gap_marker",
        "protocol_sha256": file_sha256(protocol_path),
        "cohort_result_sha256": file_sha256(cohort_path),
        "center_screen_denominator": cohort["center_screen_denominator"],
        "qualified_pair_denominator": cohort["qualified_pair_denominator"],
        "complete_run_denominator": len(projections),
        "gap_m": frozen["gap_m"],
        "warning_height_m": frozen["warning_height_m"],
        "warning_vertical_speed_m_s": frozen["warning_vertical_speed_m_s"],
        "future_contact_used_by_trigger": False,
        "future_contact_used_for_retrospective_evaluation": True,
        "online_warning_certified": False,
        "records": projections,
        "contact_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--cohort-result", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.protocol_json, args.cohort_result, args.report_dir)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"center_screens": result["center_screen_denominator"],
                      "qualified_pairs": result["qualified_pair_denominator"],
                      "complete_runs": result["complete_run_denominator"],
                      "gap_events": sum(row["control_step_end_gap_event"] is not None
                                        for row in result["records"]),
                      "warnings": sum(row["frozen_exploratory_warning"]
                                      for row in result["records"])}))


if __name__ == "__main__":
    main()
