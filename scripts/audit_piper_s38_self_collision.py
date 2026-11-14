"""Audit the two s38 Isaac self-collision replays against their source runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


CASES = ("s38-m6-f35", "s38-m8-f25")
ASSET = (
    "source/LeggedManip_Lab/LeggedManip_Lab/assets/go2_piper/"
    "go2_piper_articulation_cfg.py"
)
TOGGLE_OFF = b"enabled_self_collisions=False,"
TOGGLE_ON = b"enabled_self_collisions=True,"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def compare_reports(original: dict, replay: dict) -> dict:
    pinned_fields = (
        "task", "seed", "num_envs", "episodes_per_env", "episode_length_s",
        "box_mass", "box_friction", "box_height", "checkpoint_sha256",
        "evaluation_sha256", "evaluation_helpers_sha256", "control_sha256",
        "actor_policy_sha256", "deployment_actor_sha256",
    )
    for field in pinned_fields:
        require(field in original and field in replay and original[field] == replay[field],
                f"Source and replay differ in {field}")
    old_physics, new_physics = original["actual_physics"], replay["actual_physics"]
    old_assets, new_assets = old_physics["robot_asset_sha256"], new_physics["robot_asset_sha256"]
    require(set(old_assets) == set(new_assets) and ASSET in old_assets,
            "Robot asset inventory differs")
    require({key: value for key, value in old_assets.items() if key != ASSET}
            == {key: value for key, value in new_assets.items() if key != ASSET},
            "A robot asset other than the articulation config differs")
    require(old_assets[ASSET] != new_assets[ASSET], "Self-collision asset did not change")
    require({key: value for key, value in old_physics.items() if key != "robot_asset_sha256"}
            == {key: value for key, value in new_physics.items() if key != "robot_asset_sha256"},
            "Actual physics differs outside the asset hash table")

    for label, report, reason in (
        ("original", original, "time_out"), ("replay", replay, "base_contact")
    ):
        require(report["completed_episodes"] == 1 and report["incomplete_episodes"] == 0
                and report["successful_episodes"] == 0 and len(report["terminal_states"]) == 1,
                f"{label} denominator or outcome differs")
        require(report["termination_reasons"][reason] == 1,
                f"{label} termination reason differs")
    terminal = replay["terminal_states"][0]
    require(not terminal["hand_contact_valid"] and replay["push_contact_steps"] == [0.0]
            and terminal["safe_approach_complete"],
            "Replay did not fail after safe approach and before valid hand contact")
    require(all(value == 0.0 for value in terminal["hand_force"]),
            "Replay has a hand-box force at termination")
    ik_distance = terminal["ik_clearance_distance"]
    ik_residual = terminal["ik_clearance_residual"]
    ik_minimum = new_physics["controller_contract"]["ik_clearance_minimum"]
    require(math.isfinite(ik_minimum) and ik_minimum > 0.0
            and math.isfinite(ik_distance) and ik_distance >= ik_minimum
            and math.isfinite(ik_residual) and ik_residual == 0.0
            and replay["termination_reasons"]["arm_body_clearance"] == 0,
            "Reported center-distance proxy did not pass at the self-contact event")
    names = replay["contact_body_names"]
    base_force = terminal["body_contact_forces"][names.index("base")]
    arm_force = terminal["body_contact_forces"][names.index("link6")]
    require(math.dist(base_force, (0.0, 0.0, 0.0)) > 0.5
            and all(math.isclose(a + b, 0.0, abs_tol=1e-5) for a, b in zip(base_force, arm_force)),
            "Replay lacks opposed base/link6 contact force")
    require(terminal["elapsed_seconds"] < original["terminal_states"][0]["elapsed_seconds"],
            "Replay did not terminate before the original")
    return {
        "seed": replay["seed"],
        "checkpoint_sha256": replay["checkpoint_sha256"],
        "articulation_sha256": {"original": old_assets[ASSET], "self_collision_on": new_assets[ASSET]},
        "original_terminal_s": original["terminal_states"][0]["elapsed_seconds"],
        "replay_terminal_s": terminal["elapsed_seconds"],
        "original_box_x_displacement_m": original["terminal_states"][0]["box_displacement"][0],
        "replay_box_x_displacement_m": terminal["box_displacement"][0],
        "replay_base_contact_force_n": base_force,
        "replay_link6_contact_force_n": arm_force,
        "replay_ik_clearance_distance_m": ik_distance,
        "replay_ik_clearance_minimum_m": ik_minimum,
        "replay_ik_clearance_residual_m": ik_residual,
        "replay_arm_body_clearance_terminations": 0,
    }


def audit(source_plan: Path, original_root: Path, replay_root: Path,
          original_asset: Path, replay_asset: Path) -> dict:
    original_bytes, replay_bytes = original_asset.read_bytes(), replay_asset.read_bytes()
    require(original_bytes.count(TOGGLE_OFF) == 1
            and replay_bytes == original_bytes.replace(TOGGLE_OFF, TOGGLE_ON),
            "Articulation file change is not exactly the self-collision toggle")
    source_hash = digest(source_plan)
    plan = load(source_plan)
    planned = {row["case_id"] for row in plan["cases"]}
    require(set(CASES) <= planned, "Source plan does not include both s38 cases")
    records = []
    for case_id in CASES:
        source_file = original_root / case_id / "report.json"
        replay_dir = replay_root / case_id
        replay_file = replay_dir / "report.json"
        run_plan = load(replay_dir / "plan.json")
        status = load(replay_dir / "exit-status.json")
        original_hash, replay_hash = digest(source_file), digest(replay_file)
        require(run_plan["source_plan_sha256"] == source_hash
                and run_plan["source_report_sha256"] == original_hash
                and run_plan["original_asset_sha256"] == digest(original_asset)
                and run_plan["diagnostic_asset_sha256"] == digest(replay_asset),
                f"{case_id} plan provenance differs")
        require(status["returncode"] == 0 and status["report_exists"] is True
                and status["report_sha256"] == replay_hash,
                f"{case_id} replay did not complete with the reported hash")
        original, replay = load(source_file), load(replay_file)
        require(plan["checkpoint_sha256"] == original["checkpoint_sha256"]
                and plan["evaluation_sha256"] == original["evaluation_sha256"]
                and run_plan["checkpoint_sha256"] == replay["checkpoint_sha256"],
                f"{case_id} source or replay differs from the launch plan")
        row = compare_reports(original, replay)
        require(row["articulation_sha256"] == {
            "original": digest(original_asset), "self_collision_on": digest(replay_asset)
        }, f"{case_id} reported asset hash differs from inspected files")
        records.append({"case_id": case_id, "source_report_sha256": original_hash,
                        "replay_report_sha256": replay_hash,
                        "replay_plan_sha256": digest(replay_dir / "plan.json"), **row})
    return {"schema_version": 1, "scope": "Matched-seed Isaac diagnostic, not acceptance",
            "source_plan_sha256": source_hash, "audit_script_sha256": digest(Path(__file__)),
            "contact_authorized": False, "scene_contract_sha256": None,
            "entry_distribution_sha256": None, "records": records}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-plan", type=Path, required=True)
    parser.add_argument("--original-root", type=Path, required=True)
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--original-asset", type=Path, required=True)
    parser.add_argument("--replay-asset", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")
    result = audit(args.source_plan, args.original_root, args.replay_root,
                   args.original_asset, args.replay_asset)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"cases": len(result["records"]), "contact_authorized": False}))


if __name__ == "__main__":
    main()
