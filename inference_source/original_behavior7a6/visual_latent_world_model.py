"""Route-2 visual latent world model. NEW architecture, no trained weights.

Use build_visual_world_model("M") for the current candidate; the zero-argument
class constructor stays S for historical compatibility. No profile is trained.

The legacy visual_shadow_model remains a frozen wiring reference. Only its
strict RGB-D input contract is reused here. No actors, engine object features,
future observations, planner ranking or action execution are imported.

RSSM-inspired deterministic memory + diagonal-Gaussian latent. This is NOT a
reproduction of PlaNet/Dreamer or evidence of their learned performance.
"""
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import torch
from torch import nn
from torch.nn import functional as F
from visual_shadow_model import validate_visual_input, rgbd_channels, INTENT_FIELDS

ARCHITECTURE_ID = "piper-visual-latent-rssm-v1"
MEDIUM_ARCHITECTURE_ID = "piper-visual-latent-rssm-M-spatial-v1"
CHECKPOINT_FORMAT = "piper-visual-latent-profile-checkpoint-v1"
CLOCK_TOLERANCE_S = 1e-6
DISPLACEMENT_FIELDS = ("box_dx_anchor_body_m", "box_dy_anchor_body_m",
                       "robot_dx_anchor_body_m", "robot_dz_anchor_body_m")
EVENT_FIELDS = ("boundary_support_sufficient", "native_hard_stop_in_interval")


@dataclass(frozen=True)
class WorldModelConfig:
    hidden_dim: int = 96
    stochastic_dim: int = 32
    visual_dim: int = 64
    observation_dim: int = 128
    action_dim: int = 32
    min_std: float = 0.1
    max_std: float = 5.0
    reconstruction_height: int = 16
    reconstruction_width: int = 24
    max_candidates: int = 8
    max_rollout_steps: int = 8
    max_prediction_interval_s: float = 600.0  # model API bound, NOT execution permission
    visual_backbone: str = "tiny_cnn"
    spatial_rows: int = 3
    spatial_cols: int = 4
    color_feature_dim: int = 0
    prior_hidden_dim: int = 96
    posterior_hidden_dim: int = 128
    consequence_hidden_dim: int = 96


def model_config(profile):
    """Only two registered candidates; no unbudgeted scale search."""
    if profile == 'S':
        return WorldModelConfig()
    if profile == 'M':
        return WorldModelConfig(hidden_dim=256, stochastic_dim=64, visual_dim=128,
            observation_dim=256, action_dim=64, visual_backbone='residual_spatial',
            spatial_rows=4, spatial_cols=6, color_feature_dim=32,
            prior_hidden_dim=192, posterior_hidden_dim=256, consequence_hidden_dim=128)
    raise ValueError('Only registered S/M profiles are admitted')


def config_fingerprint(config):
    return hashlib.sha256(json.dumps(asdict(config),sort_keys=True,separators=(',',':')).encode()).hexdigest()


class ResidualSpatialBlock(nn.Module):
    """Per-frame GroupNorm; no BatchNorm or cross-frame batch statistics."""
    def __init__(self, inputs, outputs, stride=1):
        super().__init__()
        self.conv1=nn.Conv2d(inputs,outputs,3,stride,1,bias=False)
        self.norm1=nn.GroupNorm(8,outputs)
        self.conv2=nn.Conv2d(outputs,outputs,3,1,1,bias=False)
        self.norm2=nn.GroupNorm(8,outputs)
        self.skip=nn.Identity() if inputs==outputs and stride==1 else nn.Sequential(
            nn.Conv2d(inputs,outputs,1,stride,bias=False),nn.GroupNorm(8,outputs))

    def forward(self,x):
        out=F.silu(self.norm1(self.conv1(x)))
        return F.silu(self.norm2(self.conv2(out))+self.skip(x))


