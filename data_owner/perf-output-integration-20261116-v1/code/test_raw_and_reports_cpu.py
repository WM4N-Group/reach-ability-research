"""Exact raw chunk serializer + Data reports/PNG, all synthetic; no camera calls."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scoped_io import ScopeIO,scoped_path_class
from private_writer_binding import load_private_writer
from runner_outputs import write_json,write_png
import numpy as np
from PIL import Image
source=Path(os.environ['DATA_RAW_SOURCE']);pin=os.environ['DATA_RAW_SHA256']
assert hashlib.sha256(source.read_bytes()).hexdigest()==pin
spec=importlib.util.spec_from_file_location('_data_raw_original_fixture',source)
original=importlib.util.module_from_spec(spec);sys.modules[spec.name]=original;spec.loader.exec_module(original)
with tempfile.TemporaryDirectory(prefix='data-raw-reports-CPU-')as td:
    root=Path(td);live=root/'live';live.mkdir();baseline=root/'base';baseline.mkdir()
    budget=ScopeIO(live,cap_bytes=4*1024**2,reserve_bytes=262144)
    bound=load_private_writer(source,pin,budget,name='_data_raw_controlled_fixture',enabled=True)
    def emit(module,path):
        # Only _flush serializer. Deliberately no LiveMuJoCoCamera instance/factory.
        recorder=object.__new__(module.OptionalRawThirdView)
        recorder.root=module.Path(path);recorder.bytes=0;recorder.archived=0;recorder.chunks=[]
        recorder.spec=dict(max_bytes=1024**2)
        recorder.buffer=[(i*20,i*.1,np.full((8,8,3),i,dtype=np.uint8))for i in range(4)]
        recorder._flush();return recorder
    a=emit(original,baseline);b=emit(bound,live)
    assert (baseline/'raw-rgb/000000.npz').read_bytes()==(live/'raw-rgb/000000.npz').read_bytes()
    assert a.chunks==b.chunks and a.archived==b.archived==4
    for sequence in range(3):write_json(budget,live/'progress.json',dict(i=sequence,text='原报告'))
    assert json.loads((live/'progress.json').read_bytes())['i']==2
    write_png(budget,live/'camera.png',Image.fromarray(np.zeros((8,8,3),dtype=np.uint8)))
    budget.begin_finalization();write_json(budget,live/'result.json',dict(passed=False,fixture=True))
    counted=budget.reconcile();assert counted==sum(p.stat().st_size for p in live.rglob('*')if p.is_file())
    assert original.Path is Path
    print(json.dumps(dict(role='SYNTHETIC_SERIALIZERS_NOT_LIVE_CAMERA_OR_NATIVE',
        original_raw_sha256=pin,raw_chunk_byte_identical=True,synthetic_raw_frames=4,
        Data_progress_atomic_replace_and_final_report=True,PNG_controlled_file_object=True,
        budget=budget.snapshot(),Runtime_Actor_GPU_physics_training_calls=0)))
