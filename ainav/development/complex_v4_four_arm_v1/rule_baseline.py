"""E planner: fixed public rules, no VLM/WM/NEW successor optimizer/route oracle.

The shared execution layer retains legacy-common stow H for ALL five arms;
that kernel and its actual costs are separate from this rule and the new factor.

This is NOT a native driver. It uses only the actual original public catalogue
and successful matching semantic receipts. Unsupported CLIMB stays explicit.
"""
import math
from v4_native_asset import validate,require

class RuleBaseline:
    method='E_public_geometry_engineering_rule_v1'
    decision_source='fixed_rules_no_VLM_WM_or_successor_optimizer'
    def __init__(self,scene,*,journal,max_selections=64):
        validate(scene);require(callable(journal)and type(max_selections)is int and 1<=max_selections<=64,'Bounded fixed E rule/journal')
        self.scene=scene;self.journal=journal;self.max_selections=max_selections
        self.objects=tuple(sorted(scene['objects'],key=lambda o:(o['initial_xy_m'][0],o['public_ref'])))
        self.placed=set();self.approached=set();self.support_height=0.;self.pending=None;self.pending_kind=None;self.failed=False
        self.decision_count=0;self.native_success_count=0;self.complete=False;self.awaiting_terminal=False;self.last_time=None
    def _public_aliases(self,observation):
        suffix='; current original RGBD one-to-one association';aliases=set()
        for obj in observation.value['objects']:
            require(obj['label'].endswith(suffix),'Original current association labels only');aliases.add(obj['label'][:-len(suffix)])
        return aliases
    def select(self,batch):
        try:return self._select(batch)
        except Exception:self.failed=True;raise
    def _select(self,batch):
        from ainav.intents import IntentBatch
        from ainav.contracts import Primitive
        from ainav.planner import Selection
        require(type(batch)is IntentBatch and not self.failed and not self.complete and not self.awaiting_terminal and self.pending is None,'One fresh original public E decision, no fallback/retry')
        now=batch.observation.time_s;require(self.last_time is None or now>self.last_time,'Strictly fresh public query')
        require(self.decision_count<self.max_selections,'Fixed E semantic selection cap, no silent extension')
        pending=next((o for o in self.objects if o['public_ref']not in self.placed),None);kind=None
        if pending:
            require(self.support_height==0.,'All manipulation stays on ground')
            ref=pending['public_ref'];goal=pending['required_goal_xy_m']
            if ref in self._public_aliases(batch.observation):
                matches=[o for o in batch.options if o.skill=='PUSH'and o.target_ref==ref and dict(o.parameters)==dict(goal_world_x_m=goal[0],goal_world_y_m=goal[1],surface_height_m=0.)];kind=('placement',ref)
            else:
                if ref in self.approached:raise RuntimeError('E_current_association_still_unknown_after_one_declared_approach_no_view_scan')
                xy=(pending['initial_xy_m'][0]-pending['size_m'][0]/2-.58,pending['initial_xy_m'][1])
                matches=[o for o in batch.options if o.skill=='NAV'and dict(o.parameters).get('surface_height_m')==0. and all(math.isclose(dict(o.parameters)[k],v,rel_tol=0.,abs_tol=1e-12)for k,v in zip(('goal_world_x_m','goal_world_y_m'),xy))];kind=('approach',ref)
        elif self.support_height<self.scene['task']['goal_surface_height_m']:
            candidates=[o for o in batch.options if o.skill=='CLIMB'and self.support_height<dict(o.parameters)['surface_height_m']<=self.scene['task']['goal_surface_height_m']]
            if not candidates:raise RuntimeError('E_no_declared_next_CLIMB_option_not_native_failure')
            next_height=min(dict(o.parameters)['surface_height_m']for o in candidates)
            if abs(next_height-self.support_height-.2)>.01:raise RuntimeError('E_selected_original20cm_CLIMB_domain_excludes_next_declared_height_no_guard_relaxation')
            # A one-hop nominal proximity rule, not a successor cost/search.
            g=self.scene['task']['goal_bounds_xy_m'];goal=((g[0]+g[1])/2,(g[2]+g[3])/2)
            positions={o['public_ref']:o['required_goal_xy_m']for o in self.objects};positions.update({s['name']:((s['bounds_xy_m'][0]+s['bounds_xy_m'][1])/2,(s['bounds_xy_m'][2]+s['bounds_xy_m'][3])/2)for s in self.scene['platforms']})
            def key(o):
                ref=o.target_ref.removesuffix(':upper-entry');require(ref in positions,'Public declared surface reference required');xy=positions[ref];return(math.hypot(xy[0]-goal[0],xy[1]-goal[1]),o.target_ref)
            selected=min((o for o in candidates if dict(o.parameters)['surface_height_m']==next_height),key=key);matches=[selected];kind=('climb',next_height)
        else:
            g=self.scene['task']['goal_bounds_xy_m'];xy=((g[0]+g[1])/2,(g[2]+g[3])/2)
            matches=[o for o in batch.options if o.skill=='NAV'and dict(o.parameters)==dict(goal_world_x_m=xy[0],goal_world_y_m=xy[1],surface_height_m=self.support_height)];kind=('terminal_nav',None)
        require(len(matches)==1,'Exact one shared public candidate; never manufacture an option')
        option=matches[0];self.pending=option;self.pending_kind=kind;self.decision_count+=1;self.last_time=now
        ref=self.journal(dict(event='V4_E_fixed_rule_selected',query_sha256=batch.sha256,intent_sha256=option.sha256,rule_stage=kind[0],rule_prior='declared_initial_X_order_then_one_hop_goal_proximity_engineering_rule',decision_count=self.decision_count,VLM_calls=0,WM_calls=0,our_optimizer_calls=0,private_pose_or_future_or_existence_route_read=False,native_permission_claimed=False))
        return Selection(batch.sha256,option.token,option.sha256,Primitive.from_option(option).key,0,ref)
    def observe_intent(self,intent,option,receipt,binding_ref):
        from ainav.native.behavior_authority import NativeReceipt
        require(not self.failed and intent is self.pending and type(receipt)is NativeReceipt and receipt.option_sha256==option.sha256 and option.skill==intent.skill and option.parameters==intent.parameters,'Exact pending semantic/native terminal receipt required')
        if receipt.status!='succeeded':self.failed=True;raise RuntimeError('E_original_native_outcome_'+receipt.status+'_no_replacement')
        stage,value=self.pending_kind
        if stage=='placement':self.placed.add(value)
        elif stage=='approach':self.approached.add(value)
        elif stage=='climb':self.support_height=value
        elif stage=='terminal_nav':self.awaiting_terminal=True
        self.native_success_count+=1;self.pending=None;self.pending_kind=None
        self.journal(dict(event='V4_E_original_native_receipt_consumed',receipt_ref=receipt.evidence_ref,binding_ref=binding_ref,stage=stage,task_success_inferred=False))
    def reject_intent(self,intent,reason,evidence_ref):
        require(intent is self.pending,'Only the real pending rule intent may be rejected')
        self.failed=True;raise RuntimeError('E_original_judgment_rejection_no_retry:'+str(reason))
    def confirm_original_task_terminal(self,*,evidence_ref,terminal_proof=None):
        from task_terminal import VerifiedV4TaskTerminal
        if type(terminal_proof) is not VerifiedV4TaskTerminal:
            raise RuntimeError('V4_actual_typed_terminal_proof_required_E_cannot_self_certify')
        terminal_proof.confirm_rule(self,evidence_ref=evidence_ref)
        self.journal(dict(event='V4_E_actual_complete_task_confirmed',evidence_ref=evidence_ref,
            original_private_terminal_verifier=True,not_self_certified_from_goal_or_string=True,model_input=False))
        self.complete=True;self.awaiting_terminal=False
