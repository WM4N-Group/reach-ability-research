"""Pinned original public publisher serializer, SYNTHETIC CPU fixture only."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parent))
SOURCE=Path(os.environ['DATA_ORIGINAL_SOURCE'])
sys.path.insert(0,str(SOURCE))
from scoped_io import ScopeIO,PolicyStop
from observation_io import load_controlled_publisher,bind_fresh_observation_outputs
import numpy as np
original=importlib.import_module('ainav.native.observation')
source=SOURCE/'ainav/native/observation.py'
pin=os.environ['DATA_PUBLISHER_SHA256']
assert hashlib.sha256(source.read_bytes()).hexdigest()==pin
assert os.environ['CUDA_VISIBLE_DEVICES']==''
with tempfile.TemporaryDirectory(prefix='data-observation-cpu-')as td:
    root=Path(td);live=root/'live';live.mkdir()
    # Same literal output root on both serializations gives exact embedded paths.
    packet=dict(rgb=np.arange(192,dtype=np.uint8).reshape(1,1,8,8,3),
        depth_m=np.ones((1,1,8,8,1),dtype=np.float32),
        camera_K=np.eye(3)[None],T_base_optical=np.eye(4)[None],
        proprio=np.zeros((1,1,45)),actions_previous=np.zeros((1,1,5,18)),
        action_valid=np.ones((1,1,5),dtype=bool),timestamps_s=np.array([[1.]]))
    kwargs=dict(now=1.,descriptors=[],declared_map=dict(source_ref='SOFTWARE_FIXTURE',anchors=[]),
                goal='Synthetic serializer test; NOT LIVE DATA',events=[])
    def emit(publisher,path):
        for sequence in range(1,3):
            obs=publisher.publish(packet,**kwargs)
            (path/('intent-observation-%04d.json'%sequence)).write_text(obs.encoded+'\n')
    emit(original.AcquisitionPublisher(live/'query-observations'),live)
    reference=root/'baseline';live.rename(reference);live.mkdir()
    budget=ScopeIO(live,cap_bytes=1024**2,reserve_bytes=262144)
    module=load_controlled_publisher(source,pin,budget,name='_data_observation_cpu_fixture',enabled=True)
    # Fixture calls exact binding API, not the native constructor/runtime.
    driver=SimpleNamespace(root=live,publisher=original.AcquisitionPublisher(live/'query-observations'),
        r=SimpleNamespace(step_count=0,sim=SimpleNamespace(queue=[])),sequence=0,executor=None)
    receipt=bind_fresh_observation_outputs(driver,module,budget,enabled=True)
    emit(driver.publisher,driver.root)
    paths=sorted(p.relative_to(reference)for p in reference.rglob('*')if p.is_file())
    assert len(paths)==10
    for rel in paths:assert (reference/rel).read_bytes()==(live/rel).read_bytes(),str(rel)
    size=budget.reconcile();assert size==sum((live/p).stat().st_size for p in paths)
    assert original.Path is Path
    driver.sequence=1
    try:bind_fresh_observation_outputs(driver,module,budget,enabled=True)
    except ValueError:pass
    else:raise AssertionError('Cannot bind a used driver')
    assert load_controlled_publisher('/does-not-exist','',None,name='disabled',enabled=False)is None
    import torch
    assert not torch.cuda.is_initialized()and'mujoco'not in sys.modules
    print(json.dumps(dict(role='SYNTHETIC_SERIALIZER_NOT_LIVE_NATIVE',
        original_source_sha256=pin,two_IO_sites_intentionally_changed=True,
        ten_files_byte_identical=True,query_files=8,intent_files=2,
        controlled_bytes=size,snapshot=budget.snapshot(),binding_receipt=receipt,
        original_modules_unchanged=True,Runtime_Actor_GPU_physics_training_calls=0)))
