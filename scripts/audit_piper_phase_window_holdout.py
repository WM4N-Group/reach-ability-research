"""Audit a frozen two-substep loaded-bout onset coordinate on new seeds."""

import argparse
from collections import Counter
import json
from pathlib import Path

from audit_piper_hand_contact_success_controls import classify, file_sha256


LAYOUTS = ("center", "minus012", "plus012")


def bouts(rows):
    loaded = [row["hand_contact"]["force_norm_n"] > 1.0 for row in rows]
    starts = [index for index, active in enumerate(loaded)
              if active and (index == 0 or not loaded[index - 1])]
    ends = [index for index, active in enumerate(loaded)
            if active and (index + 1 == len(loaded) or not loaded[index + 1])]
    return list(zip(starts, ends))


def project(report, record, window):
    rows = report["hand_contact_substeps"]
    dt = report["scene_runtime_observation"]["physics_dt_s"]
    if (report["schema_version"] != 26 or dt != 0.005
            or len(rows) != 4 * report["push_executed_steps"]
            or len(rows) != record["push_physics_substeps"]
            or report["hand_contact_substep_contract"]["control_decimation"] != 4
            or report["hand_contact_substep_contract"]["sample_phase"]
            != "after_scene_update_before_control_step_termination"):
        raise ValueError("Substep clock or phase differs")
    illegal = []
    for index, row in enumerate(rows):
        if (row["push_control_step"] != index // 4 + 1
                or row["physics_substep"] != index % 4 + 1):
            raise ValueError(f"Incomplete substep clock at index {index}")
        event = classify(row, dt)
        if event is not None and event["failed_legal_conditions"]:
            illegal.append((index, event))
    if (len(illegal) != record["illegal_hand_substeps"]
            or (illegal[0][1] if illegal else None) != record["first_illegal_hand_event"]):
        raise ValueError("Original illegal hand audit differs")
    contact_bouts = bouts(rows)
    if sum(end - start + 1 for start, end in contact_bouts) != record[
            "sensor_force_above_1_n_samples"]:
        raise ValueError("Original loaded-contact count differs")
    windows = [{
        "kind": "first_contact" if number == 0 else "recontact",
        "start_s": (start + 1) * dt,
        "loaded_substeps": end - start + 1,
        "window_illegal": any(start <= index < min(start + window, end + 1)
                              for index, _ in illegal),
        "bout_illegal": any(start <= index <= end for index, _ in illegal),
    } for number, (start, end) in enumerate(contact_bouts)]
    first_illegal = None
    if illegal:
        index, event = illegal[0]
        number = next(number for number, (start, end) in enumerate(contact_bouts)
                      if start <= index <= end)
        first_illegal = {
            "event": event,
            "bout_kind": windows[number]["kind"],
            "loaded_bout_offset_substeps": index - contact_bouts[number][0],
            "inside_frozen_window": index - contact_bouts[number][0] < window,
        }
    return {
        "seed": record["seed"],
        "layout_tag": record["layout_tag"],
        "outcome": record["outcome"],
        "terminal_reasons": record["terminal_reasons"],
        "report_sha256": record["report_sha256"],
        "push_physics_substeps": len(rows),
        "loaded_bout_count": len(windows),
        "recontact_bout_count": max(0, len(windows) - 1),
        "longest_interbout_unloaded_substeps": max(
            (contact_bouts[number][0] - contact_bouts[number - 1][1] - 1
             for number in range(1, len(contact_bouts))), default=0),
        "window_bout_count": len(windows),
        "window_bouts_with_illegal": sum(item["window_illegal"] for item in windows),
        "window_bouts_without_illegal": sum(not item["window_illegal"]
                                             for item in windows),
        "first_illegal": first_illegal,
    }


def audit(protocol_path, cohort_path, report_dir):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    frozen = protocol["analysis_frozen_before_run"]
    seeds = protocol["seeds_in_order"]
    if (cohort["protocol_sha256"] != file_sha256(protocol_path)
            or seeds != list(range(6401, 6417))
            or frozen["center_screen_denominator"] != len(seeds)
            or frozen["loaded_bout_onset_window_substeps"] != 2
            or frozen["force_threshold_n"] != 1.0
            or len(cohort["records"]) != cohort["complete_run_denominator"]):
        raise ValueError("Frozen protocol or denominator differs")
    expected = {(seed, "center") for seed in seeds}
    expected.update((seed, tag) for seed in cohort["qualified_seeds"]
                    for tag in LAYOUTS[1:])
    records = {(row["seed"], row["layout_tag"]): row for row in cohort["records"]}
    if (len(records) != len(cohort["records"]) or set(records) != expected
            or len(cohort["qualified_seeds"]) != cohort["qualified_pair_denominator"]):
        raise ValueError("Conditional run grid differs")
    stems = {f"seed{seed}-{tag}" for seed, tag in expected}
    for suffix in ("json", "log"):
        if {path.stem for path in report_dir.glob(f"seed*.{suffix}")} != stems:
            raise ValueError(f"Original {suffix} set differs")
    projections = []
    for seed in seeds:
        tags = LAYOUTS if seed in cohort["qualified_seeds"] else LAYOUTS[:1]
        for tag in tags:
            record = records[(seed, tag)]
            stem = f"seed{seed}-{tag}"
            path, log = report_dir / f"{stem}.json", report_dir / f"{stem}.log"
            if (file_sha256(path) != record["report_sha256"]
                    or file_sha256(log) != record["log_sha256"]):
                raise ValueError(f"Original hash differs for {stem}")
            report = json.loads(path.read_text(encoding="utf-8"))
            if report["seed"] != seed:
                raise ValueError(f"Seed differs for {stem}")
            projections.append(project(report, record,
                                       frozen["loaded_bout_onset_window_substeps"]))
    groups = {}
    for tag in LAYOUTS:
        selected = [row for row in projections if row["layout_tag"] == tag]
        groups[tag] = {
            "complete_runs": len(selected),
            "outcomes": dict(Counter(
                reason for row in selected for reason in row["terminal_reasons"])),
            "loaded_bouts": sum(row["loaded_bout_count"] for row in selected),
            "recontact_bouts": sum(row["recontact_bout_count"] for row in selected),
            "window_bouts_with_illegal": sum(row["window_bouts_with_illegal"]
                                             for row in selected),
            "window_bouts_without_illegal": sum(row["window_bouts_without_illegal"]
                                                for row in selected),
            "first_illegal_hits": sum(row["first_illegal"] is not None
                                      and row["first_illegal"]["inside_frozen_window"]
                                      for row in selected),
            "first_illegal_misses": sum(row["first_illegal"] is not None
                                        and not row["first_illegal"]["inside_frozen_window"]
                                        for row in selected),
        }
    return {
        "schema_version": 1,
        "scope": "preregistered_new_seed_read_only_loaded_bout_onset_falsification",
        "protocol_sha256": file_sha256(protocol_path),
        "cohort_result_sha256": file_sha256(cohort_path),
        "complete_center_screen_denominator": len(seeds),
        "qualified_pair_denominator": len(cohort["qualified_seeds"]),
        "complete_run_denominator": len(projections),
        "loaded_bout_onset_window_substeps": frozen["loaded_bout_onset_window_substeps"],
        "phase_window_is_online_warning": False,
        "layout_groups": groups,
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
    print(json.dumps({"complete_runs": result["complete_run_denominator"],
                      "layout_groups": result["layout_groups"]}))


if __name__ == "__main__":
    main()
