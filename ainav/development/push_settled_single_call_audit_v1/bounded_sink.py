"""Bounded audit-only sink for the ONE original clocked PushSettled invocation.
No IO/world/actor construction: an authorized new owner supplies its writer and
read-only phase getter. Never calls settled/clock/report/measure or alters state.
"""
import hashlib
import json
import math
from pathlib import Path
import time

SDK_CANDIDATE_SHA256 = 'a15634610b69c0d01b68d6c61bcced9f74d60c5ffc98ffb45de9d54745ba28af'
CLOCK_SOURCE_SHA256 = 'fd1a49df4beb515308b9f146eac1ee260b818ddce39b7d556a14981ff1597180'
SCHEMA = 'AINav-D3-original-single-predicate-components-v1'
VECTORS = ('goal_xy_error_m', 'box_speed_3d_m_s', 'goal_xy_lt_original_012',
           'speed_3d_lt_original_008', 'contact_seen_latched', 'not_tipped',
           'no_forbidden_contact', 'settled_now', 'duration_before_s',
           'duration_after_s', 'returned_confirmed')
FLAGS = ('goal_xy_lt_original_012', 'speed_3d_lt_original_008',
         'contact_seen_latched', 'not_tipped', 'no_forbidden_contact')


def _need(ok, message):
    if not ok:
        raise ValueError(message)


def _text(value, limit=192):
    return type(value) is str and 0 < len(value) <= limit


class _BoundedSink:
    def __init__(self, context, writer, max_records, max_payload_bytes):
        self.context, self.writer = context, writer
        self.max_records, self.max_payload_bytes = max_records, max_payload_bytes
        self.records = self.payload_bytes = self.writer_attempts = 0
        self.total_sink_wall_ns = self.writer_wall_ns = self.max_sink_wall_ns = 0
        self.failed = self.busy = self.writer_tail_unknown = False
        self.error_type = None
        self.previous_confirmed = False
        self.first_confirmed = self.first_loss = None
        self.last_time = None

    def __call__(self, snapshot):
        started = time.perf_counter_ns()
        if self.failed or self.busy:
            self.failed = True
            raise RuntimeError('Failed/reentrant D3 audit sink cannot continue')
        self.busy = True
        try:
            _need(type(snapshot) is dict and set(snapshot) == {'schema', 'native_step_dt_s', 'hold_time_s', *VECTORS}
                  and snapshot['schema'] == SCHEMA and snapshot['native_step_dt_s'] == .02
                  and snapshot['hold_time_s'] == .5, 'Exact original D3 snapshot/thresholds required')
            for name in VECTORS:
                value = snapshot[name]
                _need(type(value) is tuple and len(value) == 1, 'Frozen single-world D3 snapshot, no truncation')
                _need(type(value[0]) is bool if name in (*FLAGS, 'settled_now', 'returned_confirmed') else
                      type(value[0]) in (int, float) and math.isfinite(value[0]), 'Only copied finite scalar/bool values')
            context = self.context()  # Raw original clock fields only, no report/term poll.
            _need(self.last_time is None or context['time_s'] > self.last_time, 'One row per actual original native advance')
            row = dict(event='D3_original_single_predicate_components', sequence=self.records + 1,
                       context=context, components=snapshot, model_input=False,
                       original_stateful_call_repeated=False, original_control_or_goal_modified=False)
            encoded = (json.dumps(row, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)+'\n').encode()
            _need(self.records < self.max_records and self.payload_bytes + len(encoded) <= self.max_payload_bytes,
                  'Finite D3 sink capacity exhausted; stop, never skip a row or resume')
            write_started = time.perf_counter_ns()
            self.writer_attempts += 1
            self.writer_tail_unknown = True
            try:
                ref = self.writer(encoded)
            finally:
                self.writer_wall_ns += time.perf_counter_ns() - write_started
            _need(_text(ref, 1024), 'Original durable owner writer must acknowledge the row')
            self.writer_tail_unknown = False
            self.records += 1
            self.payload_bytes += len(encoded)
            self.last_time = context['time_s']
            confirmed = snapshot['returned_confirmed'][0]
            if confirmed and self.first_confirmed is None:
                self.first_confirmed = dict(time_s=context['time_s'], evidence_ref=ref)
            if self.previous_confirmed and not confirmed and self.first_loss is None:
                self.first_loss = dict(time_s=context['time_s'], phase=context['phase'],
                    false_original_flags=[name for name in FLAGS if not snapshot[name][0]],
                    evidence_ref=ref, simultaneous_flags_not_unique_physical_cause=True)
            self.previous_confirmed = confirmed
        except BaseException as error:
            self.failed = True
            self.error_type = type(error).__name__  # Never dump row/env/exception args.
            raise
        finally:
            elapsed = time.perf_counter_ns() - started
            self.total_sink_wall_ns += elapsed
            self.max_sink_wall_ns = max(self.max_sink_wall_ns, elapsed)
            self.busy = False

    def report(self):
        return dict(schema='AINav-D3-bounded-sink-accounting-v1', records_acknowledged=self.records,
            serialized_payload_bytes_acknowledged=self.payload_bytes,
            payload_budget_is_not_total_ScopeIO_or_provider_disk_usage=True,
            writer_attempts=self.writer_attempts, writer_tail_unknown=self.writer_tail_unknown,
            total_sink_wall_ns=self.total_sink_wall_ns, writer_wall_ns=self.writer_wall_ns,
            writer_wall_is_inclusive_not_added_to_total=True, max_sink_wall_ns=self.max_sink_wall_ns,
            failed=self.failed, error_type=self.error_type,
            first_confirmed=self.first_confirmed, first_loss=self.first_loss,
            report_calls_native_clock_or_predicate=False, old_E20_cause_or_training_need_proven=False)


