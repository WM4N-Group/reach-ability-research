"""One bounded original independent PUSH L0 phase controller, not a scheduler; caller supplies exact PIN.

New H scope only, own-zero then explicit separate main action; never resumes any
closed phase. Directory+file flock/SHA+inode CAS/atomic replace/mode preserved.
"""
from pathlib import Path
import datetime,fcntl,gzip,hashlib,json,os,subprocess,sys,tempfile,time
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace'
W=B/'workers/PUSH-prepared-L0-full-einsum-preload-20261118-v9';M=B/'manifests/PUSH-prepared-L0-full-einsum-preload-20261118-v9'
H=B/'registry/handoff_current_status_20261115.json';A=B/'registry/PUSH_PREPARED_L0_FULL_EINSUM_PRELOAD_AUTHORITY_20261118_v9.json'
KEY='active_PUSH_prepared_L0_full_einsum_preload_20261118_v9_scope';SCOPE='data-46308-PUSH-prepared-L0-full-einsum-preload-20261118-v9';OWNER='01a1e4e1-3037-7333-9019-a3f37effe5da'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
now=lambda:datetime.datetime.now().astimezone().isoformat()


class ResourceNotReady(RuntimeError):
    """PRE-authorization refusal, never an Actor outcome or owner freshness stamp."""


def require_no_foreign_target_compute(gpu_inventory, compute_inventory, *, physical_index=0,
                             uuid='GPU-297c1146-bcec-a8ee-8437-d9603392a2e1'):
    """New future controller guard. Pure parser; does not query, lock or dispatch.

    A different GPU may be busy. Empty /proc/locks is NOT proof of target idle.
    A later race is still possible; the child's ORIGINAL PerGpuLease stays final.
    """
    if type(gpu_inventory) is not str or type(compute_inventory) is not str:
        raise ResourceNotReady('Actual successful nvidia-smi text required')
    rows=[tuple(part.strip() for part in line.split(','))for line in gpu_inventory.splitlines()if line.strip()]
    if any(len(row)!=4 for row in rows):raise ResourceNotReady('Unknown GPU inventory schema')
    target=[r for r in rows if r[1]==uuid]
    if len(target)!=1 or target[0][0]!=str(physical_index):raise ResourceNotReady('Exact unique target index/UUID')
    if not target[0][2].isdigit() or not target[0][3].isdigit():raise ResourceNotReady('Unknown target capacity/utilization')
    if int(target[0][2])<4096:raise ResourceNotReady('Original own3GiB + shared1GiB initial headroom')
    apps=[tuple(part.strip()for part in line.split(','))for line in compute_inventory.splitlines()if line.strip()]
    if any(len(r)!=3 or not r[0].isdigit()or int(r[0])<=0 or not r[1].startswith('GPU-')for r in apps):
        raise ResourceNotReady('Unknown compute PID/UUID schema, not zero')
    target_pids=tuple(sorted(int(r[0])for r in apps if r[1]==uuid))
    if target_pids:raise ResourceNotReady('Target has another compute PID; require owner safe-phase handoff')
    return dict(target_GPU_UUID=uuid,physical_index=physical_index,foreign_target_compute_PIDs=[],
        free_MiB=int(target[0][2]),later_race_not_excluded=True,
        original_child_canonical_lease_still_required=True,not_an_OwnerStamp=True)


def cas(transform):
    raw=H.read_bytes();before=json.loads(raw);after=transform(json.loads(raw));assert after['executing_thread_id']==OWNER
    assert all(after.get(k)==v for k,v in before.items()if k!=KEY), 'All peer/old H fields unchanged'
    parent=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:
        fcntl.flock(parent,fcntl.LOCK_EX)
        with H.open('rb')as f:
            fcntl.flock(f,fcntl.LOCK_EX);st=os.fstat(f.fileno());assert f.read()==raw and H.stat().st_ino==st.st_ino
            fd,tmp=tempfile.mkstemp(prefix='.standard-L1-authority-',dir=H.parent)
            try:
                os.fchmod(fd,st.st_mode&0o7777)
                with os.fdopen(fd,'wb')as out:out.write((json.dumps(after,ensure_ascii=False,indent=2)+'\n').encode());out.flush();os.fsync(out.fileno())
                assert H.read_bytes()==raw;os.replace(tmp,H);os.fsync(parent)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
    finally:os.close(parent)
    return dict(at=now(),before_H_SHA=hashlib.sha256(raw).hexdigest(),after_H_SHA=sha(H),all_peer_old_fields_preserved=True,mode_preserved=(H.stat().st_mode&0o7777)==(st.st_mode&0o7777))


