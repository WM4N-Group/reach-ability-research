"""One SDK gate and one USER-REQUESTED native-camera demo; no automatic retries."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import uuid


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def exclusive(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
@contextlib.contextmanager
def lock(p):
    with Path(p).open('a') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);yield

def verify(root):
    p=read(root/'source/protocol.json');auth=read(root/'approval.json')
    if (auth.get('approved') is not True or auth['source_manifest_sha256']!=sha(root/'source/manifest.json')
            or auth['source_protocol_sha256']!=sha(root/'source/protocol.json') or auth['root']!=str(root)
            or auth['budgets']!=dict(SDK_Apps=1,SDK_wall_s=180,physical_starts=1,physical_wall_s=1800)):
        raise PermissionError('No exact one-demo source/authority')
    for name,h in read(root/'source/manifest.json')['files'].items():
        if Path(name).name!=name or sha(root/'source'/name)!=h:raise PermissionError('Frozen video source changed')
    old=Path(p['stopped_parent_root']);terminal=read(old/'user-stop-terminal.json');ledger=read(old/'physical_ledger.json')
    if (terminal['status']!='STOPPED_USER_AFTER_ACTIVE' or ledger['starts']!=5 or ledger['active'] is not None
            or terminal['active_case_result'].get('severe') or terminal['active_case_result'].get('returncode')!=0):
        raise PermissionError('Previous physical task not safely closed')
    if sha(old/'source/manifest.json')!=p['parent_manifest_sha256']:raise PermissionError('Parent source changed')
    family=Path(p['original_family_root'])
    if sha(family/'physical_ledger.json')!=p['old_physical_ledger_sha256']:raise PermissionError('Original old-two ledger changed')
    previous=Path(p['prior_phase_root'])
    if sha(previous/'physical_ledger.json')!=p['prior_closed_ledger_sha256']:raise PermissionError('Prior eight ledger changed')
    plan=Path(p['source_refs']['source_plan']);original=read(root/'source/parent_plan.original.json')
    if sha(plan)!=original['source_plan_sha256']:raise PermissionError('Training plan changed')
    for name,h in read(plan)['source_hashes'].items():
        if sha(Path(p['source_refs']['train'])/name)!=h:raise PermissionError('Training source changed')
    for name,h in p['weight_sha256'].items():
        if sha(p['source_refs'][name])!=h:raise PermissionError('Frozen weight changed')
    return p

def sdk_gate(root):
    r=read(root/'sdk_result.json');t=read(root/'sdk_terminal.json')
    if (r.get('passed') is not True or t.get('returncode')!=0 or r.get('manifest_sha256')!=sha(root/'source/manifest.json')
            or any(r.get(k)!=0 for k in ['envs','actor_loads','physics_steps'])
            or r.get('native_video_cfg_verified') is not True or len(r.get('completed_role_checks',[]))!=4):
        raise PermissionError('No exact source-bound SDK0env pass')

def issue(root,mode,argv):
    p=verify(root);family=Path(p['original_family_root']);phase=family/'pose_allocations'/p['allocation_id']
    with lock(family/'pose_budget.lock'):
        phase.mkdir(exist_ok=True)
        if mode=='physical':
            sdk_gate(root);oldphase=family/'pose_allocations'/'native-pose-singlefactor-six-20261021-v1'
            claims=list((oldphase/'physical_claims').glob('*.json'))
            if len(claims)!=5 or (oldphase/'physical_claims/seed120603-P3.json').exists():raise PermissionError('Unused original slot no longer free')
            release=oldphase/'unused-slot-release-for-native-video.json'
            if release.exists():raise PermissionError('Slot release already issued; no retry')
            # Preserve original six-slot reservation. This append-only amendment
            # transfers its one never-started slot, rather than adding capacity.
            total=2+sum(read(x)['max_starts'] for x in (family/'pose_allocations').glob('*/reservation.json'))
            if total!=16:raise PermissionError('Unexpected parent capacity')
            exclusive(release,dict(released_starts=1,release_reason='User stops unrecorded remaining cell and requests one native-video demo',
                withdrawn_case='seed120603-P3',old_ledger_sha256=sha(Path(p['stopped_parent_root'])/'physical_ledger.json'),
                transferred_to=p['allocation_id'],source_manifest_sha256=sha(root/'source/manifest.json')))
            exclusive(phase/'reservation.json',dict(max_starts=1,allocation_id=p['allocation_id'],release_root=str(root),
                source_manifest_sha256=sha(root/'source/manifest.json'),offset_release=str(release),net_parent_reserved=16,
                role='explicit_requested_recording_demo_not_independent_test'))
        elif mode!='sdk':raise PermissionError('Unknown mode')
        nonce=uuid.uuid4().hex
        ticket=dict(mode=mode,root=str(root),argv=argv,source_manifest_sha256=sha(root/'source/manifest.json'),
                    approval_sha256=sha(root/'approval.json'),nonce=nonce,supervisor_pid=os.getpid(),
                    script='sdk_check.py' if mode=='sdk' else 'probe.py')
        exclusive(phase/(mode+'.claim.json'),ticket);(root/'permits').mkdir(exist_ok=True)
        file=root/'permits'/(mode+'.json');exclusive(file,ticket)
        return file,nonce

_ADMITTED=None

def require_execution_authority():
    global _ADMITTED
    import sys
    root=Path(__file__).resolve().parent.parent
    file=Path(os.environ.get('REACH_VIDEO_PERMIT','/NO_VIDEO_TICKET'))
    if file.parent!=root/'permits':raise PermissionError('No exact native-video permit before App')
    ticket=read(file);p=verify(root)
    if (ticket['source_manifest_sha256']!=sha(root/'source/manifest.json') or ticket['approval_sha256']!=sha(root/'approval.json')
            or ticket['nonce']!=os.environ.get('REACH_VIDEO_NONCE') or Path(sys.argv[0]).resolve()!=root/'source'/ticket['script']
            or sys.argv[1:]!=ticket['argv'] or not Path('/proc',str(ticket['supervisor_pid'])).exists()):
        raise PermissionError('Video launch identity mismatch')
    identity=(os.getpid(),str(file),ticket['nonce'])
    if _ADMITTED==identity:return
    if ticket['mode']=='physical':sdk_gate(root)
    exclusive(root/'permits'/(ticket['mode']+'.admitted.json'),dict(pid=os.getpid(),mode=ticket['mode']))
    _ADMITTED=identity
