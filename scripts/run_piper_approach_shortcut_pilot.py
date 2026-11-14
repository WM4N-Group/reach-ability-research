"""Prepare or run an isolated Isaac pilot for a screened approach shortcut."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


APPROACH = Path("mujoco/deploy/piper_push_safe_approach.json")
IK = Path("source/LeggedManip_Lab/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/mdp/box_push_ik.py")
CONTROL = IK.with_name("box_push_control.py")
CONFIG = Path("source/LeggedManip_Lab/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/config/go2_piper/box_env_cfg.py")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_hash(path: Path, expected: str) -> None:
    if digest(path) != expected:
        raise ValueError(f"Frozen file hash mismatch: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-plan", type=Path, required=True)
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--physical-gpu", type=int, choices=(0, 1), default=1)
    parser.add_argument("--skip-waypoint-index", type=int, choices=range(2, 20))
    parser.add_argument("--edge-start-index", type=int)
    parser.add_argument("--edge-end-index", type=int)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--verify-prepared", action="store_true")
    mode.add_argument("--run-prepared", action="store_true")
    args = parser.parse_args()
    if (args.edge_start_index is None) != (args.edge_end_index is None):
        parser.error("Specify both edge endpoints")
    if args.edge_start_index is not None:
        if (args.skip_waypoint_index is not None
                or not 1 <= args.edge_start_index < args.edge_end_index - 1 < 20):
            parser.error("Use one valid interior edge or a single waypoint index")
        start, end = args.edge_start_index, args.edge_end_index
    else:
        skip = args.skip_waypoint_index if args.skip_waypoint_index is not None else 18
        start, end = skip - 1, skip + 1
    removed = list(range(start + 1, end))
    if args.output.exists() != (args.verify_prepared or args.run_prepared):
        parser.error("Preparation needs a new directory; verification or running needs a prepared directory")

    baseline = json.loads(args.baseline_plan.read_text())
    screen = json.loads(args.screen.read_text())
    if (screen["joint_increment_rad"] > 0.02 or screen["samples_per_stage"] < 100
            or len(screen["cases"]) < 2 or not any(row["plan_sha256"] == digest(args.baseline_plan)
                                                   for row in screen["cases"])):
        raise ValueError("Shortcut needs a full-step screen tied to the frozen baseline")
    result = next((row for row in screen["results"]
                   if row["edge_start_index"] == start and row["edge_end_index"] == end), None)
    if (result is None or not result["static_pass"] or result["sampled_recorded_states"] < 150
            or result["minimum_protected_clearance_m"] < 0.02
            or result["minimum_box_clearance_m"] < 0.01):
        raise ValueError("Shortcut fails the recorded-state static gates")

    source = Path(baseline["source_root"])
    evaluator_source = Path(baseline["command"][1])
    for relative, key in ((APPROACH, "approach_sha256"), (IK, "ik_sha256"),
                          (CONTROL, "push_control_sha256"), (CONFIG, "push_config_sha256")):
        require_hash(source / relative, baseline[key])
    require_hash(evaluator_source, baseline["evaluator_sha256"])
    command = list(baseline["command"])
    checkpoint = Path(command[command.index("--checkpoint") + 1])
    require_hash(checkpoint, baseline["checkpoint_sha256"])
    if screen["approach_sha256"] != baseline["approach_sha256"]:
        raise ValueError("The screened and evaluated approach assets differ")

    approach = json.loads((source / APPROACH).read_text())
    if len(approach["waypoints"]) != 21:
        raise ValueError("Expected the frozen 21-waypoint approach")
    candidate = dict(approach)
    candidate["waypoints"] = approach["waypoints"][:start + 1] + approach["waypoints"][end:]
    candidate["purpose"] = ("Isolated one-waypoint shortcut diagnostic; dynamic safety unverified"
                            if len(removed) == 1 else
                            "Isolated approach shortcut diagnostic; dynamic safety unverified")
    train = args.output / "isolated/train"
    evaluator = args.output / "isolated/evaluator"
    if args.verify_prepared or args.run_prepared:
        experiment = json.loads((args.output / "plan.json").read_text())
        if (experiment["source_plan_sha256"] != digest(args.baseline_plan)
                or experiment["screen_sha256"] != digest(args.screen)
                or experiment["physical_gpu"] != args.physical_gpu
                or experiment.get("removed_waypoint_indices",
                                  [experiment.get("removed_waypoint_index")]) != removed
                or experiment.get("edge_start_index", start) != start
                or experiment.get("edge_end_index", end) != end
                or (args.output / "report.json").exists() or (args.output / "run.log").exists()):
            raise ValueError("Prepared run provenance or output state differs from this request")
        command = experiment["command"]
        if (command[1] != str(evaluator / "scripts/evaluate_box_skills.py")
                or command[command.index("--output-json") + 1] != str(args.output / "report.json")):
            raise ValueError("Prepared evaluator or report path differs from this output")
        for path, key in ((train / APPROACH, "candidate_approach_sha256"),
                          (evaluator / "scripts/evaluate_box_skills.py", "evaluator_sha256"),
                          (train / IK, "ik_sha256"), (train / CONTROL, "push_control_sha256"),
                          (train / CONFIG, "push_config_sha256")):
            require_hash(path, experiment[key])
        if json.loads((train / APPROACH).read_text()) != candidate or experiment["screen_result"] != result:
            raise ValueError("Prepared candidate differs from the screened shortcut")
        if args.verify_prepared:
            print(json.dumps({"verified": str(args.output), "candidate_approach_sha256": experiment["candidate_approach_sha256"]}))
            return
    else:
        args.output.mkdir(parents=True)
        shutil.copytree(source, train)
        shutil.copytree(evaluator_source.parents[1], evaluator)
        (train / APPROACH).write_text(json.dumps(candidate, indent=2) + "\n")

        command[1] = str(evaluator / "scripts/evaluate_box_skills.py")
        command[command.index("--output-json") + 1] = str(args.output / "report.json")
        experiment = {
            "scope": "Seen-seed 24 s isolated Isaac path pilot; not acceptance or NAV handoff",
            "source_plan_sha256": digest(args.baseline_plan),
            "screen_sha256": digest(args.screen),
            "source_approach_sha256": baseline["approach_sha256"],
            "candidate_approach_sha256": digest(train / APPROACH),
            "removed_waypoint_index": removed[0] if len(removed) == 1 else None,
            "removed_waypoint_indices": removed,
            "edge_start_index": start,
            "edge_end_index": end,
            "screen_result": result,
            "checkpoint_sha256": baseline["checkpoint_sha256"],
            "evaluator_sha256": digest(Path(command[1])),
            "ik_sha256": digest(train / IK),
            "push_control_sha256": digest(train / CONTROL),
            "push_config_sha256": digest(train / CONFIG),
            "physical_gpu": args.physical_gpu,
            "command": command,
        }
        (args.output / "plan.json").write_text(json.dumps(experiment, indent=2) + "\n")
        if args.prepare_only:
            print(json.dumps({"prepared": str(args.output), "candidate_approach_sha256": experiment["candidate_approach_sha256"]}))
            return

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(args.physical_gpu)
    geometry_root = command[command.index("--push-geometry-root") + 1]
    env["PYTHONPATH"] = str(train / "source/LeggedManip_Lab") + ":" + geometry_root
    env["PIPER_SOURCE_ROOT"] = str(train)
    with (args.output / "run.log").open("x") as log:
        completed = subprocess.run(["timeout", "-k", "15s", "1200s", *command], cwd=train,
                                   env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
    report = args.output / "report.json"
    (args.output / "exit-status.json").write_text(json.dumps({
        "returncode": completed.returncode, "report_exists": report.is_file(),
        "report_sha256": digest(report) if report.is_file() else None,
    }, indent=2) + "\n")
    if completed.returncode:
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
