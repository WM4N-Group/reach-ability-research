"""Source Piper collision hull / B-front-plane static preparation constraint.

Only FK on an isolated robot geometry specification. No MjRuntime, mj_step,
mj_forward, actor, neural checkpoint, renderer, native action or physical claim.
A sufficient separating plane for selected PROXIMAL arm hulls is NOT complete
collision/contact safety. Failure of the plane test is not an actual collision.
"""
from dataclasses import dataclass
from decimal import Decimal,localcontext,ROUND_CEILING
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import time

from ..native_pilot.analytic_chain_bounds import chain_bounds,linear_path_bound

REPO=Path(__file__).resolve().parents[3]
OLD_HELPER=Path('/home/yuanyue/re-nav -piper-deploy/artifacts/go2-piper/sim2sim-current-20261008-a/runtime-push-detour-v1/mujoco/reconfigurable_navigation/piper_robot_profile.py')
APPROACH=Path('/home/yuanyue/re-nav -piper-deploy/artifacts/go2-piper/sim2sim-current-20261008-a/push-direct-approach-v212/train/mujoco/deploy/piper_push_safe_approach.json')
PINS={
 'mujoco/robots/go2_piper/go2piper.xml':'e36f01b3dafa1d7d2820b200993f5e0a3a1c4bef948a5eb77141cb5686808c40',
 'mujoco/deploy/piper_robot_profile.json':'82709e77505deaf5689a84e886b3fc2b570e5e85e93f34d626e5d2d6fea3536a',
 'mujoco/deploy/piper_collision_profile.json':'54640d2f015626328f63e0ee98387b57ed01993c4e9595ba624c2a6b810ce276',
}
HELPER_SHA='26c095022cd2aef6b16acca16c5dcd57fc2401626c7ac7ab5de00f6c261b927d'
APPROACH_SHA='9c6db3af65afe62ace57f5d85f3a773666074b381383d037db4fa3df62162cbc'
# Documented surface-clearance scale, NOT a validated standoff extension.
SURFACE_CLEARANCE_M=.035
CLEARANCE_SOURCE=REPO/'evidence/2026-11-05/phe-a03-native-model-v1/guarded-modes/report.json'
CLEARANCE_SOURCE_SHA='c40f7d633f633c4bd597f8b28d8e6e06c2a128facbdd4e0721745e039389984b'


@dataclass(frozen=True)
class GeometryStudyProfile:
    enabled: bool=False
    values_m: tuple=(.58,)
    source: str='original_fixed0.58'

    def validate(self):
        if type(self.enabled) is not bool or not self.values_m or any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in self.values_m):
            raise ValueError('Explicit finite positive study profile required')
        if .58 not in self.values_m:raise ValueError('Original fixed baseline must be present')
        if not self.enabled and self.values_m!=(.58,):raise ValueError('Extension disabled by default; no dispatch domain changed')
        if self.enabled and self.source!='HYPOTHETICAL_CLEARANCE_SCALE_ONLY_NOT_NATIVE_DOMAIN':
            raise ValueError('Unvalidated perturbations must not be relabeled as native capability')
        return self


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pin(path,digest):
    if sha(path)!=digest:raise ValueError('Source geometry changed')


def radius_L1_upper(shape):
    # Rotation preserves norm. L1 vertex radius + L1 shape offset is conservative.
    with localcontext() as ctx:
        ctx.prec=60;ctx.rounding=ROUND_CEILING
        v=max(sum((abs(Decimal.from_float(float(x))) for x in row),Decimal(0)) for row in shape['vertices'])
        r=v+sum((abs(Decimal.from_float(float(x))) for x in shape['position']),Decimal(0))
        f=float(r)
        return math.nextafter(f,math.inf) if Decimal.from_float(f)<r else f


def _chain(model,body,mujoco):
    root=model.body('base_link').id;ids=[]
    while body!=root:
        ids.append(body);body=int(model.body_parentid[body])
        if body==0:raise ValueError('Arm collision body outside known root')
    result=[]
    for i in reversed(ids):
        n=int(model.body_jntnum[i]);joint=None
        if n>1:raise ValueError('One hinge per source arm body')
        if n:
            j=int(model.body_jntadr[i])
            if model.jnt_type[j]!=mujoco.mjtJoint.mjJNT_HINGE or any(model.jnt_pos[j]):raise ValueError('Unsupported non-origin hinge')
            joint=dict(name=model.joint(j).name,kind='hinge',pivot_m=model.jnt_pos[j].tolist())
        result.append(dict(name=model.body(i).name,parent=model.body(int(model.body_parentid[i])).name,
                           translation_m=model.body_pos[i].tolist(),joint=joint))
    return result


