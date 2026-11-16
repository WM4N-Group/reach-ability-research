"""ONE opt-in GPU-library mapping diagnostic, NOT a simulation/Actor/Renderer.
CUDA init + 16x16 EGL context only, real original GPU0 lease held throughout.
Read actual deleted RX identities/bytes. Never recover/reopen a failed world.
"""
from pathlib import Path
import argparse,hashlib,json,os,resource,signal,sys,time,traceback
OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
UUID='GPU-297c1146-bcec-a8ee-8437-d9603392a2e1'

def diagnostic(config_path=None,pin=None,*,enabled=False):
    if enabled is not True:return None
    c=json.loads(Path(config_path).read_bytes());start=time.monotonic()
    assert sys.prefix=='/mnt/yuanyue/data-team/env-native-v1'and sys.version_info[:3]==(3,11,16)
    assert os.environ.get('CUDA_VISIBLE_DEVICES')==UUID and os.environ.get('MUJOCO_EGL_DEVICE_ID')=='0'and os.environ.get('MUJOCO_GL')=='egl'
    freeze=json.loads(Path(c['freeze']).read_bytes());assert hashlib.sha256(Path(c['freeze']).read_bytes()).hexdigest()==pin
    for path,sha in freeze['files'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha
    H=Path(c['handoff']);A=Path(c['authority'])
    def authority():
        h=json.loads(H.read_bytes());q=h[c['key']]
        assert h['executing_thread_id']==q['owner']==OWNER and q['active']and q['scope_id']==c['scope_id']
        assert q['probe_dispatch_count']==1 and q['program_sha256']==pin
        assert q['authorization_sha256']==hashlib.sha256(A.read_bytes()).hexdigest()
        assert not h['bulk24_collector_v1']['global_stop']
        assert all(not v.get('active',False)for k,v in h.items()if k!=c['key']and isinstance(v,dict))
    authority();sys.path[:0]=c['imports'];from per_gpu_lease import PerGpuLease
    from scoped_io import ScopeIO
    from fd_capture import FDCapture
    from runner_outputs import write_json,finish_accounting
    root=Path(c['output']);assert not root.exists();root.mkdir(parents=True)
    budget=ScopeIO(root,cap_bytes=8*1024**2,reserve_bytes=1024**2)
    lease=None;ctx=None;capture=None;errors=[];report=dict(scope_id=c['scope_id'],role='GPU_LIBRARY_MAPPING_DIAGNOSTIC_NOT_PHYSICS',passed=False,stages=[],Runtime_Actor_model_restore_forward_Renderer_MjModel_MjData_physics_calls=0,CUDA_context_initializations=0,EGL_context_initializations=0)
    def timeout(*_):raise RuntimeError('Bounded mapping diagnostic deadline')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,60.);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.nice(15)
    def snapshot(label):
        rows=[];fdlinks=[]
        for p in Path('/proc/self/fd').iterdir():
            try:fdlinks.append(dict(fd=int(p.name),target=os.readlink(p)))
            except OSError:pass
        for line in Path('/proc/self/maps').read_text().splitlines():
            f=line.split(maxsplit=5)
            if 'x'not in f[1]or len(f)<6 or not f[5].endswith(' (deleted)'):continue
            lo,hi=[int(v,16)for v in f[0].split('-')];name=f[5]
            row=dict(raw=line,address_range=f[0],permissions=f[1],offset=f[2],device=f[3],inode=int(f[4]),name=name,bytes=hi-lo,backing_path_exists=Path(name[:-10]).exists(),fd_links=[v for v in fdlinks if v['target']==name])
            try:row['map_files_target']=os.readlink('/proc/self/map_files/'+f[0])
            except OSError as e:row['map_files_readlink_error']=repr(e)
            if 'r'in f[1]and 0<hi-lo<=64*1024**2:
                try:
                    h=hashlib.sha256();at=lo;fd=os.open('/proc/self/mem',os.O_RDONLY|os.O_CLOEXEC)
                    try:
                        while at<hi:
                            chunk=os.pread(fd,min(1024**2,hi-at),at)
                            if not chunk:raise RuntimeError('Short read of self mapped RX')
                            h.update(chunk);at+=len(chunk)
                    finally:os.close(fd)
                    row['self_RX_bytes_sha256']=h.hexdigest()
                except BaseException as e:row['self_RX_bytes_error']=repr(e)
            rows.append(row)
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<4*1024**3
        report['stages'].append(dict(stage=label,deleted_RX=rows,lease=None if lease is None else lease.check(force=True),CUDA_initialized=('torch'in sys.modules and sys.modules['torch'].cuda.is_initialized())))
        write_json(budget,root/('stage-%02d.json'%len(report['stages'])),report['stages'][-1])
    try:
        capture=FDCapture(budget,enabled=True)
        lease=PerGpuLease(physical_index=0,authority_check=authority).__enter__()
        import torch
        assert not torch.cuda.is_initialized();snapshot('torch_CPU_import_only')
        torch.cuda.init();probe_tensor=torch.empty(1,device='cuda:0',dtype=torch.float32);report['CUDA_context_initializations']=1;report['CUDA_probe_tensor_numel']=1;snapshot('after_CUDA_init_NO_MODEL_OR_FORWARD')
        from mujoco.egl import GLContext
        ctx=GLContext(16,16);ctx.make_current();report['EGL_context_initializations']=1;snapshot('after_EGL_context_NO_MODEL_DATA_RENDERER')
        ctx.free();ctx=None;snapshot('after_EGL_free')
        named=set()
        for row in Path('/proc/self/maps').read_text().splitlines():
            fields=row.split(maxsplit=5)
            if len(fields)==6 and 'x'in fields[1]and fields[5].startswith('/')and not fields[5].endswith(' (deleted)')and any(x in Path(fields[5]).name for x in('libnvidia','libcuda')):named.add(fields[5])
        report['loaded_driver_file_identity']=[]
        for name in sorted(named):
            p=Path(name);st=p.stat();entry=dict(path=name,size=st.st_size,device=st.st_dev,inode=st.st_ino)
            if st.st_size<=256*1024**2:
                h=hashlib.sha256()
                with p.open('rb')as stream:
                    for chunk in iter(lambda:stream.read(1024**2),b''):h.update(chunk)
                entry['sha256']=h.hexdigest()
            report['loaded_driver_file_identity'].append(entry)
        report['passed']=True
    except BaseException as e:report.update(error=repr(e),traceback=traceback.format_exc())
    finally:
        budget.begin_finalization()
        if ctx is not None:
            try:ctx.free()
            except BaseException as e:errors.append(dict(stage='EGL_free',error=repr(e)))
        if lease is not None:
            try:report['final_GPU']=lease.check(force=True)
            except BaseException as e:errors.append(dict(stage='final_GPU',error=repr(e)))
            lease.__exit__()
        if capture is not None:
            try:report['capture']=capture.close()
            except BaseException as e:report['capture']=getattr(e,'receipt',capture.snapshot());errors.append(dict(stage='FD_close',error=repr(e)))
        report.update(wall_s=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,close_errors=errors)
        if errors:report['passed']=False
        write_json(budget,root/'result.json',report);finish_accounting(budget,root/'final-accounting.json');signal.setitimer(signal.ITIMER_REAL,0)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--enabled',action='store_true');p.add_argument('--config');p.add_argument('--pin');a=p.parse_args()
    if a.enabled:sys.exit(0 if diagnostic(a.config,a.pin,enabled=True)['passed']else 1)
