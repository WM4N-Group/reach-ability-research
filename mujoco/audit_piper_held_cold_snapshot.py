"""Audit model provenance and physical-state loading without replaying NAV."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np

from check_piper_startup import sha256
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.piper_robot_profile import PROFILE_PATH
from reconfigurable_navigation.reachability.scenes import (
    make_movable_box_navigation_runtime,
    make_static_box_navigation_runtime,
)


def _rebuild_runtime(arguments: dict):
    make_runtime = (
        make_movable_box_navigation_runtime
        if arguments["box_mode"] == "movable"
        else make_static_box_navigation_runtime
    )
    return make_runtime(
        seed=arguments["seed"],
        box_position=np.asarray(arguments["static_box_position"], dtype=np.float64),
        box_size=np.asarray(arguments["static_box_size"], dtype=np.float64),
        box_yaw=arguments["static_box_yaw"],
        config_path=DEPLOY / (
            "config_wbc.yaml" if arguments["locomotion_policy"] == "wbc" else "config.yaml"
        ),
        physics_substeps=arguments["physics_substeps"],
        **({"box_mass": arguments["box_mass"]} if arguments["box_mode"] == "movable" else {}),
    )


def _compiled_model_sha256(model: mujoco.MjModel) -> str:
    model_bytes = np.empty(mujoco.mj_sizeModel(model), dtype=np.uint8)
    mujoco.mj_saveModel(model, buffer=model_bytes)
    return hashlib.sha256(model_bytes.tobytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text())
    if sha256(Path(__file__)) != protocol["auditor_sha256"]:
        raise ValueError("Cold snapshot auditor changed")
    rows = []
    for source in protocol["reports"]:
        path = Path(source["path"])
        if sha256(path) != source["sha256"]:
            raise ValueError(f"Source report changed: {path}")
        report = json.loads(path.read_text())
        arguments = report["arguments"]
        result = report["result"]
        event = result["motion"]["target_step_event"]
        if (report["seed"] != source["seed"] or report["phase"] != "baseline"
                or event is None or event["applied"]
                or event["closed_loop_state_v2"]["schema_version"] != 2):
            raise ValueError(f"Invalid baseline snapshot: {path}")
        runtime = _rebuild_runtime(arguments)
        state = event["closed_loop_state_v2"]
        state_type = mujoco.mjtState.mjSTATE_INTEGRATION
        state_vector = np.asarray(state["mujoco_integration_state"], dtype=np.float64)
        if (state["mujoco_integration_state_spec"] != int(state_type)
                or state_vector.shape != (mujoco.mj_stateSize(runtime.model, state_type),)):
            raise ValueError(f"MuJoCo state specification mismatch: {path}")
        mujoco.mj_setState(runtime.model, runtime.data, state_vector, state_type)
        mujoco.mj_forward(runtime.model, runtime.data)
        restored = np.empty_like(state_vector)
        mujoco.mj_getState(runtime.model, runtime.data, restored, state_type)
        runtime.history.clear()
        runtime.history.extend(
            np.asarray(frame, dtype=np.float32) for frame in state["policy_observation_history"]
        )
        runtime.last_action[:] = state["last_action"]
        runtime.velocity_command[:] = state["velocity_command"]
        runtime.ee_command[:] = state["ee_command"]
        hashes_match = bool(
            sha256(runtime.policy_path) == result["policy_sha256"]
            and sha256(runtime.config_path) == result["config_sha256"]
            and sha256(PROFILE_PATH) == result["profile_sha256"]
        )
        rows.append({
            "seed": source["seed"],
            "report_sha256": source["sha256"],
            "compiled_model_sha256": _compiled_model_sha256(runtime.model),
            "scene_xml_sha256": sha256(runtime.scene_path),
            "mujoco_version": mujoco.__version__,
            "model_state_size": len(state_vector),
            "integration_state_exact_after_forward": bool(np.array_equal(state_vector, restored)),
            "policy_config_profile_hashes_match": hashes_match,
            "policy_observation_sha256": hashlib.sha256(runtime.observation().tobytes()).hexdigest(),
        })
    output = {
        "schema_version": 1,
        "scope": "New runtime and MjData load physical state without NAV prefix; no WBC suffix execution",
        "protocol_sha256": sha256(args.protocol_json),
        "auditor_sha256": sha256(Path(__file__)),
        "model_hash_agrees_across_seeds": len({row["compiled_model_sha256"] for row in rows}) == 1,
        "all_physical_loads_exact": all(
            row["integration_state_exact_after_forward"] and row["policy_config_profile_hashes_match"]
            for row in rows
        ),
        "cold_continuation_ready": False,
        "missing_snapshot_context": [
            "candidate_joint_solution",
            "arm_target_box_pose_and_planned_base_pose",
            "full_monitor_clearance_results_and_stage",
            "prior_hold_events_and_report_accumulators",
        ],
        "rows": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({
        "model_hash_agrees_across_seeds": output["model_hash_agrees_across_seeds"],
        "all_physical_loads_exact": output["all_physical_loads_exact"],
        "cold_continuation_ready": False,
    }))


if __name__ == "__main__":
    main()
