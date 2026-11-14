"""Source-bound permission and append-only allocation/claim accounting.

Original ledger is read-only. Reservations, not just completed starts, consume
capacity. No crash recovery/retry/replacement is automatic. No simulator imports.
"""
import contextlib,fcntl,hashlib,json,os,time,uuid
from pathlib import Path


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def save(path,value):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
def exclusive(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
@contextlib.contextmanager
def locked(path):
    with Path(path).open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield


def context(root):
    root=Path(root).resolve();source=root/'source';p=load(source/'protocol.json')
    return root,source,p

def verify_source(root):
    root,source,p=context(root)
    if root!=Path(p['execution_root']).resolve():raise PermissionError('Release is not at its bound execution root')
    manifest=load(source/'manifest.json')
    for name,digest in manifest['files'].items():
        if Path(name).name!=name or sha(source/name)!=digest:raise PermissionError('Frozen release source mismatch: '+name)
    return p

def approval(root,mode):
    root,source,p=context(root)
    file=root/'approval.json'
    if not file.is_file():raise PermissionError('No explicit source-bound approval; no claim/App may be consumed')
    a=load(file)
    if a.get('approved') is not True or a.get('release_root')!=str(root) or a.get('source_manifest_sha256')!=sha(source/'manifest.json') or a.get('source_protocol_sha256')!=sha(source/'protocol.json'):
        raise PermissionError('Approval does not bind this exact release/root/protocol')
    if a.get('allocation_id')!=p['allocation_id']:raise PermissionError('Wrong approval allocation identity')
    budgets=a.get('budgets',{})
    if budgets.get('additional_SDK_Apps')!=1 or budgets.get('SDK_wall_s')!=180:raise PermissionError('No one-App SDK allocation')
    if mode=='physical' and (budgets.get('physical_starts')!=8 or budgets.get('reallocated_from_old14')!=8 or budgets.get('additional_total_physical_starts')!=0):
        raise PermissionError('No explicit8-of14 reallocation; original approval is not new authority')
    verify_source(root)
    return a,p


def family_snapshot(p):
    family=Path(p['original_family_root']);ledger=family/'physical_ledger.json'
    if sha(ledger)!=p['old_physical_ledger_sha256']:raise PermissionError('Old ledger changed; human audit required')
    old=load(ledger);auth=load(family/'approval.json')
    if auth['budgets']['max_new_Isaac_starts']!=16 or old['starts']!=2 or old['active'] is not None or len(old['not_run'])!=14 or not old['status'].startswith('STOPPED'):
        raise PermissionError('Old stopped2/16 identity not preserved')
    return family,old


def verify_external(root):
    _,source,p=context(root);ref=p['source_refs'];parent=load(source/'parent_plan.original.json');plan=Path(ref['source_plan'])
    if sha(plan)!=parent['source_plan_sha256']:raise PermissionError('Frozen training plan changed')
    for name,digest in load(plan)['source_hashes'].items():
        if sha(Path(ref['train'])/name)!=digest:raise PermissionError('Frozen train input changed: '+name)
    for name,digest in p['weight_sha256'].items():
        if sha(ref[name])!=digest:raise PermissionError('Frozen policy weight changed: '+name)


def pid_start_ticks(pid):
    return Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[19]

def phase_directory(p):return Path(p['original_family_root'])/'pose_allocations'/p['allocation_id']

def sdk_gate(root):
    root,source,p=context(root);terminal=load(root/'sdk_terminal.json');result=load(root/'sdk_result.json')
    if terminal.get('returncode')!=0 or terminal.get('gate_passed') is not True or terminal.get('manifest_sha256')!=sha(source/'manifest.json') or result.get('passed') is not True or result.get('manifest_sha256')!=sha(source/'manifest.json'):
        raise PermissionError('No complete SDK pass for this exact release')
    if any(result.get(k)!=0 for k in ['envs','actor_loads','physics_steps']):raise PermissionError('SDK0env contract violated')
    checks=result.get('completed_role_checks',[])
    expected={(arm,role) for arm in p['arms'] for role in ['planning','final_actual']}
    if (len(checks)!=8 or {(c.get('arm'),c.get('role')) for c in checks}!=expected
            or not all(c.get('state_restored') is True for c in checks)
            or not all(result.get(k) is True for k in ['actual_native_definitions_executed','actual_main_CFG_prefix_executed','common_actual_verifier_matches_original'])):
        raise PermissionError('SDK completion evidence is partial, not a full role/CFG/geometry gate')


def reserve_physical(root):
    a,p=approval(root,'physical');family,_=family_snapshot(p);sdk_gate(root)
    if (Path(root)/'physical_ledger.json').exists():raise PermissionError('Existing phase ledger: never resume/retry automatically')
    with locked(family/'pose_budget.lock'):
        allocations=family/'pose_allocations';allocations.mkdir(exist_ok=True)
        reservations=[load(f) for f in allocations.glob('*/reservation.json')]
        if 2+sum(r['max_starts'] for r in reservations)+8>16:raise PermissionError('Parent16 cap overallocated, including reservations')
        phase=phase_directory(p);phase.mkdir(exist_ok=True)
        reservation=dict(schema='explicit8-of14-reservation-v1',allocation_id=p['allocation_id'],release_root=str(Path(root).resolve()),
            source_manifest_sha256=sha(Path(root)/'source/manifest.json'),old_ledger_sha256=p['old_physical_ledger_sha256'],max_starts=8,
            parent_consumed=2,parent_max=16,approval_sha256=sha(Path(root)/'approval.json'),created_unix=time.time())
        exclusive(phase/'reservation.json',reservation);(phase/'physical_claims').mkdir()
        return reservation


def make_permit(root,mode,argv,item=None):
    a,p=approval(root,mode);family,_=family_snapshot(p);root=Path(root).resolve();phase=phase_directory(p)
    with locked(family/'pose_budget.lock'):
        (family/'pose_allocations').mkdir(exist_ok=True);phase.mkdir(exist_ok=True)
        if mode=='sdk':claim_path=phase/'sdk.claim.json'
        else:
            sdk_gate(root);r=load(phase/'reservation.json')
            if r['release_root']!=str(root) or r['source_manifest_sha256']!=sha(root/'source/manifest.json') or r['max_starts']!=8:raise PermissionError('No matching8-start reservation')
            schedule=p['schedule']
            if item not in schedule:raise PermissionError('Unregistered case')
            claims=phase/'physical_claims'
            if len(list(claims.glob('*.json')))>=8:raise PermissionError('Eight claims already consumed')
            # Case identity is also the exclusive claim key: never replace/repeat it.
            claim_path=claims/(item['output_name']+'.json')
        nonce=uuid.uuid4().hex
        claim=dict(mode=mode,release_root=str(root),allocation_id=p['allocation_id'],source_manifest_sha256=sha(root/'source/manifest.json'),
            approval_sha256=sha(root/'approval.json'),supervisor_pid=os.getpid(),supervisor_start_ticks=pid_start_ticks(os.getpid()),created_unix=time.time(),nonce=nonce,item=item)
        exclusive(claim_path,claim)
        permits=root/'permits';permits.mkdir(exist_ok=True)
        path=permits/('sdk.json' if mode=='sdk' else item['output_name']+'.json')
        ticket=dict(claim,claim_path=str(claim_path),argv=argv,script='sdk_check.py' if mode=='sdk' else 'probe.py')
        exclusive(path,ticket)
        return path,nonce
