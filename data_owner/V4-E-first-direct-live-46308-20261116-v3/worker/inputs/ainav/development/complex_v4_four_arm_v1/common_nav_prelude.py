"""Opt-in SOURCE caller for Reach's common public NAV observation prefix.

Keep host.planner (real A--E method) installed from task0. Only the original
coordinator's auxiliary model changes, once, until a genuine original NAV
terminal AND a new public acquisition. No direct command/world/model/API call.
Not adopted by the currently frozen af09 component; not a WM-ready certificate.
"""
from pathlib import Path
import hashlib, importlib
from method_entry import _reach_modules, REACH_PACKAGE
from factor_scope import FactorJournal, factors
from v4_native_asset import require

PRELUDE_SHA = '3cb37d8e3c770951283cd6f093d5c545826ff06ef01531c4f41f2bf94311ab3a'
COORDINATOR_SHA = 'c6cafbac86e549fb76a038bdb9072975831179ac670a1aba5685ae4ddc5afb8e'


def _helper(reach_source_root):
    root, _ = _reach_modules(reach_source_root)
    path = root / REACH_PACKAGE.replace('.', '/') / 'v4_common_nav_prelude.py'
    require(not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == PRELUDE_SHA,
            'Exact proposed Reach common public NAV policy, no new waypoint/route')
    module = importlib.import_module(REACH_PACKAGE + '.v4_common_nav_prelude')
    require(Path(module.__file__).resolve() == path, 'No ambient common NAV policy')
    return module


class CommonPreludeCaller:
    def __init__(self, host, policy, *, software_fixture):
        self.host, self.policy = host, policy
        self.method, self.journal = host.planner, host.journal
        self._software_fixture = software_fixture
        self.runtime, self.sim, self.queue = host.r, host.r.sim, host.r.sim.queue
        self.coordinator = None
        self.handed_off = False
        self.failed = False
        self._acquire = None

    @property
    def software_fixture(self):
        return self._software_fixture

    def _identities(self):
        h = self.host
        require(not self.failed and h.r is self.runtime and h.r.sim is self.sim and h.r.sim.queue is self.queue
                and h.planner is self.method and h.journal is self.journal
                and h._v4_factor_journal is self.journal and self.method.journal is self.journal
                and self.policy.journal is self.journal and self.journal.policy == factors(h.arm),
                'Same task-zero actual method and one same-arm factor ledger; no reset/replacement')
        require(h.owner_guard() is not False, 'Actual owner refused common-prefix caller')

    def bind_coordinator(self, coordinator):
        """Called by actual driver after own capture, before ANY semantic decision."""
        self._identities()
        from ainav.native.intent_execution import IntentExecutionCoordinator
        path = Path(self.host.source_root).resolve() / 'ainav/native/intent_execution.py'
        module = importlib.import_module('ainav.native.intent_execution')
        require(not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == COORDINATOR_SHA
                and Path(module.__file__).resolve() == path,
                'Exact original coordinator source/ABI, no alternate dispatcher')
        require(isinstance(coordinator, IntentExecutionCoordinator) and self.coordinator is None
                and self.host.coordinator is coordinator
                and coordinator.model is self.method and coordinator.journal is self.journal
                and coordinator.intent is coordinator.execution_batch is coordinator.actual_option is None
                and coordinator.sequence == 0 and not coordinator.feedback and not coordinator.blocked_commands,
                'Fresh exact original coordinator, not a mid-task switch or retry')
        require(self.policy.status == 'NEW', 'One common prefix only')
        ref = self.journal(dict(event='V4_common_NAV_auxiliary_coordinator_bound_NOT_arm_method',
            arm=self.host.arm, software_fixture=self.software_fixture, original_method_kept_at_task0=True,
            common_all_five_arms_required=True, all_capture_prefix_validation_costs_from_task0=True,
            new_optimizer_choice=False, WM_ready_or_task_success_claimed=False))
        require(type(ref) is str and bool(ref), 'Durable common-prefix caller evidence')
        self._identities()
        self._acquire = coordinator.observe_public
        self.coordinator = coordinator
        coordinator.model = self.policy
        coordinator.observe_public = self.acquire

    def acquire(self, now):
        """Original coordinator still does exactly ONE actual public acquisition."""
        try:
            self._identities()
            c = self.coordinator
            require(c is not None and self.host.coordinator is c and c.journal is self.journal,
                    'Bound original coordinator and same runtime')
            if self.handed_off:
                require(c.model is self.method, 'Never return to the prefix or another method')
                return self._acquire(now)
            require(c.model is self.policy and self.policy.status in ('NEW', 'PENDING', 'SUCCEEDED'),
                    'Rejected/failed/expired/uncertain prefix is unavailable, never method fallback')
            observation = self._acquire(now)
            if self.policy.status == 'SUCCEEDED':
                require(c.intent is c.execution_batch is c.actual_option is None and c.phase is None,
                        'Original terminal must have cleared coordinator pending execution')
                proof = self.policy.require_fresh_method_observation(observation)
                ref = self.journal(dict(event='V4_common_NAV_return_to_same_original_method',
                    arm=self.host.arm, software_fixture=self.software_fixture, **proof,
                    same_original_method_identity=True, all_prefix_costs_included=True,
                    actual_WM_forward_or_method_decisions_inferred=False,
                    physical_action_issued=False))
                require(type(ref) is str and bool(ref), 'Durable genuine-prefix handoff evidence')
                self._identities()
                require(c.model is self.policy, 'No concurrent coordinator method replacement')
                c.model = self.method
                self.handed_off = True
            return observation
        except BaseException:
            self.failed = True  # No resuming after an uncertain read/guard/journal/handoff.
            raise


