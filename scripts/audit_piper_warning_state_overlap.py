"""Check whether simple support features separate warned successes from failures."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from audit_piper_pre_ready_support_warning import COHORTS, first_warning, outcome, sha256


def feature_range(rows, key):
    values = [row[key] for row in rows]
    return [min(values), max(values)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--warning-evidence", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    frozen = json.loads(args.warning_evidence.read_text(encoding="utf-8"))
    if (frozen["analysis_sha256"] != sha256(Path(__file__).with_name(
            "audit_piper_pre_ready_support_warning.py"))
            or frozen["total_nav_starts"] != 96):
        raise ValueError("Warning source differs from the frozen four-cohort audit")

    expected = {cohort["name"]: cohort for cohort in frozen["cohorts"]}
    if set(expected) != {name for name, _, _ in COHORTS}:
        raise ValueError("Unexpected cohort manifest")
    rows = []
    for name, relative_path, first_seed in COHORTS:
        cohort = expected[name]
        warned = {item["seed"]: item for item in cohort["warning_cases"]}
        manifest_lines = []
        for seed in range(first_seed, first_seed + 24):
            path = args.artifact_root / relative_path / f"seed{seed}-baseline.json"
            manifest_lines.append(f"{seed}:{sha256(path)}\n")
            if seed not in warned:
                continue
            report = json.loads(path.read_text(encoding="utf-8"))
            trace = report["support_trace"]
            if (report["seed"] != seed or len(trace) != report["push_executed_steps"]
                    or outcome(report) != warned[seed]["outcome"]
                    or first_warning(trace, report["step_dt"]) != warned[seed]["warning_push_s"]):
                raise ValueError(f"Warning case differs for seed {seed}")
            index = round(warned[seed]["warning_push_s"] / report["step_dt"]) - 1
            prior = index - 10
            if prior < 0 or not math.isclose(
                    trace[index]["push_elapsed_s"] - trace[prior]["push_elapsed_s"],
                    0.2, abs_tol=1e-7):
                raise ValueError(f"Missing 0.2 s velocity window for seed {seed}")
            sample = trace[index]
            forces = sample["foot_normal_forces_n"]
            if (len(forces) != 4 or not all(math.isfinite(value) for value in forces)
                    or not all(math.isfinite(value) for value in sample["base_pos"])):
                raise ValueError(f"Invalid support state for seed {seed}")
            rows.append({
                "cohort": name,
                "seed": seed,
                "outcome": warned[seed]["outcome"],
                "warning_push_s": warned[seed]["warning_push_s"],
                "base_height_m": sample["base_pos"][2],
                "base_vertical_speed_0p2s_m_s": (
                    sample["base_pos"][2] - trace[prior]["base_pos"][2]
                ) / 0.2,
                "rear_normal_force_n": sum(forces[2:]),
                "front_normal_force_n": sum(forces[:2]),
            })
        manifest = hashlib.sha256("".join(manifest_lines).encode()).hexdigest()
        if manifest != cohort["report_hash_manifest_sha256"]:
            raise ValueError(f"Cohort report hashes differ for {name}")

    success = [row for row in rows if row["outcome"] == "box_settled"]
    failure = [row for row in rows if row["outcome"] == "safety_termination"]
    if len(success) != 4 or len(failure) != 16:
        raise ValueError("Expected four warned successes and sixteen warned failures")
    fields = ("base_height_m", "base_vertical_speed_0p2s_m_s",
              "rear_normal_force_n", "front_normal_force_n")
    ranges = {
        key: {"box_settled": feature_range(success, key),
              "safety_termination": feature_range(failure, key)}
        for key in fields
    }
    overlap = {
        key: max(ranges[key]["box_settled"][0], ranges[key]["safety_termination"][0])
             <= min(ranges[key]["box_settled"][1], ranges[key]["safety_termination"][1])
        for key in fields
    }
    result = {
        "schema_version": 1,
        "scope": "Read-only warned-state feature overlap; no threshold fitting or intervention",
        "analysis_sha256": sha256(Path(__file__)),
        "warning_evidence_sha256": sha256(args.warning_evidence),
        "source_report_hash_manifests": {
            name: expected[name]["report_hash_manifest_sha256"] for name, _, _ in COHORTS
        },
        "warning_cases": len(rows),
        "warned_box_settled": len(success),
        "warned_safety_termination": len(failure),
        "speed_definition": "base z(t)-base z(t-0.2s) divided by 0.2s at the first warning",
        "ranges": ranges,
        "range_overlap": overlap,
        "rows": rows,
        "interpretation": "Each measured feature range overlaps between warned successes and warned failures. No single hard threshold on these features separates this set, and a joint threshold has not been fitted or validated. Warning-time features also cannot by themselves establish a safe recovery action.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in
                      ("warning_cases", "warned_box_settled", "warned_safety_termination",
                       "ranges", "range_overlap")}, indent=2))


if __name__ == "__main__":
    main()
