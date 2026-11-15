"""One bounded OBSERVATION-ONLY study, never an A/B policy or task completion.

Original actual capture -> one actual NAV left -> one actual NAV right, with
fresh original RGBD at each boundary. No PUSH, pose/GT, retries, moving camera,
threshold changes, geometry/material change, or finding the best result frame.
Only a NEW Data-owned source/program may opt into this separate purpose.
"""
from complex_scene import need
QUALIFICATION_PURPOSE='OBSERVABILITY_QUALIFICATION_ONLY'
COMPARISON_PURPOSE='T_COMPLEX_COMPARISON'
METHOD='scripted_observability_qualification_not_A_B'
SOURCE='scripted_observability_qualification_not_task_or_method_comparison'

def validate_planner_purpose(planner,purpose):
    if purpose==COMPARISON_PURPOSE:
        need(getattr(planner,'method',None)in('greedy','multistep'),'Actual common public A/B algorithm required')
    elif purpose==QUALIFICATION_PURPOSE:
        need(type(planner)is ObservabilityQualificationPlanner and planner.method==METHOD,
             'Explicit source-owned observation-only planner, not a hidden comparison policy')
    else:raise ValueError('Exact separate purpose; no implicit diagnostic fallback')

class ObservabilityQualificationPlanner:
    method=METHOD
    decision_source=SOURCE
    complete=False  # NEVER advertises original complete-task success.
    awaiting_terminal=False
    def __init__(self,public_task,*,journal):
        need(callable(journal),'Original new-scope journal required')
        o=public_task['objects'][0]
        need(o['public_ref']=='cuboid_a'and public_task['task']['source_surface_height_m']==0.,'Exact declared initial cuboid_a ground observation study')
        x=round(float(o['initial_xy_m'][0]-o['size_m'][0]/2-.58),12);y=float(o['initial_xy_m'][1])
        # The +/- .15 are the existing original ground entry-reference offsets,
        # not lateral PUSH, free yaw, a continuous domain, or a tracking guarantee.
        self.viewpoints=(dict(target_ref='cx-observe-left',xy=(x,round(y+.15,12))),
                         dict(target_ref='cx-observe-right',xy=(x,round(y-.15,12))))
        self.target_ref=o['public_ref'];self.journal=journal;self.stage=0;self.pending=None;self.records=[];self.receipts=[]
        self.motion_complete=False;self.qualification_complete=False;self.failed=False;self.last_observation_time=None
    @property
    def status(self):return 'OBSERVABILITY_FAILED_NO_RETRY'if self.failed else 'OBSERVATION_STUDY_COMPLETE_NOT_TASK_SUCCESS'if self.qualification_complete else 'AWAIT_FINAL_FRESH_OBSERVATION'if self.motion_complete else 'FIXED_OBSERVATION_NAV_STUDY'
    def _record(self,observation,label):
        from ainav.contracts import Observation
        need(type(observation)is Observation,'Original public observation required')
        value=observation.value;now=observation.time_s
        need(self.last_observation_time is None or now>self.last_observation_time,'Fresh actual later observation, no repeated/future frame')
        aliases=[]
        for obj in value['objects']:
            # These are ONLY the unchanged original current RGBD one-to-one
            # descriptors, not the task blueprint or a body-pose substitution.
            text=obj['label'];suffix='; current original RGBD one-to-one association'
            need(text.endswith(suffix),'Exact source public association label')
            aliases.append(text[:-len(suffix)])
        row=dict(event='observability_qualification_actual_public_observation',boundary=label,
            time_s=now,observation_sha256=observation.sha256,RGB_file_sha256=value['rgb']['sha256'],
            accepted_current_public_aliases=aliases,target_visible_under_original_binding=self.target_ref in aliases,
            original_task_success=False,meaningful_A_B_decision=False,private_GT_or_pose_read=False)
        ref=self.journal(row);self.records.append(dict(row,evidence_ref=ref));self.last_observation_time=now
    def select(self,batch):
        from ainav.intents import IntentBatch
        from ainav.contracts import Primitive
        from ainav.planner import Selection
        need(type(batch)is IntentBatch and not self.failed and not self.motion_complete and self.pending is None,
             'One next unused diagnostic NAV only, no retry or task action')
        self._record(batch.observation,'initial_after_actual_supported_capture'if self.stage==0 else 'after_original_left_NAV')
        view=self.viewpoints[self.stage];params=dict(goal_world_x_m=view['xy'][0],goal_world_y_m=view['xy'][1],surface_height_m=0.)
        matches=[o for o in batch.options if o.skill=='NAV'and o.target_ref==view['target_ref']and dict(o.parameters)==params]
        need(len(matches)==1,'Exact declared finite original NAV required')
        self.pending=matches[0]
        ref=self.journal(dict(event='observability_qualification_fixed_NAV_selected',stage=self.stage,
            target_ref=view['target_ref'],parameters=params,counts_as_A_B_decision=False,VLM_calls=0,
            prescribed_measurement_order_not_task_route=True,task_success=False))
        return Selection(batch.sha256,self.pending.token,self.pending.sha256,Primitive.from_option(self.pending).key,
                         'observation-qualification-only-v1',ref)
    def observe_intent(self,intent,option,receipt,binding_ref):
        from ainav.native.behavior_authority import NativeReceipt
        need(not self.failed and not self.motion_complete and intent is self.pending and type(receipt)is NativeReceipt and receipt.option_sha256==option.sha256 and
             option.skill=='NAV'and option.target_ref==intent.target_ref and option.parameters==intent.parameters,
             'Exact actual diagnostic NAV intent/option/receipt required')
        if receipt.status!='succeeded':
            self.failed=True;raise RuntimeError('Original observation NAV failed; no replacement or PUSH fallback')
        self.receipts.append(receipt);self.stage+=1;self.pending=None;self.motion_complete=self.stage==2
        self.journal(dict(event='observability_qualification_original_NAV_succeeded',stage=self.stage,
            original_receipt_evidence_ref=receipt.evidence_ref,still_not_task_success=True))
    def reject_intent(self,intent,reason,ref):
        self.failed=True;raise RuntimeError('Original observation NAV rejected; no retry: '+str(reason))
    def finish_from_driver(self,driver):
        from scene_driver import ComplexSceneDriver
        need(type(driver)is ComplexSceneDriver,'Actual source-owned driver only')
        need(driver.planner is self and driver.purpose==QUALIFICATION_PURPOSE and self.motion_complete and
             not self.failed and not self.qualification_complete and len(self.receipts)==2,'Only this completed two-NAV study may finish')
        need(driver.executor.reported_end and driver.executor.last_outcome=='succeeded','Actual final NAV boundary required')
        driver.factory._current_completed_witness().validate(driver.r)
        driver._native_guards();driver._contact_guard();before=driver._snapshot(driver.r)
        observation=driver.observe_public(float(driver.r.sim.data.time))
        need(driver._snapshot(driver.r)==before,'Final original acquisition must not change world/FIFO')
        self._record(observation,'after_original_right_NAV');self.qualification_complete=True
        need(driver.complete is False,'Observation study cannot certify original task')
        result=dict(qualification_complete=True,original_task_success=False,AB_comparison=False,
            actual_original_NAV_receipts=2,fresh_observation_boundaries=3,observations=self.records,
            unchanged_geometry_camera_proposer_matcher_and_safety_gates=True,
            visible_in_any_fixed_view=any(r['target_visible_under_original_binding']for r in self.records),
            action_or_view_retries=0,source_domain_or_PUSH_success_not_certified=True)
        self.journal(dict(event='observability_qualification_complete_not_task',**result));return result
