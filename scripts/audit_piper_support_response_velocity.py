"""Verify read-only pulse velocity telemetry and measure its paired response."""

import argparse
import hashlib
import json
import math
from pathlib import Path


MANIFEST_SHA256 = "77bf0560d7322980e3f4601e8310ac09790cec4452a176ad3a58045f7638f743"
DECISION_STATE_SHA256 = {
    5703: "27d36b18b012b76814e9a8715c6c6418a0f943317dba1fa1c80539b4ac2249a6",
    5712: "5fa840c27d9b08cb7d5952657a82d1cd27b78f06290b7229b7940d0ea9d6877a",
}
SAMPLE_OFFSETS = (5, 10, 20, 30)


def load(path, expected=None):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError(f"Unexpected file hash: {path} {digest}")
    return json.loads(path.read_text(encoding="utf-8")), digest


def strip_read_only_velocity(report):
    stripped = dict(report)
    stripped["schema_version"] = 19
    del stripped["record_support_response_velocity"]
    stripped["support_trace"] = [
        {key: value for key, value in item.items() if key != "support_probe_dynamics"}
        for item in report["support_trace"]
    ]
    stripped["terminal"] = dict(report["terminal"])
    stripped["terminal"]["support_snapshot"] = {
        key: value for key, value in report["terminal"]["support_snapshot"].items()
        if key != "support_probe_dynamics"
    }
    return stripped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--decision-state", type=Path, required=True)
    parser.add_argument("--previous-candidate", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--seed", type=int, choices=DECISION_STATE_SHA256, required=True)
    parser.add_argument("--mode", choices=("front-up", "front-down", "rear-up", "rear-down"), required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    manifest, manifest_sha = load(args.manifest, MANIFEST_SHA256)
    row = next((item for item in manifest["runs"] if item["seed"] == args.seed
                and item["mode"] == args.mode), None)
    if row is None:
        raise ValueError("Candidate not in frozen manifest")
    previous, previous_sha = load(args.previous_candidate, row["candidate_sha256"])
    candidate, candidate_sha = load(args.candidate)
    decisions, decision_sha = load(args.decision_state, DECISION_STATE_SHA256[args.seed])
    if (candidate["schema_version"] != 20 or candidate.get("record_support_response_velocity") is not True
            or candidate["seed"] != args.seed or candidate["support_response_probe"] != args.mode
            or strip_read_only_velocity(candidate) != previous):
        raise ValueError("Read-only velocity trace changed the pulse rollout")
    original = decisions["support_trace"]
    tested = candidate["support_trace"]
    if len(tested) != candidate["push_executed_steps"]:
        raise ValueError("Incomplete support trace")
    first_action = next((index for index, item in enumerate(tested)
                         if item["support_probe_applied"]), None)
    if first_action is None:
        raise ValueError("Missing probe action")
    for index, item in enumerate(tested):
        velocity = item["support_probe_dynamics"]
        if (len(velocity["base_vel_w"]) != 3 or len(velocity["base_omega_w"]) != 3
                or not all(math.isfinite(value) for values in velocity.values() for value in values)):
            raise ValueError(f"Invalid velocity record at {index}")
        if index < first_action and velocity != {
                "base_vel_w": original[index]["recovery_decision_state"]["base_vel_w"],
                "base_omega_w": original[index]["recovery_decision_state"]["base_omega_w"],
        }:
            raise ValueError(f"Pre-action instantaneous velocity differs at {index}")
    samples = []
    for offset in SAMPLE_OFFSETS:
        index = first_action + offset
        if index >= min(len(tested), len(original)):
            continue
        observed = tested[index]["support_probe_dynamics"]
        reference = original[index]["recovery_decision_state"]
        samples.append({
            "elapsed_since_first_action_s": offset * candidate["step_dt"],
            "base_omega_y_delta_rad_s": observed["base_omega_w"][1] - reference["base_omega_w"][1],
            "base_vz_delta_m_s": observed["base_vel_w"][2] - reference["base_vel_w"][2],
        })
    report = {
        "schema_version": 1,
        "scope": "Known-state instantaneous velocity response; exact same rollout after stripping read-only telemetry, no independent viability claim",
        "seed": args.seed,
        "mode": args.mode,
        "manifest_sha256": manifest_sha,
        "decision_state_sha256": decision_sha,
        "previous_candidate_sha256": previous_sha,
        "candidate_sha256": candidate_sha,
        "audit_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "whole_previous_rollout_equal_after_stripping_velocity": True,
        "pre_action_velocity_equal_steps": first_action,
        "samples": samples,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({"seed": args.seed, "mode": args.mode,
                      "pre_action_velocity_equal_steps": first_action}, allow_nan=False))


if __name__ == "__main__":
    main()
