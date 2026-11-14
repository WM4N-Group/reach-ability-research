"""Audit pre-step feature overlap without fitting a recovery classifier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from check_piper_startup import sha256


FEATURES = (
    "instantaneous_hand_error_m",
    "pre_step_hand_error_m",
    "base_linear_speed_m_s",
    "arm_joint_speed_norm_rad_s",
    "hand_feedback_integral_norm_m",
    "orientation_feedback_integral_norm_rad",
    "base_x_m",
)


def _features(event: dict) -> dict[str, float]:
    pre = event["pre_step_state"]
    qpos = np.asarray(pre["qpos"], dtype=np.float64)
    qvel = np.asarray(pre["qvel"], dtype=np.float64)
    hand_integral = np.asarray(pre["hand_feedback_integral"], dtype=np.float64)
    orientation_integral = np.asarray(pre["orientation_feedback_integral"], dtype=np.float64)
    if (qpos.shape != (32,) or qvel.shape != (30,)
            or hand_integral.shape != (3,) or orientation_integral.shape != (3,)
            or not all(np.isfinite(vector).all() for vector in (
                qpos, qvel, hand_integral, orientation_integral,
            ))):
        raise ValueError("Unexpected or nonfinite pre-step state")
    return {
        "instantaneous_hand_error_m": event["instantaneous_hand_error_m"],
        "pre_step_hand_error_m": event["pre_step_hand_error_m"],
        "base_linear_speed_m_s": float(np.linalg.norm(qvel[:3])),
        "arm_joint_speed_norm_rad_s": float(np.linalg.norm(qvel[18:24])),
        "hand_feedback_integral_norm_m": float(np.linalg.norm(hand_integral)),
        "orientation_feedback_integral_norm_rad": float(np.linalg.norm(orientation_integral)),
        "base_x_m": float(qpos[0]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text())
    if sha256(Path(__file__)) != protocol["auditor_sha256"]:
        raise ValueError("Frozen feature auditor changed")
    rows = []
    for item in protocol["reports"]:
        path = Path(item["path"])
        if sha256(path) != item["sha256"]:
            raise ValueError(f"Source report changed: {path}")
        report = json.loads(path.read_text())
        event = report["result"]["motion"]["target_step_event"]
        if (report["seed"] != item["seed"] or report["phase"] != "x_minus_12mm"
                or report["offset_local_m"] != [-0.012, 0.0, 0.0]):
            raise ValueError(f"Not the selected held-step report: {path}")
        eligible = bool(
            event is not None and event["applied"]
            and report["baseline_comparison"] is not None
            and all(report["baseline_comparison"][key] is True for key in (
                "same_nav_trace", "same_precontact_state", "same_pre_step_trace",
                "same_pre_step_state",
            ))
        )
        row = {
            "seed": item["seed"], "layout": item["layout"],
            "source_sha256": item["sha256"], "eligible": eligible,
            "reason": report["result"]["reason"],
        }
        if eligible:
            entries = [entry for entry in report["result"]["motion"]["wbc_hold_events"]
                       if entry["time"] > event["time"]]
            final_delay = entries[-1]["time"] - event["time"] if entries else None
            row.update({
                "ten_second_acceptance": bool(
                    report["result"]["reason"] == "completed"
                    and final_delay is not None and final_delay <= protocol["deadline_seconds"]
                ),
                "final_hold_start_delay_s": final_delay,
                "pre_step_features": _features(event),
            })
        rows.append(row)
    overlap = {}
    for layout in sorted({item["layout"] for item in rows}):
        eligible = [item for item in rows if item["eligible"] and item["layout"] == layout]
        accepted = [item for item in eligible if item["ten_second_acceptance"]]
        rejected = [item for item in eligible if not item["ten_second_acceptance"]]
        if not accepted or not rejected:
            overlap[layout] = {"comparable": False, "accepted": len(accepted),
                               "rejected": len(rejected)}
            continue
        features = {}
        for name in FEATURES:
            accepted_values = [item["pre_step_features"][name] for item in accepted]
            rejected_values = [item["pre_step_features"][name] for item in rejected]
            left = [min(accepted_values), max(accepted_values)]
            right = [min(rejected_values), max(rejected_values)]
            features[name] = {
                "accepted_range": left,
                "rejected_range": right,
                "ranges_overlap": max(left[0], right[0]) <= min(left[1], right[1]),
            }
        overlap[layout] = {"comparable": True, "accepted": len(accepted),
                           "rejected": len(rejected), "features": features}
    output = {
        "schema_version": 1,
        "scope": "Retrospective pre-step scalar overlap audit; no fitted or validated predictor",
        "protocol_sha256": sha256(args.protocol_json),
        "auditor_sha256": sha256(Path(__file__)),
        "rows": rows,
        "layout_overlap": overlap,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({name: {key: value for key, value in detail.items()
                             if key != "features"} for name, detail in overlap.items()}))


if __name__ == "__main__":
    main()
