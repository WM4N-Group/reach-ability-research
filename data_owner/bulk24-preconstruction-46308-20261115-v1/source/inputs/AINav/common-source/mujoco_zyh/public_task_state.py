"""Shared causal body/task/visible-front features for task-model adapters.

All69 values come from current public proprioception, already declared control
mode/age, and current RGBD. No world odometry, full box center, hidden properties,
future motor output, learned target selection, or executable target is produced.
"""
import hashlib,json,math
import numpy as np
from visual_box_proposals import _validate,propose_visual_candidates
from .visible_surface_goal import describe_visible_goal

MACROS=('WAIT','PUSH_A','RECOVER_A','NAV_B','PUSH_B','NAV_STEP','CLIMB_STEP','NAV_HIGH','CLIMB_HIGH','NAV_C','PUSH_C','NAV_BRIDGE','CLIMB_BRIDGE','NAV_FAR','BRAKE_FAR')
SCHEMA=dict(version='public-body-task-visible-front-state-v1',size=69,
    fields=dict(proprio=[0,45],declared_macro_onehot=[45,60],observed_declared_macro_age_s=[60,61],
        visible_front_normal_body_xyz=[61,64],visible_front_plane_offset_m=[64,65],visible_front_gap_body_x_m=[65,66],
        visible_front_p90_residual_m=[66,67],visible_front_inlier_fraction=[67,68],visible_front_valid=[68,69]),
    explicit_task_appearance_cues=dict(NAV_STEP='green',NAV_BRIDGE='red'),
    missing_geometry='Zeros in61:68 with valid68=0, never interpreted as zero distance or safety',
    target_identity_or_action_admission_certified=False)
SCHEMA_SHA256=hashlib.sha256(json.dumps(SCHEMA,sort_keys=True).encode()).hexdigest()


def assemble_public_task_state(rgb,depth,K,mount,proprio,*,time_s,declared_macro,macro_declared_at_s):
    _validate(rgb,depth,K,mount);p=np.asarray(proprio,dtype=np.float32)
    if p.shape!=(45,) or not np.isfinite(p).all():raise ValueError('Exactly45 finite public proprio features required')
    if declared_macro not in MACROS:raise ValueError('Current causally declared macro required')
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in (time_s,macro_declared_at_s)) or not 0<=macro_declared_at_s<=time_s:raise ValueError('Actual current timestamp and past/current declaration time required')
    state=np.zeros(69,np.float32);state[:45]=p;state[45+MACROS.index(declared_macro)]=1.;state[60]=time_s-macro_declared_at_s
    cue=SCHEMA['explicit_task_appearance_cues'].get(declared_macro);reason='No declared visible-front measurement for this macro';proof=None
    if cue is not None:
        proposals=propose_visual_candidates(rgb,depth,K,mount)
        candidates=[r for r in proposals['candidates'] if r['appearance_family']==cue]
        try:
            if len(candidates)!=1:raise ValueError('Current appearance cue has zero or multiple components')
            proof=describe_visible_goal(rgb,depth,K,mount,frame_local_ref=candidates[0]['frame_local_ref'],current_RGB_sha256=proposals['RGB_sha256'],standoff_m=1.05)
            plane=proof['plane'];normal=np.asarray(plane['normal_body_xyz']);offset=plane['plane_offset_body_m']
            state[61:64]=normal;state[64]=offset;state[65]=offset/normal[0];state[66]=plane['p90_inlier_residual_m'];state[67]=plane['inlier_fraction'];state[68]=1.
            reason=None
        except ValueError as exc:reason=str(exc)
    return dict(state=state,state_schema_sha256=SCHEMA_SHA256,geometry_valid=bool(state[68]),geometry_missing_reason=reason,
        geometry_provenance=proof,explicit_appearance_cue=cue,learned_target_identity=False,
        uses_future_commands_or_world_pose=False,physical_action_admitted=False)
