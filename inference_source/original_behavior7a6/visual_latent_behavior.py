"""Explicit behavior successor of M64: generic skills, no task-stage actions.

Retains the original RGBD/native-history encoder, h256/z64 dynamics and learned
64x96 decoder. Separate short-horizon and option-terminal motion predictions are
trained from executed actions. Terminal success is an uncalibrated option outcome,
never a native safety/entry gate. Old checkpoints retain their original loaders.
"""
from dataclasses import asdict, replace
import hashlib
import json
import math
import torch
from torch import nn
from torch.nn import functional as F
from visual_latent_control import ControlM, load_control_checkpoint, MACROS, FIELDS
from visual_latent_highres import highres_config, DECODER_ID
from visual_latent_world_model import Belief, VisualLatentWorldModel, config_fingerprint

SKILLS = ('NAV', 'PUSH', 'CLIMB', 'EXIT_PUSH', 'RECOVER', 'HOLD')
ARCHITECTURE_ID = 'piper-M64-generic11-public60-target8-options-v1'
CHECKPOINT_FORMAT = 'piper-M64-behavior-checkpoint-v1'
MACRO_SKILL = {name: ('NAV' if name.startswith('NAV') else 'PUSH' if name.startswith('PUSH')
    else 'CLIMB' if name.startswith('CLIMB') else 'RECOVER' if name.startswith('RECOVER') else 'HOLD')
    for name in MACROS}
CONTRACT = dict(version='generic-behavior11-context68-v1',
    skills=list(SKILLS), action='6 skill onehot + public declared WORLD approachXY/10 for NAV/CLIMB only (zero for relative PUSH/EXIT/RECOVER/HOLD), declared surface height (current support for NAV/PUSH, destination support for CLIMB), initial PUSH distance, nominal interval; actual duration replaces interval before encoding',
    context='45 current public proprio +6 actually observed skill onehot +observed skill age +8 current observed target geometry; prospective target8 separate',
    no_task_stage_or_NAV_STEP_bias=True, maximum_query_image_age_s=.101,
    short_horizons_s=[.1, .5, 1., 2.], max_option_budget_s=60.,
    motion_fields=list(FIELDS), physical_std_floor_m=.002,
    terminal='Actual native option terminal motion in last-real-image axes, predicted elapsed time and native option-purpose success. An external early exit censors the hypothetical original PUSH completion; it is not a PUSH failure label.',
    terminal_condition_budget_s=60.,
    terminal_motion_clock='Last actual RGBD acquired at/before native endpoint; no exact-event image is assumed. Native receipt elapsed and image elapsed are separate labels.',
    option_success_is_safety_or_full_task_success=False, private_inputs=False,
    imagery='Short interval RGBD or hypothetical native-option-terminal RGBD, not future input or recursive actual frames')
CONTRACT_SHA = hashlib.sha256(json.dumps(CONTRACT, sort_keys=True).encode()).hexdigest()


def encode_action(raw, duration_s):
    if raw.ndim != 2 or raw.shape[1] != 11 or duration_s.shape != (len(raw),):
        raise ValueError('Generic action11 and explicit requested durations required')
    if not torch.isfinite(raw).all() or not torch.isfinite(duration_s).all():
        raise ValueError('Finite public skill/parameters required')
    one = raw[:, :6]
    if not (((one == 0) | (one == 1)).all() and (one.sum(-1) == 1).all()):
        raise ValueError('Exactly one generic native skill required')
    if (duration_s <= 0).any() or (duration_s > 60.).any():
        raise ValueError('Positive bounded declared prediction interval required')
    non_navigation = (one[:, 0]+one[:, 2]) == 0
    if (raw[non_navigation, 6:8] != 0).any():
        raise ValueError('Relative PUSH/exit/recovery must not receive a hidden measured world goal')
    if ((one[:, 1] == 1) & (raw[:, 9] <= 0)).any():
        raise ValueError('PUSH needs a positive declared distance')
    result = raw.clone()
    result[:, 6] *= 2.  # exported WORLD x/10 -> x/5
    result[:, 7] *= 10./3.
    result[:, 8:10] /= .6
    result[:, 10] = torch.log1p(duration_s)/math.log(61.)
    return result


