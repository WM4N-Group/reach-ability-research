"""Rank position-IK starts on recorded precontact snapshots, without dynamics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np
import torch

from check_piper_arm_precontact_motion import (
    CONTROL,
    DEPLOY,
    PROFILE_PATH,
    STATIC_BOX_BODY,
    PiperArmClearanceChecker,
    PiperPositionReachabilityOracle,
    PiperQuasiStaticSupportChecker,
    PiperSelfClearanceChecker,
    ReachabilityQuery,
    batch,
    hand_point_parameters,
    make_movable_box_navigation_runtime,
    make_static_box_navigation_runtime,
    sha256,
    _hand_position,
)
from reconfigurable_navigation.reachability.box_state import BoxStateReader
from reconfigurable_navigation.reachability.clearance import ARM_BODY_NAMES
from reconfigurable_navigation.reachability.contact_geometry import (
    PiperContactGeometryReader,
    native_push_orientation,
)


class SnapshotSearch:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        with path.open() as source:
            report = json.load(source)
        for source_path, expected in report["source_sha256"].items():
            if sha256(Path(source_path)) != expected:
                raise ValueError(f"Source hash mismatch: {source_path}")
        self.result = report["result"]
        scene = self.result["scene"]
        self.hand_point = self.result["candidate"].get("hand_point", {}).get("mode", "legacy-proxy")
        self.hand_body, self.hand_offset = hand_point_parameters(self.hand_point)
        orientation = self.result["candidate"].get("target_orientation_world")
        self.target_orientation = np.asarray(orientation) if orientation is not None else None
        movable = scene.get("box_mode", "static") == "movable"
        factory = make_movable_box_navigation_runtime if movable else make_static_box_navigation_runtime
        self.runtime = factory(
            seed=self.result["seed"],
            box_position=np.asarray(scene.get("requested_box_position", scene["box_position"])),
            box_size=np.asarray(scene["box_size"]),
            box_yaw=scene.get("requested_box_yaw", scene["box_yaw"]),
            config_path=DEPLOY / (
                "config_wbc.yaml" if self.result["locomotion_policy"] == "wbc"
                else "config.yaml"
            ),
            physics_substeps=self.result.get("simulation", {}).get("physics_substeps", 1),
            **({"box_mass": scene["box_mass"]} if movable else {}),
        )
        for field, asset in (
            ("policy_sha256", self.runtime.policy_path),
            ("config_sha256", self.runtime.config_path),
            ("profile_sha256", PROFILE_PATH),
        ):
            if sha256(asset) != self.result[field]:
                raise ValueError(f"Asset hash mismatch: {field}")
        state = self.result["candidate"]["precontact_state"]
        if state is None:
            raise ValueError(f"Missing precontact state: {path}")
        for field in ("qpos", "qvel", "ctrl"):
            values = np.asarray(state[field], dtype=np.float64)
            destination = getattr(self.runtime.data, field)
            if values.shape != destination.shape or not np.isfinite(values).all():
                raise ValueError(f"Invalid snapshot {field}: {path}")
            destination[:] = values
        self.runtime.data.time = state["time"]
        mujoco.mj_forward(self.runtime.model, self.runtime.data)
        self.oracle = PiperPositionReachabilityOracle(self.runtime)
        self.self_checker = PiperSelfClearanceChecker(self.runtime)
        self.environment_checker = PiperArmClearanceChecker(
            self.runtime, protected_body_names=frozenset({STATIC_BOX_BODY})
        )
        self.contact_geometry_reader = PiperContactGeometryReader(self.runtime)
        finger_bodies = self.contact_geometry_reader.region.hand_bodies
        self.finger_environment_checker = PiperArmClearanceChecker(
            self.runtime,
            protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=finger_bodies,
        )
        self.nonhand_environment_checker = PiperArmClearanceChecker(
            self.runtime,
            protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=ARM_BODY_NAMES - finger_bodies,
        )
        self.support_checker = PiperQuasiStaticSupportChecker(self.runtime)
        self.base = np.asarray(self.result["nav"]["actual_base_pose"])
        self.starting_arm = self.runtime.data.qpos[
            self.runtime.joint_qpos_adr[12:]
        ].copy()
        cosine, sine = np.cos(scene["box_yaw"]), np.sin(scene["box_yaw"])
        self.rotation = np.array(
            [[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]]
        )
        self.box_position = np.asarray(scene["box_position"])
        if movable:
            box_state = BoxStateReader(self.runtime).read()
            self.box_position = box_state.position
            self.rotation = box_state.rotation
        self.thresholds = self.result["thresholds"]

    def evaluate(
        self, initial: np.ndarray, target_local: np.ndarray, samples: int,
        *, from_held_pose: bool = False,
        diagnose_designated_hand_approach: bool = False,
    ) -> dict[str, object]:
        if from_held_pose and not getattr(self, "final_state_active", False):
            raise ValueError(f"Complete final state must be activated: {self.path}")
        target_world = self.box_position + self.rotation @ target_local
        query = ReachabilityQuery(self.base, target_world)
        candidate = self.oracle.solve(
            query, initial_joint_positions=initial,
            hand_offset=self.hand_offset if self.hand_point == "legacy-proxy" else None,
            target_quaternion=self.target_orientation,
        )
        result = {
            "snapshot": str(self.path),
            "hand_point": self.hand_point,
            "kinematic_feasible": bool(candidate.kinematic_feasible),
            "position_error": candidate.position_error,
            "orientation_error": candidate.orientation_error,
            "joint_limit_margin": candidate.joint_limit_margin,
            "joint_solution": candidate.joint_solution.tolist(),
            "passed": False,
        }
        if not candidate.kinematic_feasible:
            return result
        hand_local = self.rotation.T @ (
            self.oracle.hand_position(
                query, candidate.joint_solution, body_name=self.hand_body, offset=self.hand_offset
            )
            - self.box_position
        )
        gate_passed = bool(
            CONTROL["side_approach_ready"](
                batch(hand_local), self.result["scene"]["box_size"][0] / 2.0,
                self.thresholds["push_approach_distance"],
            )[0]
        ) and bool(abs(hand_local[2]) < 0.06)
        minimum_self = float("inf")
        minimum_environment = float("inf")
        minimum_finger_environment = float("inf")
        minimum_nonhand_environment = float("inf")
        minimum_support = float("inf")
        starting_arm = np.asarray(self.starting_arm, dtype=np.float64)
        if starting_arm.shape != (6,) or not np.isfinite(starting_arm).all():
            raise ValueError(f"Missing valid final arm positions: {self.path}")
        if from_held_pose and not np.allclose(
            starting_arm, self.result["motion"]["final_joint_position"], rtol=0, atol=1e-10,
        ):
            raise ValueError(f"Final arm replay mismatch: {self.path}")
        for fraction in np.linspace(0.0, 1.0, samples):
            arm = starting_arm + fraction * (
                candidate.joint_solution - starting_arm
            )
            own = self.self_checker.evaluate(self.base, arm, required_clearance=0.0)
            environment = self.environment_checker.evaluate(
                self.base, arm, required_clearance=0.0
            )
            if diagnose_designated_hand_approach:
                finger_environment = self.finger_environment_checker.evaluate(
                    self.base, arm, required_clearance=0.0
                )
                nonhand_environment = self.nonhand_environment_checker.evaluate(
                    self.base, arm, required_clearance=0.0
                )
                minimum_finger_environment = min(
                    minimum_finger_environment, finger_environment.minimum_clearance
                )
                minimum_nonhand_environment = min(
                    minimum_nonhand_environment, nonhand_environment.minimum_clearance
                )
            support = self.support_checker.evaluate_configuration(
                self.base, arm, required_margin=0.0
            )
            minimum_self = min(minimum_self, own.minimum_clearance)
            minimum_environment = min(minimum_environment, environment.minimum_clearance)
            minimum_support = min(minimum_support, support.support_margin)
        clearance_margin = min(
            minimum_self - self.thresholds["self_clearance"],
            minimum_environment - self.thresholds["environment_clearance"],
        )
        self_motion_bound = self.self_checker.linear_path_sampling_motion_bound(
            starting_arm, candidate.joint_solution, samples=samples
        )
        environment_motion_bound = self.environment_checker.linear_path_sampling_motion_bound(
            starting_arm, candidate.joint_solution, samples=samples
        )
        continuous_self_lower_bound = minimum_self - self_motion_bound
        continuous_environment_lower_bound = minimum_environment - environment_motion_bound
        designated_hand_approach = None
        designated_hand_approach_passed = False
        selected_clearance_margin = min(
            continuous_self_lower_bound - self.thresholds["self_clearance"],
            continuous_environment_lower_bound - self.thresholds["environment_clearance"],
        )
        if diagnose_designated_hand_approach:
            finger_motion_bound = self.finger_environment_checker.linear_path_sampling_motion_bound(
                starting_arm, candidate.joint_solution, samples=samples
            )
            nonhand_motion_bound = self.nonhand_environment_checker.linear_path_sampling_motion_bound(
                starting_arm, candidate.joint_solution, samples=samples
            )
            continuous_finger_lower_bound = minimum_finger_environment - finger_motion_bound
            continuous_nonhand_lower_bound = minimum_nonhand_environment - nonhand_motion_bound
            contact_geometry = self._read_contact_geometry(candidate.joint_solution)
            fingers = contact_geometry["fingers"]
            designated_face_ready = bool(fingers) and all(
                finger["separated_witnesses_valid"]
                and finger["box_point_in_front_region"]
                for finger in fingers
            )
            contact_free = not contact_geometry["contact_samples"]
            designated_hand_approach_passed = bool(
                designated_face_ready
                and contact_free
                and continuous_finger_lower_bound >= 0.0
                and continuous_nonhand_lower_bound >= self.thresholds["environment_clearance"]
            )
            selected_clearance_margin = min(
                continuous_self_lower_bound - self.thresholds["self_clearance"],
                continuous_nonhand_lower_bound - self.thresholds["environment_clearance"],
                continuous_finger_lower_bound,
            )
            designated_hand_approach = {
                "scope": "Static designated-finger approach diagnosis; no contact execution permission",
                "contact_execution_enabled": False,
                "minimum_finger_clearance": minimum_finger_environment,
                "minimum_nonhand_environment_clearance": minimum_nonhand_environment,
                "continuous_finger_clearance_lower_bound": continuous_finger_lower_bound,
                "continuous_nonhand_environment_clearance_lower_bound": continuous_nonhand_lower_bound,
                "minimum_clearance_margin": selected_clearance_margin,
                "designated_face_ready": designated_face_ready,
                "contact_free": contact_free,
                "fingers": fingers,
                "passed": designated_hand_approach_passed,
            }
        legacy_clearance_passed = bool(
            clearance_margin >= 0.0
            and (not from_held_pose or (
                continuous_self_lower_bound >= self.thresholds["self_clearance"]
                and continuous_environment_lower_bound >= self.thresholds["environment_clearance"]
            ))
        )
        selected_clearance_passed = (
            bool(
                minimum_self >= self.thresholds["self_clearance"]
                and continuous_self_lower_bound >= self.thresholds["self_clearance"]
                and designated_hand_approach_passed
            )
            if diagnose_designated_hand_approach else legacy_clearance_passed
        )
        result.update(
            path_start="measured_terminal_state" if from_held_pose else "nav_snapshot",
            hand_local=hand_local.tolist(),
            hand_gate_passed=gate_passed,
            minimum_self_clearance=minimum_self,
            minimum_environment_clearance=minimum_environment,
            minimum_support_margin=minimum_support,
            minimum_clearance_margin=clearance_margin,
            selected_clearance_margin=selected_clearance_margin,
            continuous_self_clearance_lower_bound=continuous_self_lower_bound,
            continuous_environment_clearance_lower_bound=continuous_environment_lower_bound,
            continuous_clearance_passed=bool(
                continuous_self_lower_bound >= self.thresholds["self_clearance"]
                and continuous_environment_lower_bound >= self.thresholds["environment_clearance"]
            ),
            designated_hand_approach=designated_hand_approach,
            passed=bool(
                gate_passed and selected_clearance_passed
                and minimum_support >= self.thresholds["quasistatic_support_margin"]
                and candidate.joint_limit_margin >= self.thresholds["joint_limit_margin"]
            ),
        )
        return result

    def _read_contact_geometry(self, arm_joint_positions: np.ndarray) -> dict[str, object]:
        saved_state = self.oracle._save_state()
        try:
            self.oracle._set_query_state(
                ReachabilityQuery(self.base, self.box_position), arm_joint_positions
            )
            return self.contact_geometry_reader.read()
        finally:
            self.oracle._restore_state(*saved_state)

    def verify_baseline(self) -> None:
        candidate = self.result["candidate"]
        original = candidate["static_path"]
        actual = self.evaluate(
            np.asarray(candidate["ik_initial"]),
            np.asarray(candidate["target_local"]),
            original["samples"] if original is not None else 2,
        )
        if actual["kinematic_feasible"] != candidate["kinematic_feasible"] or not np.allclose(
            actual["joint_solution"], candidate["joint_solution"], rtol=0.0, atol=1e-10
        ):
            raise ValueError(f"Baseline IK replay mismatch: {self.path}")
        if original is None:
            return
        for field in (
            "minimum_self_clearance", "minimum_environment_clearance",
            "minimum_support_margin",
        ):
            if not np.isclose(actual[field], original[field], rtol=0.0, atol=1.0e-10):
                raise ValueError(f"Baseline replay mismatch: {field} in {self.path}")

    def activate_final_state(self) -> None:
        if not self.result["passed"] or self.result["safety"]["first_box_contact"] is not None:
            raise ValueError(f"Cannot replay failed or contacting motion: {self.path}")
        motion = self.result["motion"]
        state = motion.get("final_state")
        if state is None:
            raise ValueError(f"Missing complete final state: {self.path}")
        for field in ("qpos", "qvel", "ctrl"):
            values = np.asarray(state[field], dtype=np.float64)
            destination = getattr(self.runtime.data, field)
            if values.shape != destination.shape or not np.isfinite(values).all():
                raise ValueError(f"Invalid final state {field}: {self.path}")
            destination[:] = values
        if not np.isfinite(state["time"]):
            raise ValueError(f"Invalid final state time: {self.path}")
        self.runtime.data.time = state["time"]
        mujoco.mj_forward(self.runtime.model, self.runtime.data)
        self.starting_arm = self.runtime.data.qpos[self.runtime.joint_qpos_adr[12:]].copy()
        if not np.allclose(self.starting_arm, motion["final_joint_position"], rtol=0, atol=1e-10):
            raise ValueError(f"Final arm replay mismatch: {self.path}")
        hand_error = np.linalg.norm(
            _hand_position(self.runtime, self.hand_point) - motion["final_hand_position"]
        )
        if not np.isfinite(hand_error) or hand_error > 1e-6:
            raise ValueError(f"Final hand replay mismatch ({hand_error:.9g} m): {self.path}")
        base = self.runtime.env.robot_qpos_adr
        rotation = self.runtime.data.xmat[self.runtime.base_id].reshape(3, 3)
        self.base = np.array([
            *self.runtime.data.qpos[base : base + 2], np.arctan2(rotation[1, 0], rotation[0, 0]),
        ])
        box = self.box_reader.read() if hasattr(self, "box_reader") else BoxStateReader(self.runtime).read()
        self.box_position = box.position
        self.rotation = box.rotation
        if self.target_orientation is not None:
            self.target_orientation = native_push_orientation(box.quaternion)
        self.final_state_active = True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--random-starts", type=int, default=64)
    parser.add_argument("--search-seed", type=int, default=0)
    parser.add_argument("--path-samples", type=int, default=101)
    parser.add_argument("--hand-target-local", type=float, nargs=3)
    parser.add_argument("--from-held-pose", action="store_true")
    parser.add_argument("--diagnose-designated-hand-approach", action="store_true")
    parser.add_argument("--ik-center", type=float, nargs=6)
    parser.add_argument("--search-scale", type=float, default=1.0)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    if args.random_starts < 0 or args.search_seed < 0 or args.path_samples < 2:
        parser.error("Counts and seed must be non-negative; path needs at least 2 samples")
    if args.hand_target_local is not None and not np.isfinite(args.hand_target_local).all():
        parser.error("Target must be finite")
    if not np.isfinite(args.search_scale) or args.search_scale <= 0.0:
        parser.error("Search scale must be finite and positive")
    if args.ik_center is not None and not np.isfinite(args.ik_center).all():
        parser.error("IK center must be finite")
    torch.set_num_threads(1)
    snapshots = [SnapshotSearch(path) for path in args.input_json]
    if len({snapshot.hand_point for snapshot in snapshots}) != 1:
        parser.error("Input snapshots must use the same hand point reference")
    for snapshot in snapshots:
        snapshot.verify_baseline()
        if args.from_held_pose:
            snapshot.activate_final_state()
    target_local = np.asarray(
        args.hand_target_local if args.hand_target_local is not None
        else snapshots[0].result["candidate"]["target_local"]
    )
    reference = snapshots[0].result["candidate"]
    starts = [np.asarray(reference["ik_initial"])] + [
        np.asarray(snapshot.result["candidate"]["joint_solution"])
        for snapshot in snapshots
    ]
    generator = np.random.default_rng(args.search_seed)
    center = np.asarray(
        args.ik_center if args.ik_center is not None else reference["joint_solution"]
    )
    if np.any(center < snapshots[0].oracle.arm_low) or np.any(center > snapshots[0].oracle.arm_high):
        parser.error("IK center must satisfy joint limits")
    if args.ik_center is not None:
        starts.append(center)
    for _ in range(args.random_starts):
        starts.append(np.clip(
            center + args.search_scale * generator.normal(0.0, [0.35, 0.35, 0.35, 0.5, 0.5, 0.25]),
            snapshots[0].oracle.arm_low + 0.05,
            snapshots[0].oracle.arm_high - 0.05,
        ))
    candidates = []
    for index, initial in enumerate(starts):
        results = [
            snapshot.evaluate(
                initial,
                target_local,
                args.path_samples,
                from_held_pose=args.from_held_pose,
                diagnose_designated_hand_approach=args.diagnose_designated_hand_approach,
            )
            for snapshot in snapshots
        ]
        candidates.append({
            "index": index,
            "ik_initial": initial.tolist(),
            "passed": all(result["passed"] for result in results),
            "minimum_clearance_margin": min(
                result.get("selected_clearance_margin", -1.0) for result in results
            ),
            "snapshots": results,
        })
        print(json.dumps({key: candidates[-1][key] for key in (
            "index", "passed", "minimum_clearance_margin"
        )}), flush=True)
    ranked = sorted(
        candidates,
        key=lambda candidate: (candidate["passed"], candidate["minimum_clearance_margin"]),
        reverse=True,
    )
    report = {
        "schema_version": 1,
        "scope": (
            "Complete measured terminal qpos/qvel/ctrl replay; fixed-terminal-state "
            "joint-linear clearance bound only; no dynamic controller or contact certificate"
            if args.from_held_pose else
            "Fixed-base sampled position-IK search; no dynamic certificate"
        ),
        "from_held_pose": args.from_held_pose,
        "diagnose_designated_hand_approach": args.diagnose_designated_hand_approach,
        "contact_execution_enabled": False,
        "source_sha256": {str(Path(__file__).resolve()): sha256(Path(__file__))},
        "input_sha256": {str(path.resolve()): sha256(path) for path in args.input_json},
        "search_seed": args.search_seed,
        "ik_center": center.tolist(),
        "search_scale": args.search_scale,
        "path_samples": args.path_samples,
        "hand_target_local": target_local.tolist(),
        "hand_point": snapshots[0].hand_point,
        "baseline_replays_verified": len(snapshots),
        "passing_candidates": sum(candidate["passed"] for candidate in candidates),
        "best": ranked[0],
        "candidates": ranked,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())