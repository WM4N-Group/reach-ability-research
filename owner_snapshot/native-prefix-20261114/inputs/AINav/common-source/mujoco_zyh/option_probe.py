"""Fresh bounded fixed-PUSH forecast cases with exact FIRST observed exit labels."""
from pathlib import Path
import json,math
import numpy as np
from .stall_stow import StallStowRouter,SoftStall

PLAN='option_forecast_study_v2_plan.json'


def load_plan():return json.loads(Path(__file__).with_name(PLAN).read_text())


def case_protocol(case):
    p=json.loads(Path(__file__).with_name('soft_stall_stow_protocol_v7.json').read_text())
    p.update(schema='piper-mujoco-terminated-option-forecast-case-v2',purpose='New fixed PUSH observed until first native goal/soft/hard exit; soft failure recovers, hard protection censors. No continued-PUSH future after exit.',
        source_id='terminated-option-20261025-v2-'+case['case_id'],episode_id='terminated-option-20261025-v2-'+case['case_id']+'-episode0',source_group='terminated-option-forecast-v2-'+case['case_id'],
        resource_lock_dir='/mnt/yuanyue/data/go2-piper-world-model',seed=case['seed'],role=case['role'],training_allowed=case['role']=='train',forecast_study_training_authorized=case['role']=='train',option_forecast_case=case['case_id'],
        probe_physics=dict(mass_kg=case['mass_kg_executor_private'],friction=case['friction_executor_private']),
        initial_probe_geometry=load_plan()['visible_geometry_groups'][case['initial_geometry_group']],
        max_sim_seconds=60,max_wall_seconds=1200,full_state_review=case['case_id'] in ('train-0','test-0'))
    return p


def validate_case(p):
    case=next((c for c in load_plan()['cases'] if c['case_id']==p.get('option_forecast_case')),None)
    if case is None or p!=case_protocol(case):raise ValueError('Exact fresh registered option-forecast case required')
    return p


def capture_initial_goal(runtime):
    """Initial software goal epoch only, AFTER compile and before FIRST step."""
    import torch
    p=runtime.sim
    if runtime.step_count or p.data.time or p.queue:raise ValueError('Initial geometry/goal capture after physics forbidden')
    position=p.data.xpos[p.box_id].copy();quat=p.data.xquat[p.box_id].copy()
    p.scene['box'].data.default_root_state[0,:3]=torch.tensor(position,dtype=torch.float32)
    p.scene['box'].data.default_root_state[0,3:7]=torch.tensor(quat,dtype=torch.float32)
    p.box_push_target=torch.tensor(position+[.6,0.,0.],dtype=torch.float32)[None]
    return dict(actual_initial_box_xyz=position.tolist(),original_world_X_plus06_goal=p.box_push_target.tolist(),initialization_only=True,physics_steps=0)


class NativeGoalBoundary(Exception):pass


class OptionProbeRouter(StallStowRouter):
    def __init__(self,*args):super().__init__(*args);self.first_exit=None
    def mark(self,kind,flags=None):
        if self.first_exit is None:
            p=self.r.sim
            self.first_exit=dict(time_s=float(p.data.time),box_xy=p.data.xpos[p.box_id,:2].tolist(),kind=kind,actual_measured=True,first_exit=True,native_flags=flags or {},actual_joint_q=p.data.qpos[p.qids].tolist(),actual_joint_dq=p.data.qvel[p.dids].tolist())
    def termination(self):
        try:flags=super().termination()
        except SoftStall:
            self.mark('soft_progress_abort');raise
        if self.recovery is None and self.kind=='push' and self.native.phase!='prepare':
            bad=[k for k,v in flags.items() if k!='box_settled' and v]
            if bad:self.mark('native_hard_protection',flags)
            elif flags['box_settled']:self.mark('native_goal_reached',flags)
        return flags
    def update(self):
        try:super().update()
        except RuntimeError as error:
            if str(error)=='native_success_before_stall_not_a_failure_recovery' and self.native.finish is not None and self.first_exit and self.first_exit['kind']=='native_goal_reached':raise NativeGoalBoundary('Observed native PUSH goal; no Finish/control continuation claimed')
            raise
    def after_step(self):
        try:
            super().after_step()
            if self.recovery is None and self.kind=='push' and self.native.phase!='prepare':
                box=self.r.push['bridge'].box_push;p=self.r.sim
                flags=dict(box_contact=bool(box.forbidden_box_contact(p)[0]),invalid_hand_contact=bool(box.invalid_hand_contact(p,p.hand_cfg)[0]),box_tipped=bool(box.box_tipped(p)[0]))
                if any(flags.values()):
                    self.mark('native_hard_protection',flags);raise RuntimeError('option_probe_native_contact_guard_200Hz:'+str(flags))
        except RuntimeError:
            if self.first_exit is None and self.kind=='push' and self.native.phase!='prepare':self.mark('native_hard_protection')
            raise
    def report(self):
        out=super().report();out['option_first_exit']=self.first_exit
        out['scope']='PUSH until its FIRST observed native goal/soft/hard exit; NO post-exit continued-PUSH labels'
        return out
