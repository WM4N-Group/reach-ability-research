"""Verify read-only recovery telemetry against archived same-seed baselines."""

import argparse
import copy
import json
import math
from pathlib import Path

from audit_piper_nav_push_baseline_cohort import sha256


BASELINE_SHA256 = {
    5701: "df801b27af5589f5fe7dba5088ebace8b4f6a4e0e8141be6abda96601dbf3c24",
    5703: "c7725ab232462bad44652eba6e9ca6d3ac2184250a36487012dee2433de0f9db",
    5712: "efd907bed8e99925a71369042ce37f6e948084796aeba8b9118abb08e035f14c",
    5716: "9ec2829e4db024506780c692770bc281be6f7856bbb9134804cafd161fa8ebca",
    5717: "6abab2e598f8885694100734756743a86caf53b9ff3a9971171d7c5c23952c25",
    5723: "1eb159b2d6df5608ab3047001871123629e7fd4232a99f4b4c6a204a857824bd",
}


def finite_vector(values, length):
    return len(values) == length and all(math.isfinite(value) for value in values)


def check(seed, baseline_path, candidate_path):
    if sha256(baseline_path) != BASELINE_SHA256[seed]:
        raise ValueError(f"Seed{seed} baseline hash differs")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if (baseline["seed"] != seed or candidate["seed"] != seed
            or baseline["schema_version"] != 14 or candidate["schema_version"] != 18
            or not candidate["record_recovery_decision_state"]
            or candidate["control_sha256"] != baseline["control_sha256"]
            or candidate["nav_actor_sha256"] != baseline["nav_actor_sha256"]
            or candidate["push_checkpoint_sha256"] != baseline["push_checkpoint_sha256"]):
        raise ValueError(f"Seed{seed} source contract differs")
    if len(candidate["support_trace"]) != candidate["push_executed_steps"]:
        raise ValueError(f"Seed{seed} incomplete decision trace")
    cleaned = copy.deepcopy(candidate)
    cleaned["schema_version"] = 14
    cleaned.pop("record_recovery_decision_state")
    if cleaned.pop("support_response_probe", None) is not None:
        raise ValueError(f"Seed{seed} contains a support intervention")
    previous_next_input = None
    for index, record in enumerate(cleaned["support_trace"]):
        state = record.pop("recovery_decision_state")
        if (not finite_vector(state["base_vel_w"], 3)
                or not finite_vector(state["base_omega_w"], 3)
                or not finite_vector(state["box_pos"], 3)
                or not finite_vector(state["box_quat"], 4)
                or not finite_vector(state["box_vel_w"], 3)
                or not finite_vector(state["box_omega_w"], 3)
                or not finite_vector(state["actor_input_before_action"], 226)
                or not finite_vector(state["actor_action_before_step"], 12)
                or not math.isfinite(state["settled_duration_s"])):
            raise ValueError(f"Seed{seed} invalid decision state at step {index}")
        if (state["arm_controller"]["safe_approach_index"] != record["arm_approach_index"]
                or state["arm_controller"]["motion_ready"] != record["motion_ready"]
                or state["arm_controller"]["reference"] != record["arm_reference"]):
            raise ValueError(f"Seed{seed} controller snapshot differs at step {index}")
        if previous_next_input is not None and previous_next_input != state["actor_input_before_action"]:
            raise ValueError(f"Seed{seed} actor history does not align at step {index}")
        previous_next_input = state["next_actor_input"]
        if index + 1 < len(cleaned["support_trace"]):
            if not finite_vector(previous_next_input, 226):
                raise ValueError(f"Seed{seed} missing next actor input at step {index}")
        elif previous_next_input is not None and not finite_vector(previous_next_input, 226):
            raise ValueError(f"Seed{seed} malformed final next actor input")
    if (cleaned["support_trace"]
            and cleaned["support_trace"][0]["push_elapsed_s"] != 0.02):
        raise ValueError(f"Seed{seed} first PUSH sample differs")
    if "support_snapshot" in cleaned["terminal"]:
        cleaned["terminal"]["support_snapshot"].pop("recovery_decision_state")
    if cleaned != baseline:
        raise ValueError(f"Seed{seed} existing report fields or trajectory differ")
    return {
        "schema_version": 1,
        "seed": seed,
        "analysis_sha256": sha256(Path(__file__)),
        "baseline_sha256": sha256(baseline_path),
        "candidate_sha256": sha256(candidate_path),
        "old_report_fields_equal": True,
        "decision_samples": len(candidate["support_trace"]),
        "outcome": candidate["outcome"],
        "terminal_reasons": candidate["terminal"].get("reasons", {}),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, choices=tuple(BASELINE_SHA256), required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")
    result = check(args.seed, args.baseline, args.candidate)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(f"seed={args.seed} unchanged={result['old_report_fields_equal']} "
          f"decision_samples={result['decision_samples']}")


if __name__ == "__main__":
    main()