class SpatialColorFeatures(nn.Module):
    """Keep spatial raw-image color/depth cues, not simulator color labels.

    A fixed grid preserves location and brightness/chromatic information that
    normalization in the residual stream might attenuate. No object masks,
    palette lookup, color-class augmentation or privileged geometry is used.
    """
    def __init__(self,config):
        super().__init__()
        self.grid=(config.spatial_rows,config.spatial_cols)
        self.project=nn.Sequential(nn.Linear(5*self.grid[0]*self.grid[1],config.color_feature_dim),nn.SiLU())

    def forward(self,channels):
        pooled=F.adaptive_avg_pool2d(channels,self.grid)
        valid=pooled[:,4:5]
        depth=pooled[:,3:4]/valid.clamp_min(1e-6)
        grid=torch.cat((pooled[:,:3],depth,valid),dim=1)
        return self.project(grid.flatten(1))


@dataclass(frozen=True)
class Belief:
    h: torch.Tensor
    z: torch.Tensor
    mean: torch.Tensor
    std: torch.Tensor
    time_s: torch.Tensor
    anchor_time_s: torch.Tensor
    has_observation: torch.Tensor
    is_posterior: torch.Tensor

    @property
    def features(self):
        return torch.cat((self.h, self.z), dim=-1)


@dataclass(frozen=True)
class ObservationTrace:
    states: tuple
    prior_mean: torch.Tensor
    prior_std: torch.Tensor
    posterior_mean: torch.Tensor
    posterior_std: torch.Tensor

    @property
    def last(self):
        return self.states[-1]


@dataclass(frozen=True)
class ImaginedRollout:
    features: torch.Tensor
    latent_mean: torch.Tensor
    latent_std: torch.Tensor
    displacement_mean: torch.Tensor
    displacement_std: torch.Tensor
    event_logits: torch.Tensor
    time_s: torch.Tensor
    final: Belief  # flattened B*N; no actual observation was assimilated

    @property
    def event_probabilities(self):
        """Uncalibrated model scores, NOT certified safety probabilities."""
        return self.event_logits.sigmoid()

    @property
    def cumulative_displacement_mean(self):
        # Interval deltas use ONE latest-real-observation body anchor throughout.
        return self.displacement_mean.cumsum(dim=2)


class VisualObservationEncoder(nn.Module):
    def __init__(self, config):
        super().__init__()
        if config.visual_backbone == 'tiny_cnn':
            # Exact default-S module order/shapes/initialization retained.
            self.visual = nn.Sequential(
                nn.Conv2d(5, 16, 5, 2, 2), nn.SiLU(),
                nn.Conv2d(16, 24, 3, 2, 1), nn.SiLU(),
                nn.Conv2d(24, 32, 3, 2, 1), nn.SiLU(),
                nn.AdaptiveAvgPool2d((config.spatial_rows,config.spatial_cols)), nn.Flatten(),
                nn.Linear(32*config.spatial_rows*config.spatial_cols, config.visual_dim), nn.SiLU())
        else:
            self.visual = nn.Sequential(
                nn.Conv2d(5,32,5,2,2,bias=False),nn.GroupNorm(8,32),nn.SiLU(),
                ResidualSpatialBlock(32,32),ResidualSpatialBlock(32,64,2),
                ResidualSpatialBlock(64,64),ResidualSpatialBlock(64,128,2),
                ResidualSpatialBlock(128,128),
                nn.AdaptiveAvgPool2d((config.spatial_rows,config.spatial_cols)),nn.Flatten(),
                nn.Linear(128*config.spatial_rows*config.spatial_cols,config.visual_dim),nn.SiLU())
            self.spatial_color=SpatialColorFeatures(config)
        self.proprio = nn.Sequential(nn.Linear(45, 32), nn.SiLU())
        self.calibration = nn.Sequential(nn.Linear(16, 16), nn.SiLU())
        self.configured_color_dim = config.color_feature_dim
        self.fuse = nn.Sequential(nn.Linear(config.visual_dim + config.color_feature_dim + 32 + 16,
                                             config.observation_dim), nn.SiLU())

    def forward(self, packet):
        b, t, h, w = validate_visual_input(packet)
        channels = rgbd_channels(packet)
        visual = self.visual(channels).reshape(b, t, -1)
        if self.configured_color_dim:
            visual = torch.cat((visual,self.spatial_color(channels).reshape(b,t,-1)),dim=-1)
        k = packet['camera_K'].float()
        kn = torch.stack((k[:, 0, 0]/w, k[:, 1, 1]/h,
                          k[:, 0, 2]/w, k[:, 1, 2]/h), dim=-1)
        mount = packet['T_base_optical'][:, :3].reshape(b, 12).float()
        calibration = self.calibration(torch.cat((kn, mount), dim=-1))
        proprio = self.proprio(packet['proprio'].float())
        return self.fuse(torch.cat((visual, proprio,
                                   calibration[:, None].expand(b, t, -1)), dim=-1))


