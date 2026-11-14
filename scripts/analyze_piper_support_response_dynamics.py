"""Measure paired pulse kinematics and check finite differences against Isaac velocities."""

import argparse
import hashlib
import json
import math
from pathlib import Path


DECISION_STATE_SHA256 = {
    5703: "27d36b18b012b76814e9a8715c6c6418a0f943317dba1fa1c80539b4ac2249a6",
    5712: "5fa840c27d9b08cb7d5952657a82d1cd27b78f06290b7229b7940d0ea9d6877a",
}
MANIFEST_SHA256 = "77bf0560d7322980e3f4601e8310ac09790cec4452a176ad3a58045f7638f743"
OFFSETS_STEPS = (5, 10, 20, 30)


def load(path, expected_sha):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected_sha:
        raise ValueError(f"Unexpected file hash: {path} {digest}")
    return json.loads(path.read_text(encoding="utf-8"))


def quaternion_conjugate(q):
    return (q[0], -q[1], -q[2], -q[3])


def quaternion_multiply(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    )


def average_world_omega(previous, current, dt):
    delta = quaternion_multiply(current, quaternion_conjugate(previous))
    if delta[0] < 0:
        delta = tuple(-value for value in delta)
    vector_norm = math.sqrt(sum(value * value for value in delta[1:]))
    if vector_norm < 1e-12:
        return (0.0, 0.0, 0.0)
    scale = 2.0 * math.atan2(vector_norm, delta[0]) / (vector_norm * dt)
    return tuple(value * scale for value in delta[1:])


def kinematics(trace, index, dt):
    previous, current = trace[index - 1:index + 1]
    return {
        "base_omega_y_avg_rad_s": average_world_omega(
            previous["base_quat"], current["base_quat"], dt
        )[1],
        "base_vz_avg_m_s": (current["base_pos"][2] - previous["base_pos"][2]) / dt,
    }


def pitch(quaternion):
    w, x, y, z = quaternion
    return math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--decision-state-dir", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    manifest = load(args.manifest, MANIFEST_SHA256)
    result = {
        "schema_version": 1,
        "scope": "Known-state finite-step response only; average finite-difference velocities are not instantaneous control inputs or a reachability certificate",
        "analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "manifest_sha256": MANIFEST_SHA256,
        "decision_state_sha256": DECISION_STATE_SHA256,
        "seeds": [],
    }
    for seed in (5703, 5712):
        rows = [row for row in manifest["runs"] if row["seed"] == seed]
        if len(rows) != 4 or {row["mode"] for row in rows} != {
                "front-up", "front-down", "rear-up", "rear-down"}:
            raise ValueError(f"Incomplete pulse modes: {seed}")
        baseline = load(args.baseline_dir / f"seed{seed}-baseline.json",
                        "c7725ab232462bad44652eba6e9ca6d3ac2184250a36487012dee2433de0f9db"
                        if seed == 5703 else
                        "efd907bed8e99925a71369042ce37f6e948084796aeba8b9118abb08e035f14c")
        decisions = load(args.decision_state_dir / f"seed{seed}-decision-state.json",
                         DECISION_STATE_SHA256[seed])
        trace = baseline["support_trace"]
        decision_trace = decisions["support_trace"]
        dt = baseline["step_dt"]
        if (abs(dt - 0.02) > 1e-9 or len(trace) != len(decision_trace)
                or any({key: value for key, value in decision_item.items()
                        if key != "recovery_decision_state"} != original
                       for decision_item, original in zip(decision_trace, trace))):
            raise ValueError(f"Decision-state and baseline trajectories differ: {seed}")
        errors = []
        for index in range(1, len(trace)):
            approximate = kinematics(trace, index, dt)
            measured = decision_trace[index]["recovery_decision_state"]
            errors.append({
                "base_omega_y_rad_s": approximate["base_omega_y_avg_rad_s"] - measured["base_omega_w"][1],
                "base_vz_m_s": approximate["base_vz_avg_m_s"] - measured["base_vel_w"][2],
            })
        warning_s = 6.48 if seed == 5703 else 6.04
        trigger_index = round(warning_s / dt) - 1
        first_action_index = trigger_index + 1
        warning = decision_trace[trigger_index]["recovery_decision_state"]
        pulse_traces = {}
        for row in rows:
            mode = row["mode"]
            candidate = load(args.candidate_dir / f"seed{seed}-{mode}.json", row["candidate_sha256"])
            audit = load(args.candidate_dir / f"seed{seed}-{mode}-audit.json", row["audit_sha256"])
            if (candidate["handoff"] != baseline["handoff"]
                    or audit["pre_action_equal_steps"] != first_action_index
                    or audit["pulse_steps"] != 20):
                raise ValueError(f"Unmatched intervention: {seed} {mode}")
            pulse_traces[mode] = candidate["support_trace"]
        samples = []
        for offset in OFFSETS_STEPS:
            index = first_action_index + offset
            baseline_state = kinematics(trace, index, dt)
            baseline_pitch = pitch(trace[index]["base_quat"])
            responses = {}
            for mode, candidate_trace in pulse_traces.items():
                candidate_state = kinematics(candidate_trace, index, dt)
                responses[mode] = {
                    "base_omega_y_avg_delta_rad_s": (
                        candidate_state["base_omega_y_avg_rad_s"] - baseline_state["base_omega_y_avg_rad_s"]
                    ),
                    "base_vz_avg_delta_m_s": candidate_state["base_vz_avg_m_s"] - baseline_state["base_vz_avg_m_s"],
                    "base_pitch_delta_rad": pitch(candidate_trace[index]["base_quat"]) - baseline_pitch,
                }
            samples.append({"elapsed_since_first_action_s": offset * dt, "responses": responses})
        result["seeds"].append({
            "seed": seed,
            "warning_s": warning_s,
            "warning_measured_base_omega_y_rad_s": warning["base_omega_w"][1],
            "warning_measured_base_vz_m_s": warning["base_vel_w"][2],
            "finite_difference_validation": {
                key: {
                    "rmse": math.sqrt(sum(error[key] ** 2 for error in errors) / len(errors)),
                    "maximum_abs": max(abs(error[key]) for error in errors),
                    "warning_step_error": errors[trigger_index - 1][key],
                }
                for key in errors[0]
            },
            "samples": samples,
        })
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(result["seeds"], indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
