"""Estimate signed and even pulse response from two archived Isaac states."""

import argparse
import hashlib
import json
from pathlib import Path

from analyze_piper_front_foot_response import pitch


BASELINE_SHA256 = {
    5201: "9fcf7fef65ac62c650c80dc41bd09d0115c227b77f605e0e2f52ca6e6ecd9e37",
    5124: "8a44073e44709c03a388af1cb4f1d4ac040c3f1d06e16d629c0be5a50f4c6c91",
}
PROBE_SHA256 = {
    (5201, "up"): "6c8fe0dee6fb0d9bdd60695f637dae81738a10abd114c780f0a4f4aeefa4db6e",
    (5201, "down"): "af8ba4fc01b4f3720e0abc6ccf6ca9929a754b58e41dc30631b2d46fff766513",
    (5124, "up"): "c9aa02c9c9afb8119725cc75719164fc14cfabbfc8ac38d3531602e54044c22d",
    (5124, "down"): "36a31234a572efd082102d80742c37fdf8070f9dae2296ab951c10facf9d61e3",
}
TIMES_S = (4.40, 4.60, 4.80, 5.00, 5.20, 5.40, 5.60)


def load(path, expected):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise ValueError(f"Unexpected report hash: {path} {digest}")
    return json.loads(path.read_text(encoding="utf-8"))


def values(record):
    forces = record["foot_normal_forces_n"]
    return {
        "base_height_m": record["base_pos"][2],
        "base_pitch_rad": pitch(record["base_quat"]),
        "front_foot_height_relative_to_base_m": sum(
            record["foot_body_pos"][index][2] - record["base_pos"][2] for index in (0, 1)
        ) / 2,
        "front_normal_force_n": sum(forces[:2]),
        "rear_normal_force_n": sum(forces[2:]),
    }


def decompose(baseline, up, down):
    return {
        key: {
            "baseline": baseline[key],
            "up_minus_baseline": up[key] - baseline[key],
            "down_minus_baseline": down[key] - baseline[key],
            "odd_half_difference": (up[key] - down[key]) / 2,
            "even_remainder": (up[key] + down[key]) / 2 - baseline[key],
        }
        for key in baseline
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--probe-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    results = []
    for seed in (5201, 5124):
        baseline = load(args.baseline_dir / f"seed{seed}-base-contact-source.json",
                        BASELINE_SHA256[seed])
        probes = {
            direction: load(args.probe_dir / f"seed{seed}-front-{direction}.json",
                            PROBE_SHA256[(seed, direction)])
            for direction in ("up", "down")
        }
        if any(probe["handoff"] != baseline["handoff"] for probe in probes.values()):
            raise ValueError(f"Seed{seed} handoff differs")
        samples = []
        for time in TIMES_S:
            index = round(time / 0.02) - 1
            records = [run["support_trace"][index] for run in (baseline, probes["up"], probes["down"])]
            if any(abs(record["push_elapsed_s"] - time) > 1e-8 for record in records):
                raise ValueError(f"Seed{seed} sample time differs at {time}")
            samples.append({
                "push_elapsed_s": time,
                "response": decompose(*(values(record) for record in records)),
            })
        results.append({"seed": seed, "samples": samples})
    report = {
        "schema_version": 1,
        "scope": "Exploratory local odd/even decomposition at previously observed states; no fitted dynamics, uncertainty bound or viability certificate",
        "pulse_command_half_amplitude_m": 0.005,
        "odd_gain_definition": "odd_half_difference divided by 0.005 m; output units per commanded target metre",
        "analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs_sha256": {str(seed): {
            "baseline": BASELINE_SHA256[seed],
            **{direction: PROBE_SHA256[(seed, direction)] for direction in ("up", "down")},
        } for seed in (5201, 5124)},
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps(results, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
