"""Opt-in selected-v6 consumer delta; never imports a simulator or NumPy.

The caller is SHA-pinned and the callback is inside the ORIGINAL capture dwell /
queue acceptance branch, before its ORIGINAL whole-path recheck/begin_segment.
Only original ordered waypoint COPIES may be assigned. This is not permission
for physical execution and the software guards are not safety certificates.
"""
import hashlib
from pathlib import Path
import time
from .stow_path_choice import optimize, vector

FROZEN_STALL_SHA256 = 'ffbab28c81de7909fb8092f28a8917782e6918cdad53bcacbb0925e31589a28f'
CALLBACK = '_reach_stow_path_choice_at_capture'
ANCHOR = '                for goal in ([self.compact_goal] if arrival_capture else self.waypoints):'
INSERT = ("                if not arrival_capture:\n"
          "                    _reach_choice_callback = globals().get('_reach_stow_path_choice_at_capture')\n"
          "                    if _reach_choice_callback is not None:\n"
          "                        _reach_choice_callback(self, start, capture=capture, queued=queued, now=now)\n")


def transform_stall_source(original):
    if hashlib.sha256(original.encode()).hexdigest() != FROZEN_STALL_SHA256:
        raise ValueError('Exact selected complete-v6 ProtectedStow source required')
    if original.count(ANCHOR) != 1 or CALLBACK in original:
        raise ValueError('Exact original capture caller required; no stacking hooks')
    changed = original.replace(ANCHOR, INSERT+ANCHOR, 1)
    if restore_stall_source(changed) != original:
        raise ValueError('Source delta is not exactly reversible')
    return changed


def restore_stall_source(changed):
    if changed.count(INSERT) != 1:
        raise ValueError('One exact additive capture hook required')
    original = changed.replace(INSERT, '', 1)
    if hashlib.sha256(original.encode()).hexdigest() != FROZEN_STALL_SHA256:
        raise ValueError('Disabled/removed delta must recover the exact original')
    return original


def _six(value):
    return vector(value.tolist() if hasattr(value, 'tolist') else value)


def _raw(value):
    if hasattr(value, 'numpy'):
        value = value.numpy()
    if hasattr(value, 'tobytes'):
        return value.tobytes()
    if hasattr(value, 'tolist'):
        return _raw(value.tolist())
    if isinstance(value, (tuple, list)):
        return tuple(_raw(x) for x in value)
    if isinstance(value, dict):
        return tuple((k, _raw(v)) for k, v in sorted(value.items()))
    return value


def _state(owner, namespace):
    """Read-only mutation sentinel, not a security boundary or physical audit."""
    s = owner.s
    return (float(s.data.time), _raw(s.data.qpos), _raw(s.data.qvel),
            _raw(getattr(s.data, 'ctrl', None)), tuple(_raw(a) for a in s.queue),
            _raw(s.delays), _raw(s.box_push_target), namespace['history_sha'](s),
            _raw(owner.r.last.position), _raw(owner.r.last.velocity),
            _raw(owner.r.last.feedforward), _raw(owner.reference), _raw(owner.velocity),
            _raw(owner.compact_goal), tuple(_raw(q) for q in owner.waypoints),
            owner.phase, owner.index, owner.segment_start, owner.segment_duration,
            _raw(owner.segment_origin), owner.retired_history_sha, _raw(owner.original_goal))


def _selected_session(host, owner):
    """Object identity, not phase labels, goal hashes, or extra NN evaluation."""
    executor = host.executor
    session = executor.session
    if session is None or executor.option is None or executor.option.skill != 'PUSH' or executor.reported_end:
        return None
    machine = getattr(session, 'machine', None)
    brake = getattr(machine, 'brake', None)
    services = getattr(machine, 'services', None)
    if (getattr(session, 'placement_source_height', None) != 0 or
            type(session.placement_source_height) is bool or
            getattr(machine, 'confirmed', None) is not True or
            getattr(brake, 'stow', None) is not owner or
            getattr(services, 'session', None) is not session):
        return None
    if (services.native is not machine.native or services.p is not owner.s or
            session.runtime.sim is not owner.s or brake.r.sim is not owner.s or
            machine.native.r.sim is not owner.s):
        raise RuntimeError('Selected ground placement owner/runtime identity mismatch')
    return session


class _GuardUnavailable(Exception):
    pass


