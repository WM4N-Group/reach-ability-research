"""One-shot secure transport: caller stdin -> detached pair child environment.

No key files, key argv, echo, API probe, retries or new physical admission.
Only accepts the already-qualified Nov5 v3 release and exact entry pins.
The caller must disable local terminal echo before transmitting the one line.
"""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
from datetime import datetime

RELEASE = Path('/mnt/yuanyue/data/go2-piper-reachability/phe-old-v9-execution-release-20261105-v3')
PYTHON = '/mnt/yuanyue/envs/piper-zyh-mujoco-340d7d8-v1/bin/python'
ENTRY_PINS = {
    'credential_entry.py': 'c139d2eaf6445c6db72f29206a6d980277b5f1f8946682234f573600f77cd869',
    'run_pair_once.py': 'b284fcdc13ae2810b595a134e8ffca9e3b0eb62772b4a8b1e69fd8e8654f9eac',
    'runtime-source-freeze.json': '33bf591cfba13157b02bd8be920c4aed71333baded890cdd9f798a7db20adedb',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_key(value):
    if not value.startswith('sk-') or not 10 <= len(value) <= 512 or any(c.isspace() for c in value):
        raise ValueError('Credential format invalid; value suppressed')
    return value


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    r = RELEASE
    for name, digest in ENTRY_PINS.items():
        if sha(r / name) != digest:
            raise ValueError('Entry freeze mismatch before credential input')
    runtime = json.loads((r / 'runtime-source-freeze.json').read_text())
    for name, digest in runtime['files'].items():
        if sha(r / name) != digest:
            raise ValueError('Runtime freeze mismatch before credential input')
    for arm in ('A', 'B'):
        admission = json.loads((r / arm / 'main-admission.json').read_text())
        root = Path(admission['new_physical_root'])
        if not admission.get('admitted') or not admission.get('own_zero_passed'):
            raise ValueError('Missing prior actual admission')
        if sha(root / 'freeze.json') != admission['physical_freeze_sha256']:
            raise ValueError('Main freeze mismatch')
        for name, digest in json.loads((root / 'freeze.json').read_text())['inputs'].items():
            if sha(root / name) != digest:
                raise ValueError('Main input changed')
        if any((root / name).exists() for name in ('attempt.claim', 'own-wrapper.claim', 'report.json')):
            raise ValueError('Existing arm attempt is never restarted')
    if (r / 'physical-pair.claim').exists() or (r / 'control' / 'stdin-launch.json').exists():
        raise ValueError('Existing pair launch is never restarted')
    sys.path.insert(0, str(r))
    from runtime_entry import readiness
    snapshot = readiness(Path('/mnt/yuanyue/data/go2-piper-world-model'), [
        'integrated-world-model-training-gpu0.lock',
        'native-observer-physics-gpu1.lock',
        'native-observer-sdk-gpu1.lock'])
    if not snapshot['available']:
        print(json.dumps({'status': 'RESOURCE_BUSY_NO_CREDENTIAL_READ_NO_LAUNCH', 'snapshot': snapshot}), flush=True)
        return
    print('READY_FOR_ONE_PRIVATE_STDIN_LINE_NO_ECHO', flush=True)
    key = validate_key(sys.stdin.readline(514).rstrip('\n'))
    env = os.environ.copy()
    env.pop('DEEPSEEK_KEY_FILE', None)
    env.update(DEEPSEEK_API_KEY=key, CUDA_VISIBLE_DEVICES='', MUJOCO_GL='egl',
               MUJOCO_EGL_DEVICE_ID='1', OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2',
               MKL_NUM_THREADS='2', PYTHONDONTWRITEBYTECODE='1')
    control = r / 'control'
    command = ['/usr/bin/timeout', '--signal=TERM', '--kill-after=10', '14500',
               PYTHON, '-I', '-B', str(r / 'run_pair_once.py'), '--release', str(r)]
    with (control / 'actual-pair-launcher.log').open('x') as log:
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=subprocess.STDOUT, env=env, close_fds=True,
                                 start_new_session=True, cwd=r, umask=0o077)
    del env['DEEPSEEK_API_KEY']
    del key
    record = {'status': 'DETACHED_ONESHOT_PAIR_LAUNCHED', 'at': datetime.now().astimezone().isoformat(),
              'supervisor_pid': child.pid, 'release': str(r), 'command_without_secret': command,
              'credential_transport': 'private stdin to child environment only; no credential file or argv',
              'automatic_retry': False, 'whole_pair_wall_limit_s': 14500,
              'per_arm_wall_limit_s': 7200, 'launcher_sha256': sha(Path(__file__))}
    with (control / 'stdin-launch.json').open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