def require_live_prelude(value):
    require(type(value) is CommonPreludeCaller and value.software_fixture is False,
            'Fixture prefix caller cannot enter a live driver')


def attach_common_nav_prelude(*, enabled=False, driver=None, reach_source_root=None, software_fixture=False):
    require(type(enabled) is bool and type(software_fixture) is bool, 'Explicit opt-in/fixture provenance')
    if not enabled:
        return None
    h = driver
    require(h.arm in ('A', 'B', 'C', 'D', 'E') and not hasattr(h, '_v4_common_nav_prelude'),
            'Exactly one shared auxiliary prefix, available identically to all five methods')
    require(h.r.step_count == 0 and float(h.r.sim.data.time) == 0. and not h.r.sim.queue
            and h.tick == 0 and h.loop is h.coordinator is h.executor is None
            and getattr(h.writer, 'steps', None) == 0,
            'Fresh own-zero driver/writer; never attach to inflight/closed scope')
    require(type(h.journal) is FactorJournal and h.journal.policy == factors(h.arm)
            and h.journal is h._v4_factor_journal is h.planner.journal,
            'Same original common factor journal and actual arm method')
    require(getattr(h.planner, 'pending', None) is None and getattr(h.planner, 'calls', 0) == 0
            and getattr(getattr(h.planner, 'wm', None), 'forward_batches', 0) == 0,
            'Before method selection/WM forward; no counters or histories reset')
    require(h.owner_guard() is not False, 'Actual owner refused common-prefix assembly')
    module = _helper(reach_source_root)
    policy = module.CommonNavObservationPrelude(arm=h.arm, journal=h.journal, enabled=True,
                                                software_fixture=software_fixture)
    caller = CommonPreludeCaller(h, policy, software_fixture=software_fixture)
    ref = h.journal(dict(event='V4_common_NAV_caller_attached_SOURCE_NOT_native_qualified',
        arm=h.arm, software_fixture=software_fixture, Reach_policy_sha256=PRELUDE_SHA,
        target_ref=module.TARGET_REF, parameters=dict(module.PARAMETERS),
        original_method_not_replaced=True, same_all_five_prefix_required_not_runs_attested=True,
        max_prefix_requests=1, retry_or_alternate_view=False, all_costs_from_task0=True,
        same_actual_recorder_and_native_guards=True, WM_ready_or_task_success_claimed=False,
        no_API_WM_Actor_or_physics_call=True))
    require(type(ref) is str and bool(ref), 'Durable source-only attachment evidence')
    caller._identities()
    h._v4_common_nav_prelude = caller
    return caller
