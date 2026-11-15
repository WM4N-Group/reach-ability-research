"""Public-file -> original AINav IntentPlanner binding, never a native launcher.

Data passes the resulting planner to the source-owned ComplexSceneDriver.
Only the two pinned PUBLIC files are read. No scene constructor, private pose,
existence route, calibration, training artifact or native namespace is loaded.
"""
from hashlib import sha256
import json
import math
from pathlib import Path
from types import MappingProxyType
from .complex_intent_planner import ComplexIntentPlanner, _original_intent_batch_type
from .complex_public_model import PublicSceneModel

# Common A/B settings. Depth counts decision bundles, not native requests.
COMMON_LIMITS = MappingProxyType(dict(max_depth=4, max_transitions=256, max_wall_s=.25))


def _xy_key(xy):
    if len(xy) != 2 or any(type(x) not in (int, float) or not math.isfinite(x) for x in xy):
        raise ValueError('Finite public declaration XY required')
    # Same source declaration arithmetic, NOT a sensor/goal tolerance.
    return tuple(round(float(x), 12) for x in xy)


def declared_nav_xy(model):
    """All public NAV declarations, not a selected or prescribed task route."""
    points = [*model.points]
    for obj in model.objects:
        for x in (obj['initial_xy_m'][0], *obj['allowed_placement_x_m']):
            points.append((x - obj['size_m'][0] / 2 - model.setback, obj['initial_xy_m'][1]))
    points.append(model.goal_xy)
    return tuple(dict.fromkeys(_xy_key(p) for p in points))


class SourceBoundComplexIntentPlanner(ComplexIntentPlanner):
    """Validate the entire fresh common catalogue, not just the chosen option.

    The nominal search must not plan through an unavailable goal, a hidden extra
    action or an independently reordered PUSH domain. Original native admission
    remains solely the judge/factory's job. These checks grant no permission.
    """
    decision_source = 'reach_public_finite_common_domain'

    def __init__(self, model, *, method, journal, terminal_target_ref, source_pins):
        super().__init__(model, method=method, journal=journal,
                         terminal_target_ref=terminal_target_ref, **COMMON_LIMITS)
        self.source_pins = dict(source_pins)
        self._nav_domain = declared_nav_xy(model)
        self._push_domain = tuple((c['public_ref'], _xy_key((c['goal_world_x_m'], c['goal_world_y_m'])))
                                  for c in model.placements)
        self._seen_batches = set()
        self._last_observation_time = None
        self.journal(dict(event='reach_complex_source_bound', method=method,
            public_source_pins=self.source_pins, scene_id=model.task['scene_id'],
            common_limits=dict(COMMON_LIMITS), common_initial_declared_reference_xy_m=list(model.initial.robot_reference_xy_m),
            common_nominal_envelope_radius_m=model.radius, public_nav_declaration_count=len(self._nav_domain),
            finite_push_declaration_count=len(self._push_domain),
            execution_authorized=False, actual_task_success=None, private_source_read=False))

    def _validate_catalogue(self, batch):
        if not isinstance(batch, _original_intent_batch_type()):
            raise ValueError('Original public IntentBatch only, never a private ExecutionBatch')
        if batch.sha256 in self._seen_batches:
            raise ValueError('Fresh source batch required; replay is not a new acquisition')
        now = batch.observation.time_s
        if self._last_observation_time is not None and now <= self._last_observation_time:
            raise ValueError('Fresh strictly later public observation required')
        nav = []; push = []; mapping = {}
        for opt in batch.options:
            params = dict(opt.parameters)
            if (opt.skill not in ('NAV', 'PUSH') or set(params) != {
                    'goal_world_x_m', 'goal_world_y_m', 'surface_height_m'} or params['surface_height_m'] != 0.):
                raise ValueError('Exact common ground NAV/PUSH public catalogue required')
            xy = _xy_key((params['goal_world_x_m'], params['goal_world_y_m']))
            if opt.skill == 'PUSH':
                push.append((opt.target_ref, xy))
            else:
                nav.append(xy); mapping[xy] = opt.target_ref
        if tuple(nav) != self._nav_domain or tuple(push) != self._push_domain:
            raise ValueError('Complete ordered public source catalogue required; no missing/extra/duplicate goals')
        if mapping.get(_xy_key(self.model.goal_xy)) != self.terminal_ref:
            raise ValueError('Source-owned original terminal NAV reference required')
        return mapping

    def select(self, batch):
        mapping = self._validate_catalogue(batch)
        # Mappings come from THIS real public batch, not synthetic native tokens.
        self.nav_refs = {xy: mapping[_xy_key(xy)] for xy in self._nav_domain}
        result = super().select(batch)
        self._seen_batches.add(batch.sha256)
        self._last_observation_time = batch.observation.time_s
        return result


def build_source_bound_planner(*, public_task_path, expected_task_sha256,
                               finite_placements_path, expected_placements_sha256,
                               method, journal, terminal_target_ref):
    """Construct only the public planner; owner separately supplies qualified driver.

    File identities must be exact preregistered hashes. This does not validate the
    source's constructor, dynamic feasibility, camera ABI or resource admission.
    """
    values = []; pins = {}
    for name, path, expected in (('public_task', public_task_path, expected_task_sha256),
                                 ('finite_placements', finite_placements_path, expected_placements_sha256)):
        if (not isinstance(expected, str) or len(expected) != 64 or
                any(c not in '0123456789abcdef' for c in expected)):
            raise ValueError('Explicit frozen public file SHA256 required')
        path = Path(path).resolve()
        with path.open('rb') as stream:
            raw = stream.read(65537)
        if len(raw) > 65536 or sha256(raw).hexdigest() != expected:
            raise ValueError('Frozen public source SHA/size mismatch: ' + name)
        values.append(json.loads(raw)); pins[name] = dict(path=str(path), sha256=expected)
    model = PublicSceneModel(*values, declared_initial_reference_xy_m=(-.08, 0.),
                             nominal_envelope_radius_m=.45)
    return SourceBoundComplexIntentPlanner(model, method=method, journal=journal,
        terminal_target_ref=terminal_target_ref, source_pins=pins)
