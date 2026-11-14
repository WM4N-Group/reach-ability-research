"""Verify read-only base contact filters against known-state Isaac reports."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path


EXPECTED_SHA256 = {
    5201: {
        "baseline": "ef72841ca7700e1ca1d369ad50b4e4149c8e0441bb651497358c5b9efad8ab0c",
        "source": "9fcf7fef65ac62c650c80dc41bd09d0115c227b77f605e0e2f52ca6e6ecd9e37",
    },
    5124: {
        "baseline": "b541f293014ddebe8425a68a6662ae9e837702a9491bfc2f8009b15218353944",
        "source": "8a44073e44709c03a388af1cb4f1d4ac040c3f1d06e16d629c0be5a50f4c6c91",
    },
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path, seed, kind):
    digest = sha256(path)
    if digest != EXPECTED_SHA256[seed][kind]:
        raise ValueError(f"Unexpected seed{seed} {kind} hash: {digest}")
    with path.open(encoding="utf-8") as stream:
        report = json.load(stream)
    if report["seed"] != seed or len(report["support_trace"]) != report["push_executed_steps"]:
        raise ValueError(f"Unexpected seed{seed} {kind} report layout")
    return report, digest


def legacy_projection(report):
    result = copy.deepcopy(report)
    result.pop("schema_version")
    result.pop("record_base_contact_source")
    for sample in result["support_trace"]:
        sample.pop("base_contact_source")
    result["terminal"]["support_snapshot"].pop("base_contact_source")
    return result


def norm(vector):
    return math.sqrt(sum(value * value for value in vector))


def inspect(seed, baseline_path, source_path):
    baseline, baseline_hash = load(baseline_path, seed, "baseline")
    source, source_hash = load(source_path, seed, "source")
    old = copy.deepcopy(baseline)
    old.pop("schema_version")
    if old != legacy_projection(source):
        raise ValueError(f"Seed{seed} legacy trajectory changed")
    if source["schema_version"] != 14 or not source["record_base_contact_source"]:
        raise ValueError(f"Seed{seed} lacks base source telemetry")
    source_samples = [sample["base_contact_source"] for sample in source["support_trace"]]
    residuals = []
    box_forces = []
    ground_forces = []
    valid_ground_points = 0
    first_contact_s = None
    for sample, contact in zip(source["support_trace"], source_samples):
        net = contact["net_force_w"]
        ground = contact["filtered"]["ground"]["force_w"]
        box = contact["filtered"]["box"]["force_w"]
        if len(net) != 3 or len(ground) != 3 or len(box) != 3:
            raise ValueError(f"Invalid seed{seed} force vector layout")
        if not all(math.isfinite(value) for value in net + ground + box):
            raise ValueError(f"Non-finite seed{seed} force")
        residuals.append(max(abs(net[index] - ground[index] - box[index]) for index in range(3)))
        ground_forces.append(norm(ground))
        box_forces.append(norm(box))
        if norm(ground) > 0.5:
            point = contact["filtered"]["ground"]["contact_pos"]
            if point is None or not all(math.isfinite(value) for value in point):
                raise ValueError(f"Missing seed{seed} ground point under load")
            valid_ground_points += 1
        if norm(net) > 0.5 and first_contact_s is None:
            first_contact_s = sample["push_elapsed_s"]
    if max(residuals) > 1e-3 or max(box_forces) > 1e-3:
        raise ValueError(f"Seed{seed} filters do not account for the base force")
    terminal_source = source["terminal"]["support_snapshot"]["base_contact_source"]
    if terminal_source != source_samples[-1]:
        raise ValueError(f"Seed{seed} pre-reset terminal sensor snapshot differs")
    reasons = source["terminal"]["reasons"]
    if ((seed == 5201 and (not reasons["base_contact"] or first_contact_s != 5.82))
            or (seed == 5124 and (not reasons["box_settled"] or first_contact_s is not None))):
        raise ValueError(f"Seed{seed} outcome differs from frozen baseline")
    return {
        "seed": seed,
        "baseline_sha256": baseline_hash,
        "source_sha256": source_hash,
        "legacy_fields_and_samples_equal": True,
        "push_executed_steps": source["push_executed_steps"],
        "terminal_reasons": reasons,
        "first_base_contact_gt_0p5n_s": first_contact_s,
        "ground_loaded_samples_gt_0p5n": valid_ground_points,
        "maximum_net_minus_ground_minus_box_force_component_n": max(residuals),
        "maximum_ground_force_norm_n": max(ground_forces),
        "maximum_box_force_norm_n": max(box_forces),
        "terminal_base_contact_source": terminal_source,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for seed in (5201, 5124):
        parser.add_argument(f"--baseline-{seed}", type=Path, required=True)
        parser.add_argument(f"--source-{seed}", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")
    results = [inspect(seed, getattr(args, f"baseline_{seed}"), getattr(args, f"source_{seed}"))
               for seed in (5201, 5124)]
    report = {
        "schema_version": 1,
        "scope": "Read-only known-state base contact source; filtered force is not an actuator or safety certificate",
        "analysis_sha256": sha256(Path(__file__)),
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
