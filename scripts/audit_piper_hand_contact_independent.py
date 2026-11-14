"""Audit preregistered unseen-seed hand-contact substeps and PhysX manifolds."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path

from audit_piper_hand_contact_success_controls import classify, file_sha256
from audit_piper_scene_identity_layers import project_layers


def substep_only_illegal_steps(illegal_flags):
    if len(illegal_flags) % 4:
        raise ValueError("Illegal-contact flags do not cover full control steps")
    return [step + 1 for step in range(len(illegal_flags) // 4)
            if any(illegal_flags[4 * step:4 * step + 3])
            and not illegal_flags[4 * step + 3]]


def summarize_report(report, protocol):
    control = protocol["control"]
    seed = report["seed"]
    observed = report["scene_runtime_observation"]
    sources = observed["source_sha256"]
    if (report["schema_version"] != 26 or report["task"] != protocol["task"]
            or report["nav_actor_sha256"] != protocol["nav_actor_sha256"]
            or report["push_checkpoint_sha256"] != protocol["push_checkpoint_sha256"]
            or report["control_sha256"] != protocol["control_sha256"]
            or sources["diagnostic"] != protocol["diagnostic_sha256"]
            or sources["scene_observer"] != protocol["observer_sha256"]
            or sources["piper_box_env_cfg"] != protocol["remote_source_piper_cfg_sha256"]
            or report["nav_start_x_m"] != control["nav_start_x_m"]
            or report["nav_goal_xyyaw"] != [control["nav_goal_x_m"], 0.0, 0.0]
            or report["nav_arm_home"] is not control["nav_arm_home"]
            or report["nav_timeout_s"] != control["nav_timeout_s"]
            or report["push_budget_s"] != control["push_budget_s"]
            or report["step_dt"] != control["control_dt_s"]
            or observed["physics_dt_s"] != control["physics_dt_s"]
            or observed["control_dt_s"] != control["control_dt_s"]
            or report["skip_nav"] or report["handoff_settle_stable_s"]
            or report["safe_approach_arm_rate_scale"] != 1.0
            or any(report[key] for key in (
                "front_foot_feedback", "nav_leg_support_until_ready",
                "pre_ready_leg_action_cap", "hold_push_arm_at_handoff",
                "front_foot_probe_offset_m", "front_foot_hold_offset_m",
                "support_margin_pause_m", "record_base_contact_substeps",
                "record_base_contact_manifold", "record_recovery_decision_state"))
            or any(report[key] is not True for key in control if key.startswith("record_")
                   and key != "record_scene_runtime_observation")):
        raise ValueError(f"Frozen control or source differs for seed{seed}")
    layers = project_layers(report)
    contract = report["hand_contact_substep_contract"]
    manifold = report["hand_contact_manifold_contract"]
    if (contract["physics_dt_s"] != control["physics_dt_s"]
            or contract["control_decimation"] != 4
            or contract["sensor"] != "box_contact_hand"
            or contract["sample_phase"]
            != "after_scene_update_before_control_step_termination"
            or manifold["source"] != "box_contact_hand.contact_physx_view.get_contact_data"
            or manifold["capacity_per_pair"] != 32
            or len(manifold["prim_paths"]) != 1
            or not manifold["prim_paths"][0].endswith("/Robot/link6")
            or not manifold["filter_prim_paths_expr"]):
        raise ValueError(f"Hand contact sampling contract differs for seed{seed}")
    rows = report["hand_contact_substeps"]
    if len(rows) != 4 * report["push_executed_steps"]:
        raise ValueError(f"Missing or duplicate hand substeps for seed{seed}")
    if ("handoff" not in report) != (report["outcome"] == "nav_timeout"):
        raise ValueError(f"NAV timeout/handoff mismatch for seed{seed}")
    if (report["outcome"] == "push_terminated"
            and report["terminal"]["reasons"].get("invalid_hand_contact")
            and rows[-1]["hand_contact"]
            != report["terminal"]["invalid_hand_contact_detail"]):
        raise ValueError(f"Terminal hand contact is not the last substep for seed{seed}")

    sensor_loaded_samples = 0
    illegal_samples = 0
    first_illegal_event = None
    maximum_illegal_force_n = None
    sensor_without_loaded_point_substeps = 0
    illegal_flags = []
    point_samples = 0
    capacity_steps = []
    substeps_without_loaded_point = 0
    zero_force_candidate_points = 0
    loaded_points = 0
    unpaired_loaded_points = 0
    maximum_sensor_to_loaded_m = None
    maximum_candidate_mean_to_sensor_m = None
    maximum_scalar_force_difference_n = None
    for index, row in enumerate(rows):
        step, substep = divmod(index, 4)
        if (row["push_control_step"] != step + 1
                or row["physics_substep"] != substep + 1):
            raise ValueError(f"Hand substep clock differs at index {index} seed{seed}")
        sensor = row["hand_contact"]
        contacts = row["contact_manifold"]
        if len(contacts) > manifold["capacity_per_pair"]:
            raise ValueError(f"Hand manifold exceeds capacity for seed{seed}")
        if contacts:
            point_samples += 1
        if len(contacts) == manifold["capacity_per_pair"]:
            capacity_steps.append((step + 1, substep + 1))
        if contacts and all(point["normal_force_n"] <= 1.0 for point in contacts):
            substeps_without_loaded_point += 1
        zero_force_candidate_points += sum(point["normal_force_n"] == 0.0
                                           for point in contacts)
        if not math.isfinite(sensor["force_norm_n"]) or sensor["force_norm_n"] < 0:
            raise ValueError(f"Invalid hand sensor force for seed{seed}")
        for point in contacts:
            values = [point["normal_force_n"], point["separation_m"],
                      *point["point_w"], *point["normal_w"]]
            if len(values) != 8 or any(not math.isfinite(value) for value in values):
                raise ValueError(f"Non-finite PhysX hand point for seed{seed}")
        if contacts:
            scalar_difference = abs(sum(point["normal_force_n"] for point in contacts)
                                    - sensor["force_norm_n"])
            maximum_scalar_force_difference_n = max(
                maximum_scalar_force_difference_n or 0.0, scalar_difference)
        sensor_point = sensor["contact_pos_w_m"]
        if contacts and sensor_point is not None:
            mean = [sum(point["point_w"][axis] for point in contacts) / len(contacts)
                    for axis in range(3)]
            distance = math.dist(mean, sensor_point)
            maximum_candidate_mean_to_sensor_m = max(
                maximum_candidate_mean_to_sensor_m or 0.0, distance)
        loaded_this_substep = False
        for point in contacts:
            if point["normal_force_n"] <= 1.0:
                continue
            loaded_this_substep = True
            loaded_points += 1
            if sensor_point is None:
                unpaired_loaded_points += 1
            else:
                distance = math.dist(point["point_w"], sensor_point)
                maximum_sensor_to_loaded_m = max(maximum_sensor_to_loaded_m or 0.0,
                                                 distance)
        event = classify(row, control["physics_dt_s"])
        if event is not None:
            sensor_loaded_samples += 1
            if not loaded_this_substep:
                sensor_without_loaded_point_substeps += 1
        illegal = event is not None and bool(event["failed_legal_conditions"])
        illegal_flags.append(illegal)
        if illegal:
            illegal_samples += 1
            if first_illegal_event is None:
                first_illegal_event = event
            maximum_illegal_force_n = max(maximum_illegal_force_n or 0.0,
                                          event["force_norm_n"])
    return {
        "seed": seed,
        "outcome": report["outcome"],
        "terminal_reasons": sorted(key for key, active in
                                   report.get("terminal", {}).get("reasons", {}).items() if active),
        "entered_push": "handoff" in report,
        "push_physics_substeps": len(rows),
        "sensor_force_above_1_n_samples": sensor_loaded_samples,
        "sensor_above_1_n_without_loaded_point_substeps":
            sensor_without_loaded_point_substeps,
        "illegal_hand_substeps": illegal_samples,
        "first_illegal_hand_event": first_illegal_event,
        "maximum_illegal_hand_force_n": maximum_illegal_force_n,
        "substep_only_illegal_control_steps": substep_only_illegal_steps(illegal_flags),
        "manifold_nonempty_substeps": point_samples,
        "manifold_capacity_reached": capacity_steps,
        "manifold_without_above_1_n_point_substeps": substeps_without_loaded_point,
        "zero_force_candidate_points": zero_force_candidate_points,
        "loaded_point_count_above_1_n": loaded_points,
        "unpaired_loaded_point_count": unpaired_loaded_points,
        "maximum_sensor_to_loaded_point_m": maximum_sensor_to_loaded_m,
        "maximum_candidate_mean_to_sensor_m": maximum_candidate_mean_to_sensor_m,
        "maximum_scalar_force_sum_difference_n": maximum_scalar_force_difference_n,
        **layers,
    }


def audit(protocol_path, diagnostic_path, observer_path, report_dir):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if (file_sha256(diagnostic_path) != protocol["diagnostic_sha256"]
            or file_sha256(observer_path) != protocol["observer_sha256"]
            or protocol["analysis_frozen_before_run"]["force_threshold_n"] != 1.0
            or protocol["analysis_frozen_before_run"]["loaded_point_normal_force_threshold_n"] != 1.0):
        raise ValueError("Frozen diagnostic, observer or analysis threshold differs")
    seeds = protocol["seeds_in_order"]
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError("Preregistered seed denominator is empty or repeated")
    expected = {f"seed{seed}.json" for seed in seeds}
    expected_logs = {f"seed{seed}.log" for seed in seeds}
    if ({path.name for path in report_dir.glob("seed*.json")} != expected
            or {path.name for path in report_dir.glob("seed*.log")} != expected_logs):
        raise ValueError("Report or log set differs from the frozen denominator")
    records = []
    for seed in seeds:
        path = report_dir / f"seed{seed}.json"
        log = report_dir / f"seed{seed}.log"
        if (not log.stat().st_size
                or "NAV_PUSH_HANDOFF_DIAGNOSTIC=" not in log.read_text(encoding="utf-8")):
            raise ValueError(f"Missing completion marker for seed{seed}")
        report = json.loads(path.read_text(encoding="utf-8"))
        if report["seed"] != seed:
            raise ValueError(f"Report seed mismatch for seed{seed}")
        record = summarize_report(report, protocol)
        record["report_sha256"] = file_sha256(path)
        record["log_sha256"] = file_sha256(log)
        records.append(record)
    outcomes = Counter(reason for row in records for reason in row["terminal_reasons"])
    outcomes.update({"nav_timeout": sum(row["outcome"] == "nav_timeout" for row in records),
                     "push_budget_exhausted": sum(row["outcome"] == "push_budget_exhausted"
                                                  for row in records)})
    return {
        "schema_version": 1,
        "scope": "independent_seed_same_default_scene_hand_contact_audit_only",
        "protocol_sha256": file_sha256(protocol_path),
        "diagnostic_sha256": file_sha256(diagnostic_path),
        "observer_sha256": file_sha256(observer_path),
        "complete_denominator": len(records),
        "push_entries": sum(row["entered_push"] for row in records),
        "route_outcomes": dict(Counter(row["outcome"] for row in records)),
        "outcomes": dict(outcomes),
        "total_substep_only_illegal_control_steps": sum(
            len(row["substep_only_illegal_control_steps"]) for row in records),
        "configuration_groups": len({row["configuration_sha256"] for row in records}),
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
    print(json.dumps({key: result[key] for key in (
        "complete_denominator", "push_entries", "outcomes",
        "total_substep_only_illegal_control_steps", "configuration_groups")}))


if __name__ == "__main__":
    main()