def geometry_constraint(*,samples=65):
    if samples<2 or samples>129:raise ValueError('Bounded FK sample count required; not a tuning loop')
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='':raise ValueError('Explicit CPU-only environment required')
    import numpy as np
    import mujoco
    began=time.perf_counter()
    for name,h in PINS.items():pin(REPO/name,h)
    pin(OLD_HELPER,HELPER_SHA);pin(APPROACH,APPROACH_SHA)
    pin(CLEARANCE_SOURCE,CLEARANCE_SOURCE_SHA)
    if json.loads(CLEARANCE_SOURCE.read_text())['native_guard_thresholds']['surface_clearance']!=SURFACE_CLEARANCE_M:
        raise ValueError('Do not tune the documented geometric clearance')
    spec_import=importlib.util.spec_from_file_location('reach_pinned_geometry_profiles',OLD_HELPER)
    module=importlib.util.module_from_spec(spec_import);spec_import.loader.exec_module(module)
    spec=mujoco.MjSpec.from_file(str(REPO/'mujoco/robots/go2_piper/go2piper.xml'))
    # Source XML already stores assets/ in each mesh file as well as meshdir.
    # Normalize ONLY isolated file resolution, without editing source/geometry.
    spec.meshdir=str(REPO/'mujoco/robots/go2_piper')
    module.apply_piper_robot_profile(spec,REPO/'mujoco/deploy/piper_robot_profile.json')
    module.apply_piper_collision_profile(spec,REPO/'mujoco/deploy/piper_collision_profile.json')
    model=spec.compile();data=mujoco.MjData(model)
    root=model.body('base_link').id
    if model.jnt_type[int(model.body_jntadr[root])]!=mujoco.mjtJoint.mjJNT_FREE:raise ValueError('Known base free joint required')
    data.qpos[:7]=[0.,0.,0.,1.,0.,0.,0.]
    joints=[model.joint('joint'+str(i)) for i in range(1,7)]
    qids=[int(j.qposadr[0]) for j in joints]
    path=np.asarray(json.loads(APPROACH.read_text())['waypoints'],float)
    if path.shape!=(2,6):raise ValueError('Exact source nominal two-point path required')
    collision=json.loads((REPO/'mujoco/deploy/piper_collision_profile.json').read_text())
    selected=[s for s in collision['shapes'] if s['body'] in ('Piper','link1','link2','link3','link4','link5')]
    shapes=[]
    for shape in selected:
        if shape['kind']!='Mesh':raise ValueError('This prototype handles source hulls explicitly, no radius guess')
        body=model.body(shape['body']).id;R=np.empty(9);mujoco.mju_quat2Mat(R,np.array(shape['quaternion'],float))
        points=np.asarray(shape['vertices'])@R.reshape(3,3).T+np.array(shape['position'])
        chain=_chain(model,body,mujoco)
        if any(b['joint'] for b in chain):
            bound=chain_bounds(chain,attached_point_radius_m=radius_L1_upper(shape))
            index=[int(n.replace('joint',''))-1 for n in bound['joint_names']]
            ku=linear_path_bound(bound,path[:,index].tolist())['nominal_point_path_lipschitz_m_per_u']
        else:ku=0.
        shapes.append(dict(name=shape['name'],body=body,body_name=shape['body'],points=points,Ku=ku,max_x=-math.inf))
    trace=[];tool=model.body('end_effector').id
    for u in np.linspace(0.,1.,samples):
        data.qpos[qids]=(1-u)*path[0]+u*path[1]
        mujoco.mj_kinematics(model,data)  # only FK; zero integration or forward dynamics
        xmax=-math.inf
        for shape in shapes:
            world=shape['points']@data.xmat[shape['body']].reshape(3,3).T+data.xpos[shape['body']]
            maximum=float(world[:,0].max());shape['max_x']=max(shape['max_x'],maximum);xmax=max(xmax,maximum)
        trace.append(dict(u=float(u),proximal_hull_max_base_x_m=xmax,tool_base_xyz_m=data.xpos[tool].tolist()))
    upper=max(s['max_x']+s['Ku']/(2*(samples-1)) for s in shapes)
    sampled=max(s['max_x'] for s in shapes)
    shape_rows=[dict(name=s['name'],body=s['body_name'],vertices=len(s['points']),sampled_max_x_m=s['max_x'],
                     model_path_Ku_m=s['Ku'],sample_to_curve_allowance_m=s['Ku']/(2*(samples-1))) for s in shapes]
    return dict(schema='reach-source-arm-front-plane-geometry-v1',
                role='STATIC_NOMINAL_GEOMETRY_PROFILE_NOT_NATIVE_EXECUTION_OR_ACTUAL_STATE',
                robot_geometry_sha256=PINS,helper_sha256=HELPER_SHA,approach_sha256=APPROACH_SHA,
                task_geometry='registered unrotated B front world-X plane; actual finite box is on positive-X side',
                represented_body_set=[s['body'] for s in shape_rows],excluded=['tool/wrist link6 and fingers','legs/base','self-collision','contact/support/tracking'],
                curve='source q0->q1 linear nominal arm-reference interpolation; fixed base orientation',
                source_path_declared_static_not_dynamically_validated=True,
                maximum_x_upper_model_m=upper,sampled_maximum_x_m=sampled,
                surface_clearance_m=SURFACE_CLEARANCE_M,
                margin_equation='standoff - maximum_x_upper_model - surface_clearance',
                spatial_relation='positive margin separates represented hulls behind infinite front plane; failure does NOT prove finite-box collision',
                continuum_model_allowance_from_global_levers=True,actual_tracking_bound=None,
                floating_point_certificate=False,physical_safety_certified=False,
                shapes=shape_rows,FK_trace=trace,FK_calls=samples,
                mj_step_calls=0,mj_forward_calls=0,actor_WM_calls=0,renderer_calls=0,
                wall_s=time.perf_counter()-began,execution_authorized=False)