def bind_clocked_settled_sink(*, enabled=False, env=None, runtime=None, write_record=None,
                              phase_reader=None, phase_source_ref=None, scope_id=None,
                              world_role=None, max_records=None, max_payload_bytes=None):
    """Bind to the SELECTED VIEW, after its fresh original clock construction.

    Do this after make_target_context returns, before any termination read. Its
    TargetBridge copies deliberately SKIP callable attrs, so binding only the
    root/raw bridge does not bind a selected view. Aux uses a distinct explicitly
    registered sink/context; never merge aux samples into the main diagnosis.
    All source/identity checks here are cold; callbacks do no file stat/hash.
    """
    _need(type(enabled) is bool, 'Explicit independent diagnostic opt-in')
    if not enabled:
        return None
    _need(callable(write_record) and callable(phase_reader) and _text(phase_source_ref)
          and _text(scope_id) and world_role in ('task', 'aux')
          and type(max_records) is int and 0 < max_records <= 100000
          and type(max_payload_bytes) is int and 0 < max_payload_bytes <= 64*1024*1024,
          'Explicit finite owner scope/world/phase/sink limits')
    _need(not hasattr(env, '_ainav_push_settled_audit'), 'One sink per fresh selected env, no rebind')
    clock = env.settled
    _need(type(clock).__name__ == 'ClockedNativeSettled' and clock.data is env.data
          and clock.box is env.scene['box'] and runtime.sim.data is env.data
          and clock.reads == clock.advances == 0 and not clock.failed
          and clock.last_duration == 0. and clock.last_contact is False,
          'Fresh original selected-view clock in this same actual world, no history reset')
    native = clock.native
    for function, expected in ((type(clock).__call__, CLOCK_SOURCE_SHA256),
                               (type(native).__call__, SDK_CANDIDATE_SHA256)):
        path = Path(function.__code__.co_filename)
        _need(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected,
              'Selected original clock and exact new audit-only SDK file identities')
    data, box = env.data, env.scene['box']
    def context():
        _need(env.data is data and runtime.sim.data is data and env.scene['box'] is box
              and env.settled is clock and clock.native is native and not clock.failed,
              'Same original clock/world/target view during single-call audit')
        now = float(data.time)
        tick = runtime.step_count
        _need(type(tick) is int and tick >= 0 and math.isfinite(now)
              and abs(now - tick * .005) <= 1e-7 and clock.last_read_time == now
              and .02-1e-7 <= now-clock.last_native_time <= .02+1e-7,
              'Actual 200Hz physical count and original pending 20ms native advance')
        phase = phase_reader()
        _need(_text(phase, 96), 'Read-only actual phase string or explicit UNKNOWN, not a stateful poll')
        return dict(scope_id=scope_id, world_role=world_role, time_s=now, physical_tick=tick,
            phase=phase, phase_source_ref=phase_source_ref,
            original_clock_last_read_s=clock.last_read_time,
            original_clock_previous_native_s=clock.last_native_time,
            original_clock_reads_including_current=clock.reads,
            original_clock_advances_before_current=clock.advances,
            callback_before_original_clock_postcall_accounting=True,
            native_sample_is_not_10Hz_video_interpolation=True)
    sink = _BoundedSink(context, write_record, max_records, max_payload_bytes)
    env._ainav_push_settled_audit = sink
    return sink
