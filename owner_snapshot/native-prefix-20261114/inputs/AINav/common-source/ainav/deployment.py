"""Explicit host deployment coordinates, never a skill/controller override.

Default is the historical A800 GPU1. The user-authorized 5090 profile changes
ONLY device selection and path/lock declarations; prior frozen runs stay intact.
"""
from dataclasses import asdict,dataclass
from pathlib import Path


@dataclass(frozen=True)
class HostProfile:
    name:str
    root:str
    actor_device:str
    egl_device_id:int
    shared_gpu:bool
    def __post_init__(self):
        if self.actor_device not in ('cuda:0','cuda:1') or self.egl_device_id not in (0,1):raise ValueError('Explicit registered CUDA/EGL device required')
        if not Path(self.root).is_absolute() or not self.name:raise ValueError('Explicit absolute host deployment root required')
    @property
    def lock_path(self):
        if self.name=='a800':return '/root/wm-open-baselines/gpu1.lock'
        return str(Path(self.root)/'locks'/('gpu'+str(self.egl_device_id)+'.lock'))
    def runtime_config(self,native_config):
        result=dict(native_config);result['actor_device']=self.actor_device
        changed={k for k in set(result)|set(native_config) if result.get(k)!=native_config.get(k)}
        if changed-{'actor_device'}:raise RuntimeError('Deployment may not change native task/controller configuration')
        return result
    def report(self):return dict(asdict(self),lock_path=self.lock_path,controller_actor_scene_parameters_changed=False)


def profile(name):
    if name=='a800':return HostProfile('a800','/mnt/yuanyue/ainav','cuda:1',1,True)
    if name=='yuanyue-5090':return HostProfile('yuanyue-5090','/workspace/project/ainav','cuda:0',0,True)
    raise ValueError('Choose an explicitly registered deployment; no automatic CPU/other-GPU fallback')
