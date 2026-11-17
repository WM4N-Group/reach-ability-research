"""Explicit one-probe controller; no scheduler/zero/main or retry path."""
import datetime
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

OWNER = '01a1e4e1-3037-7333-9019-a3f37effe5da'
R = Path('/mnt/yuanyue/data-team/deployments/46308-20261114')
H = R/'workspace/registry/handoff_current_status_20261115.json'
KEY = 'active_resource_cold_library_leaves_20261117_v1_scope'
now = lambda: datetime.datetime.now().astimezone().isoformat()
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cas(transform):
    raw = H.read_bytes()
    before = json.loads(raw)
    after = transform(json.loads(raw))
    assert after['executing_thread_id'] == OWNER
    assert all(after.get(k) == v for k, v in before.items() if k != KEY)
    directory = os.open(H.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(directory, fcntl.LOCK_EX)
        with H.open('rb') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            st = os.fstat(stream.fileno())
            assert stream.read() == raw and H.stat().st_ino == st.st_ino
            fd, temporary = tempfile.mkstemp(prefix='.cold-probe-', dir=H.parent)
            try:
                os.fchmod(fd, st.st_mode & 0o7777)
                with os.fdopen(fd, 'wb') as out:
                    out.write((json.dumps(after, ensure_ascii=False, indent=2)+'\n').encode())
                    out.flush()
                    os.fsync(out.fileno())
                assert H.read_bytes() == raw and H.stat().st_ino == st.st_ino
                os.replace(temporary, H)
                os.fsync(directory)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
    finally:
        os.close(directory)
    return dict(at=now(), before_H_SHA=hashlib.sha256(raw).hexdigest(), after_H_SHA=sha(H),
                all_peer_old_fields_preserved=True, mode_preserved=(H.stat().st_mode & 0o7777) == (st.st_mode & 0o7777))


def execute(config_path, pin):
    c = json.loads(Path(config_path).read_bytes())
    assert c['key'] == KEY and c['owner'] == OWNER and sha(c['freeze_path']) == pin
    freeze = json.loads(Path(c['freeze_path']).read_bytes())
    assert freeze['files'][str(Path(__file__))] == sha(__file__)
    for path, digest in freeze['files'].items():
        assert not Path(path).is_symlink() and sha(path) == digest, path
    prepared = json.loads(Path(c['prepare_receipt']).read_bytes())
    assert prepared['stage'] == 'ACTUAL_CPU_PREPARE_NO_NATIVE' and prepared['program_sha256'] == pin and prepared['CUDA_initialized'] is False
    raw = H.read_bytes()
    h = json.loads(raw)
    assert sha(H) == c['expected_H_SHA'] and h['executing_thread_id'] == OWNER and KEY not in h
    assert not h['bulk24_collector_v1']['global_stop'] and all(not row.get('active', False) for row in h.values() if isinstance(row, dict))
    assert not Path(c['output']).exists()
    used = int(subprocess.check_output(['du', '-s', '-B1', '/mnt/yuanyue/data-team'], text=True, timeout=60).split()[0])
    assert used + c['output_cap_bytes'] + c['launcher_cap_bytes'] < 40 << 30
    assert os.statvfs(R).f_bavail * os.statvfs(R).f_frsize > c['disk_floor_bytes']
    canonical = {}
    for name, inode in [('physics', 3428729629), ('sdk', 3428729630)]:
        path = R/f'resource-locks/native-observer-{name}-gpu0.lock'
        st = path.stat()
        assert (st.st_dev, st.st_ino) == (51, inode)
        canonical[str(path)] = [st.st_dev, st.st_ino]
    assert not any(len(row.split()) > 5 and row.split()[5].split(':')[-1] in {'3428729629', '3428729630'} for row in Path('/proc/locks').read_text().splitlines())
    gpu = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,memory.free,utilization.gpu', '--format=csv,noheader,nounits'], text=True, timeout=10)
    assert any(row.split(',')[0].strip() == '0' and c['GPU_UUID'] in row for row in gpu.splitlines())
    sys.path[:0] = c['import_paths']
    from scoped_io import ScopeIO
    from runner_outputs import write_json, finish_accounting
    from controlled_process import ControlledProcess
    launch = Path(c['launcher_output'])
    launch.mkdir()
    budget = ScopeIO(launch, cap_bytes=c['launcher_cap_bytes'], reserve_bytes=1 << 18, max_open=4)
    with budget.open('H-before-authorize.json.gz', 'xb') as out:
        out.write(gzip.compress(raw, mtime=0))
    def authorize(state):
        assert KEY not in state and sha(H) == c['expected_H_SHA']
        assert all(not row.get('active', False) for row in state.values() if isinstance(row, dict))
        state[KEY] = dict(active=True, owner=OWNER, scope_id=c['scope_id'], phase='ACTUAL_NO_WORLD_COLD_RESOURCE_PROBE',
            probe_PID=None, probe_dispatch_count=1, probe_max=1, zero_dispatch_count=0, main_dispatch_count=0,
            automatic_retry=False, worlds_max=0, Actor_restore_forward_max=0,
            program_sha256=pin, authorization_sha256=sha(c['authority']), question=c['question'], authorized_at=now(),
            resources=dict(owned_allocated_bytes=used, owned_limit_bytes=40 << 30, provider_quota_unknown=True,
                reserved_bytes=c['output_cap_bytes']+c['launcher_cap_bytes'], canonical=canonical, GPU_inventory=gpu))
        return state
    write_json(budget, launch/'authorize-CAS-proof.json', cas(authorize))
    child = capture = error = None
    started = time.monotonic()
    try:
        env = os.environ.copy()
        env.update(CUDA_VISIBLE_DEVICES=c['GPU_UUID'], MUJOCO_GL='egl', MUJOCO_EGL_DEVICE_ID='0', LD_PRELOAD=c['LD_PRELOAD'])
        child = ControlledProcess([c['python'], '-I', '-B', c['worker_path'], '--enabled', '--config', str(config_path), '--pin', pin],
            budget, stdout_path='startup.stdout', stderr_path='startup.stderr', env=env, cwd=c['cwd'], enabled=True)
        def bind_pid(state):
            q = state[KEY]
            assert q['active'] and q['program_sha256'] == pin and q['probe_PID'] is None
            q['probe_PID'] = child.process.pid
            return state
        write_json(budget, launch/'actual-PID-CAS-proof.json', cas(bind_pid))
        capture = child.finish(timeout_s=c['wall_cap_s']+10)
    except BaseException as exc:
        error = type(exc).__name__
        capture = getattr(exc, 'receipt', None)
        if child is not None and child.process.poll() is None:
            try:
                child.finish(timeout_s=.1)
            except BaseException:
                pass
    result_path = Path(c['output'])/'result.json'
    result = json.loads(result_path.read_bytes()) if result_path.is_file() else None
    def finish(state):
        q = state[KEY]
        assert q['active'] and q['program_sha256'] == pin
        if child is not None and child.process.poll() is None:
            q.update(phase='STOPPING_PROCESS_STILL_LIVE_NOT_CLOSED', stop_requested=True)
        else:
            q.update(active=False, phase='CLOSED_NO_RETRY', closed_at=now(), result_exists=result is not None,
                result_sha256=sha(result_path) if result is not None else None,
                passed=None if result is None else result['passed'], error_type=error,
                world_calls=0, zero_dispatch_count=0, main_dispatch_count=0)
        return state
    proof = cas(finish)
    # Nonzero child has latched ScopeIO; finalization MUST precede proof writes.
    budget.begin_finalization()
    write_json(budget, launch/'result-CAS-proof.json', proof)
    write_json(budget, launch/'launcher-result.json', dict(at=now(), program_sha256=pin, child_PID=None if child is None else child.process.pid,
        capture=capture, error_type=error, wall_s=time.monotonic()-started, worker_passed=None if result is None else result['passed']))
    finish_accounting(budget, launch/'final-output-accounting.json')
    print(json.dumps(dict(at=now(), program_sha256=pin, child_PID=None if child is None else child.process.pid,
        worker_passed=None if result is None else result['passed'], scope_active=json.loads(H.read_bytes())[KEY]['active'], H_SHA=sha(H))))


if __name__ == '__main__':
    execute(sys.argv[1], sys.argv[2])
