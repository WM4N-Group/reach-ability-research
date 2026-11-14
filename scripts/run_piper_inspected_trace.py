"""Replay a frozen Isaac plan while inspecting a different environment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


APPROACH = Path("mujoco/deploy/piper_push_safe_approach.json")
IK = Path("source/LeggedManip_Lab/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/mdp/box_push_ik.py")
CONTROL = IK.with_name("box_push_control.py")
CONFIG = Path("source/LeggedManip_Lab/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/config/go2_piper/box_env_cfg.py")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(path: Path, expected: str) -> None:
    if digest(path) != expected:
        raise ValueError(f"Frozen asset hash mismatch: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-plan", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inspect-env-index", type=int, required=True)
    parser.add_argument("--physical-gpu", type=int, choices=(0, 1), default=1)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--run-prepared", action="store_true")
    args = parser.parse_args()

    source = json.loads(args.source_plan.read_text())
    original = list(source["command"])
    if (original.count("--inspect-env-index") != 1
            or original.count("--output-json") != 1
            or original[original.index("--num_envs") + 1] != "8"
            or original[original.index("--episodes-per-env") + 1] != "1"
            or original[original.index("--episode-length-s") + 1] != "24"
            or not 0 <= args.inspect_env_index < 8):
        raise ValueError("Expected the frozen 8-environment, 24 s inspected plan")

    approach_hash = source.get("candidate_approach_sha256", source.get("approach_sha256"))
    for path, expected in ((args.source_root / APPROACH, approach_hash),
                           (args.source_root / IK, source["ik_sha256"]),
                           (args.source_root / CONTROL, source["push_control_sha256"]),
                           (args.source_root / CONFIG, source["push_config_sha256"]),
                           (Path(original[1]), source["evaluator_sha256"]),
                           (Path(original[original.index("--checkpoint") + 1]),
                            source["checkpoint_sha256"])):
        verify(path, expected)

    command = original.copy()
    command[command.index("--inspect-env-index") + 1] = str(args.inspect_env_index)
    command[command.index("--output-json") + 1] = str(args.output / "report.json")
    plan = {
        "scope": "Frozen seen-seed 24 s diagnostic with changed inspected env only",
        "source_plan_sha256": digest(args.source_plan),
        "source_root": str(args.source_root),
        "source_inspect_env_index": int(original[original.index("--inspect-env-index") + 1]),
        "inspect_env_index": args.inspect_env_index,
        "physical_gpu": args.physical_gpu,
        "approach_sha256": approach_hash,
        "evaluator_sha256": source["evaluator_sha256"],
        "checkpoint_sha256": source["checkpoint_sha256"],
        "command": command,
    }
    if args.prepare_only:
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
        print(json.dumps({"prepared": str(args.output), "plan_sha256": digest(args.output / "plan.json")}))
        return

    if (json.loads((args.output / "plan.json").read_text()) != plan
            or (args.output / "run.log").exists()
            or (args.output / "report.json").exists()):
        raise ValueError("Prepared plan or output state differs")
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(args.physical_gpu)
    geometry_root = command[command.index("--push-geometry-root") + 1]
    env["PYTHONPATH"] = str(args.source_root / "source/LeggedManip_Lab") + ":" + geometry_root
    env["PIPER_SOURCE_ROOT"] = str(args.source_root)
    with (args.output / "run.log").open("x") as log:
        completed = subprocess.run(["timeout", "-k", "15s", "1200s", *command],
                                   cwd=args.source_root, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, check=False)
    report = args.output / "report.json"
    (args.output / "exit-status.json").write_text(json.dumps({
        "returncode": completed.returncode,
        "report_exists": report.is_file(),
        "report_sha256": digest(report) if report.is_file() else None,
    }, indent=2) + "\n")
    if completed.returncode:
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
