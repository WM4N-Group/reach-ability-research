"""Audit frozen lateral box-pose strata without issuing a scene certificate."""

import argparse
from collections import Counter
import json
from pathlib import Path

from audit_piper_hand_contact_independent import summarize_report
from audit_piper_hand_contact_success_controls import file_sha256


def run_grid(protocol):
    seeds = protocol["seeds_in_order"]
    layouts = protocol["layouts_in_order"]
    jitter = protocol["original_box_reset_xy_jitter_m"]
    if (protocol["run_order"] != "seed_major_then_layouts_in_order"
            or not seeds or len(seeds) != len(set(seeds))
            or not layouts or len({row["tag"] for row in layouts}) != len(layouts)
            or any(not row["tag"].isalnum() for row in layouts)
            or len({row["nominal_box_y_m"] for row in layouts}) != len(layouts)
            or jitter != [-0.03, 0.03]):
        raise ValueError("Invalid frozen seed/layout grid")
    nominal = [row["nominal_box_y_m"] for row in layouts]
    if any(abs(left - right) <= jitter[1] - jitter[0]
           for index, left in enumerate(nominal) for right in nominal[index + 1:]):
        raise ValueError("Nominal lateral layout intervals overlap")
    runs = [(seed, row["tag"], row["nominal_box_y_m"])
            for seed in seeds for row in layouts]
    if len(runs) != protocol["analysis_frozen_before_run"]["complete_denominator"]:
        raise ValueError("Frozen denominator differs from the run grid")
    return runs


def audit(protocol_path, diagnostic_path, observer_path, report_dir):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    sources = protocol["source_sha256"]
    if (file_sha256(diagnostic_path) != sources["diagnostic"]
            or file_sha256(observer_path) != sources["scene_observer"]
            or protocol["analysis_frozen_before_run"]["force_threshold_n"] != 1.0
            or protocol["analysis_frozen_before_run"]["loaded_point_normal_force_threshold_n"] != 1.0):
        raise ValueError("Frozen diagnostic, observer or analysis threshold differs")
    runs = run_grid(protocol)
    names = {f"seed{seed}-{tag}" for seed, tag, _ in runs}
    if ({path.stem for path in report_dir.glob("seed*.json")} != names
            or {path.stem for path in report_dir.glob("seed*.log")} != names):
        raise ValueError("Report or log set differs from the frozen denominator")
    source_protocol = {
        **protocol,
        "diagnostic_sha256": sources["diagnostic"],
        "observer_sha256": sources["scene_observer"],
        "remote_source_piper_cfg_sha256": sources["piper_box_env_cfg"],
    }
    records = []
    for seed, tag, nominal_y in runs:
        stem = f"seed{seed}-{tag}"
        path = report_dir / f"{stem}.json"
        log_path = report_dir / f"{stem}.log"
        if (not log_path.stat().st_size
                or "NAV_PUSH_HANDOFF_DIAGNOSTIC=" not in log_path.read_text(encoding="utf-8")):
            raise ValueError(f"Missing completion marker for {stem}")
        report = json.loads(path.read_text(encoding="utf-8"))
        observed = report["scene_runtime_observation"]
        box_position = observed["box_spawn"]["initial_position_m"]
        initial_box = report["initial_state"]["box_pos"]
        if (report["seed"] != seed or report["box_nominal_y_m"] != nominal_y
                or observed["source_sha256"] != sources
                or box_position != [protocol["nominal_box_xz_m"][0], nominal_y,
                                    protocol["nominal_box_xz_m"][1]]
                or len(initial_box) != 3
                or abs(initial_box[0] - box_position[0]) > 0.0301
                or abs(initial_box[1] - nominal_y) > 0.0301
                or abs(initial_box[2] - box_position[2]) > 0.001):
            raise ValueError(f"Loaded layout or original box reset differs for {stem}")
        record = summarize_report(report, source_protocol)
        record.update({
            "layout_tag": tag,
            "box_nominal_y_m": nominal_y,
            "initial_box_xy_m": initial_box[:2],
            "report_sha256": file_sha256(path),
            "log_sha256": file_sha256(log_path),
        })
        records.append(record)

    layout_groups = {}
    for layout in protocol["layouts_in_order"]:
        tag = layout["tag"]
        selected = [row for row in records if row["layout_tag"] == tag]
        reasons = Counter(reason for row in selected for reason in row["terminal_reasons"])
        reasons["nav_timeout"] = sum(row["outcome"] == "nav_timeout" for row in selected)
        reasons["push_budget_exhausted"] = sum(
            row["outcome"] == "push_budget_exhausted" for row in selected)
        layout_groups[tag] = {
            "nominal_box_y_m": layout["nominal_box_y_m"],
            "complete_denominator": len(selected),
            "push_entries": sum(row["entered_push"] for row in selected),
            "outcomes": dict(reasons),
            "push_physics_substeps": sum(row["push_physics_substeps"] for row in selected),
            "hand_contact_exposed_runs": sum(
                row["sensor_force_above_1_n_samples"] > 0 for row in selected),
            "sensor_force_above_1_n_samples": sum(
                row["sensor_force_above_1_n_samples"] for row in selected),
            "manifold_nonempty_substeps": sum(
                row["manifold_nonempty_substeps"] for row in selected),
            "illegal_hand_substeps": sum(row["illegal_hand_substeps"] for row in selected),
            "substep_only_illegal_control_steps": sum(
                len(row["substep_only_illegal_control_steps"]) for row in selected),
            "configuration_groups": len({row["configuration_sha256"] for row in selected}),
        }
    if (any(row["configuration_groups"] != 1 for row in layout_groups.values())
            or len({row["configuration_sha256"] for row in records}) != len(layout_groups)):
        raise ValueError("Observed configuration strata do not match the frozen layouts")
    return {
        "schema_version": 1,
        "scope": "three_nominal_lateral_box_pose_strata_mechanism_only",
        "protocol_sha256": file_sha256(protocol_path),
        "source_sha256": sources,
        "complete_denominator": len(records),
        "layout_groups": layout_groups,
        "contact_mode_evaluable": all(
            group["hand_contact_exposed_runs"] > 0 for group in layout_groups.values()),
        "records": records,
        "scene_contract_sha256": None,
        "entry_distribution_sha256": None,
        "contact_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--observer", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.protocol_json, args.diagnostic, args.observer, args.report_dir)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"complete_denominator": result["complete_denominator"],
                      "layout_groups": result["layout_groups"]}))


if __name__ == "__main__":
    main()