def compare(profile,geometry):
    profile.validate()
    import numpy as np
    from scipy.optimize import milp,Bounds,LinearConstraint
    required=geometry['maximum_x_upper_model_m']+geometry['surface_clearance_m']
    rows=[dict(standoff_m=s,nominal_base_reference_shift_from058_m=.58-s,
               tool_reference_shift_without_retargeting_m=abs(s-.58),
               model_front_plane_margin_m=s-required,proxy_preparation_distance_cost_m=abs(s-.58),
               geometric_model_pass=s-required>=0,native_parameter_allowed=(s==.58),
               real_Push_target_or_success_preserved='UNKNOWN_without_original_IK_controller_retarget',
               old7a6_action11_preparation_applicability='baseline_only' if s==.58 else 'UNKNOWN_no_standoff_channel') for s in profile.values_m]
    feasible=[r for r in rows if r['geometric_model_pass']]
    best=min(feasible,key=lambda x:(x['proxy_preparation_distance_cost_m'],x['standoff_m'])) if feasible else None
    t=time.perf_counter();solver=milp(np.array([r['proxy_preparation_distance_cost_m'] for r in rows]),
                  integrality=np.ones(len(rows)),bounds=Bounds(np.zeros(len(rows)),np.array([float(r['geometric_model_pass']) for r in rows])),
                  constraints=LinearConstraint(np.ones((1,len(rows))),1,1),options=dict(time_limit=2.))
    idx=int(np.argmax(solver.x)) if solver.success else None
    return dict(schema='reach-fixed-enumeration-MILP-same-domain-v1',rows=rows,
                study_profile=dict(enabled=profile.enabled,source=profile.source,values_m=list(profile.values_m)),
                native_dispatch_domain_m=[.58],physical_dispatch=False,
                methods=dict(fixed_original=dict(standoff_m=.58,geometric_model_pass=next(r['geometric_model_pass'] for r in rows if r['standoff_m']==.58)),
                             full_enumeration=dict(best=best,geometry_recomputed=False),
                             generic_MILP=dict(status=int(solver.status),best=None if idx is None else rows[idx],wall_s=time.perf_counter()-t)),
                common_same_finite_domain_objective_constraints=True,
                objective_unit='m of nominal base-reference deviation, NOT seconds or task completion cost',
                parameter_margin_derivative_m_per_m=1.,
                difficult_shared_work='source hull FK and continuous-curve envelope precomputation',
                remaining_parameter_problem='affine constraint on fixed-reference translation; no new optimizer warranted',
                contact_IK_support_dynamics_not_modeled=True,execution_authorized=False)