def bind_to_host(host, stall_module, *, enabled=False, emit=None):
    """Call AFTER loading a new owned transformed module and BEFORE execution.

    Default False installs nothing, reads no session/goal and evaluates no guard.
    Enabled mode reads host.executor.session live at the original call boundary;
    no cached session, synthetic capture admission, NN/Actor call or world write.
    Caller must bind BOTH source aliases if both are loaded. No source hot edit.
    """
    if type(enabled) is not bool:
        raise ValueError('Explicit Boolean study arm required')
    if not enabled:
        return {'status': 'DEFAULT_DISABLED', 'installed': False}
    if not callable(emit):
        raise ValueError('Explicit evidence-only journal sink required')
    ns = vars(stall_module)
    restore_stall_source(Path(ns['__file__']).read_text())
    cls = ns['ProtectedStow']
    if cls.update.__globals__ is not ns or CALLBACK not in cls.update.__code__.co_consts:
        raise ValueError('Loaded original update must consume this module callback')
    if CALLBACK in ns:
        raise ValueError('Do not replace or stack a live binding')
    # Use the ALREADY-LOADED original namespace's NumPy/array constructor.
    # This adapter is stdlib-only locally; no environment/package installation.
    array = ns['np'].array

    def at_capture(owner, start, *, capture, queued, now):
        if type(owner) is not cls:
            raise ValueError('Exact transformed ProtectedStow owner required')
        session = _selected_session(host, owner)
        if session is None:
            return {'status': 'OUT_OF_SCOPE_ORIGINAL_UNCHANGED', 'changed': False}
        if (owner.native_arrival is not None or owner.phase != 'UNLOAD_CAPTURE' or
                owner.index != 0 or owner.segment_start is not None or
                not bool(capture) or queued.get('screen_pass') is not True or
                owner.support_anchors_latched is not True or
                owner.captured_since is None or now-owner.captured_since < .2-1e-8 or
                now != float(owner.s.data.time)):
            raise RuntimeError('Missing original capture/dwell/queue caller witness')
        if _six(start) != _six(owner.s.data.qpos[owner.s.qids[12:]]):
            raise RuntimeError('Actual first-edge origin must be current native q')
        session.machine.services.assert_immutable()
        original = tuple(owner.waypoints)
        endpoint = _six(owner.compact_goal)
        if not original or _six(original[-1]) != endpoint:
            raise ValueError('Exact original compact endpoint required')
        before = _state(owner, ns)
        started = time.perf_counter()

        def guard(a, b):
            reason = owner.native.guard.segment(array(a, dtype=float), array(b, dtype=float))
            if type(reason) is not str:
                raise _GuardUnavailable('Non-string original guard result')
            return reason

        try:
            result = optimize(_six(owner.reference), _six(start), [_six(q) for q in original],
                              guard_segment=guard)
        except _GuardUnavailable:
            # Selection unavailable, NOT successful guard / task infeasibility.
            # Preserve the path for the untouched original runtime recheck.
            result = dict(status='GUARD_UNKNOWN_ORIGINAL_FOR_NATIVE_RECHECK', changed=False,
                          actual_total_completion_cost_s=None, actual_successor_repair_cost_s=None,
                          execution_authorized=False)
        if _selected_session(host, owner) is not session or _state(owner, ns) != before:
            raise RuntimeError('Path query changed current session/state/FIFO/goal/reference')
        session.machine.services.assert_immutable()
        result.update(selection_wall_s=time.perf_counter()-started,
                      consumer_stage='selection_before_original_full_path_recheck',
                      original_capture_queue_branch=True, model_input=False,
                      physical_commands_issued_by_optimizer=0)
        selected = ([original[i-1].copy() for i in result['chosen_path_indices'][1:]]
                    if result['changed'] else None)
        if selected is not None and _six(selected[-1]) != endpoint:
            raise RuntimeError('Selected path lost original endpoint')
        emit(dict(event='reach_selected_ground_confirmed_stow_path_choice', **result))
        if _selected_session(host, owner) is not session or _state(owner, ns) != before:
            raise RuntimeError('Evidence sink mutated native control state')
        if selected is not None:
            owner.waypoints = selected  # Original recheck/begin_segment/command consume this SAME field.
        owner._reach_stow_path_choice = result
        return result

    ns[CALLBACK] = at_capture
    return {'status': 'OPT_IN_INSTALLED_NOT_PHYSICALLY_QUALIFIED', 'installed': True,
            'source_original_sha256': FROZEN_STALL_SHA256, 'execution_authorized': False}
