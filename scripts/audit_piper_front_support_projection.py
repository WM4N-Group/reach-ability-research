"""Audit fore-aft COM projection against loaded foot contacts in archived Isaac runs."""

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def margin(record, names):
    w, x, y, z = record["base_quat"]
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    forward = (math.cos(yaw), math.sin(yaw))
    contacts = []
    for index, name in enumerate(names):
        force = record["foot_normal_forces_n"][index]
        ground = record["ground_contacts"][name]
        if not math.isfinite(force) or abs(force - ground["ground_normal_force"][2]) >= 1e-3:
            raise ValueError(f"Unqualified ground force for {name}")
        if force > 2.0:
            point = ground["ground_contact_pos"]
            if point is None or not all(math.isfinite(value) for value in point):
                raise ValueError(f"Missing loaded ground contact point for {name}")
            contacts.append(point)
    if not contacts:
        return None
    com = record["robot_com_pos"]
    if not all(math.isfinite(value) for value in (*forward, *com[:2])):
        raise ValueError("Non-finite COM or base heading")
    return max(sum(point[i] * forward[i] for i in range(2)) for point in contacts) - sum(
        com[i] * forward[i] for i in range(2)
    )


def describe(report):
    trace = report["support_trace"]
    names = report["support_foot_body_names"]
    if (set(names) != {"FL_foot", "FR_foot", "RL_foot", "RR_foot"}
            or len(trace) != report["push_executed_steps"]
            or abs(report["step_dt"] - 0.02) > 1e-9):
        raise ValueError(f"Unexpected support trace for seed {report['seed']}")
    first_negative = None
    longest_negative_steps = 0
    negative_steps = 0
    run = 0
    minimum = None
    missing = 0
    for index, record in enumerate(trace):
        if abs(record["push_elapsed_s"] - (index + 1) * report["step_dt"]) > 1e-8:
            raise ValueError(f"Unexpected PUSH time for seed {report['seed']}")
        value = margin(record, names)
        if value is None:
            missing += 1
            run = 0
            continue
        minimum = value if minimum is None else min(minimum, value)
        if value < 0:
            negative_steps += 1
            run += 1
            longest_negative_steps = max(longest_negative_steps, run)
            if first_negative is None:
                first_negative = record["push_elapsed_s"]
        else:
            run = 0
    return {
        "first_negative_s": first_negative,
        "minimum_margin_m": minimum,
        "negative_steps": negative_steps,
        "longest_consecutive_negative_steps": longest_negative_steps,
        "samples_without_loaded_contact": missing,
        "lead_to_terminal_s": report["push_elapsed_s"] - first_negative if first_negative is not None else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--manifest-json", type=Path, required=True)
    parser.add_argument("--reports-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")
    protocol = json.loads(args.protocol_json.read_text(encoding="utf-8"))
    if sha256(args.manifest_json) != protocol["manifest_sha256"]:
        raise ValueError("Frozen 80-run manifest hash mismatch")
    manifest = json.loads(args.manifest_json.read_text(encoding="utf-8"))
    if (len(manifest["cases"]) != protocol["total_runs"]
            or manifest["qualified_push_traces"] != protocol["expected_qualified_push_traces"]):
        raise ValueError("Unexpected retrospective cohort denominator")
    cases = []
    for entry in manifest["cases"]:
        seed = entry["seed"]
        directory = protocol["cohorts"][entry["cohort"]]
        path = args.reports_root / directory / f"seed{seed}-baseline.json"
        digest = sha256(path)
        if digest != entry["report_sha256"]:
            raise ValueError(f"Archived seed{seed} report hash mismatch")
        report = json.loads(path.read_text(encoding="utf-8"))
        if (report["seed"] != seed or report["push_elapsed_s"] != entry["push_elapsed_s"]
                or not report["record_push_support_trace"]
                or (report["push_executed_steps"] > 0 and not report["record_push_contact_load_trace"])):
            raise ValueError(f"Unexpected seed{seed} trace contract")
        projection = describe(report) if report["push_executed_steps"] else None
        cases.append({"seed": seed, "cohort": entry["cohort"], "outcome": entry["outcome"],
                      "report_sha256": digest, "projection": projection})
    if len({case["seed"] for case in cases}) != protocol["total_runs"]:
        raise ValueError("Duplicate or missing seeds")
    summary = {}
    for outcome in sorted({case["outcome"] for case in cases}):
        group = [case for case in cases if case["outcome"] == outcome]
        observed = [case for case in group if case["projection"] is not None]
        summary[outcome] = {
            "runs": len(group),
            "push_traces": len(observed),
            "any_negative": sum(case["projection"]["first_negative_s"] is not None for case in observed),
            "negative_at_least_five_consecutive_steps": sum(
                case["projection"]["longest_consecutive_negative_steps"] >= 5 for case in observed
            ),
        }
    report = {
        "schema_version": 1,
        "scope": protocol["interpretation"],
        "analysis_sha256": sha256(Path(__file__)),
        "protocol_sha256": sha256(args.protocol_json),
        "manifest_sha256": sha256(args.manifest_json),
        "total_runs": len(cases),
        "push_traces": sum(case["projection"] is not None for case in cases),
        "outcomes": dict(Counter(case["outcome"] for case in cases)),
        "summary": summary,
        "cases": cases,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
