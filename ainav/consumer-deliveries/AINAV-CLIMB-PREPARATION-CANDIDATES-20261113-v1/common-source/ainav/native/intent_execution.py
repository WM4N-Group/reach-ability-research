"""Keep semantic intent while native prerequisites run, with separate receipts.

This coordinator chooses no task/object/successor. The VLM+tree owns the intent;
only an existing NAV may prepare its own entry on the same support. No compound
fake native session, fabricated completion, physical retry, or actor modification.
"""
from dataclasses import asdict
from ..contracts import Primitive,ProtectionRequest,sha
from ..intents import IntentBatch,ExecutionBatch,SkillIntent
from ..planner import Selection
from .behavior_authority import BehaviorOption,NativeReceipt


class IntentExecutionCoordinator:
    def __init__(self,*,planner,observe,catalogue,judge,bind,snapshot,protection,journal,
                 capability_contract,max_preparations=2,max_rejections=3,max_intent_seconds=180.):
        if type(max_preparations) is not int or not 0<=max_preparations<=2 or type(max_rejections) is not int or not 1<=max_rejections<=3 or not 0<max_intent_seconds<=180:
            raise ValueError('Bounded prerequisite/rejection/intent budgets required')
        self.model=planner;self.observe_public=observe;self.catalogue=catalogue;self.judge=judge;self.bind=bind
        self.snapshot=snapshot;self.protection=protection;self.journal=journal;self.capability_contract=capability_contract
        self.max_preparations=max_preparations;self.max_rejections=max_rejections;self.max_intent_seconds=max_intent_seconds
        self.intent=None;self.model_selection=None;self.preparations=0;self.started=None;self.sequence=0
        self.execution_batch=None;self.actual_option=None;self.phase=None;self.binding_ref=None
        self.blocked_world=None;self.blocked_commands=set();self.feedback=[]

    def check_deadline(self,now):
        if self.intent is not None and now-self.started>self.max_intent_seconds:raise TimeoutError('Intent prerequisite budget exhausted; no controller retry')

    def _reject(self,reason,ref):
        self.model.reject_intent(self.intent,reason,ref)
        self.blocked_commands.add(Primitive.from_option(self.intent).command_key)
        self.feedback.append(dict(kind='revaluation',description='Execution prerequisite rejected intent: '+reason,evidence_ref=ref))
        self.feedback=self.feedback[-3:];self.intent=None;self.model_selection=None;self.started=None

    def __call__(self,now):
        self.check_deadline(now)
        before=self.snapshot()
        safety=self.protection(now)
        if safety is not None:
            if not isinstance(safety,ProtectionRequest) or self.snapshot()!=before:raise ValueError('Actual unchanged-world native safety request required')
            return safety
        if self.blocked_world!=before:self.blocked_world=before;self.blocked_commands.clear()
        # One actual acquisition per physical boundary. Rejected intentions can
        # be revised on that same immutable observation; no fake sensor tick.
        observation=self.observe_public(now)
        if observation.time_s!=now or self.snapshot()!=before:raise ValueError('Fresh read-only public observation required')
        for _ in range(self.max_rejections):
            if self.intent is None:
                options=tuple(x for x in self.catalogue(observation) if Primitive.from_option(x).command_key not in self.blocked_commands)
                if not options:raise RuntimeError('All current semantic intents rejected; no task fallback')
                self.sequence+=1
                batch=IntentBatch('ainav-intent-%06d'%self.sequence,observation,options,self.capability_contract)
                selected=self.model.select(batch)
                matches=[x for x in options if x.sha256==selected.option_sha256 and x.token==selected.token]
                if len(matches)!=1 or selected.query_sha256!=batch.sha256:raise ValueError('Exact model-selected semantic intent required')
                self.intent=matches[0];self.model_selection=selected;self.preparations=0;self.started=now
                self.journal(dict(event='skill_intent_selected',intent=asdict(self.intent),intent_sha256=self.intent.sha256,
                    semantic_query_sha256=batch.sha256,model_selection_ref=selected.evidence_ref,
                    intent_source=getattr(self.model,'decision_source','vlm_tree'),
                    counts_as_model_decision=getattr(self.model,'decision_source','vlm_tree')=='vlm_tree',physical_action_issued=False))
            status,option,ref=self.judge(self.intent,now)
            if self.snapshot()!=before:raise RuntimeError('Execution judge modified world or FIFO')
            if status=='BLOCKED':self._reject(str(option),ref);continue
            if status not in ('READY','PREPARE') or not isinstance(option,BehaviorOption):raise ValueError('Typed actual option or structured rejection required')
            if status=='PREPARE':
                if option.skill!='NAV' or self.intent.skill not in ('PUSH','CLIMB'):raise ValueError('Only existing same-support NAV may prepare an interaction')
                if self.preparations>=self.max_preparations:self._reject('prerequisite preparation limit reached',ref);continue
                self.preparations+=1
            elif option.skill!=self.intent.skill or option.parameters!=self.intent.parameters:
                raise ValueError('Judge cannot substitute another task skill or goal parameters')
            self.phase='preparation' if status=='PREPARE' else 'interaction'
            self.sequence+=1
            native=ExecutionBatch('ainav-execution-%06d'%self.sequence,observation,(option,),self.capability_contract)
            self.bind(native)
            if self.snapshot()!=before:raise RuntimeError('Native binding modified world or FIFO')
            self.execution_batch=native;self.actual_option=option;self.binding_ref=ref
            self.journal(dict(event='intent_native_execution_bound',intent_sha256=self.intent.sha256,intent=asdict(self.intent),
                execution_role=self.phase,intent_source=getattr(self.model,'decision_source','vlm_tree'),preparation_count=self.preparations,native_option=asdict(option),native_option_sha256=option.sha256,
                physical_query_sha256=native.sha256,capability_contract=self.capability_contract,physical_decision_id=native.decision_id,physical_observation_sha256=observation.sha256,model_selection_ref=self.model_selection.evidence_ref,judgment_ref=ref,
                preparation_counts_as_model_skill_selection=False,task_success_claimed=False,model_input=False))
            return native
        raise RuntimeError('No currently feasible selected intent after bounded judgment feedback; no task fallback')

    def select(self,batch):
        """Private dispatcher adapter. No second VLM or fabricated task choice."""
        if not isinstance(batch,ExecutionBatch) or batch is not self.execution_batch or self.intent is None:
            raise ValueError('Only the exact judged/bound execution batch may reach dispatch')
        o=self.actual_option
        ref=self.journal(dict(event='execution_refinement_dispatch',intent_sha256=self.intent.sha256,native_option_sha256=o.sha256,
            physical_query_sha256=batch.sha256,execution_role=self.phase,judgment_ref=self.binding_ref,
            counts_as_model_decision=False,physical_action_issued=False))
        return Selection(batch.sha256,o.token,o.sha256,Primitive.from_option(o).key,self.model_selection.tree_revision,ref)

    def observe(self,option,receipt):
        if self.intent is None or option is not self.actual_option or not isinstance(receipt,NativeReceipt) or receipt.option_sha256!=option.sha256:
            raise ValueError('Actual native outcome for current intent execution required')
        role=self.phase
        self.journal(dict(event='intent_actual_native_outcome',intent_sha256=self.intent.sha256,execution_role=role,
            native_option_sha256=option.sha256,receipt=asdict(receipt),intent_succeeded=role=='interaction' and receipt.status=='succeeded'))
        if role=='preparation' and receipt.status=='succeeded':
            # Keep the model's pending intent. A NEW acquisition/judgment must
            # precede any interaction construction, even after successful NAV.
            self.execution_batch=None;self.actual_option=None;self.phase=None;self.binding_ref=None
            return
        if role=='interaction':self.model.observe_intent(self.intent,option,receipt,self.binding_ref)
        else:self.model.reject_intent(self.intent,'native prerequisite '+receipt.status,receipt.evidence_ref)
        self.intent=None;self.model_selection=None;self.started=None;self.execution_batch=None;self.actual_option=None;self.phase=None;self.binding_ref=None
