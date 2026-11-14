"""Compare fresh-MjData held-step continuation with frozen no-restore reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_piper_startup import sha256


def _accepts(report: dict, deadline: float) -> bool:
    result = report["result"]
    motion = result["motion"]
    event = motion["target_step_event"]
    entries = [
        item for item in motion["wbc_hold_events"]
        if event is not None and item["time"] > event["time"]
    ]
    return bool(
        event is not None and event["applied"] and result["reason"] == "completed"
        and entries and entries[-1]["time"] - event["time"] <= deadline
    )


def _maximum_difference(left: list[dict], right: list[dict], field: str) -> float | None:
    if len(left) != len(right):
        return None
    return max((abs(a[field] - b[field]) for a, b in zip(left, right)), default=0.0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text())
    if (sha256(Path(__file__)) != protocol["evaluator_sha256"]
            or sha256(Path(protocol["runner"])) != protocol["runner_sha256"]
            or sha256(Path(protocol["motion_source"])) != protocol["motion_sha256"]):
        raise ValueError("Frozen source hash mismatch")
    gates = protocol["trajectory_gates"]
    rows = []
    for planned in protocol["planned_candidates"]:
        seed, phase = planned["seed"], planned["phase"]
        baseline_path = args.report_dir / f"seed{seed}-baseline-v4.json"
        candidate_path = args.report_dir / f"seed{seed}-{phase}-v4.json"
        baseline = json.loads(baseline_path.read_text())
        candidate = json.loads(candidate_path.read_text())
        reference_meta = protocol["reference_reports"][f"{seed}:{phase}"]
        reference_path = Path(reference_meta["path"])
        if sha256(reference_path) != reference_meta["sha256"]:
            raise ValueError(f"Reference report changed: {reference_path}")
        reference = json.loads(reference_path.read_text())
        comparison = candidate["baseline_comparison"]
        event = candidate["result"]["motion"]["target_step_event"]
        if (baseline["seed"] != seed or baseline["phase"] != "baseline"
                or candidate["seed"] != seed or candidate["phase"] != phase
                or baseline["protocol_sha256"] != sha256(args.protocol_json)
                or candidate["protocol_sha256"] != sha256(args.protocol_json)
                or comparison["baseline_sha256"] != sha256(baseline_path)
                or candidate["offset_local_m"] != protocol["offsets_m"][phase]
                or event is None or not event["applied"]):
            raise ValueError(f"Invalid fresh-data pair: {seed} {phase}")
        current_result = candidate["result"]
        reference_result = reference["result"]
        current_trace = current_result["motion"]["trace"]
        reference_trace = reference_result["motion"]["trace"]
        same_times = [item["time"] for item in current_trace] == [
            item["time"] for item in reference_trace
        ]
        hand_difference = _maximum_difference(
            current_trace, reference_trace, "hand_position_error"
        )
        speed_difference = _maximum_difference(current_trace, reference_trace, "arm_speed")
        current_qpos = current_result["motion"]["final_state"]["qpos"]
        reference_qpos = reference_result["motion"]["final_state"]["qpos"]
        qpos_difference = (
            max(abs(a - b) for a, b in zip(current_qpos, reference_qpos))
            if len(current_qpos) == len(reference_qpos) else None
        )
        current_accepts = _accepts(candidate, protocol["primary_deadline_seconds"])
        reference_accepts = _accepts(reference, protocol["primary_deadline_seconds"])
        matched = all(comparison[key] is True for key in (
            "same_nav_trace", "same_precontact_state", "same_pre_step_trace",
            "same_pre_step_state", "same_closed_loop_state_v2", "restore_roundtrip_verified",
        ))
        passed = bool(
            matched and event.get("restore_mode") == "fresh-data"
            and current_result["reason"] == reference_result["reason"]
            and current_accepts == reference_accepts and same_times
            and hand_difference is not None
            and hand_difference <= gates["maximum_sampled_hand_error_difference_m"]
            and speed_difference is not None
            and speed_difference <= gates["maximum_sampled_arm_speed_difference_rad_s"]
            and qpos_difference is not None
            and qpos_difference <= gates["maximum_final_qpos_difference"]
        )
        rows.append({
            "seed": seed, "phase": phase, "passed": passed,
            "paired_v2_state": matched,
            "reason": current_result["reason"],
            "reference_reason": reference_result["reason"],
            "ten_second_acceptance": current_accepts,
            "reference_ten_second_acceptance": reference_accepts,
            "same_trace_times": same_times,
            "maximum_sampled_hand_error_difference_m": hand_difference,
            "maximum_sampled_arm_speed_difference_rad_s": speed_difference,
            "maximum_final_qpos_difference": qpos_difference,
            "candidate_report_sha256": sha256(candidate_path),
            "baseline_report_sha256": sha256(baseline_path),
            "reference_report_sha256": sha256(reference_path),
        })
    output = {
        "schema_version": 1,
        "scope": "Fresh MjData in one Python process; known no-contact held-step states",
        "protocol_sha256": sha256(args.protocol_json),
        "evaluator_sha256": sha256(Path(__file__)),
        "all_passed": all(row["passed"] for row in rows),
        "rows": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"all_passed": output["all_passed"], "rows": rows}))


if __name__ == "__main__":
    main()
