"""Run a new seed under an existing, hash-verified precontact contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

import check_piper_arm_precontact_motion as motion
from check_piper_startup import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract-json", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists() or args.seed < 0:
        parser.error("Require a new output path and nonnegative seed")
    source = json.loads(args.contract_json.read_text())
    for path, expected in source["source_sha256"].items():
        if sha256(Path(path)) != expected:
            raise ValueError(f"Source hash mismatch: {path}")
    arguments = dict(source["arguments"])
    arguments["seed"] = args.seed
    arguments["output_json"] = str(args.output_json)
    torch.set_num_threads(1)
    result = motion.run_episode(argparse.Namespace(**arguments))
    report = {"schema_version": 1, "arguments": arguments,
              "source_sha256": {**source["source_sha256"],
                  str(Path(__file__).resolve()): sha256(Path(__file__))}, "result": result,
              "contract_source": str(args.contract_json.resolve()),
              "contract_source_sha256": sha256(args.contract_json)}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"seed": args.seed, "passed": result["passed"],
                      "reason": result["reason"]}, indent=2))


if __name__ == "__main__":
    main()
