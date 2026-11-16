"""API0 bounded integration policy, NOT five-arm C/E or an autonomous method.
Only public fixed intents: first declared box required PUSH, its20cm CLIMB,
then its one common box-top-centre NAV. Optional one original ground approach.
The C factor route ONLY selects legacy-H ON/new-successor OFF for this technical
component; it does not make this planner the real AINav C baseline.
"""
class BoundedEngineeringPolicy:
    enabled=False
    software_fixture=False
    decision_source='API0_BOUNDED_COMPONENT_ENGINEERING_NOT_C_OR_E_METHOD'
    awaiting_terminal=False
    def __init__(self,scene,*,journal):
        self.scene=scene;self.journal=journal;self.obj=min(scene['objects'],key=lambda o:(o['initial_xy_m'][0],o['public_ref']));self.stage='PUSH';self.approached=False;self.pending=None;self.pending_stage=None;self.receipts=[];self.complete=False;self.failed=False;self.decision_count=0
    def select(self,batch):
        from ainav.intents import IntentBatch
        from ainav.contracts import Primitive
        from ainav.planner import Selection
        if type(batch)is not IntentBatch or self.pending is not None or self.failed or self.complete or self.decision_count>=4:raise RuntimeError('Bounded current public component decisions only; no fallback/retry')
        obj=self.obj;ref=obj['public_ref'];kind=self.stage;goal=obj['required_goal_xy_m'];params=None;target=None
        if kind=='PUSH':
            suffix='; current original RGBD one-to-one association';aliases=set()
            for item in batch.observation.value['objects']:
                if not item['label'].endswith(suffix):raise RuntimeError('Exact original current public association only')
                aliases.add(item['label'][:-len(suffix)])
            if ref not in aliases:
                if self.approached:raise RuntimeError('Current public association still absent after one declared approach; no scan/retry')
                kind='APPROACH';xy=(obj['initial_xy_m'][0]-obj['size_m'][0]/2-.58,obj['initial_xy_m'][1]);params=dict(goal_world_x_m=xy[0],goal_world_y_m=xy[1],surface_height_m=0.)
            else:target=ref;params=dict(goal_world_x_m=goal[0],goal_world_y_m=goal[1],surface_height_m=0.)
        elif kind=='CLIMB':target=ref+':upper-entry';params=dict(surface_height_m=obj['size_m'][2])
        elif kind=='TOP_NAV':target='v4-box-top-'+ref;params=dict(goal_world_x_m=goal[0],goal_world_y_m=goal[1],surface_height_m=obj['size_m'][2])
        else:raise RuntimeError('No component task extension')
        skill='NAV'if kind in('APPROACH','TOP_NAV')else kind
        matches=[o for o in batch.options if o.skill==skill and(target is None or o.target_ref==target)and dict(o.parameters)==params]
        if len(matches)!=1:raise RuntimeError('One exact common public candidate required; never synthesize a goal')
        self.pending=matches[0];self.pending_stage=kind;self.decision_count+=1;ref=self.journal(dict(event='Data_bounded_API0_component_public_intent_selected',component_not_five_arm_method=True,query_sha256=batch.sha256,intent_sha256=self.pending.sha256,stage=kind,VLM_calls=0,WM_calls=0,new_optimizer_calls=0,legacy_H_factor_route='C_FLAGS_ONLY_NOT_REAL_C_BASELINE',uses_private_live_pose_or_future=False))
        return Selection(batch.sha256,self.pending.token,self.pending.sha256,Primitive.from_option(self.pending).key,0,ref)
    def observe_intent(self,intent,option,receipt,binding_ref):
        from ainav.native.behavior_authority import NativeReceipt
        if intent is not self.pending or type(receipt)is not NativeReceipt or receipt.option_sha256!=option.sha256 or option.skill!=intent.skill or option.parameters!=intent.parameters:raise RuntimeError('Exact current original semantic/native receipt required')
        self.receipts.append(dict(stage=self.pending_stage,intent_sha256=intent.sha256,native_option_sha256=option.sha256,receipt=dict(receipt.__dict__),binding_ref=binding_ref))
        if receipt.status!='succeeded':self.failed=True;raise RuntimeError('Original native component outcome:'+receipt.status+'; no retry')
        if self.pending_stage=='APPROACH':self.approached=True
        elif self.pending_stage=='PUSH':self.stage='CLIMB'
        elif self.pending_stage=='CLIMB':self.stage='TOP_NAV'
        elif self.pending_stage=='TOP_NAV':self.complete=True;self.stage='DONE'
        self.pending=None;self.pending_stage=None
    def reject_intent(self,intent,reason,evidence_ref):
        self.failed=True;raise RuntimeError('Original component admission rejection:'+str(reason)+'; no replacement')