def normalize_context(public60, target8, normalization):
    if public60.ndim != 2 or public60.shape[1] != 60 or target8.shape != (len(public60), 8):
        raise ValueError('Current public60 and separate prospective target8 required')
    if not torch.isfinite(public60).all() or not torch.isfinite(target8).all():
        raise ValueError('No private/nonfinite context or fabricated missing geometry')
    one = public60[:, 45:51]
    if not (((one == 0) | (one == 1)).all() and (one.sum(-1) == 1).all()):
        raise ValueError('Actual observed generic skill required; never candidate overwrite')
    result = public60.clone()
    result[:, :45] = (result[:, :45]-result.new_tensor(normalization['mean']))/result.new_tensor(normalization['std'])
    result[:, 51] /= 30.
    geometry = result[:, 52:60]
    target = target8.clone()
    for g in (geometry, target):
        if not ((g[:, 7] == 0) | (g[:, 7] == 1)).all():
            raise ValueError('Explicit observed-geometry validity required')
        g[:, 3:5] /= 3.
        g[:, 5] /= .005
    return torch.cat((result, target), -1)


class BehaviorM(ControlM):
    def __init__(self):
        super().__init__()
        self.architecture_id = ARCHITECTURE_ID
        self.profile_name = 'M64B'
        self.macro_action = nn.Sequential(nn.Linear(11, 64), nn.SiLU())
        self.public_context = nn.Sequential(nn.Linear(68, 256), nn.SiLU(), nn.Linear(256, 256), nn.Tanh())
        nn.init.zeros_(self.public_context[2].weight);nn.init.zeros_(self.public_context[2].bias)
        self.terminal_motion = nn.Sequential(nn.Linear(320, 128), nn.SiLU(), nn.Linear(128, 12))
        self.terminal_outcome = nn.Sequential(nn.Linear(320, 64), nn.SiLU(), nn.Linear(64, 3))
        with torch.no_grad():
            self.terminal_motion[-1].weight.zero_();self.terminal_motion[-1].bias.zero_()
            self.terminal_motion[-1].bias[6:].fill_(math.log(math.expm1(.05)))
            self.terminal_outcome[-1].bias[0] = math.log(math.expm1(3.))

    def predict_declared(self, *args, **kwargs):
        raise ValueError('Use explicit generic predict_behavior; old stage-coded action20 is incompatible')

    def imagine_candidates(self, *args, **kwargs):
        raise ValueError('Use generic behavior predictions with public action11')

    def predict_behavior(self, query, public60, target8, action11, duration_s, normalization, *, terminal=False):
        b = self._validate_state(query)
        if not query.has_observation.all() or action11.ndim != 3 or action11.shape[0] != b or action11.shape[-1] != 11:
            raise ValueError('Actual observed belief and public candidate action11 required')
        n = action11.shape[1]
        if not 1 <= n <= 16 or public60.shape != (b, 60) or target8.shape != (b, n, 8) or duration_s.shape != (b, n):
            raise ValueError('Causal context/candidate shapes differ')
        if not terminal and (duration_s > 2.01).any():
            raise ValueError('Short-horizon request exceeds2s; use explicit terminal prediction')
        age = query.time_s-query.anchor_time_s
        if (age < -1e-6).any() or (age > .101).any():
            raise ValueError('Real image/body clock exceeds causal query-age bound')
        repeated = Belief(**{k: getattr(query, k).repeat_interleave(n, 0) for k in query.__dataclass_fields__})
        context = normalize_context(public60.repeat_interleave(n, 0), target8.reshape(b*n, 8), normalization)
        repeated = replace(repeated, h=repeated.h+self.public_context(context))
        action = self.macro_action(encode_action(action11.reshape(b*n, 11), duration_s.reshape(-1)))
        prior = self._advance(repeated, action, duration_s.reshape(-1), (0., 1.), False)
        if terminal:
            raw = self.terminal_motion(prior.features)
            outcome = self.terminal_outcome(prior.features)
            result = dict(mean=raw[:, :6], std=(F.softplus(raw[:, 6:])+.002).clamp(max=5.),
                elapsed_s=F.softplus(outcome[:, 0])+.005,
                elapsed_std_s=F.softplus(outcome[:, 1])+.02,
                option_success_logits=outcome[:, 2])
            prior = replace(prior, time_s=repeated.time_s+result['elapsed_s'].double())
        else:
            result = self._decode_residual(prior)
            result.pop('event_logits')  # original risk rows remain unused/unsupervised
            velocity = public60[:, 42:45];omega = public60[:, 39:42]
            rotation = omega*age.float()[:, None]
            angle = rotation.norm(dim=-1, keepdim=True)
            cross = lambda x, y: torch.cross(x, y, dim=-1)
            velocity = velocity+torch.sinc(angle/torch.pi)*cross(rotation, velocity)+.5*torch.sinc(angle/(2*torch.pi)).square()*cross(rotation, cross(rotation, velocity))
            cv = velocity.repeat_interleave(n, 0)*(duration_s+age.float()[:, None]).reshape(-1, 1)
            baseline = result['mean'].new_zeros((b*n, 6))
            baseline[:, 2] = cv[:, 0];baseline[:, 3] = cv[:, 2];baseline[:, 4] = cv[:, 1]
            result['mean'] = result['mean']+baseline
        return {k: v.reshape(b, n, *v.shape[1:]) for k, v in result.items()}, prior

    def checkpoint_payload(self, training_updates=0):
        payload = VisualLatentWorldModel.checkpoint_payload(self, training_updates)
        payload.update(checkpoint_format=CHECKPOINT_FORMAT, contract_sha256=CONTRACT_SHA,
            decoder_id=DECODER_ID, displacement_fields=list(FIELDS), behavior_branch_trained=training_updates > 0,
            physical_control_admitted=False, native_risk_heads_supervised=False,
            option_outcome_is_safety_gate=False, training_stage='generic-skill-and-terminal-consequences-v1')
        return payload


