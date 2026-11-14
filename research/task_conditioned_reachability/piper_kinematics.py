"""Static MuJoCo FK/IK for repository Piper assets. Never step or load policy.

Adapter reuses the existing fixed-base pose-IK oracle without constructing its
actor runtime. Only a private MjData is modified; no live scene/state is touched.
"""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from contextlib import contextmanager

import mujoco
import numpy as np

REPO = Path(__file__).resolve().parents[2]
MUJOCO_ROOT = REPO / 'mujoco'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_existing(name, directory):
    """Import original module source, not a copied/reimplemented oracle."""
    package = '_reach_original_piper'
    if package not in sys.modules:
        mod = ModuleType(package)
        mod.__path__ = [str(directory)]
        sys.modules[package] = mod
    return importlib.import_module(f'{package}.{name}')


@contextmanager
def no_physics_steps():
    original = {name: getattr(mujoco, name) for name in ('mj_step', 'mj_step1', 'mj_step2')}
    def forbidden(*args, **kwargs):
        raise RuntimeError('Physics integration is forbidden in this static study')
    try:
        for name in original:
            setattr(mujoco, name, forbidden)
        yield
    finally:
        for name, fn in original.items():
            setattr(mujoco, name, fn)


class PiperKinematics:
    def __init__(self, *, position_tolerance_m=.002, orientation_tolerance_rad=np.pi / 180,
                 max_iterations=80, native_collision_profile=False):
        self.scene = MUJOCO_ROOT / 'robots/go2_piper/scene.xml'
        self.robot_xml = self.scene.with_name('go2piper.xml')
        self.profile_path = MUJOCO_ROOT / 'deploy/piper_robot_profile.json'
        self.config = MUJOCO_ROOT / 'deploy/deploy_mujoco/go2_piper/config.yaml'
        self.native_collision_profile = bool(native_collision_profile)
        # Use frozen original profile operation; no alternate frame/IK model.
        profile_module_name = '_reach_piper_profile'
        import importlib.util
        profile_code = MUJOCO_ROOT / 'reconfigurable_navigation/piper_robot_profile.py'
        spec = importlib.util.spec_from_file_location(profile_module_name, profile_code)
        profile_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(profile_module)
        declared = json.loads(self.profile_path.read_text())
        self.provenance = {str(p.relative_to(REPO)): sha(p) for p in
                           (self.scene, self.robot_xml, self.profile_path, self.config, profile_code)}
        for rel, expected in declared['usd_sha256'].items():
            actual = sha(REPO / rel)
            if actual != expected:
                raise ValueError(f'USD profile source mismatch: {rel}')
            self.provenance[rel] = actual
        # Source mesh hashes are recorded even though IK uses only kinematics.
        for p in sorted((self.scene.parent / 'assets').rglob('*')):
            if p.is_file():
                self.provenance[str(p.relative_to(REPO))] = sha(p)
        with no_physics_steps():
            spec = mujoco.MjSpec.from_file(str(self.scene))
            profile_module.apply_piper_robot_profile(spec, self.profile_path)
            if self.native_collision_profile:
                collision_path = MUJOCO_ROOT / 'deploy/piper_collision_profile.json'
                collision = json.loads(collision_path.read_text())
                for rel, expected in collision['usd_sha256'].items():
                    if sha(REPO / rel) != expected:
                        raise ValueError(f'Collision-profile USD source mismatch: {rel}')
                self.provenance[str(collision_path.relative_to(REPO))] = sha(collision_path)
                profile_module.apply_piper_collision_profile(spec, collision_path)
            self.model = spec.compile()
            self.data = mujoco.MjData(self.model)
        self.joint_names = tuple(f'{leg}_{j}_joint' for leg in ('FL', 'FR', 'RL', 'RR')
                                 for j in ('hip', 'thigh', 'calf')) + tuple(f'joint{i}' for i in range(1, 7))
        joint_ids = np.array([self.model.joint(n).id for n in self.joint_names])
        self.joint_qpos = self.model.jnt_qposadr[joint_ids]
        self.joint_dof = self.model.jnt_dofadr[joint_ids]
        self.arm_joint_ids = joint_ids[12:]
        self.base_id = self.model.body('base_link').id
        self.base_qpos = int(self.model.jnt_qposadr[self.model.body_jntadr[self.base_id]])
        # Explicit mathematical fixed-body pose, NOT a settled native standing state.
        self.data.qpos[self.base_qpos:self.base_qpos + 7] = (0, 0, .35, 1, 0, 0, 0)
        # No actors/configured PD. Leg pose does not enter fixed-base serial arm IK.
        self.data.qpos[self.joint_qpos[:12]] = ([.1, .8, -1.5, -.1, .8, -1.5,
                                                .1, 1., -1.5, -.1, 1., -1.5])
        self.data.qpos[self.joint_qpos[12:]] = np.clip(np.zeros(6),
                                   self.model.jnt_range[self.arm_joint_ids, 0],
                                   self.model.jnt_range[self.arm_joint_ids, 1])
        mujoco.mj_forward(self.model, self.data)
        self.base_position = self.data.xpos[self.base_id].copy()
        self.base_rotation = self.data.xmat[self.base_id].reshape(3, 3).copy()
        original_dir = MUJOCO_ROOT / 'reconfigurable_navigation/reachability'
        oracle_module = load_existing('oracle', original_dir)
        self.query_class = load_existing('schema', original_dir).ReachabilityQuery
        for n in ['oracle.py', 'schema.py']:
            self.provenance[str((original_dir / n).relative_to(REPO))] = sha(original_dir / n)
        runtime = SimpleNamespace(model=self.model, data=self.data,
                                  joint_qpos_adr=self.joint_qpos, joint_dof_adr=self.joint_dof,
                                  default_qpos=self.data.qpos[self.joint_qpos].copy(),
                                  env=SimpleNamespace(robot_qpos_adr=self.base_qpos))
        self.oracle = oracle_module.PiperPositionReachabilityOracle(
            runtime, tolerance=position_tolerance_m, orientation_tolerance=orientation_tolerance_rad,
            max_iterations=max_iterations)
        self.default_seed = runtime.default_qpos[12:].copy()
        self.midpoint_seed = (self.oracle.arm_low + self.oracle.arm_high) / 2
        self.ee_id = self.model.body('end_effector').id
        self.model_bytes = hashlib.sha256(self.model.qpos0.tobytes() + self.model.jnt_range.tobytes()).hexdigest()

    def snapshot(self):
        return tuple(a.copy() for a in (self.data.qpos, self.data.qvel, self.data.ctrl))

    def restored(self, snapshot):
        return all(np.array_equal(a, b) for a, b in zip(snapshot,
                  (self.data.qpos, self.data.qvel, self.data.ctrl)))

    def target_world(self, point_base):
        p = np.asarray(point_base, dtype=float)
        if p.shape != (3,) or not np.isfinite(p).all():
            raise ValueError('Expected finite 3D base-frame target')
        return self.base_position + self.base_rotation @ p

    def fk(self, arm_q):
        query = self.query_class(np.zeros(3), np.zeros(3))
        return self.oracle.end_effector_pose(query, np.asarray(arm_q, dtype=float))

    def solve(self, point_base, quaternion_world):
        """Fixed two seed attempts; failure is solver_not_found, not unreachable proof."""
        query = self.query_class(np.zeros(3), self.target_world(point_base))
        before = self.snapshot()
        attempts = []
        for name, q in [('default', self.default_seed), ('midpoint', self.midpoint_seed)]:
            result = self.oracle.solve(query, initial_joint_positions=q,
                                       target_quaternion=np.asarray(quaternion_world, dtype=float))
            if not self.restored(before):
                raise RuntimeError('Original oracle did not restore private qpos/qvel/ctrl')
            attempts.append(dict(seed=name, found=bool(result.kinematic_feasible),
                                 position_error_m=result.position_error,
                                 orientation_error_rad=result.orientation_error,
                                 iterations=result.iterations,
                                 joint_margin_rad=result.joint_limit_margin,
                                 q_rad=result.joint_solution.tolist()))
            if result.kinematic_feasible:
                # Independently evaluate returned q via original FK, not just success flag.
                actual_p, actual_q = self.fk(result.joint_solution)
                pe = float(np.linalg.norm(actual_p - query.target_position))
                oe = 2 * np.arccos(np.clip(abs(np.dot(actual_q, quaternion_world)), 0, 1))
                if pe > self.oracle.tolerance + 1e-10 or oe > self.oracle.orientation_tolerance + 1e-10:
                    raise RuntimeError('Returned solution failed fresh FK residual check')
                return dict(found=True, classification='pose_IK_found', attempts=attempts,
                            verified_position_error_m=pe, verified_orientation_error_rad=float(oe))
        return dict(found=False, classification='bounded_solver_not_found_NOT_unreachable_proof', attempts=attempts)

    def contract(self):
        bodies = []
        bid = self.ee_id
        while bid != self.base_id and bid > 0:
            bodies.append(dict(name=self.model.body(bid).name,
                               parent=self.model.body(int(self.model.body_parentid[bid])).name,
                               local_position_m=self.model.body_pos[bid].tolist(),
                               local_quaternion_wxyz=self.model.body_quat[bid].tolist()))
            bid = int(self.model.body_parentid[bid])
        mount = self.model.body('Piper').id
        mount_p = self.base_rotation.T @ (self.data.xpos[mount] - self.base_position)
        mount_r = self.base_rotation.T @ self.data.xmat[mount].reshape(3, 3)
        return dict(robot='repository_Go2_Piper_profile_NOT_physical_calibration',
                    frame='base_link_xyz_m_actual_compiled_asset_axes',
                    fixed_base_world_position_m=self.base_position.tolist(),
                    mount_body='Piper', mount_position_in_base_m=mount_p.tolist(),
                    mount_rotation_in_base=mount_r.tolist(), end_effector_body='end_effector',
                    tool_offset='compiled end_effector origin; NOT legacy link6+0.15m proxy',
                    chain_from_tip_to_base=bodies,
                    arm_joint_order=list(self.joint_names[12:]),
                    hard_joint_low_rad=self.oracle.arm_low.tolist(),
                    hard_joint_high_rad=self.oracle.arm_high.tolist(),
                    numerical_model_metadata_sha256=self.model_bytes,
                    profile_USD_and_model_assets=self.provenance,
                    position_tolerance_m=self.oracle.tolerance,
                    orientation_tolerance_rad=self.oracle.orientation_tolerance,
                    max_iterations=self.oracle.max_iterations,
                    seed_policy='fixed default then midpoint, stop when valid; no previous-query warm start',
                    default_seed_rad=self.default_seed.tolist(), midpoint_seed_rad=self.midpoint_seed.tolist(),
                    native_USD_collision_geometry_loaded=self.native_collision_profile,
                    collision_checked=False, support_checked=False, actuators_or_delay_checked=False,
                    actor_loaded=False, physical_integration_steps=0,
                    note='Static private model/FK/IK only. Body .35m is not a real supported/settled stance.')
