"""Causal, CPU-only initial-contact early warning for one native PUSH attempt.

Development candidate, not a controller or a safety certificate. Oracle course-X
coordinates are executor diagnostics, NEVER world-model inputs. No mass, colour,
future trajectory, original outcome, or policy output is consumed here. The
caller must retain native hard protections and must separately implement/load-
test unloading, braking, support capture and stowing. A request permits NONE of
those actions by itself. Construct a fresh monitor for each attempt/goal epoch;
there is intentionally no reset/clear-failure method.
"""
from dataclasses import dataclass
from math import isfinite
from numbers import Real


_EPS = 1e-9  # Clock roundoff only, not a displacement tolerance.


def _finite(value):
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(value)


@dataclass(frozen=True)
class ContactProgressConfig:
    window_s: float = .08
    minimum_forward_progress_m: float = .002
    maximum_sample_gap_s: float = .020001

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if not _finite(value) or value <= 0:
                raise ValueError(f'{name} must be finite and positive')
        if self.maximum_sample_gap_s >= self.window_s:
            raise ValueError('A window must contain multiple measured control intervals')


@dataclass(frozen=True)
class ContactProgressSample:
    control_tick: int
    time_s: float
    push_active: bool
    motion_ready: bool
    legal_hand_contact: bool
    measurement_valid: bool
    box_course_x_m: float | None
    # Executor's immutable original-goal guard, not a new/current-position goal.
    # Live integration must include near-goal tolerance, not just final success.
    near_original_goal: bool
    native_settled: bool = False
    native_hard_stop: bool = False


@dataclass(frozen=True)
class ContactProgressDecision:
    status: str
    control_tick: int
    time_s: float
    segment_start_s: float | None
    elapsed_contact_s: float
    observed_forward_dx_m: float | None
    new_soft_abort_request: bool
    soft_abort_requested: bool
    attempt_failed: bool
    failure_time_s: float | None
    native_hard_stop_latched: bool
    initial_progress_established: bool
    # Static negative permissions are deliberate: no physical recovery implied.
    retraction_authorized: bool = False
    nav_takeover_authorized: bool = False
    object_globally_unmovable: bool = False
    model_input_allowed: bool = False


class InitialContactProgressMonitor:
    """One-shot initial-contact detector; later stalls require another protocol.

    A lost contact, invalid sample, skipped tick or >20ms measurement gap breaks
    the continuous window. Time is never accumulated across such interruptions.
    Clock/tick replay errors raise before changing state. Hard stop outranks both
    a new soft-abort and native success, including after a prior warning. Once a
    request is latched, later movement/settling cannot relabel this attempt as a
    success. Passed initial progress is also sticky: normal target stopping is
    not relabelled as an *initial*-contact obstruction.
    """

    def __init__(self, config: ContactProgressConfig | None = None):
        self.config = config if config is not None else ContactProgressConfig()
        if not isinstance(self.config, ContactProgressConfig):
            raise TypeError('Expected ContactProgressConfig')
        self._last_tick = None
        self._last_time = None
        self._start_s = None
        self._start_x = None
        self._elapsed = 0.
        self._dx = None
        self._abort_time = None
        self._hard_stop = False
        self._progress = False
        self._settled = False

    def _clear_window(self):
        self._start_s = self._start_x = None
        self._elapsed = 0.
        self._dx = None

    def _decision(self, s, status, new=False):
        return ContactProgressDecision(
            status=status, control_tick=s.control_tick, time_s=float(s.time_s),
            segment_start_s=self._start_s, elapsed_contact_s=self._elapsed,
            observed_forward_dx_m=self._dx, new_soft_abort_request=new,
            soft_abort_requested=self._abort_time is not None and not self._hard_stop,
            attempt_failed=self._abort_time is not None or self._hard_stop,
            failure_time_s=self._abort_time,
            native_hard_stop_latched=self._hard_stop,
            initial_progress_established=self._progress,
        )

    def observe(self, s: ContactProgressSample) -> ContactProgressDecision:
        if not isinstance(s, ContactProgressSample):
            raise TypeError('Expected ContactProgressSample')
        if type(s.control_tick) is not int or s.control_tick < 0:
            raise ValueError('A nonnegative integer control tick is required')
        if not _finite(s.time_s) or s.time_s < 0:
            raise ValueError('A finite nonnegative simulation timestamp is required')
        for name in ('push_active', 'motion_ready', 'legal_hand_contact',
                     'measurement_valid', 'near_original_goal', 'native_settled',
                     'native_hard_stop'):
            if type(getattr(s, name)) is not bool:
                raise ValueError(f'{name} must be an explicit boolean')
        if self._last_tick is not None and (
            s.control_tick <= self._last_tick or s.time_s <= self._last_time
        ):
            raise ValueError('Duplicate/backwards clock or tick; use a fresh attempt monitor')
        gap = self._last_time is not None and (
            s.control_tick != self._last_tick + 1
            or s.time_s - self._last_time > self.config.maximum_sample_gap_s + _EPS
        )
        self._last_tick, self._last_time = s.control_tick, float(s.time_s)

        if s.native_hard_stop:
            self._hard_stop = True
        if self._hard_stop:
            return self._decision(s, 'NATIVE_HARD_STOP')
        if self._abort_time is not None:
            return self._decision(s, 'SOFT_ABORT_LATCHED')
        if s.native_settled:
            self._settled = True
        if self._settled:
            self._clear_window()
            return self._decision(s, 'NATIVE_SUCCESS_NO_INITIAL_WARNING')
        if self._progress:
            return self._decision(s, 'INITIAL_PROGRESS_ESTABLISHED')

        if gap:
            self._clear_window()
        if not s.push_active or not s.motion_ready:
            self._clear_window()
            return self._decision(s, 'WAIT_ACTIVE_READY')
        if not s.measurement_valid or not _finite(s.box_course_x_m):
            self._clear_window()
            return self._decision(s, 'INVALID_MEASUREMENT_NO_OBSTRUCTION_LABEL')
        if s.near_original_goal:
            self._clear_window()
            return self._decision(s, 'NEAR_ORIGINAL_GOAL_NO_INITIAL_WARNING')
        if not s.legal_hand_contact:
            self._clear_window()
            return self._decision(s, 'NO_LEGAL_CONTACT_NO_OBSTRUCTION_LABEL')

        if self._start_s is None:
            self._start_s, self._start_x = float(s.time_s), float(s.box_course_x_m)
        self._elapsed = float(s.time_s) - self._start_s
        # Signed world-course advance, not abs motion, arm motion or path length.
        self._dx = float(s.box_course_x_m) - self._start_x
        if self._elapsed + _EPS < self.config.window_s:
            return self._decision(s, 'WINDOW_RESTARTED_AFTER_GAP' if gap else 'OBSERVING_CONTACT')
        if self._dx >= self.config.minimum_forward_progress_m:
            self._progress = True
            return self._decision(s, 'INITIAL_PROGRESS_ESTABLISHED')
        self._abort_time = float(s.time_s)
        return self._decision(s, 'CURRENT_ATTEMPT_INSUFFICIENT_INITIAL_PROGRESS', new=True)
