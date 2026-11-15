"""Original select/reject_intent/observe_intent seam for T-COMPLEX-01.

No world/controller construction, private state, fixed success route or motor
command. Match ONLY options actually present in each fresh source IntentBatch.
NAV waypoints/finite goals/final protected stop must be registered by the common
scene host. Missing mapping is explicit, never manufactured or silently skipped.
"""
from dataclasses import replace
import math
from .finite_multistep_planner import propose


def _original_intent_batch_type():
    from ainav.intents import IntentBatch
    return IntentBatch


def original_selection(batch, option, journal_ref):
    # These are the EXISTING original pure contract types, imported only when
    # the owner has already loaded its exact qualified source namespace.
    from ainav.contracts import Primitive
    from ainav.planner import Selection
    return Selection(batch.sha256,option.token,option.sha256,
                     Primitive.from_option(option).key,0,journal_ref)


class ComplexIntentPlanner:
    def __init__(self, model, *, method, journal, terminal_target_ref,
                 selection_factory=original_selection, nav_ref_by_xy=None,
                 max_depth=4,max_transitions=256,max_wall_s=.25):
        if method not in ('greedy','multistep'):raise ValueError('Same-domain method')
        if not isinstance(terminal_target_ref,str) or not terminal_target_ref:
            raise ValueError('Original protected-arrival terminal reference must be registered')
        self.model=model;self.method=method;self.journal=journal;self.terminal_ref=terminal_target_ref
        self.selection_factory=selection_factory;self.nav_refs={}if nav_ref_by_xy is None else dict(nav_ref_by_xy)
        self.limits=dict(max_depth=max_depth,max_transitions=max_transitions,max_wall_s=max_wall_s)
        self.nominal_context=model.initial;self.pending=None;self.queue=[];self.bundle=None;self.bundle_next=None
        self.decision_count=0;self.native_success_count=0;self.awaiting_terminal=False
        self.terminal_evidence_ref=None;self.failed_reason=None

    @property
    def complete(self):
        return self.terminal_evidence_ref is not None and self.failed_reason is None

    @staticmethod
    def _xy_equal(a,b):
        # Declaration arithmetic only (e.g. .5-.58 vs -.08), NOT sensor/pose
        # tolerance, nearest-neighbour matching or a changed native goal array.
        return all(type(x)in(int,float)and type(y)in(int,float)and
                   math.isfinite(x)and math.isfinite(y)and abs(x-y)<=1e-12 for x,y in zip(a,b))

    def _new_bundle(self):
        out=propose(self.nominal_context,arcs=self.model.arcs,is_goal=self.model.is_goal,
                    state_key=self.model.key,method=self.method,
                    cost_unit='m_nominal_NAV_route_plus_box_translation',**self.limits)
        action=out['action']
        if action is None:
            self.failed_reason=out['status']
            raise RuntimeError('Public finite planner abstained: '+out['status'])
        matches=[a for a in self.model.arcs(self.nominal_context)if a.action==action]
        if len(matches)!=1:raise ValueError('Same common-domain decision identity')
        self.bundle=action;self.bundle_next=matches[0].next_state
        route=action.nominal_NAV_route_xy_m
        self.queue=[dict(skill='NAV',xy=tuple(xy),public_ref=None,terminal=False)for xy in route[1:]]
        if action.kind=='PUSH_WITH_NAV_ROUTE':
            self.queue.append(dict(skill='PUSH',xy=action.goal_xy_m,public_ref=action.public_ref,terminal=False))
        elif action.kind=='NAV_AND_ORIGINAL_TERMINAL_STOP':
            if not self.queue:raise ValueError('Final original NAV/stop cannot be replaced by a nominal goal bit')
            self.queue[-1]['terminal']=True
        else:raise ValueError('Unknown source decision kind')
        self.decision_count+=1
        self.journal(dict(event='reach_complex_public_decision',method=self.method,
            decision_index=self.decision_count,nominal_action=action.__dict__,
            nominal_geometry_forecast_not_actual_world=True,counts_as_algorithm_decision=True,
            planned_native_request_count=len(self.queue),depth_units='DECISION_BUNDLES_NOT_NATIVE_SKILLS',
            planner_wall_s=out['planner_wall_s'],examined_transitions=out['examined_transitions'],
            fallback_to_shared_greedy=out['fallback_to_shared_greedy'],execution_authorized=False))

    def select(self,batch):
        if not isinstance(batch,_original_intent_batch_type()):
            raise ValueError('Original public IntentBatch only, never a private ExecutionBatch')
        if self.pending is not None or self.complete or self.failed_reason is not None:
            raise ValueError('Fresh original semantic batch and no pending interaction')
        if self.awaiting_terminal:
            raise RuntimeError('Original common task terminal/12N/protected-arrival proof is still required')
        if not self.queue:self._new_bundle()
        request=self.queue[0];matches=[]
        for option in batch.options:
            params=dict(option.parameters)
            if option.skill!=request['skill'] or set(params)!=set(('goal_world_x_m','goal_world_y_m','surface_height_m')):
                continue
            if params['surface_height_m']!=0. or not self._xy_equal((params['goal_world_x_m'],params['goal_world_y_m']),request['xy']):continue
            if request['skill']=='PUSH':
                ref=request['public_ref']
                if option.target_ref!=ref and not option.target_ref.startswith(ref+':'):continue
            else:
                ref=self.terminal_ref if request['terminal']else self.nav_refs.get(request['xy'])
                if ref is not None and option.target_ref!=ref:continue
            matches.append(option)
        if len(matches)!=1:
            raise ValueError('Exact unique current source semantic option missing/ambiguous: '+str(request))
        option=matches[0]
        ref=self.journal(dict(event='reach_complex_semantic_intent_selected',method=self.method,
            decision_index=self.decision_count,intent_sha256=option.sha256,
            actual_source_target_ref=option.target_ref,actual_source_parameters=dict(option.parameters),
            batch_sha256=batch.sha256,VLM_calls=0,physical_action_issued=False))
        self.pending=option.sha256
        return self.selection_factory(batch,option,ref)

    def reject_intent(self,intent,reason,evidence_ref):
        self.failed_reason='ORIGINAL_INTENT_REJECTION:'+str(reason)
        self.journal(dict(event='reach_complex_original_intent_rejected',method=self.method,
            intent_sha256=intent.sha256,reason=reason,evidence_ref=evidence_ref,physical_retry=False))
        raise RuntimeError(self.failed_reason)  # shared fail-closed, not a fabricated recovery policy

    def observe_intent(self,intent,actual,receipt,binding_ref):
        if (self.pending!=intent.sha256 or actual.skill!=intent.skill or actual.target_ref!=intent.target_ref
                or actual.parameters!=intent.parameters or receipt.option_sha256!=actual.sha256):
            raise ValueError('Original exact intent/native interaction/receipt binding')
        self.journal(dict(event='reach_complex_actual_native_interaction',method=self.method,
            intent_sha256=intent.sha256,native_option_sha256=actual.sha256,status=receipt.status,
            receipt_ref=receipt.evidence_ref,binding_ref=binding_ref,counts_as_algorithm_decision=False))
        if receipt.status!='succeeded':
            self.failed_reason='ORIGINAL_NATIVE_INTERACTION_'+str(receipt.status)
            raise RuntimeError(self.failed_reason)
        request=self.queue.pop(0);self.pending=None;self.native_success_count+=1
        if request['skill']=='NAV':
            self.nominal_context=replace(self.nominal_context,robot_reference_xy_m=request['xy'])
        else:
            # Original registered PUSH must include its actual immutable goal,
            # placement verification/stow gates. This advances only nominal
            # goal/reference context; NEVER records a private measured pose.
            self.nominal_context=self.bundle_next
        if not self.queue:
            self.nominal_context=self.bundle_next
            if self.bundle.kind=='NAV_AND_ORIGINAL_TERMINAL_STOP':self.awaiting_terminal=True
            self.bundle=None;self.bundle_next=None

    def confirm_original_task_terminal(self, *, evidence_ref):
        if (not self.awaiting_terminal or self.pending is not None or self.queue
                or not self.model.is_goal(self.nominal_context) or self.failed_reason is not None
                or type(evidence_ref)is not str or not evidence_ref):
            raise ValueError('External ORIGINAL complete-task/protected-arrival verifier, not nominal end state')
        # The owner-qualified common verifier must call this ONLY after both/all
        # original placements + actual remote region + supported safe stop pass.
        # The planner does not access private feet/load or certify them itself.
        self.terminal_evidence_ref=evidence_ref;self.awaiting_terminal=False
        self.journal(dict(event='reach_complex_original_task_terminal_received',method=self.method,
            evidence_ref=evidence_ref,nominal_prediction_not_terminal_evidence=True))