def build_behavior_m(parent=None):
    model = BehaviorM()
    if parent is None:
        return model
    old = load_control_checkpoint(parent)
    excluded = ('macro_action.0.', 'public_context.0.', 'terminal_motion.', 'terminal_outcome.')
    copy = {k: v for k, v in old.state_dict().items() if not k.startswith(excluded)}
    missing, unexpected = model.load_state_dict(copy, strict=False)
    if unexpected or any(not k.startswith(excluded) for k in missing):
        raise ValueError('Unexpected M64 parent transfer mismatch')
    with torch.no_grad():
        aw = model.macro_action[0].weight;cw = model.public_context[0].weight
        aw.zero_();cw.zero_()
        model.macro_action[0].bias.copy_(old.macro_action[0].bias)
        model.public_context[0].bias.copy_(old.public_context[0].bias)
        cw[:, :45].copy_(old.public_context[0].weight[:, :45])
        for i, skill in enumerate(SKILLS):
            modes = [j for j, name in enumerate(MACROS) if MACRO_SKILL[name] == skill]
            if modes:
                aw[:, i].copy_(old.macro_action[0].weight[:, modes].mean(1))
                cw[:, 45+i].copy_(old.public_context[0].weight[:, [45+j for j in modes]].mean(1))
        aw[:, 6:10].copy_(old.macro_action[0].weight[:, 15:19])
        # Duration now uses explicit log scaling; old NAV_STEP bias is discarded.
        cw[:, 51].copy_(old.public_context[0].weight[:, 60])
        cw[:, 52:60].copy_(old.public_context[0].weight[:, 61:69])
        cw[:, 60:68].copy_(old.public_context[0].weight[:, 69:77])
    return model


def load_behavior_checkpoint(payload):
    if (payload.get('checkpoint_format') != CHECKPOINT_FORMAT or payload.get('architecture_id') != ARCHITECTURE_ID
            or payload.get('profile') != 'M64B' or payload.get('contract_sha256') != CONTRACT_SHA
            or payload.get('config') != asdict(highres_config())
            or payload.get('config_sha256') != config_fingerprint(highres_config())
            or payload.get('displacement_fields') != list(FIELDS)
            or payload.get('physical_control_admitted') is not False
            or payload.get('behavior_branch_trained') is not True
            or type(payload.get('training_updates')) is not int or payload['training_updates'] <= 0):
        raise ValueError('Explicit trained behavioral checkpoint required')
    model = build_behavior_m();model.load_state_dict(payload['state_dict'], strict=True)
    return model
