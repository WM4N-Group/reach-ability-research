"""Use ONLY the caller-supplied original credential mechanism for a ready arm.

No directory search, other-process environment, key copying, key argv/logging or
isolated API probe. Original key loader validates a provided key_file; the value
lives only in this one child environment. This file does not confer admission.
"""
import argparse,hashlib,json,os,resource,sys
from pathlib import Path


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--release',type=Path,required=True);ap.add_argument('--arm',choices=('A','B'),required=True);a=ap.parse_args()
    r=a.release.resolve();admission=json.loads((r/a.arm/'main-admission.json').read_text())
    if not admission.get('admitted') or not admission.get('own_zero_passed'):raise ValueError('Own source/native zero admission required before authentication')
    root=Path(admission['new_physical_root']);freeze=root/'freeze.json'
    if (root/'attempt.claim').exists() or (root/'own-wrapper.claim').exists():
        raise ValueError('Existing actual attempt is never restarted; do not reopen credentials')
    if hashlib.sha256(freeze.read_bytes()).hexdigest()!=admission['physical_freeze_sha256']:raise ValueError('Prepared source changed')
    frozen=json.loads(freeze.read_text())
    for name in ('source/deepseek_intent_planner.py','launch_once.sh'):
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=frozen['inputs'][name]:
            raise ValueError('Credential consumer or launch script changed before authentication')
    own=json.loads((r/'runtime-source-freeze.json').read_text())
    for name,h in own['files'].items():
        if hashlib.sha256((r/name).read_bytes()).hexdigest()!=h:
            raise ValueError('Own admitted wrapper changed before authentication')
    if not (os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('DEEPSEEK_KEY_FILE')):
        raise ValueError('Supply existing secure DEEPSEEK_API_KEY or DEEPSEEK_KEY_FILE to this process; never paste key into chat')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    sys.path.insert(0,str(root/'source'))
    from deepseek_intent_planner import load_credential
    key=load_credential(key_file=os.environ.get('DEEPSEEK_KEY_FILE'))
    env=os.environ.copy();env['DEEPSEEK_API_KEY']=key
    # The prepared script is the same bounded, own-qualified native collector
    # wrapper for A/B, including correct GPU1 renderer and live native video.
    os.execve('/bin/bash',['/bin/bash',str(root/'launch_once.sh')],env)


if __name__=='__main__':main()
