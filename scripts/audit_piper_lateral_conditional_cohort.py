"""Audit complete center screens and their prespecified lateral contact pairs."""

import argparse
from collections import Counter
import json
from pathlib import Path

from audit_piper_hand_contact_independent import summarize_report
from audit_piper_hand_contact_success_controls import file_sha256


LAYOUTS = {"center": 0.0, "minus012": -0.12, "plus012": 0.12}


def qualifies(report):
    return (report["outcome"] == "push_terminated"
            and report["terminal"]["reasons"].get("box_settled") is True
            and any(row["hand_contact"]["force_norm_n"] > 1.0
                    for row in report["hand_contact_substeps"]))


def expected_runs(protocol, center_reports):
    seeds = protocol["seeds_in_order"]
    if (not seeds or len(seeds) != len(set(seeds))
            or len(seeds) != protocol["analysis_frozen_before_run"]["center_screen_denominator"]
            or protocol["screen_layout"] != {"tag": "center", "nominal_box_y_m": 0.0}
            or protocol["qualified_layouts_in_order"] != [
                {"tag": "minus012", "nominal_box_y_m": -0.12},
                {"tag": "plus012", "nominal_box_y_m": 0.12}]
            or protocol["run_order"] !=
            "all_center_screens_in_seed_order_then_qualified_seeds_in_order_each_minus_then_plus"
            or protocol["original_box_reset_xy_jitter_m"] != [-0.03, 0.03]):
        raise ValueError("Frozen conditional screen grid differs")
    if set(center_reports) != set(seeds):
        raise ValueError("Center screen denominator is incomplete")
    qualified = [seed for seed in seeds if qualifies(center_reports[seed])]
    runs = [(seed, "center") for seed in seeds]
    runs.extend((seed, tag) for seed in qualified for tag in ("minus012", "plus012"))
    return qualified, runs


def audit(protocol_path, diagnostic_path, observer_path, report_dir):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    sources = protocol["source_sha256"]
    if (file_sha256(diagnostic_path) != sources["diagnostic"]
            or file_sha256(observer_path) != sources["scene_observer"]
            or protocol["analysis_frozen_before_run"]["force_threshold_n"] != 1.0
            or protocol["analysis_frozen_before_run"]["loaded_point_normal_force_threshold_n"] != 1.0):
        raise ValueError("Frozen source or threshold differs")
    center_reports = {}
    for seed in protocol["seeds_in_order"]:
        path = report_dir / f"seed{seed}-center.json"
        center_reports[seed] = json.loads(path.read_text(encoding="utf-8"))
    qualified, runs = expected_runs(protocol, center_reports)
    names = {f"seed{seed}-{tag}" for seed, tag in runs}
    if ({path.stem for path in report_dir.glob("seed*.json")} != names
            or {path.stem for path in report_dir.glob("seed*.log")} != names):
        raise ValueError("Report or log set differs from the conditional run grid")
    source_protocol = {
        **protocol,
        "diagnostic_sha256": sources["diagnostic"],
        "observer_sha256": sources["scene_observer"],
        "remote_source_piper_cfg_sha256": sources["piper_box_env_cfg"],
    }
    records = []
    for seed, tag in runs:
        stem = f"seed{seed}-{tag}"
        path, log_path = report_dir / f"{stem}.json", report_dir / f"{stem}.log"
        if (not log_path.stat().st_size
                or "NAV_PUSH_HANDOFF_DIAGNOSTIC=" not in log_path.read_text(encoding="utf-8")):
            raise ValueError(f"Missing completion marker for {stem}")
        report = center_reports[seed] if tag == "center" else json.loads(
            path.read_text(encoding="utf-8"))
        observed = report["scene_runtime_observation"]
        box_position = observed["box_spawn"]["initial_position_m"]
        initial_box = report["initial_state"]["box_pos"]
        if (report["seed"] != seed or report["box_nominal_y_m"] != LAYOUTS[tag]
                or observed["source_sha256"] != sources
                or box_position != [protocol["nominal_box_xz_m"][0], LAYOUTS[tag],
                                    protocol["nominal_box_xz_m"][1]]
                or len(initial_box) != 3
                or abs(initial_box[0] - box_position[0]) > 0.0301
                or abs(initial_box[1] - LAYOUTS[tag]) > 0.0301
                or abs(initial_box[2] - box_position[2]) > 0.001):
            raise ValueError(f"Loaded layout or box reset differs for {stem}")
        record = summarize_report(report, source_protocol)
        record.update(layout_tag=tag, box_nominal_y_m=LAYOUTS[tag],
                      initial_box_xy_m=initial_box[:2], report_sha256=file_sha256(path),
                      log_sha256=file_sha256(log_path))
        records.append(record)

    groups = {}
    for tag in LAYOUTS:
        selected = [row for row in records if row["layout_tag"] == tag]
        reasons = Counter(reason for row in selected for reason in row["terminal_reasons"])
        reasons["nav_timeout"] = sum(row["outcome"] == "nav_timeout" for row in selected)
        reasons["push_budget_exhausted"] = sum(
            row["outcome"] == "push_budget_exhausted" for row in selected)
        groups[tag] = {
            "complete_denominator": len(selected),
            "push_entries": sum(row["entered_push"] for row in selected),
            "outcomes": dict(reasons),
            "hand_contact_exposed_runs": sum(
                row["sensor_force_above_1_n_samples"] > 0 for row in selected),
            "sensor_force_above_1_n_samples": sum(
                row["sensor_force_above_1_n_samples"] for row in selected),
            "illegal_hand_substeps": sum(row["illegal_hand_substeps"] for row in selected),
            "substep_only_illegal_control_steps": sum(
                len(row["substep_only_illegal_control_steps"]) for row in selected),
            "configuration_groups": len({row["configuration_sha256"] for row in selected}),
        }
    expected_configurations = 3 if qualified else 1
    if (any(group["configuration_groups"] != (1 if group["complete_denominator"] else 0)
            for group in groups.values())
            or len({row["configuration_sha256"] for row in records})
            != expected_configurations):
        raise ValueError("Loaded lateral configuration strata differ")
    return {
        "schema_version": 1,
        "scope": "independent_center_screen_conditional_lateral_pose_pairs_only",
        "protocol_sha256": file_sha256(protocol_path),
        "source_sha256": sources,
        "center_screen_denominator": len(protocol["seeds_in_order"]),
        "qualified_seeds": qualified,
        "qualified_pair_denominator": len(qualified),
        "complete_run_denominator": len(records),
        "layout_groups": groups,
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
    print(json.dumps({"center_screen_denominator": result["center_screen_denominator"],
                      "qualified_seeds": result["qualified_seeds"],
                      "layout_groups": result["layout_groups"]}))


if __name__ == "__main__":
    main()
