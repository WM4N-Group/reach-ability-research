"""Extract fixed-time observable states from the frozen 5801-5824 cohort."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


ANCHORS_S = (0.0, 0.02, 2.0, 4.0, 5.0, 6.0)
MANIFEST_SHA256 = "73d9e91e5694a45c3dcb966684029f37dfd4b2ae50ce58084283c936bbb5eef2"
FOOT_NAMES = ("FL_foot", "FR_foot", "RL_foot", "RR_foot")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite_vector(values, size):
    return len(values) == size and all(math.isfinite(value) for value in values)


def pitch(quaternion):
    w, x, y, z = quaternion
    return math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x))))


def state_features(state, velocity, angular_velocity, forces, leg_jacobians, arm_index,
                   motion_ready, names, time_s):
    if (not finite_vector(state["base_pos"], 3)
            or not finite_vector(state["base_quat"], 4)
            or not finite_vector(velocity, 3)
            or not finite_vector(angular_velocity, 3)
            or not finite_vector(forces, 4)):
        raise ValueError("Nonfinite observed base or support state")
    errors = [leg_jacobians[name]["maximum_joint_target_error_rad"] for name in FOOT_NAMES]
    limits = [leg_jacobians[name]["minimum_soft_joint_limit_margin_rad"] for name in FOOT_NAMES]
    if not all(math.isfinite(value) for value in errors + limits):
        raise ValueError("Nonfinite leg authority telemetry")
    positive = {name: max(0.0, forces[names.index(name)]) for name in FOOT_NAMES}
    total = sum(positive.values())
    return {
        "push_elapsed_s": time_s,
        "base_height_m": state["base_pos"][2],
        "base_pitch_rad": pitch(state["base_quat"]),
        "base_vertical_velocity_m_s": velocity[2],
        "base_y_angular_velocity_rad_s": angular_velocity[1],
        "foot_normal_forces_n": {name: forces[names.index(name)] for name in FOOT_NAMES},
        "supported_feet_gt_2n": sum(value > 2.0 for value in forces),
        "rear_positive_force_share": ((positive["RL_foot"] + positive["RR_foot"]) / total
                                      if total > 0.0 else None),
        "maximum_leg_target_tracking_error_rad": max(errors),
        "minimum_leg_soft_joint_limit_margin_rad": min(limits),
        "arm_approach_index": arm_index,
        "motion_ready": motion_ready,
        "remaining_push_budget_s": 12.0 - time_s,
    }


def handoff_features(report):
    handoff = report["handoff"]
    physical = handoff["state"]
    controller = handoff["controller"]
    return state_features(
        physical, physical["base_vel"], physical["base_omega"],
        handoff["telemetry"]["foot_normal_forces_n"], handoff["leg_jacobians"],
        controller["safe_approach_index"], controller["motion_ready"],
        report["support_foot_body_names"], 0.0,
    )


def trace_features(item, names):
    physical = item["recovery_decision_state"]
    return state_features(
        item, physical["base_vel_w"], physical["base_omega_w"],
        item["foot_normal_forces_n"], item["leg_jacobians"],
        item["arm_approach_index"], item["motion_ready"], names, item["push_elapsed_s"],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if (protocol["analysis_sha256"] != sha256(Path(__file__))
            or protocol["input_manifest_sha256"] != MANIFEST_SHA256
            or protocol["anchors_s"] != list(ANCHORS_S)
            or sha256(args.manifest) != MANIFEST_SHA256):
        raise ValueError("Frozen protocol, analysis or input manifest differs")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if [item["seed"] for item in manifest["reports"]] != list(range(5801, 5825)):
        raise ValueError("The full pre-registered denominator is required")
    rows = []
    control_sha = None
    for entry in manifest["reports"]:
        seed = entry["seed"]
        path = args.report_dir / f"seed{seed}-baseline.json"
        if sha256(path) != entry["sha256"]:
            raise ValueError(f"Seed{seed} report hash differs")
        report = json.loads(path.read_text(encoding="utf-8"))
        if (report["seed"] != seed or report["schema_version"] != 18
                or report["step_dt"] != 0.02 or report["push_budget_s"] != 12.0
                or report["nav_start_x_m"] != -0.25
                or report["nav_goal_xyyaw"] != [-0.05, 0.0, 0.0]
                or set(report["support_foot_body_names"]) != set(FOOT_NAMES)
                or len(report["support_trace"]) != report["push_executed_steps"]):
            raise ValueError(f"Seed{seed} control or trace contract differs")
        if control_sha is None:
            control_sha = report["control_sha256"]
        elif control_sha != report["control_sha256"]:
            raise ValueError(f"Seed{seed} control source differs")
        trace = report["support_trace"]
        if (entry["outcome"] == "nav_timeout") != (not trace):
            raise ValueError(f"Seed{seed} NAV/PUSH denominator differs")
        states = {}
        for time_s in ANCHORS_S:
            key = f"{time_s:.2f}"
            if not trace or (time_s > 0.0 and time_s > report["push_elapsed_s"] + 1e-8):
                states[key] = None
            elif time_s == 0.0:
                states[key] = handoff_features(report)
            else:
                index = round(time_s / report["step_dt"]) - 1
                if index >= len(trace) or abs(trace[index]["push_elapsed_s"] - time_s) > 1e-8:
                    raise ValueError(f"Seed{seed} missing fixed PUSH sample {time_s}")
                states[key] = trace_features(trace[index], report["support_foot_body_names"])
        if entry["outcome"] != "nav_timeout":
            active = [name for name, value in report["terminal"]["reasons"].items() if value]
            if active != [entry["outcome"]]:
                raise ValueError(f"Seed{seed} terminal label differs")
        rows.append({
            "seed": seed,
            "outcome": entry["outcome"],
            "warning_push_s": entry.get("warning_push_s"),
            "terminal_push_s": report["push_elapsed_s"] if trace else None,
            "anchor_states": states,
        })
    output = {
        "schema_version": 1,
        "scope": "Fixed-scene known-cohort observable state inventory; no classifier, threshold or action certificate",
        "analysis_sha256": sha256(Path(__file__)),
        "protocol_sha256": sha256(args.protocol),
        "manifest_sha256": MANIFEST_SHA256,
        "control_sha256": control_sha,
        "anchors_s": list(ANCHORS_S),
        "outcome_counts": dict(Counter(row["outcome"] for row in rows)),
        "rows": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2, allow_nan=False)
    print(json.dumps({"outcome_counts": output["outcome_counts"],
                      "anchor_coverage": {f"{time_s:.2f}": sum(
                          row["anchor_states"][f"{time_s:.2f}"] is not None for row in rows)
                          for time_s in ANCHORS_S}}, indent=2))


if __name__ == "__main__":
    main()
