"""Score frozen held-command predictions against independent target-step runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_piper_startup import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--predictions-json", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text())
    predictions = json.loads(args.predictions_json.read_text())
    summary = json.loads(args.summary_json.read_text())
    if (sha256(Path(__file__)) != protocol["evaluation_script_sha256"]
            or predictions["protocol_sha256"] != sha256(args.protocol_json)
            or summary["protocol_sha256"] != sha256(args.protocol_json)
            or predictions["prediction_script_sha256"]
            != protocol["prediction_script_sha256"]
            or summary["summary_script_sha256"]
            != protocol["summary_script_sha256"]):
        raise ValueError("Protocol or analysis source mismatch")
    expected = {
        seed: batch["name"]
        for batch in protocol["batches"] for seed in batch["seeds"]
    }
    if (len(predictions["entries"]) != len(expected)
            or len(summary["entries"]) != len(expected)):
        raise ValueError("Incomplete independent batch")
    forecast = {item["seed"]: item for item in predictions["entries"]}
    if set(forecast) != set(expected):
        raise ValueError("Missing or duplicate forecasts")
    rows = []
    for item in summary["entries"]:
        seed = item["seed"]
        if (seed not in expected or item["phase"] != protocol["phase"]
                or item["layout"] != expected[seed]
                or forecast[seed]["layout"] != expected[seed]
                or item["baseline_sha256"] != forecast[seed]["baseline_sha256"]):
            raise ValueError(f"Unmatched independent result: {seed}")
        eligible = forecast[seed]["eligible"]
        matched = item["matched_pre_step_state"]
        if eligible and matched and (
                item["initial_step_hand_error_m"] <= protocol["hand_tolerance_m"]):
            raise ValueError(f"Step did not leave the position gate: {seed}")
        hold_delay = (
            item["final_hold_start_time"] - item["step_time"]
            if item["final_hold_start_time"] is not None else None
        )
        outcome = bool(
            eligible and matched and item["accepted"]
            and hold_delay is not None
            and hold_delay <= protocol["primary_deadline_seconds"]
        )
        prediction = forecast[seed]["predict_recovery_by_deadline"]
        rows.append({
            "seed": seed,
            "layout": item["layout"],
            "baseline_reason": forecast[seed]["baseline_reason"],
            "candidate_reason": item["reason"],
            "eligible": eligible,
            "matched_pre_step_state": matched,
            "body_forward_command_m": forecast[seed]["body_forward_command_m"],
            "predicted_recovery": prediction,
            "actual_recovery_by_deadline": outcome,
            "prediction_correct": prediction == outcome if eligible and matched else None,
            "final_hold_start_delay_seconds": hold_delay,
            "report_sha256": item["report_sha256"],
            "baseline_sha256": item["baseline_sha256"],
        })
    if len({item["seed"] for item in rows}) != len(expected):
        raise ValueError("Duplicate candidate seed")
    evaluated = [item for item in rows if item["eligible"] and item["matched_pre_step_state"]]
    report = {
        "schema_version": 1,
        "scope": "Held-out check of an exploratory body-forward command interval",
        "protocol_sha256": sha256(args.protocol_json),
        "predictions_sha256": sha256(args.predictions_json),
        "full_summary_sha256": sha256(args.summary_json),
        "evaluation_script_sha256": sha256(Path(__file__)),
        "eligible_matched": len(evaluated),
        "correct": sum(item["prediction_correct"] for item in evaluated),
        "true_positive": sum(item["predicted_recovery"] is True
                             and item["actual_recovery_by_deadline"] for item in evaluated),
        "true_negative": sum(item["predicted_recovery"] is False
                             and not item["actual_recovery_by_deadline"] for item in evaluated),
        "false_positive": sum(item["predicted_recovery"] is True
                              and not item["actual_recovery_by_deadline"] for item in evaluated),
        "false_negative": sum(item["predicted_recovery"] is False
                              and item["actual_recovery_by_deadline"] for item in evaluated),
        "entries": sorted(rows, key=lambda item: item["seed"]),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({key: report[key] for key in (
        "eligible_matched", "correct", "true_positive", "true_negative",
        "false_positive", "false_negative",
    )}))


if __name__ == "__main__":
    main()
