"""Read only source/model inputs; compile private CPU geometry, never simulate.

No actor, SDK, environment, trial report, trajectory, or reserved outcome reads.
Outputs are NEW evidence, not modifications of the closed experiment package.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np

from analytic_chain_bounds import chain_bounds, linear_path_bound
from preparation_theory import path_budget

REPO = Path(__file__).resolve().parents[3]
OWNER = Path('/home/yuanyue/re-nav -piper-deploy/artifacts/go2-piper/sim2sim-current-20261008-a')
MDP = 'source/LeggedManip_Lab/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/mdp/'
CONFIG = 'source/LeggedManip_Lab/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/config/go2_piper/box_env_cfg.py'
EXPECTED_MANIFEST = '149ac2b4c25138b035efc68fccb948c544bdab4e842426d080b75ee27821054b'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def extract_chain(model, mujoco):
    """Use compiled, profile-overridden transforms, NOT raw XML joint limits."""
    root = model.body('base_link').id
    cursor = model.body('end_effector').id
    ids = []
    while cursor != root:
        if cursor == 0:
            raise ValueError('Tool does not descend from base_link')
        ids.append(cursor)
        cursor = int(model.body_parentid[cursor])
    chain = []
    for body in reversed(ids):
        count = int(model.body_jntnum[body])
        if count > 1:
            raise ValueError('Multiple joints in one chain body not supported')
        joint = None
        if count:
            j = int(model.body_jntadr[body])
            if model.jnt_type[j] != mujoco.mjtJoint.mjJNT_HINGE:
                raise ValueError('Non-hinge internal joint')
            if not np.isclose(np.linalg.norm(model.jnt_axis[j]), 1., rtol=0., atol=1e-14):
                raise ValueError('Non-unit compiled joint axis')
            joint = dict(name=model.joint(j).name, kind='hinge',
                         pivot_m=model.jnt_pos[j].tolist(), axis=model.jnt_axis[j].tolist(),
                         hard_range_rad=model.jnt_range[j].tolist())
        chain.append(dict(name=model.body(body).name,
                          parent=model.body(int(model.body_parentid[body])).name,
                          translation_m=model.body_pos[body].tolist(),
                          quaternion_wxyz=model.body_quat[body].tolist(), joint=joint))
    if [b['joint']['name'] for b in chain if b['joint']] != [f'joint{i}' for i in range(1, 7)]:
        raise ValueError('Unexpected native arm joint chain')
    hand = model.body('end_effector').id
    spheres = [i for i in range(model.ngeom) if model.geom_bodyid[i] == hand
               and model.geom_type[i] == mujoco.mjtGeom.mjGEOM_SPHERE]
    if len(spheres) != 1 or abs(model.geom_size[spheres[0], 0]-.01) > 1e-6:
        raise ValueError('Unexpected native hand sphere')
    if np.any(model.geom_pos[spheres[0]]):
        raise ValueError('Native sampler assumes sphere centered at body origin')
    return chain, dict(radius_m=float(model.geom_size[spheres[0], 0]),
                       center_offset_m=model.geom_pos[spheres[0]].tolist(),
                       role='source helper inflates the box by this radius; not whole-arm coverage')


def derive(source, owner):
    """Return reproducible inputs/bounds with no calls to mj_forward/mj_step."""
    if sha(source/'manifest.json') != EXPECTED_MANIFEST:
        raise ValueError('Not the closed source identity; do not silently rebind')
    manifest = read(source/'manifest.json')
    selected = ['protocol.json', 'parent_plan.original.json', 'probe.py',
                'finite_cloud_sampler_frozen.py', 'prospective_support.py']
    for name in selected:
        if sha(source/name) != manifest['files'][name]:
            raise ValueError('Source input drift: '+name)
    protocol = read(source/'protocol.json')
    train = owner/'push-direct-approach-v212/train'
    geometry = owner/'runtime-push-detour-v1/mujoco'
    plan = train.parent/'plan.json'
    if sha(plan) != read(source/'parent_plan.original.json')['source_plan_sha256']:
        raise ValueError('Frozen train plan drift')
    train_inputs = ['mujoco/deploy/piper_push_safe_approach.json', CONFIG,
                    MDP+'box_push_geometry.py', MDP+'box_push_ik.py', MDP+'box_push_control.py']
    for name in train_inputs:
        if sha(train/name) != read(plan)['source_hashes'][name]:
            raise ValueError('Frozen train source drift: '+name)
    inputs = [source/'manifest.json', plan]+[source/n for n in selected]+[train/n for n in train_inputs]
    inputs += [geometry/n for n in ['robots/go2_piper/go2piper.xml',
                                    'reconfigurable_navigation/piper_robot_profile.py',
                                    'deploy/piper_robot_profile.json', 'deploy/piper_collision_profile.json']]
    # Reuse exactly the native private-model constructor, not the Isaac runtime.
    tree = ast.parse((train/(MDP+'box_push_geometry.py')).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'PiperBaseArmGeometryShield')
    namespace = dict(np=np, Path=Path)
    sys.path.insert(0, str(geometry))
    try:
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                     str(train/(MDP+'box_push_geometry.py')), 'exec'), namespace)
        g = namespace['PiperBaseArmGeometryShield'](geometry, .035)
        loaded = Path(sys.modules['reconfigurable_navigation.piper_robot_profile'].__file__).resolve()
        if loaded != (geometry/'reconfigurable_navigation/piper_robot_profile.py').resolve():
            raise ValueError('Cached geometry module belongs to another checkout')
    finally:
        sys.path.pop(0)
    chain, sphere = extract_chain(g.model, g.mujoco)
    bounds = chain_bounds(chain)
    disk_path = read(train/'mujoco/deploy/piper_push_safe_approach.json')
    # Matches torch.as_tensor(..., dtype=torch.float32) before numpy in query.
    waypoints = [[struct.unpack('f', struct.pack('f', x))[0] for x in row]
                 for row in disk_path['waypoints']]
    path = linear_path_bound(bounds, waypoints)
    ku = path['nominal_point_path_lipschitz_m_per_u']
    # Only three known structural constants are supplied: all prospective errors UNKNOWN.
    declared = {key: bounds[key] for key in ('point_radius_m', 'point_jacobian_operator_bound_m_per_rad')}
    declared.update(nominal_point_path_lipschitz_m_per_u=ku,
                    provenance='analytic edge-length bound on source-bound private native geometry; no observed error calibration')
    unknown = path_budget([i/40 for i in range(41)], declared)
    return dict(schema='native-analytic-preparation-bounds-v1',
                recorded_at=datetime.now(timezone.utc).isoformat(),
                role='source/model analytic derivation and CPU software only; not a robot sample',
                source_manifest_sha256=EXPECTED_MANIFEST,
                remote_source_refs={k: protocol['source_refs'][k] for k in ('train', 'geometry', 'source_plan')},
                source_inputs={str(p): sha(p) for p in inputs},
                geometry_binding='same native constructor plus current local XML/profile hashes; not independent real-robot geometry certification',
                chain=chain, represented_sphere=sphere,
                center_bounds=bounds, nominal_waypoints_float32_rad=waypoints,
                nominal_path=path,
                sampling_only=dict(intervals_per_segment=40,
                                   analytic_gap_term_m=ku/80,
                                   intervals_for_1mm_gap_budget=math.ceil(ku/.002),
                                   intervals_for_5mm_gap_budget=math.ceil(ku/.010),
                                   cost_note='64 fixed residual corners multiply FK nodes; no new FK evaluation here'),
                tracking_and_geometry_budget=unknown,
                missing_actual_path_link='No prospective joint-distance bound to this geometric path. Controller limits, residual, projection and tracking do not prove one.',
                scope_exclusions=['base motion/orientation and box estimation bounds',
                                  'time-varying residual path derivative',
                                  'continuous residual interior coverage by 64 corners',
                                  'whole arm/body geometry coverage', 'numeric/model discrepancy',
                                  'final-output support/reserve witness', 'task benefit'],
                private_models_compiled=1, actual_FK_calls=0, physical_steps=0,
                SDK_starts=0, actor_forward_calls=0, physical_starts=0,
                reserved_outcomes_read=False, runtime_control_changed=False,
                execution_authorized=False, physical_safety_certified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=REPO.parent/'artifacts/go2-piper/native-pose-singlefactor-six-20261021-r2/source')
    parser.add_argument('--owner', type=Path, default=OWNER)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Never overwrite evidence')
    value = derive(args.source.resolve(), args.owner.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, value)
    print(json.dumps({k: value[k] for k in ('center_bounds', 'nominal_path', 'sampling_only', 'tracking_and_geometry_budget')}, indent=2))


if __name__ == '__main__':
    main()
