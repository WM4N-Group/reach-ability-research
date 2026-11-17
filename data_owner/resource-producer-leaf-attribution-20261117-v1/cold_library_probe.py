"""One future-only, no-world actual cold-library/owner-producer attribution.

NOT a D3 retry, resource repair, old-failure cause or physics admission. The
original ResourceWatch and held PerGpuLease still own all safety decisions.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import threading
import time

OWNER = '01a1e4e1-3037-7333-9019-a3f37effe5da'
UUID = 'GPU-297c1146-bcec-a8ee-8437-d9603392a2e1'
QUESTION = 'ACTUAL_NO_WORLD_CUDA_EGL_COLD_INTERVAL_VS_ORIGINAL_HELD_RESOURCE_PRODUCER_LEAVES_NOT_D3_CAUSE_OR_REPAIR'


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(config_path=None, pin=None, *, enabled=False):
    if enabled is not True:
        return None
    c = json.loads(Path(config_path).read_bytes())
    need(c['question'] == QUESTION and c['owner'] == OWNER, 'New explicit diagnostic identity')
    need(c['scope_id'] == 'data-46308-resource-cold-library-leaves-20261117-v1', 'Single new bounded diagnostic scope')
    need(c['probe_max'] == 1 and c['worlds_max'] == 0 and c['retry_max'] == 0, 'One no-world diagnostic, no retry')
    need((c['wall_cap_s'], c['RSS_cap_bytes'], c['GPU_cap_bytes']) == (90, 4 << 30, 3 << 30), 'Original finite resource caps')
    need(c['interval_s'] == 1 and c['max_oldest_age_s'] == 2, 'Original 1s/2s policy, no relaxation')
    need(c['output_cap_bytes'] == 8 << 20 and c['reserve_bytes'] == 1 << 20 and c['disk_floor_bytes'] == 2 << 30, 'Bounded controlled output and disk floor')
    need(sha(c['freeze_path']) == pin, 'Exact complete new freeze')
    freeze = json.loads(Path(c['freeze_path']).read_bytes())
    need(freeze['question'] == QUESTION and freeze['scope_id'] == c['scope_id'], 'New freeze/question binding')
    for name, digest in freeze['files'].items():
        p = Path(name)
        need(not p.is_symlink() and sha(p) == digest, 'Frozen source drift: ' + name)
    need(sys.prefix == '/mnt/yuanyue/data-team/env-native-v1' and sys.version_info[:3] == (3, 11, 16), 'Original private interpreter')
    need(os.environ.get('CUDA_VISIBLE_DEVICES') == UUID and os.environ.get('MUJOCO_EGL_DEVICE_ID') == '0' and os.environ.get('MUJOCO_GL') == 'egl', 'Actual UUID and original physical EGL binding')
    need(os.environ.get('LD_PRELOAD') == c['LD_PRELOAD'], 'Original Expat loader')
    sys.path[:0] = c['import_paths']
    import torch
    from per_gpu_lease import PerGpuLease
    from lease_leaf_timing import build_timed_check
    # Pin/compile the actual method without entering/acquiring a lease or GPU.
    lease = PerGpuLease(physical_index=0, authority_check=lambda: None)
    timed, trace = build_timed_check(lease.check, enabled=True)
    need(callable(timed) and trace.last_attempt is None and not lease.fds, 'Unexecuted exact original held-check overlay')
    need(not torch.cuda.is_initialized(), 'CPU prepare must not initialize CUDA')
    return c


def run(config_path=None, pin=None, *, enabled=False):
    if enabled is not True:
        return None
    started = time.monotonic()
    c = prepare(config_path, pin, enabled=True)
    from scoped_io import ScopeIO
    from fd_capture import FDCapture
    from runner_outputs import write_json, finish_accounting
    from resource_watch import ResourceWatch
    from fast_health import make_original_fast_health
    from timed_probe import make_timed_scope_probe
    from per_gpu_lease import PerGpuLease
    from lease_leaf_timing import build_timed_check
    import torch
    import shutil
    from types import SimpleNamespace

    hpath, apath = Path(c['handoff']), Path(c['authority'])
    authorization_sha = sha(apath)
    periodic_entered = threading.Event()
    main_ident = threading.get_ident()
    def authority():
        h = json.loads(hpath.read_bytes())
        q = h[c['key']]
        need(h['executing_thread_id'] == q['owner'] == OWNER and q['active'], 'Real live maintenance/scope owner')
        need(q['scope_id'] == c['scope_id'] and q['probe_PID'] == os.getpid() and q['phase'] == 'ACTUAL_NO_WORLD_COLD_RESOURCE_PROBE', 'Actual scope and worker PID')
        need(q['probe_dispatch_count'] == 1 and q['zero_dispatch_count'] == q['main_dispatch_count'] == 0 and q['program_sha256'] == pin, 'Single diagnostic count, no zero/main borrowing')
        need(q['authorization_sha256'] == authorization_sha == sha(apath), 'Immutable new authorization')
        need(not h['bulk24_collector_v1']['global_stop'], 'Original global stop')
        need(all(not row.get('active', False) for key, row in h.items() if key != c['key'] and isinstance(row, dict)), 'No competing Data authority')
        if threading.get_ident() != main_ident:
            periodic_entered.set()  # Schedule overlap, NOT a freshness/owner stamp.
    # The controller must bind the actual Popen PID by CAS before any lease.
    gate = time.monotonic()
    while json.loads(hpath.read_bytes())[c['key']]['probe_PID'] is None:
        need(time.monotonic() - gate < 3, 'Actual worker PID not bound; no native start')
        time.sleep(.01)
    authority()
    root = Path(c['output'])
    need(not root.exists(), 'Never reuse a diagnostic output root')
    root.mkdir(parents=True)
    budget = ScopeIO(root, cap_bytes=c['output_cap_bytes'], reserve_bytes=c['reserve_bytes'])
    state = budget.state
    lease = watch = capture = ctx = tensor = timed = trace = producer = None
    errors = []
    intervals = []
    result = dict(scope_id=c['scope_id'], question=QUESTION, program_sha256=pin, PID=os.getpid(),
                  passed=False, resource_repair=False, D3_cause_recovered=False,
                  Runtime_Actor_restore_forward_Renderer_MjModel_MjData_physics_API_calls=0,
                  world_calls=0, zero_dispatch_count=0, main_dispatch_count=0,
                  actual_CUDA_init_completed=False, actual_EGL_init_completed=False,
                  deliberate_native_overlap_not_actual_D3_constructor=True)
    def alarm(*_):
        raise RuntimeError('Original finite cold diagnostic wall deadline')
    signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, c['wall_cap_s'] - 10)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.nice(15)
    health = make_original_fast_health(torch, state=state, start_mono=started,
        wall_cap_s=c['wall_cap_s'], rss_cap_bytes=c['RSS_cap_bytes'], gpu_cap_bytes=c['GPU_cap_bytes'])
    def stage(label, action):
        watch()
        row = dict(stage=label, started=time.monotonic(), completed=None, action_completed=False)
        intervals.append(row)
        try:
            value = action()
            row['action_completed'] = True
            return value
        except BaseException as exc:
            row['error_type'] = type(exc).__name__
            raise
        finally:
            row['completed'] = time.monotonic()
    try:
        capture = FDCapture(budget, stdout_path=root/'stdout.bin', stderr_path=root/'stderr.bin', enabled=True)
        lease = PerGpuLease(physical_index=0, authority_check=authority).__enter__()
        timed, trace = build_timed_check(lease.check, enabled=True)
        producer = make_timed_scope_probe(SimpleNamespace(check=timed), budget,
            min_free_bytes=c['disk_floor_bytes'], disk_free=lambda path: shutil.disk_usage(path).free, enabled=True)
        watch = ResourceWatch(producer, state=state, token=object(), fast_health=health,
            interval_s=c['interval_s'], max_stale_s=c['max_oldest_age_s']).start()
        # One deliberate overlap with the ORIGINAL periodic callback. No synthetic
        # GIL hold, forced extra probe, fake time or later sample selected for success.
        wait_started = time.monotonic()
        while not periodic_entered.wait(.01):
            watch()
            need(time.monotonic() - wait_started <= 3, 'Periodic overlap never observed; stop without retry')
        result['overlap_event_delivered_at'] = time.monotonic()
        def cuda():
            nonlocal tensor
            torch.cuda.init()
            tensor = torch.empty(1, device='cuda:0', dtype=torch.float32)
            result['actual_CUDA_init_completed'] = True
        stage('actual_CUDA_init_one_element_NO_ACTOR', cuda)
        def egl_import():
            from mujoco.egl import GLContext
            return GLContext
        context_class = stage('actual_mujoco_EGL_import_NO_MODEL', egl_import)
        def egl_construct():
            nonlocal ctx
            ctx = context_class(16, 16)
            ctx.make_current()
            result['actual_EGL_init_completed'] = True
        stage('actual_16x16_EGL_context_NO_RENDERER', egl_construct)
        def egl_free():
            nonlocal ctx
            ctx.free()
            ctx = None
        stage('actual_EGL_free', egl_free)
        # Require completion of that same periodic attempt before finalization.
        # Its original started/completed age still decides acceptance.
        delivery_wait = time.monotonic()
        while watch.probe_calls < 2:
            watch()
            need(time.monotonic() - delivery_wait <= 3, 'Original periodic delivery incomplete; no retry')
            time.sleep(.01)
        watch()
        result['passed'] = True
    except BaseException as exc:
        result.update(error_type=type(exc).__name__, resource_failure=state.reason)
    finally:
        # Seal BEFORE any cleanup/reserve reporting. No new native action resumes.
        budget.begin_finalization()
        if ctx is not None:
            try:
                ctx.free()
            except BaseException as exc:
                errors.append(dict(stage='EGL_cleanup', error_type=type(exc).__name__))
        tensor = None
        if watch is not None:
            try:
                watch.close()
            except BaseException as exc:
                errors.append(dict(stage='watch_close', error_type=type(exc).__name__))
        if trace is not None and trace.last_attempt is not None:
            result['last_original_held_check_leaf_attempt'] = asdict(trace.last_attempt)
        if producer is not None and producer.last_attempt is not None:
            result['last_full_original_producer_attempt'] = asdict(producer.last_attempt)
        if watch is not None:
            result['original_watch'] = dict(interval_s=watch.interval, max_oldest_age_s=watch.max_stale,
                check_calls=watch.check_calls, successful_probe_calls=watch.probe_calls,
                oldest_completed_pair=watch.last_observation_stamp, probe_wall_s=watch.probe_wall_s)
        if lease is not None:
            result['last_original_GPU_observation'] = lease.last_gpu
            try:
                lease.__exit__()
            except BaseException as exc:
                errors.append(dict(stage='lease_close', error_type=type(exc).__name__))
        if capture is not None:
            try:
                result['FD_capture'] = capture.close()
            except BaseException as exc:
                errors.append(dict(stage='FD_close', error_type=type(exc).__name__))
        signal.setitimer(signal.ITIMER_REAL, 0)
        result.update(actual_native_intervals=intervals, close_errors=errors,
                      wall_s=time.monotonic()-started, RSS_peak_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                      original_fast_health=health.metrics, resource_failure=state.reason,
                      no_observation_or_delivery_time_replaced=True, automatic_retry=False,
                      OS_command_vs_GIL_split_not_available_from_parent_leaf_times=True)
        if errors or state.reason is not None:
            result['passed'] = False
        write_json(budget, root/'result.json', result)
        finish_accounting(budget, root/'final-output-accounting.json')
    return 0 if result['passed'] else 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--enabled', action='store_true')
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--config')
    parser.add_argument('--pin')
    args = parser.parse_args()
    if not args.enabled:
        raise SystemExit(0)
    if args.prepare:
        c = prepare(args.config, args.pin, enabled=True)
        print(json.dumps(dict(stage='ACTUAL_CPU_PREPARE_NO_NATIVE', program_sha256=args.pin,
                              CUDA_initialized=False, lease_API_world_calls=0)))
    else:
        raise SystemExit(run(args.config, args.pin, enabled=True))