def execute(phase,pin):
    assert phase in ('zero','main')and len(pin)==64
    freeze=M/'program-freeze.json';assert sha(freeze)==pin;f=json.loads(freeze.read_bytes())
    c=json.loads((W/'protocol.json').read_bytes());assert f['files'][str(W/'protocol.json')]==sha(W/'protocol.json')
    assert f['files'][str(Path(__file__))]==sha(__file__)and f['files'][str(A)]==sha(A)
    prepared=json.loads((M/'actual-prepare-receipt.json').read_bytes());assert prepared['program_sha256']==pin and prepared['CUDA_initialized']is False
    assert prepared['stage']=='PREPARED_L0_FULL_EINSUM_PRELOAD_CPU_PREPARE_PASS'
    metadata=prepared['metadata_qualification']
    checks=prepared['query_binding_qualification']
    assert prepared['zero_lifecycle_qualification']==dict(successful_original_probe_ack_and_join=True,live_mismatch_latched=True,missing_ack_refused=True,CPU_fixture_only=True)
    clear=prepared['clearance_einsum_qualification']
    assert clear==dict(CPU_fixture_only=True,original_einsum_clearance_passed_running_import_audit=True,no_new_modules_at_exact_math_callsite=True,only_torch_backend_preloaded_no_optional_package_installed=True,original_clearance_source_sha256='817fe86a272706519ba5f1da84242b3a744da2514fe979b0a6ee7812d33fb54b',torch_backend_source_sha256='969d5271687e5540861b9e3605eb8fccc0a00eca48570625e12fdd5e40cdd05d',unchanged_optional_backend_unavailable_disabled=True,no_physics_or_resource_qualification=True)
    after=prepared['first_original_after_step_qualification']
    assert after==dict(CPU_fixture_only=True,preloaded_frozen_original_module_sha256='0e3a913491aba296ca620c107582f15c768aa74de44a6fa1a7c9f05795f9a330',real_original_after_step_wrapper_running_hook_reaches_synthetic_callee=True,masked_exception_type_path_line_chain_preserved_bounded=True,no_physics_or_resource_qualification=True)
    direct=prepared['direct_transport_qualification']
    assert direct['CPU_fixture_only'] and direct['no_native_NVML_or_lease_calls'] and direct['private_direct_call_once_no_extra_GPU_or_authority_probe']
    assert direct['driver_sha256']=='008cc04afc61b8317ed4ddccfa2d1bd367ceb6e71334eb352dc846e0ac450340'
    selected=prepared['selected_option_qualification']
    assert selected==dict(CPU_fixture_only=True,original_movement_XY_rejected=True,wrong_distance_goal_attempt_rejected=True,
        only_public_push_parameters={'push_distance_m':.6,'surface_height_m':0.},private_approach_view_and_history_preserved=True,
        original_goal_SHA_carried_unchanged=True,helper_sha256='177ec5aa34b70c656feead849b69bef20da6721c53b151112e803d643b13da55')
    assert checks['actual_watch_configuration']=={'interval_s':.5,'max_oldest_age_s':2.,'read_from_actual_object_before_start':True}
    assert all(checks[k] is True for k in ('public_Observation_returned','raw_descriptor_rejected','stale_descriptor_rejected','main_PUSH_allowed','zero_PUSH_rejected','main_NAV_rejected','health_failure_propagated','CPU_fixture_only'))
    assert prepared['all_run_helper_file_gate_cpu_checked'] and prepared['helper_count']==39
    assert metadata['original_resolver_missing_pin_negative_rejected'] and metadata['original_resolver_real_declaring_pin_positive_returned'] and metadata['original_backend_factory_executor_constructor_and_attach_ABI_returned']
    assert metadata['actual_compiled_model_or_physical_witness_verification'] is False and metadata['CUDA_initialized'] is False and metadata['not_native_admission_or_zero'] is True
    raw=H.read_bytes();h=json.loads(raw);assert h['executing_thread_id']==OWNER and not h['bulk24_collector_v1']['global_stop']
    assert all(not v.get('active',False)for k,v in h.items()if isinstance(v,dict)and k!=KEY)
    used=int(subprocess.check_output(['du','-s','-B1','/mnt/yuanyue/data-team'],text=True).split()[0]);assert used+(4<<30)+524288<40*1024**3
    stats={}
    for name,ino in [('physics',3428729629),('sdk',3428729630)]:
        p=R/f'resource-locks/native-observer-{name}-gpu0.lock';st=p.stat();assert(st.st_dev,st.st_ino)==(51,ino);stats[str(p)]=(st.st_dev,st.st_ino)
    assert not any(len(row.split())>5 and row.split()[5].split(':')[-1]in {'3428729629','3428729630'}for row in Path('/proc/locks').read_text().splitlines())
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=10)
    apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_gpu_memory','--format=csv,noheader,nounits'],text=True,timeout=10)
    target_preflight=require_no_foreign_target_compute(gpu,apps)  # SAME execution branch, before H CAS/child/count.
    peer=json.loads(Path(c['peer_safe_phase_proof']).read_bytes());assert sha(c['peer_safe_phase_proof'])==c['peer_safe_phase_proof_SHA256']
    assert peer['audit_scope_closed'] and peer['all_own_processes_exited'] and peer['all_original_FDs_closed']
    assert all(row['independent_nonblocking_reacquire_and_close'] for row in peer['original_canonical_lock_checks'])
    for d in Path('/proc').iterdir():
        if not d.name.isdigit() or int(d.name)==os.getpid():continue
        try:cmd=(d/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
        except OSError:continue
        assert not any(x in cmd for x in [str(B/'workers')+'/',str(R/'runtime/workers')+'/',str(R/'runtime/diagnostics')+'/']),(d.name,cmd[:200])
        # argv only used as a predicate, never persisted. Reject active foreign collector phase before H/child.
        argv=cmd.split();assert not any(x.startswith('/mnt/yuanyue/v-jepa/collection/') and x.endswith('.py') for x in argv),(d.name,'peer collection phase live')
    S=R/'runtime/workers'/SCOPE;root=S/phase
    if phase=='zero':assert KEY not in h and not S.exists()
    else:
        q=h[KEY];assert q['active']and q['owner']==OWNER and q['whole_program_freeze_sha256']==pin and q['zero_passed']and q['zero_dispatch_count']==1 and q['main_dispatch_count']==0
        assert not root.exists()and sha(S/'zero/result.json')==q['zero_result_sha256']
    sys.path.insert(0,str(W/'policy'));from scoped_io import ScopeIO
    from runner_outputs import write_json,finish_accounting
    from controlled_process import ControlledProcess
    L=M/('launcher-'+phase);L.mkdir();budget=ScopeIO(L,cap_bytes=262144,reserve_bytes=65536,max_open=4,text_buffer_bytes=8192)
    with budget.open('H-before-authorize.json.gz','xb')as stream:stream.write(gzip.compress(raw,mtime=0))
    def authorize(state):
        assert state['executing_thread_id']==OWNER
        if phase=='zero':
            assert KEY not in state
            state[KEY]=dict(active=True,owner=OWNER,scope_id=SCOPE,phase='PREPARED_L0_LIVE_BIAS_FULL_ZERO_AUTHORIZED_ONCE',authorization_sha256=sha(A),whole_program_freeze_sha256=pin,zero_dispatch_count=1,main_dispatch_count=0,zero_passed=False,camera_sha256=None,automatic_retry=False,question=c['question'],plan_sha256=c['plan_sha256'],resources=dict(at=now(),owned_allocated_bytes=used,owned_limit_bytes=40*1024**3,provider_quota_unknown=True,reserved_total_new_outputs_bytes=(4<<30)+524288,canonical=stats,GPU_inventory=gpu,target_compute_preflight=target_preflight),zero_PID=None)
        else:
            q=state[KEY];assert q['active']and q['whole_program_freeze_sha256']==pin and q['zero_passed']and q['main_dispatch_count']==0
            q.update(main_dispatch_count=1,main_PID=None,phase='PREPARED_L0_LIVE_BIAS_FULL_MAIN_AUTHORIZED_ONCE',main_preflight=dict(at=now(),target_compute=target_preflight,canonical=stats,GPU_inventory=gpu))
        return state
    write_json(budget,L/'authorize-CAS-proof.json',cas(authorize))
    child=None;capture=None;error=None;started=time.monotonic()
    try:
        env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=c['GPU_UUID'],MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='0',LD_PRELOAD=c['LD_PRELOAD'])
        child=ControlledProcess(['/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',c['worker_path'],'--enabled','--phase',phase,'--config',str(W/'protocol.json'),'--program-sha256',pin],budget,stdout_path='startup.stdout',stderr_path='startup.stderr',env=env,cwd=str(W),enabled=True)
        def bind_pid(state):
            q=state[KEY];assert q['active']and q['whole_program_freeze_sha256']==pin and q.get(phase+'_PID')is None;q[phase+'_PID']=child.process.pid;return state
        write_json(budget,L/'actual-PID-CAS-proof.json',cas(bind_pid))
        capture=child.finish(timeout_s=(330. if phase=='zero'else 1830.))
    except BaseException as exc:
        error=type(exc).__name__;capture=getattr(exc,'receipt',None)
        if child is not None and child.process.poll()is None:
            try:child.finish(timeout_s=.1)
            except BaseException:pass
    result_path=root/'result.json';result=json.loads(result_path.read_bytes())if result_path.is_file()else None
    def finish(state):
        q=state[KEY];assert q['active']and q['whole_program_freeze_sha256']==pin
        if child is not None and child.process.poll()is None:
            q.update(phase='PREPARED_L0_LIVE_BIAS_FULL_STOPPING_PROCESS_STILL_LIVE_NOT_CLOSED',stop_requested=True,live_PID=child.process.pid)
            return state
        if phase=='zero'and error is None and child is not None and child.process.returncode==0 and result is not None and result['passed']and result['program_sha256']==pin and result['actual_task_steps']==0 and result.get('zero_lifecycle_retirement',{}).get('watch_joined_before_observer_close') is True:
            q.update(zero_passed=True,zero_result_sha256=sha(result_path),camera_sha256=result['own_zero_camera']['spec_sha256'],phase='PREPARED_L0_LIVE_BIAS_FULL_OWN_ZERO_PASS_MAIN_NOT_AUTHORIZED')
        else:
            q.update(active=False,closed_at=now(),phase='PREPARED_L0_LIVE_BIAS_FULL_CLOSED_NO_RETRY',closed_phase=phase,result_exists=result is not None,result_sha256=sha(result_path)if result is not None else None,passed=None if result is None else result['passed'],usage_known=False if result is None else result.get('usage_known',False),actual_task_steps=None if result is None else result.get('actual_task_steps'),actual_task_sim_s=None if result is None else result.get('actual_task_sim_s'),actual_auxiliary_calibration=None if result is None else result.get('actual_auxiliary_calibration'),wall_s=None if result is None else result.get('wall_s'),case_loop=None if result is None else result.get('case_loop'),no_second_dispatch_or_control=True)
        return state
    closure_proof=cas(finish)
    budget.begin_finalization()  # Keep failure latch; allow bounded closure proof/tail accounting.
    write_json(budget,L/'result-CAS-proof.json',closure_proof)
    write_json(budget,L/'launcher-result.json',dict(at=now(),phase=phase,program_sha256=pin,child_PID=None if child is None else child.process.pid,capture=capture,error_type=error,wall_s=time.monotonic()-started,result_exists=result is not None,worker_passed=None if result is None else result['passed']))
    finish_accounting(budget,L/'final-accounting.json')
    print(json.dumps(dict(at=now(),phase=phase,program_sha256=pin,child_PID=None if child is None else child.process.pid,worker_passed=None if result is None else result['passed'],result_exists=result is not None,H_SHA=sha(H),scope_active=json.loads(H.read_bytes())[KEY]['active'])))


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--enabled',action='store_true');ap.add_argument('--phase',choices=('zero','main'));ap.add_argument('--program-sha256');args=ap.parse_args()
    if args.enabled:execute(args.phase,args.program_sha256)
