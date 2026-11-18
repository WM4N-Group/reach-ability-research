"""Independent direct GPU accounting positive parity under unchanged original held watcher.

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
QUESTION = 'NO_WORLD_DIRECT_NVML_OWN_PID_PARITY_UNDER_ORIGINAL_HELD_WATCH'


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
    need(c['scope_id'] == 'data-46308-push-nvml-own-pid-parity-20261118-v1', 'Single new bounded diagnostic scope')
    need(c['probe_max'] == 1 and c['worlds_max'] == 0 and c['retry_max'] == 0, 'One no-world diagnostic, no retry')
    need((c['wall_cap_s'], c['RSS_cap_bytes'], c['GPU_cap_bytes']) == (90, 4 << 30, 3 << 30), 'Original finite resource caps')
    need(c['interval_s'] == .5 and c['max_oldest_age_s'] == 2, 'Original v6 0.5s START / 2s oldest policy, no relaxation')
    need(c['CUDA_initialization_max']==c['tensor_numel_max']==c['direct_GPU_diagnostic_calls_max']==1 and c['EGL_context_max']==0, 'Exactly one CUDA-init and one float; no actual Actor/world/EGL')
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
    from direct_nvml import LIB, DRIVER_SHA, LIB_ID, DirectNvml
    from zero_retirement import zero_watch_class
    from resource_watch import ResourceWatch
    st=LIB.stat()
    need((st.st_dev,st.st_ino,st.st_size)==LIB_ID and freeze['files'].get(str(LIB))==DRIVER_SHA, 'Exact actual NVML ABI object pinned')
    need(callable(zero_watch_class(ResourceWatch).retire_for_zero) and callable(DirectNvml.observe), 'Actual diagnostic callsite imports no native handles')
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
    def authority():
        h = json.loads(hpath.read_bytes())
        q = h[c['key']]
        need(h['executing_thread_id'] == q['owner'] == OWNER and q['active'], 'Real live maintenance/scope owner')
        need(q['scope_id'] == c['scope_id'] and q['probe_PID'] == os.getpid() and q['phase'] == 'ACTUAL_NO_WORLD_NVML_OWN_PID_PARITY', 'Actual scope and worker PID')
        need(q['probe_dispatch_count'] == 1 and q['zero_dispatch_count'] == q['main_dispatch_count'] == 0 and q['program_sha256'] == pin, 'Single diagnostic count, no zero/main borrowing')
        need(q['authorization_sha256'] == authorization_sha == sha(apath), 'Immutable new authorization')
        need(not h['bulk24_collector_v1']['global_stop'], 'Original global stop')
        need(all(not row.get('active', False) for key, row in h.items() if key != c['key'] and isinstance(row, dict)), 'No competing Data authority')
        need(not q.get('stop_requested',False), 'Scope stop is not resumable')
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
    lease = watch = capture = nvml = tensor = timed = trace = producer = None
    from direct_nvml import DirectNvml, MIB
    from zero_retirement import zero_watch_class
    from collections import deque
    original_samples=deque(maxlen=24)
    errors = []
    intervals = []
    result = dict(scope_id=c['scope_id'], question=QUESTION, program_sha256=pin, PID=os.getpid(),
                  passed=False, resource_repair=False, D3_cause_recovered=False,
                  Runtime_Actor_restore_forward_Renderer_MjModel_MjData_physics_API_calls=0,
                  world_calls=0, zero_dispatch_count=0, main_dispatch_count=0,
                  actual_CUDA_init_completed=False, actual_EGL_init_completed=False,
                  is_positive_own_PID_GPU_accounting_diagnostic_not_full_skill_or_cold_Runtime=True,
                  direct_transport_promoted_to_owner_stamp_or_resource_gate=False)
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
        result['held_original_canonical_rows']=[dict(row) for row in lease.rows]
        def original_producer():
            producer()
            sample=producer.last_attempt
            original_samples.append((sample.started,sample.completed,dict(lease.last_gpu),asdict(trace.last_attempt),asdict(sample)))
        watch = zero_watch_class(ResourceWatch)(original_producer, state=state, token=object(), fast_health=health,
            interval_s=c['interval_s'], max_stale_s=c['max_oldest_age_s']).start()
        nvml=stage('pinned_direct_NVML_init_readonly',lambda:DirectNvml(enabled=True))
        def cuda():
            nonlocal tensor
            torch.cuda.init()
            tensor=torch.empty(1,device='cuda:0',dtype=torch.float32)
            torch.cuda.synchronize()
            need(tensor.numel()==1 and tensor.element_size()==4 and torch.cuda.is_initialized(),'Exactly one actual float32 element')
            result['actual_CUDA_init_completed']=True
        stage('actual_CUDA_init_one_element_NO_ACTOR',cuda)
        cuda_done=time.monotonic()
        while True:
            watch();pair=watch.last_observation_stamp
            samples=tuple(original_samples)
            matching=[s for s in samples if cuda_done<=pair[0]<=s[0]<=s[1]<=pair[1]]
            if len(matching)==1:break
            need(time.monotonic()-cuda_done<3.,'No first fresh original loaded-PID successful observation')
            time.sleep(.01)
        original=matching[0];gpu=original[2]
        need(gpu['PID']==os.getpid() and gpu['own_observation_state']=='MEASURED' and gpu['own_compute_bytes']>0,'Original loaded PID row required')
        result['paired_original_committed_watch_stamp']=list(pair)
        result['paired_original_GPU']=gpu
        result['paired_original_full_probe']=original[4]
        result['paired_original_leaf_probe']=original[3]
        # Extra read-only GPU transport comparison, not an extra owner/lease
        # composite probe and never a modification or refresh of the watch pair.
        direct=stage('pinned_direct_NVML_one_positive_loaded_own_PID',lambda:nvml.observe(initialized=True,free_floor_mib=1024))
        result['paired_direct_positive']=asdict(direct)
        result['direct_read_compared_by_original_MiB_quantization']=direct.own_bytes is not None and direct.own_bytes//MIB*MIB==gpu['own_compute_bytes']
        result['direct_vs_original_free_MiB_delta']=direct.free_mib-gpu['free_MiB']
        need(result['direct_read_compared_by_original_MiB_quantization'],'Loaded PID accounting mismatch; no new physical candidate')
        need(direct.compute_rows==1,'Only this candidate PID present in actual comparison window')
        result['ordered_original_watch_retirement']=watch.retire_for_zero()
        budget.begin_finalization()
        watch.close()
        result['watch_joined_before_NVML_and_lease_close']=not watch.thread.is_alive()
        result['passed'] = True
    except BaseException as exc:
        result.update(error_type=type(exc).__name__, resource_failure=state.reason)
    finally:
        # Seal BEFORE any cleanup/reserve reporting. No new native action resumes.
        budget.begin_finalization()
        if watch is not None and not result.get('watch_joined_before_NVML_and_lease_close'):
            try:
                watch.close()
            except BaseException as exc:
                errors.append(dict(stage='watch_close', error_type=type(exc).__name__))
        if nvml is not None:
            try:
                nvml.close();result['direct_NVML_close_completed']=True
            except BaseException as exc:
                errors.append(dict(stage='NVML_close', error_type=type(exc).__name__))
        tensor=None
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
                              CUDA_initialized=False, lease_API_world_calls=0, direct_NVML_calls=0,
                              original_watcher_cadence_s=.5, original_oldest_age_s=2)))
    else:
        raise SystemExit(run(args.config, args.pin, enabled=True))