class VisualLatentWorldModel(nn.Module):
    """Causal observation posterior and image-free action-conditioned prior.

    Native executed 18-axis targets condition observed short-interval filtering;
    declared 8-D macros condition imagined intervals via a DIFFERENT encoder.
    Their type is explicit. Training must cover both granularities; neither
    encoder knows an executed future command sequence in advance.

    Macro target uv and goal xy are references anchored to the latest REAL
    observation/body frame, not coordinates in a fabricated future image.
    Assimilating a new real frame resets that anchor and invalidates old plans.
    """
    architecture_id = ARCHITECTURE_ID

    def __init__(self, config=None):
        super().__init__()
        self.config = config or WorldModelConfig()
        c = self.config
        if min(c.hidden_dim, c.stochastic_dim, c.visual_dim, c.observation_dim,
               c.action_dim, c.reconstruction_height, c.reconstruction_width,
               c.max_candidates, c.max_rollout_steps, c.spatial_rows, c.spatial_cols,
               c.prior_hidden_dim, c.posterior_hidden_dim, c.consequence_hidden_dim) < 1 or not 0 < c.min_std < c.max_std:
            raise ValueError('Invalid world-model configuration')
        if (c.visual_backbone not in ('tiny_cnn','residual_spatial')
                or (c.visual_backbone=='tiny_cnn' and c.color_feature_dim!=0)
                or (c.visual_backbone=='residual_spatial' and c.color_feature_dim<1)):
            raise ValueError('Invalid visual profile/color branch configuration')
        self.architecture_id=ARCHITECTURE_ID if c.visual_backbone=='tiny_cnn' else MEDIUM_ARCHITECTURE_ID
        self.profile_name='S' if c.visual_backbone=='tiny_cnn' else 'M'
        self.encoder = VisualObservationEncoder(c)
        self.native_action = nn.Sequential(nn.Linear(19, c.action_dim), nn.SiLU())
        self.macro_action = nn.Sequential(nn.Linear(len(INTENT_FIELDS), c.action_dim), nn.SiLU())
        self.dynamics = nn.GRUCell(c.stochastic_dim + c.action_dim + 2 + 1, c.hidden_dim)
        self.prior = nn.Sequential(nn.Linear(c.hidden_dim, c.prior_hidden_dim), nn.SiLU(),
                                   nn.Linear(c.prior_hidden_dim, 2*c.stochastic_dim))
        self.posterior = nn.Sequential(nn.Linear(c.hidden_dim + c.observation_dim, c.posterior_hidden_dim),
                                       nn.SiLU(), nn.Linear(c.posterior_hidden_dim, 2*c.stochastic_dim))
        feature_dim = c.hidden_dim + c.stochastic_dim
        # Mean/std for 4 interval displacements + 2 event logits. No ranking.
        self.consequences = nn.Sequential(nn.Linear(feature_dim, c.consequence_hidden_dim), nn.SiLU(), nn.Linear(c.consequence_hidden_dim, 10))
        # Low-resolution observation reconstruction is a TRAINING auxiliary,
        # not a full video generator or a claim of meaningful generated images.
        self.observation_decoder = nn.Sequential(nn.Linear(feature_dim, 192), nn.SiLU(),
            nn.Linear(192, 5*c.reconstruction_height*c.reconstruction_width))
        self.proprio_decoder = nn.Sequential(nn.Linear(feature_dim, 64), nn.SiLU(), nn.Linear(64, 45))

    def checkpoint_payload(self,training_updates=0):
        """Metadata separates S/M; saving a random model never implies fitting."""
        if type(training_updates) is not int or training_updates<0:
            raise ValueError('Explicit nonnegative training update count required')
        return dict(checkpoint_format=CHECKPOINT_FORMAT,architecture_id=self.architecture_id,
                    profile=self.profile_name,config=asdict(self.config),
                    config_sha256=config_fingerprint(self.config),training_updates=training_updates,
                    state_dict={k:v.detach().clone() for k,v in self.state_dict().items()})

    @property
    def device(self):
        return next(self.parameters()).device

    def _normal(self, raw):
        mean, raw_std = raw.chunk(2, dim=-1)
        std = (F.softplus(raw_std) + self.config.min_std).clamp(max=self.config.max_std)
        return mean, std

    @staticmethod
    def _value(mean, std, sample):
        return mean + std*torch.randn_like(std) if sample else mean

    def initial_state(self, time_s):
        if (not isinstance(time_s, torch.Tensor) or time_s.ndim != 1
                or time_s.device != self.device or not time_s.is_floating_point()
                or not torch.isfinite(time_s).all() or (time_s < 0).any()):
            raise ValueError('Finite nonnegative initial clock [B] required')
        b = len(time_s)
        if b < 1:
            raise ValueError('Empty state')
        h = torch.zeros(b, self.config.hidden_dim, device=self.device)
        z = torch.zeros(b, self.config.stochastic_dim, device=self.device)
        return Belief(h, z, z.clone(), torch.ones_like(z), time_s.double().clone(),
                      time_s.double().clone(), torch.zeros(b, dtype=torch.bool, device=self.device),
                      torch.zeros(b, dtype=torch.bool, device=self.device))

    def _validate_state(self, state):
        if not isinstance(state, Belief):
            raise ValueError('Versioned visual Belief required, not a legacy state vector')
        b = state.h.shape[0]
        dims = {'h': (b, self.config.hidden_dim), 'z': (b, self.config.stochastic_dim),
                'mean': (b, self.config.stochastic_dim), 'std': (b, self.config.stochastic_dim),
                'time_s': (b,), 'anchor_time_s': (b,),
                'has_observation': (b,), 'is_posterior': (b,)}
        for name, shape in dims.items():
            v = getattr(state, name)
            if tuple(v.shape) != shape or v.device != self.device:
                raise ValueError('Belief shape/device mismatch: '+name)
            if name in ('has_observation', 'is_posterior'):
                if v.dtype != torch.bool:
                    raise ValueError('Belief flags must be boolean')
            elif not v.is_floating_point() or not torch.isfinite(v).all():
                raise ValueError('Nonfinite/nonfloating belief')
        if (state.std <= 0).any() or (state.time_s < state.anchor_time_s).any():
            raise ValueError('Invalid belief distribution/clock')
        return b

    def _advance(self, state, action_embedding, duration_s, action_kind, sample=False):
        if (not torch.isfinite(duration_s).all() or (duration_s <= 0).any()
                or (duration_s > self.config.max_prediction_interval_s).any()):
            raise ValueError('Prediction duration out of declared model range')
        kind = state.h.new_tensor(action_kind).expand(len(state.h), 2)
        inp = torch.cat((state.z, action_embedding, kind,
                         torch.log1p(duration_s.float())[:, None]), dim=-1)
        h = self.dynamics(inp, state.h)
        mean, std = self._normal(self.prior(h))
        return Belief(h, self._value(mean, std, sample), mean, std,
                      state.time_s + duration_s.double(), state.anchor_time_s,
                      state.has_observation, torch.zeros_like(state.is_posterior))

    def observe(self, packet, initial=None, sample=False):
        """Filter only real history. No future labels/macros are accepted.

        A timestamp already assimilated as a posterior cannot be counted twice.
        For a forecast at exactly the next real frame time, use correct().
        """
        b, t, _, _ = validate_visual_input(packet)
        if packet['rgb'].device != self.device:
            raise ValueError('Packet/model device mismatch')
        embedding = self.encoder(packet)
        state = self.initial_state(packet['timestamps_s'][:, 0]) if initial is None else initial
        if self._validate_state(state) != b:
            raise ValueError('Observation/state batch mismatch')
        states, pmeans, pstds, qmeans, qstds = [], [], [], [], []
        for i in range(t):
            clock = packet['timestamps_s'][:, i].double()
            dt = clock - state.time_s
            same_time = dt.abs() <= CLOCK_TOLERANCE_S
            if (dt < -CLOCK_TOLERANCE_S).any() or (same_time & state.is_posterior).any():
                raise ValueError('Out-of-order or duplicate real observation')
            advanced = dt > CLOCK_TOLERANCE_S
            if advanced.any():
                action = torch.cat((packet['actions_previous'][:, i].float(),
                    packet['action_valid'][:, i, None].float()), dim=-1)
                proposal = self._advance(state, self.native_action(action),
                    dt.clamp_min(1e-9), (1., 0.), sample)
                fields = {}
                for key in state.__dataclass_fields__:
                    old, new = getattr(state, key), getattr(proposal, key)
                    mask = advanced[:, None] if old.ndim == 2 else advanced
                    fields[key] = torch.where(mask, new, old)
                state = Belief(**fields)
            pmeans.append(state.mean); pstds.append(state.std)
            mean, std = self._normal(self.posterior(torch.cat((state.h, embedding[:, i]), dim=-1)))
            state = replace(state, z=self._value(mean, std, sample), mean=mean, std=std,
                            time_s=clock, anchor_time_s=clock,
                            has_observation=torch.ones_like(state.has_observation),
                            is_posterior=torch.ones_like(state.is_posterior))
            states.append(state); qmeans.append(mean); qstds.append(std)
        return ObservationTrace(tuple(states), torch.stack(pmeans, 1), torch.stack(pstds, 1),
                                torch.stack(qmeans, 1), torch.stack(qstds, 1))

    def correct(self, prior, real_packet, sample=False):
        """Correct an imagined PRIOR at its exact timestamp, using a real frame.

        Do not relabel/tile an old frame as future feedback. That provenance
        must be enforced by the acquisition/data loader, not this tensor API.
        """
        validate_visual_input(real_packet)
        self._validate_state(prior)
        if (real_packet['rgb'].shape[1] != 1 or prior.is_posterior.any()
                or not torch.allclose(real_packet['timestamps_s'][:, 0].double(), prior.time_s, atol=CLOCK_TOLERANCE_S, rtol=0)):
            raise ValueError('Correction needs one new real frame at prior time, not a posterior replay')
        return self.observe(real_packet, initial=prior, sample=sample).last

    def decode_consequences(self, state):
        self._validate_state(state)
        raw = self.consequences(state.features)
        std = (F.softplus(raw[:, 4:8]) + self.config.min_std).clamp(max=self.config.max_std)
        return {'mean': raw[:, :4], 'std': std, 'event_logits': raw[:, 8:]}

    def decode_observation(self, state):
        self._validate_state(state)
        c = self.config
        raw = self.observation_decoder(state.features).reshape(-1, 5, c.reconstruction_height,
                                                               c.reconstruction_width)
        return {'rgb': raw[:, :3].sigmoid(), 'depth_normalized': raw[:, 3:4].sigmoid(),
                'depth_valid_logits': raw[:, 4:5], 'proprio': self.proprio_decoder(state.features)}

    def imagine_candidates(self, belief, macro_intents, durations_s, anchor_times_s, sample=False):
        """Open-loop priors ONLY: [B,N,H,8] actions, [B,N,H] durations.

        All target uv/goal coordinates refer to the latest real anchor. A plan
        from before an observation correction is rejected. No future images,
        object truth, native actor commands or future labels can be passed.
        """
        b = self._validate_state(belief)
        if not belief.has_observation.all():
            raise ValueError('Cannot imagine from a state that never received RGB-D')
        if (not isinstance(macro_intents, torch.Tensor) or macro_intents.ndim != 4
                or macro_intents.shape[0] != b or macro_intents.shape[-1] != 8
                or macro_intents.device != self.device or not macro_intents.is_floating_point()
                or not torch.isfinite(macro_intents).all()):
            raise ValueError('Finite declared macro actions [B,N,H,8] required')
        _, n, horizon, _ = macro_intents.shape
        if not 1 <= n <= self.config.max_candidates or not 1 <= horizon <= self.config.max_rollout_steps:
            raise ValueError('Candidate/horizon exceeds model API bound (not an execution budget)')
        if (not isinstance(durations_s, torch.Tensor) or tuple(durations_s.shape) != (b, n, horizon)
                or durations_s.device != self.device or not durations_s.is_floating_point()
                or not torch.isfinite(durations_s).all() or (durations_s <= 0).any()
                or (durations_s > self.config.max_prediction_interval_s).any()):
            raise ValueError('Finite positive per-macro durations [B,N,H] required')
        if (not isinstance(anchor_times_s, torch.Tensor) or tuple(anchor_times_s.shape) != (b,)
                or anchor_times_s.device != self.device or not anchor_times_s.is_floating_point()
                or not torch.allclose(anchor_times_s.double(), belief.anchor_time_s, atol=CLOCK_TOLERANCE_S, rtol=0)):
            raise ValueError('Stale/wrong image-body anchor; regenerate plans after correction')
        modes = macro_intents[..., :3]
        if (not ((modes == 0) | (modes == 1)).all() or not (modes.sum(-1) == 1).all()
                or ((macro_intents[..., 5:7] < 0) | (macro_intents[..., 5:7] > 1)).any()
                or (macro_intents[..., 7] < 0).any()):
            raise ValueError('One NAV/PUSH/CLIMB mode, normalized anchor uv, nonnegative distance required')
        state = Belief(**{name: getattr(belief, name).repeat_interleave(n, dim=0)
                          for name in belief.__dataclass_fields__})
        features, means, stds, dmeans, dstds, logits, clocks = [], [], [], [], [], [], []
        for i in range(horizon):
            act = macro_intents[:, :, i].reshape(b*n, 8).float()
            state = self._advance(state, self.macro_action(act),
                                  durations_s[:, :, i].reshape(b*n), (0., 1.), sample)
            pred = self.decode_consequences(state)
            features.append(state.features); means.append(state.mean); stds.append(state.std)
            dmeans.append(pred['mean']); dstds.append(pred['std']); logits.append(pred['event_logits'])
            clocks.append(state.time_s)
        pack = lambda xs: torch.stack(xs, 1).reshape(b, n, horizon, *xs[0].shape[1:])
        return ImaginedRollout(pack(features), pack(means), pack(stds), pack(dmeans),
                               pack(dstds), pack(logits), pack(clocks), state)

    def forward(self, history, macro_intents, durations_s, sample=False):
        trace = self.observe(history, sample=sample)
        return trace, self.imagine_candidates(trace.last, macro_intents, durations_s,
                                              trace.last.anchor_time_s, sample=sample)


def build_visual_world_model(profile='M'):
    """Current main entry defaults to M; zero-arg class stays historical S."""
    return VisualLatentWorldModel(model_config(profile))


def load_profile_checkpoint(payload,expected_profile):
    """Strict CPU/profile import. Legacy raw checkpoints need explicit handling."""
    config=model_config(expected_profile)
    expected_id=ARCHITECTURE_ID if expected_profile=='S' else MEDIUM_ARCHITECTURE_ID
    if (not isinstance(payload,dict) or payload.get('checkpoint_format')!=CHECKPOINT_FORMAT
            or payload.get('architecture_id')!=expected_id or payload.get('profile')!=expected_profile
            or payload.get('config')!=asdict(config)
            or payload.get('config_sha256')!=config_fingerprint(config)
            or type(payload.get('training_updates')) is not int or payload['training_updates']<0):
        raise ValueError('Checkpoint profile/config/version mismatch; no silent S/M or legacy conversion')
    model=build_visual_world_model(expected_profile)
    model.load_state_dict(payload['state_dict'],strict=True)
    return model
