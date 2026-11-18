"""Small one-decision categorical policy, not multi-step PPO or whole-body RL.

Used only after a registered real collector supplies complete qualified episodes.
CPU tests exercise the math with clearly synthetic returns, never train a model.
"""
from math import exp, isfinite
from random import Random
from dataclasses import dataclass
from hashlib import sha256
import json

from episode_feedback import reward


@dataclass(frozen=True)
class PolicyState:
    logits: tuple
    update_count: int = 0

    def __post_init__(self):
        if type(self.logits) is not tuple or not 2 <= len(self.logits) <= 8 or not all(
                type(x) in (float,int) and isfinite(x) for x in self.logits):
            raise ValueError('Explicit finite categorical policy in immutable action order')
        if type(self.update_count) is not int or self.update_count < 0:
            raise ValueError('Monotone update counter')

    def probabilities(self):
        top = max(self.logits)
        weights = [exp(x-top) for x in self.logits]
        return tuple(w/sum(weights) for w in weights)

    def fingerprint(self):
        return sha256(json.dumps((self.logits,self.update_count),separators=(',',':'),allow_nan=False).encode()).hexdigest()

    def draw(self, rng):
        if type(rng) is not Random:
            raise TypeError('Explicit seeded per-worker sampler')
        return rng.choices(range(len(self.logits)), weights=self.probabilities(), k=1)[0]


def collect_gradient(policy, actions, attempts, *, registered_program, allocated_ancestors, used_rollout_ids):
    """Return raw score-function gradient, known denominator and consumed IDs.

    Caller must use one unchanged policy version for every worker batch and freeze
    training distribution before collection. No implicit importance correction.
    """
    if tuple(a.index for a in actions)!=tuple(range(len(policy.logits))) or len(actions)!=len(policy.logits):
        raise ValueError('Frozen action order and dimension')
    exact=tuple(actions);seen=set(used_rollout_ids);accepted=[];censored=[];prob=policy.probabilities();g=[0.] * len(prob)
    for a in attempts:
        if a.behavior_policy_sha256!=policy.fingerprint():
            raise ValueError('Stale/mixed behavior policy: no implicit off-policy update')
        if a.rollout_id in seen:
            raise ValueError('Duplicate rollout; no replay or repeat fit')
        seen.add(a.rollout_id)
        if not 0<=a.used_action.index<len(exact) or exact[a.used_action.index]!=a.used_action:
            raise ValueError('The action attached to this attempt drifted from its preregistration')
        y=reward(a,registered_program=registered_program,allocated_ancestors=allocated_ancestors)
        if y is None:
            censored.append(a.rollout_id);continue
        accepted.append(a.rollout_id)
        # An on-policy baseline independent of the sampled action (fixed 0.5).
        for j,p in enumerate(prob):g[j]+=(y-.5)*(float(j==a.used_action.index)-p)
    return tuple(g),tuple(accepted),tuple(censored)


def apply_gradient(policy, gradient, complete_count, *, rate):
    if type(rate) not in (float,int) or not isfinite(rate) or not 0.<rate<=1.:
        raise ValueError('Finite preregistered step size')
    if type(complete_count) is not int or complete_count < 1:
        raise ValueError('No optimizer update without real qualified rewards')
    if len(gradient)!=len(policy.logits) or not all(type(x) in (int,float) and isfinite(x) for x in gradient):
        raise ValueError('Finite batch with exactly the connector head shape')
    return PolicyState(tuple(x+rate*g/complete_count for x,g in zip(policy.logits,gradient)),policy.update_count+1)
