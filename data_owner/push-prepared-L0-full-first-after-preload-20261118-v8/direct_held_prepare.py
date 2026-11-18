"""CPU-only execution of the private GPU transport call site on exact source."""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from tempfile import TemporaryDirectory
import hashlib,os
from direct_held_check import build_direct_held_check
from direct_nvml import CAP,LIB,LIB_ID,DRIVER_SHA,NvmlReadError,own_bytes,U32_MAX,U64_MAX

def qualify_direct_held(freeze):
    import per_gpu_lease as api
    import torch
    assert not torch.cuda.is_initialized()
    st=LIB.stat();assert (st.st_dev,st.st_ino,st.st_size)==LIB_ID and freeze['files'][str(LIB)]==DRIVER_SHA
    calls=[];reject=None;stub=NS(free_mib=23684,utilization=0,own_bytes=None)
    def auth():
        calls.append('auth')
        if reject=='owner':raise api.ResourceStop('fixture owner revoked')
    def read(*,initialized,free_floor_mib):
        calls.append('read');assert free_floor_mib==1024 and initialized() is False
        if reject=='GPU':raise NvmlReadError('fixture reader unavailable')
        return stub
    def refused(action,typename):
        try:action()
        except typename:return
        raise AssertionError('guard did not refuse')
    with TemporaryDirectory()as name:
        d=Path(name);lease=api.PerGpuLease(physical_index=0,authority_check=auth)
        assert build_direct_held_check(lease.check,read) is None
        fds=[]
        try:
            for i in range(2):
                p=d/f'lock{i}';p.touch();fd=os.open(p,os.O_RDONLY);fds.append(fd);s=p.stat()
                lease.rows.append(dict(path=str(p),device=s.st_dev,inode=s.st_ino))
            lease.fds=list(fds);binding=d/'binding';binding.write_bytes(b'SYNTHETIC fixture')
            lease.profile=dict(lease.profile,binding=binding,sha256=hashlib.sha256(binding.read_bytes()).hexdigest())
            check,trace=build_direct_held_check(lease.check,read,enabled=True)
            with patch.object(api.subprocess,'check_output',side_effect=AssertionError('Unexpected CLI in private direct path')):
                row=check(force=True);assert row['own_observation_state']=='CUDA_UNINITIALIZED_NO_PID_ROW' and row['free_MiB']==23684 and row['UUID']==api.PROFILES[0]['UUID']
                assert calls==['auth','read'] and trace.GPU_read_calls==1
                assert check() is row and trace.GPU_read_calls==1
                reject='owner';refused(lambda:check(force=True),api.ResourceStop);assert trace.GPU_read_calls==1
                reject='GPU';refused(lambda:check(force=True),NvmlReadError);assert trace.GPU_read_calls==2 and lease.last_gpu is row
                reject=None;stub.free_mib=1023;refused(lambda:check(force=True),api.ResourceStop)
                stub.free_mib=23684;stub.own_bytes=CAP+1;refused(lambda:check(force=True),api.ResourceStop)
                assert trace.GPU_read_calls==4 and lease.last_gpu is row
                lease.pid+=1;refused(lambda:check(force=True),api.ResourceStop);assert trace.GPU_read_calls==4;lease.pid-=1
                binding.write_bytes(b'drift');refused(lambda:check(force=True),api.ResourceStop);assert trace.GPU_read_calls==4
                (d/'lock0').rename(d/'old');(d/'lock0').touch();refused(lambda:check(force=True),api.ResourceStop);assert trace.GPU_read_calls==4
        finally:
            for fd in fds:os.close(fd)
    assert own_bytes((),pid=1,initialized=False) is None
    refused(lambda:own_bytes((),pid=1,initialized=True),NvmlReadError)
    refused(lambda:own_bytes(((1,U64_MAX,U32_MAX,U32_MAX),),pid=1,initialized=True),NvmlReadError)
    assert not torch.cuda.is_initialized()
    return dict(CPU_fixture_only=True,no_native_NVML_or_lease_calls=True,
        original_guards_retained=['held_FDs_path_inodes','live_PID','authority','binding_SHA','free_floor','own_GPU_cap'],
        original_entry_and_final_CLI_not_modified=True,uninitialized_missing_distinct_from_loaded_missing_unknown=True,
        private_direct_call_once_no_extra_GPU_or_authority_probe=True,real_native_pid_parity_separately_matched=True,
        driver_sha256=DRIVER_SHA)
