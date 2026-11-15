"""Immutable public inputs and symbolic primitives, not a state-transition model."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from .native.behavior_authority import BehaviorOption, NativeReceipt, SKILLS


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def exact(value, keys, what):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError('Exact '+what+' fields required')


def text(value, what, limit=2048):
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError('Bounded nonempty '+what+' required')
    return value


@dataclass(frozen=True)
class Primitive:
    skill: str
    target_ref: str
    parameters: tuple = ()
    preconditions: tuple = ()

    def __post_init__(self):
        if self.skill not in SKILLS:
            raise ValueError('Unsupported native primitive')
        text(self.target_ref, 'observable/declared target reference', 160)
        allowed = {'goal_world_x_m', 'goal_world_y_m', 'surface_height_m',
                   'push_distance_m', 'requested_interval_s'}
        if not isinstance(self.parameters, tuple) or any(not isinstance(x, tuple) or len(x) != 2 for x in self.parameters):
            raise ValueError('Immutable parameter pairs required')
        keys = [x[0] for x in self.parameters]
        if keys != sorted(set(keys)) or not set(keys) <= allowed or any(not finite(v) for _, v in self.parameters):
            raise ValueError('Unique finite declared primitive parameters required')
        if any(k in ('push_distance_m', 'requested_interval_s') and v <= 0 for k, v in self.parameters):
            raise ValueError('Positive distance/interval required')
        if (not isinstance(self.preconditions, tuple) or len(set(self.preconditions)) != len(self.preconditions)
                or any(not isinstance(x, str) or not x or len(x) > 240 for x in self.preconditions)):
            raise ValueError('Bounded symbolic preconditions required')

    @property
    def command_key(self):
        return sha(dict(skill=self.skill, target_ref=self.target_ref,
                        parameters={k:float(round(v,12)) for k,v in self.parameters}))

    @property
    def key(self):
        return sha(self.public())

    def public(self):
        return dict(skill=self.skill, target_ref=self.target_ref,
                    parameters=dict(self.parameters), preconditions=list(self.preconditions))

    @classmethod
    def parse(cls, value):
        if isinstance(value,dict) and value.get('hypothesis_only') is True:
            value={k:v for k,v in value.items() if k!='hypothesis_only'}
        exact(value, ('skill', 'target_ref', 'parameters', 'preconditions'), 'primitive')
        if not isinstance(value['parameters'], dict) or not isinstance(value['preconditions'], list):
            raise ValueError('Object parameters and list preconditions required')
        return cls(value['skill'], value['target_ref'], tuple(sorted(value['parameters'].items())),
                   tuple(value['preconditions']))

    @classmethod
    def from_option(cls, option):
        return cls(option.skill, option.target_ref, option.parameters)


@dataclass(frozen=True)
class SkillPlan:
    plan_id: str
    steps: tuple
    reaches_goal: bool
    evidence_summary: str | None = None

    def __post_init__(self):
        text(self.plan_id, 'plan ID', 80)
        if not isinstance(self.steps, tuple) or not 1 <= len(self.steps) <= 16 or not all(isinstance(x, Primitive) for x in self.steps):
            raise ValueError('One to sixteen typed primitive steps required')
        if type(self.reaches_goal) is not bool:
            raise ValueError('Explicit hypothetical terminal-goal flag required')
        if self.evidence_summary is not None:
            text(self.evidence_summary, 'plan evidence summary', 2048)

    @classmethod
    def parse(cls, value, targets):
        fields = ('plan_id', 'steps', 'reaches_goal')
        if isinstance(value, dict) and 'evidence_summary' in value:
            # Explicit optional explanation, never a primitive/goal/admission edit.
            fields += ('evidence_summary',)
            text(value['evidence_summary'], 'plan evidence summary', 2048)
        exact(value, fields, 'skill plan')
        if not isinstance(value['steps'], list):
            raise ValueError('Step list required')
        steps = tuple(Primitive.parse(x) for x in value['steps'])
        if any(x.target_ref not in targets for x in steps):
            raise ValueError('Plan invented an unobserved/undeclared target')
        return cls(value['plan_id'], steps, value['reaches_goal'], value.get('evidence_summary'))


# Caller must use the real public observation adapter. This boundary rejects
# common leaks; the input audit/provenance is still necessary, not proved by names.
PUBLIC_STATE = {'q', 'dq', 'gravity', 'angular_velocity', 'linear_velocity',
                'support_surface', 'posture', 'localization', 'task_status', 'skill_status'}
OBJECT_FIELDS = {'target_ref', 'label', 'bbox_xyxy', 'geometry', 'evidence_ref'}


@dataclass(frozen=True)
class Observation:
    encoded: str

    def __post_init__(self):
        value = json.loads(self.encoded)
        if canonical(value) != self.encoded:
            raise ValueError('Canonical immutable public observation required')
        exact(value, ('time_s', 'rgb', 'objects', 'public_state', 'declared_map', 'goal', 'events'), 'public observation')
        if not finite(value['time_s']) or value['time_s'] < 0:
            raise ValueError('Actual nonnegative sensor clock required')
        exact(value['rgb'], ('path', 'sha256', 'time_s', 'width', 'height'), 'real RGB frame')
        rgb = value['rgb']
        if (not isinstance(rgb['path'], str) or not Path(rgb['path']).is_absolute()
                or not isinstance(rgb['sha256'], str) or len(rgb['sha256']) != 64
                or any(c not in '0123456789abcdef' for c in rgb['sha256'])
                or not finite(rgb['time_s']) or not 0 <= rgb['time_s'] <= value['time_s']
                or any(type(rgb[k]) is not int or rgb[k] <= 0 for k in ('width', 'height'))):
            raise ValueError('Absolute real RGB path, hash, dimensions and causal timestamp required')
        if value['time_s'] - rgb['time_s'] > .100001:
            raise ValueError('Stale RGB cannot ground a current native decision')
        if not isinstance(value['objects'], list) or len(value['objects']) > 64:
            raise ValueError('Bounded observed objects required')
        refs = []
        for obj in value['objects']:
            exact(obj, OBJECT_FIELDS, 'observed object')
            refs.append(text(obj['target_ref'], 'observed target reference', 160))
            text(obj['label'], 'visual label', 160)
            text(obj['evidence_ref'], 'object evidence reference')
            b = obj['bbox_xyxy']
            if (not isinstance(b, list) or len(b) != 4 or not all(finite(x) for x in b)
                    or not 0 <= b[0] < b[2] <= rgb['width'] or not 0 <= b[1] < b[3] <= rgb['height']):
                raise ValueError('Observed pixel box must be inside the actual frame')
            # Geometry comes from measured RGBD/static declaration, never GT.
            g = obj['geometry']
            exact(g, ('status', 'source', 'values', 'uncertainty'), 'public geometry')
            if g['status'] not in ('unknown', 'measured', 'declared') or g['source'] not in ('unavailable', 'RGBD', 'declared_map'):
                raise ValueError('Explicit non-private geometry provenance required')
            allowed_geometry = {'center_xyz_m', 'size_xyz_m'}
            if (not isinstance(g['values'], dict) or not set(g['values']) <= allowed_geometry
                    or not isinstance(g['uncertainty'], dict) or not set(g['uncertainty']) <= allowed_geometry):
                raise ValueError('Only explicit public position/dimension estimates and uncertainty allowed')
            for values in (g['values'], g['uncertainty']):
                for key, vector in values.items():
                    if not isinstance(vector, list) or len(vector) != 3 or not all(finite(x) for x in vector):
                        raise ValueError('Finite three-vector measured geometry required')
                    if (values is g['uncertainty'] or key == 'size_xyz_m') and any(x < 0 for x in vector):
                        raise ValueError('Nonnegative size/uncertainty required')
            if g['status'] == 'unknown' and (g['source'] != 'unavailable' or g['values'] or g['uncertainty']):
                raise ValueError('Unknown geometry must not contain invented numbers')
            if g['status'] != 'unknown' and (not g['values'] or set(g['values']) != set(g['uncertainty'])
                    or g['source'] != ('RGBD' if g['status'] == 'measured' else 'declared_map')):
                raise ValueError('Geometry estimate requires matching uncertainty and source')
        if len(refs) != len(set(refs)):
            raise ValueError('Distinct observed object IDs required')
        if not isinstance(value['public_state'], dict) or not set(value['public_state']) <= PUBLIC_STATE:
            raise ValueError('Only whitelisted public robot channels allowed')
        exact(value['declared_map'], ('source_ref', 'anchors'), 'declared static map')
        text(value['declared_map']['source_ref'], 'static map source')
        if not isinstance(value['declared_map']['anchors'], list) or len(value['declared_map']['anchors']) > 64:
            raise ValueError('Bounded declared anchor list required')
        anchor_refs = []
        for anchor in value['declared_map']['anchors']:
            exact(anchor, ('target_ref', 'description', 'position_xyz_m', 'uncertainty_xyz_m'), 'static anchor')
            anchor_refs.append(text(anchor['target_ref'], 'static target', 160))
            text(anchor['description'], 'static geometry description')
            for key in ('position_xyz_m', 'uncertainty_xyz_m'):
                x = anchor[key]
                if not isinstance(x, list) or len(x) != 3 or not all(finite(y) for y in x):
                    raise ValueError('Finite explicit declared geometry/uncertainty required')
            if any(x < 0 for x in anchor['uncertainty_xyz_m']):
                raise ValueError('Nonnegative map uncertainty required')
        if len(set(refs + anchor_refs)) != len(refs + anchor_refs):
            raise ValueError('Observed and declared target references must be globally unambiguous')
        text(value['goal'], 'final task instruction', 4096)
        if (not isinstance(value['events'], list) or len(value['events']) > 32
                or any(not isinstance(x, dict) or set(x) != {'kind', 'description', 'evidence_ref'}
                       or x['kind'] not in ('failure', 'new_objects', 'revaluation', 'completion')
                       or not isinstance(x['description'], str) or len(x['description']) > 2048
                       or not isinstance(x['evidence_ref'], str) or not x['evidence_ref'] for x in value['events'])):
            raise ValueError('Only bounded actual public event evidence allowed')
        # No arbitrary nested state payloads where private catalogues could hide.
        self._audit_state(value['public_state'])

    @staticmethod
    def _audit_state(state):
        for key, value in state.items():
            if key in ('q', 'dq', 'gravity', 'angular_velocity', 'linear_velocity'):
                if not isinstance(value, list) or len(value) != (18 if key in ('q', 'dq') else 3) or not all(finite(x) for x in value):
                    raise ValueError('Finite explicit public proprioception vector required')
            elif not isinstance(value, str) or len(value) > 1024:
                raise ValueError('Bounded public status text required; arbitrary nested state rejected')

    @classmethod
    def create(cls, value):
        return cls(canonical(value))

    @property
    def value(self):
        return json.loads(self.encoded)

    @property
    def sha256(self):
        return hashlib.sha256(self.encoded.encode()).hexdigest()

    @property
    def time_s(self):
        return self.value['time_s']

    @property
    def targets(self):
        v = self.value
        return frozenset([x['target_ref'] for x in v['objects']] + [x['target_ref'] for x in v['declared_map']['anchors']])

    def verify_image(self):
        value = self.value['rgb']
        if file_sha(value['path']) != value['sha256']:
            raise ValueError('Observed image bytes changed before inference')
        return Path(value['path'])


@dataclass(frozen=True)
class DecisionBatch:
    decision_id: str
    observation: Observation
    options: tuple
    capability_contract: str

    def __post_init__(self):
        text(self.decision_id, 'unique decision ID', 160)
        capability = json.loads(self.capability_contract)
        if canonical(capability) != self.capability_contract:
            raise ValueError('Canonical immutable native capability contract required')
        exact(capability, ('source_ref', 'skills', 'constraints'), 'native capability contract')
        text(capability['source_ref'], 'frozen native capability source')
        if (not isinstance(capability['skills'], list) or not capability['skills']
                or not all(isinstance(x, str) and x in SKILLS for x in capability['skills'])
                or len(set(capability['skills'])) != len(capability['skills'])
                or not isinstance(capability['constraints'], list) or not 1 <= len(capability['constraints']) <= 64
                or any(not isinstance(x, str) or not x or len(x) > 2048 for x in capability['constraints'])):
            raise ValueError('Actual supported skills and explicit bounded native constraints required')
        if not isinstance(self.observation, Observation):
            raise ValueError('Typed immutable observed context required')
        if (not isinstance(self.options, tuple) or not 1 <= len(self.options) <= 128
                or not all(isinstance(x, BehaviorOption) for x in self.options)):
            raise ValueError('Bounded frozen native-admitted option catalogue required')
        if len({x.token for x in self.options}) != len(self.options):
            raise ValueError('Distinct native candidate tokens required')
        if any(x.skill not in capability['skills'] for x in self.options):
            raise ValueError('Native catalogue includes an undeclared capability')
        if any(x.target_ref not in self.observation.targets for x in self.options):
            raise ValueError('Native catalogue target lacks public evidence/declaration')
        mandatory = [x for x in self.options if x.mandatory_protection]
        if mandatory and (len(mandatory) != 1 or len(self.options) != 1):
            raise ValueError('Mandatory protection must not be mixed with task choices')

    @property
    def sha256(self):
        return sha(dict(decision_id=self.decision_id, observation_sha256=self.observation.sha256,
                        options=[x.sha256 for x in self.options], capability_contract=self.capability_contract))

    def public(self):
        return dict(decision_id=self.decision_id, query_sha256=self.sha256,
                    observation=self.observation.value, capability_contract=json.loads(self.capability_contract),
                    admitted_first_actions=[dict(token=x.token, **Primitive.from_option(x).public()) for x in self.options])


@dataclass(frozen=True)
class ProtectionRequest:
    """Native-only safety request: must work even when vision/VLM is unavailable."""
    decision_id: str
    time_s: float
    option: BehaviorOption
    native_evidence_ref: str

    def __post_init__(self):
        text(self.decision_id, 'unique safety decision ID', 160)
        text(self.native_evidence_ref, 'actual native protection evidence')
        if (not finite(self.time_s) or self.time_s < 0 or not isinstance(self.option, BehaviorOption)
                or not self.option.mandatory_protection or self.option.skill not in ('EXIT_PUSH', 'RECOVER', 'HOLD')):
            raise ValueError('Actual native-only mandatory protection required')

    @property
    def options(self):
        return (self.option,)

    @property
    def sha256(self):
        return sha(dict(decision_id=self.decision_id, time_s=self.time_s,
                        option_sha256=self.option.sha256, native_evidence_ref=self.native_evidence_ref))
