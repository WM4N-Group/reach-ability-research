"""Task intents are NOT native options, entry receipts, or motor permission."""
from dataclasses import dataclass,asdict
import json
from .contracts import DecisionBatch,Observation,Primitive,canonical,sha,text,finite
from .native.behavior_authority import BehaviorOption


@dataclass(frozen=True)
class SkillIntent:
    token: str
    skill: str
    target_ref: str
    parameters: tuple
    budget_s: float = 60.

    def __post_init__(self):
        text(self.token,'intent token',160)
        Primitive(self.skill,self.target_ref,self.parameters)
        if self.skill not in ('NAV','PUSH','CLIMB','HOLD') or not finite(self.budget_s) or not 0<self.budget_s<=60:
            raise ValueError('Task-progress intent and bounded native interval required')

    @property
    def mandatory_protection(self):return False
    @property
    def sha256(self):return sha(dict(layer='semantic_skill_intent',**asdict(self)))


@dataclass(frozen=True)
class IntentBatch(DecisionBatch):
    """Reuse the AINav tree input protocol without pretending entry admission."""
    semantic_intents_only = True

    def __post_init__(self):
        text(self.decision_id,'intent decision ID',160)
        if not isinstance(self.observation,Observation):raise ValueError('Actual public observation required')
        c=json.loads(self.capability_contract)
        if canonical(c)!=self.capability_contract or set(c)!={'source_ref','skills','constraints'}:
            raise ValueError('Canonical explicit intent capability contract required')
        text(c['source_ref'],'intent capability source')
        if (not isinstance(c['skills'],list) or not c['skills'] or len(set(c['skills']))!=len(c['skills'])
            or not set(c['skills'])<={'NAV','PUSH','CLIMB','HOLD'} or not isinstance(c['constraints'],list)
            or not 1<=len(c['constraints'])<=64):raise ValueError('Bounded task-intent capability contract required')
        for x in c['constraints']:text(x,'intent constraint',2048)
        if (not isinstance(self.options,tuple) or not 1<=len(self.options)<=128
            or not all(isinstance(x,SkillIntent) for x in self.options)
            or len({x.token for x in self.options})!=len(self.options)
            or any(x.skill not in c['skills'] or x.target_ref not in self.observation.targets for x in self.options)):
            raise ValueError('Distinct declared/observed task intents required; no native permission implied')

    @property
    def sha256(self):return sha(dict(layer='semantic_skill_intent',decision_id=self.decision_id,
        observation_sha256=self.observation.sha256,intents=[x.sha256 for x in self.options],capability_contract=self.capability_contract))

    def public(self):
        value=super().public()
        value.update(decision_layer='semantic_skill_intent',execution_policy='The listed first actions are INTENTS, not current native admissions. Select task/object/skill; an independent execution judge handles trained spatial entry limits, safe same-support positioning and rechecks. Never claim a future success.')
        return value


@dataclass(frozen=True)
class ExecutionBatch(DecisionBatch):
    """Private, strict native batch. It must never be sent to the VLM."""
    def public(self):raise ValueError('Private execution bindings must never be model input')
