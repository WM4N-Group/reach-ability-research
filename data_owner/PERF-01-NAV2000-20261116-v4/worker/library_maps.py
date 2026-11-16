"""Named ELF closure + ONE measured EGL memfd pattern, no blanket deleted skip.
New policy: file SHA inventory stays separate from runtime-generated RX identity.
Generated code is owner-authorized bootstrap trust, not a named file SHA/signature.
"""
from pathlib import Path
from dataclasses import dataclass
import hashlib,json,os

class MappingAdmissionError(RuntimeError):pass

def deny(reason,row):
    raise MappingAdmissionError(reason+'; mapping_identity='+json.dumps(row,sort_keys=True))

@dataclass(frozen=True)
class ExecutableSnapshot:
    files:frozenset
    generated:tuple
    def __iter__(self):return iter(self.files)
    def record(self):
        return dict(named_file_paths=sorted(self.files),runtime_generated_RX=[dict(v)for v in self.generated],
            runtime_RX_not_file_SHA=True,bootstrap_owner_trust_not_root_or_native_memory_protection=True)


def _rx_digest(lo,hi):
    fd=os.open('/proc/self/mem',os.O_RDONLY|os.O_CLOEXEC);h=hashlib.sha256();at=lo
    try:
        while at<hi:
            data=os.pread(fd,min(65536,hi-at),at)
            if not data:raise RuntimeError('Short mapped RX read')
            h.update(data);at+=len(data)
    finally:os.close(fd)
    return h.hexdigest()


def _capture(lines,policy,read_rx):
    files=set();generated=[]
    if policy is not None:
        if (policy.get('kind')!='OBSERVED_EGL_MEMFD_RX_8192_PINNED_DRIVER_BOOTSTRAP_V1'
            or policy.get('name')!='/memfd:/.glXXXXXX (deleted)'
            or not policy.get('evidence_result_sha256')or not policy.get('driver_files_sha256')):
            raise ValueError('Specific measured GPU-library evidence + driver freeze required')
    for line in lines:
        f=line.split(maxsplit=5)
        if len(f)<6 or 'x'not in f[1]or not f[5].startswith('/'):continue
        name=f[5];lo,hi=[int(v,16)for v in f[0].split('-')]
        row=dict(address=f[0],permissions=f[1],offset=f[2],device=f[3],inode=int(f[4]),name=name,bytes=hi-lo)
        if name.endswith(' (deleted)'):
            if (policy is None or name!=policy['name']or f[1]!='r-xs'or int(f[2],16)!=0
                or f[3]!='00:01'or hi-lo!=8192 or int(f[4])<=0):
                deny('Unapproved deleted executable mapping; NOT silently skipped',row)
            row['RX_sha256']=read_rx(lo,hi)
            if type(row['RX_sha256'])is not str or len(row['RX_sha256'])!=64:deny('Unknown actual RX bytes',row)
            generated.append(tuple(sorted(row.items())))
        else:files.add(name)  # Exact file hash/stat/canonical policy is FrozenFiles, not duplicated here.
    if not files:raise MappingAdmissionError('Unknown/empty named executable file closure')
    if len(generated)>4:raise MappingAdmissionError('Unexpected EGL generated RX mapping count')
    return ExecutableSnapshot(frozenset(files),tuple(sorted(generated)))


def executable_file_maps(gl_runtime_policy=None):
    # Read kernel VMA metadata once and only8KiB/pattern RX, not repeated full ELF hashing.
    return _capture(Path('/proc/self/maps').read_text().splitlines(),gl_runtime_policy,_rx_digest)
