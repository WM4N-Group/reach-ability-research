"""Audit an independent same-seed NAV-to-PUSH baseline/feedback pair."""

import argparse
import json
from pathlib import Path

import audit_piper_front_foot_feedback_pilot as pilot


SEEDS = tuple(range(5601, 5609))


def check(seed, baseline_path, candidate_path):
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if (baseline["seed"] != seed or candidate["seed"] != seed
            or baseline["schema_version"] != 14 or candidate["schema_version"] != 17
            or baseline.get("front_foot_feedback", False) or not candidate["front_foot_feedback"]
            or candidate["control_sha256"] != baseline["control_sha256"]
            or candidate["nav_actor_sha256"] != baseline["nav_actor_sha256"]
            or candidate["push_checkpoint_sha256"] != baseline["push_checkpoint_sha256"]
            or candidate.get("handoff") != baseline.get("handoff")):
        raise ValueError(f"Seed{seed} pair provenance or handoff differs")
    pilot.BASELINE_SHA256[seed] = pilot.sha256(baseline_path)
    if baseline["outcome"] == "nav_timeout":
        if (candidate["outcome"] != "nav_timeout"
                or candidate["trace"] != baseline["trace"]
                or candidate["nav_terminal_command"] != baseline["nav_terminal_command"]
                or baseline["push_executed_steps"] or candidate["push_executed_steps"]):
            raise ValueError(f"Seed{seed} NAV timeout pair differs")
        result = {
            "seed": seed,
            "baseline_sha256": pilot.sha256(baseline_path),
            "candidate_sha256": pilot.sha256(candidate_path),
            "handoff_and_pre_feedback_equal": True,
            "baseline_outcome": "nav_timeout",
            "candidate_outcome": "nav_timeout",
            "baseline_terminal_reasons": {},
            "candidate_terminal_reasons": {},
        }
    else:
        if baseline["outcome"] not in ("push_terminated", "push_budget_exhausted"):
            raise ValueError(f"Seed{seed} unexpected baseline outcome")
        if not any(sample["front_foot_feedback"] is not None for sample in candidate["support_trace"]):
            if (candidate["outcome"] != baseline["outcome"]
                    or candidate["push_executed_steps"] != baseline["push_executed_steps"]
                    or candidate["terminal"].get("reasons") != baseline["terminal"].get("reasons")
                    or candidate["front_foot_feedback_steps"]):
                raise ValueError(f"Seed{seed} no-feedback pair differs")
            for original, modified in zip(baseline["support_trace"], candidate["support_trace"]):
                sample = pilot.copy.deepcopy(modified)
                if sample.pop("front_foot_feedback") is not None:
                    raise ValueError(f"Seed{seed} feedback activated in no-op pair")
                sample.pop("front_foot_feedback_leg_actions")
                if sample != original:
                    raise ValueError(f"Seed{seed} no-feedback trace differs")
            result = {
                "seed": seed,
                "baseline_sha256": pilot.sha256(baseline_path),
                "candidate_sha256": pilot.sha256(candidate_path),
                "handoff_and_pre_feedback_equal": True,
                "baseline_outcome": baseline["outcome"],
                "candidate_outcome": candidate["outcome"],
                "baseline_push_elapsed_s": baseline["push_elapsed_s"],
                "candidate_push_elapsed_s": candidate["push_elapsed_s"],
                "baseline_terminal_reasons": baseline["terminal"].get("reasons", {}),
                "candidate_terminal_reasons": candidate["terminal"].get("reasons", {}),
                "active_steps": 0,
            }
        else:
            result = pilot.check(seed, baseline_path, candidate_path)
            result["handoff_and_pre_feedback_equal"] = result.pop(
                "handoff_and_219_pre_feedback_samples_equal"
            )
            result["baseline_terminal_reasons"] = baseline["terminal"].get("reasons", {})
    result["schema_version"] = 1
    result["analysis_sha256"] = pilot.sha256(Path(__file__))
    result["pilot_audit_sha256"] = pilot.sha256(Path(pilot.__file__))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, choices=SEEDS, required=True)
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
    print(f"seed={args.seed} baseline={result['baseline_outcome']} "
          f"candidate={result['candidate_outcome']}")


if __name__ == "__main__":
    main()
