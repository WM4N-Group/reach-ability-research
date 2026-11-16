"""Original raw_frames -> new actual encoder call path, four synthetic frames only."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scoped_io import ScopeIO
from private_writer_binding import load_private_writer
from runner_outputs import write_json
from controlled_encoder import encode_raw_master
import numpy as np
source=Path(os.environ['DATA_RAW_SOURCE']);pin=os.environ['DATA_RAW_SHA256']
with tempfile.TemporaryDirectory(prefix='data-master-encoder-SOFTWARE-')as td:
    root=Path(td);budget=ScopeIO(root,cap_bytes=8*1024**2,reserve_bytes=1024**2)
    raw=load_private_writer(source,pin,budget,name='_data_encoder_raw_SOFTWARE',enabled=True)
    rawroot=root/'direct-third-view';rawroot.mkdir()
    spec=dict(kind='named_world',name='SYNTHETIC_ONLY',width=16,height=16,
        stride_physics_ticks=20,chunk_frames=16,max_bytes=1024**2)
    write_json(budget,rawroot/'metadata.json',dict(origin=raw.SOFTWARE,camera_spec=spec))
    r=object.__new__(raw.OptionalRawThirdView);r.root=raw.Path(rawroot);r.spec=spec
    r.bytes=r.archived=0;r.chunks=[];r.buffer=[(i*20,i*.1,np.full((16,16,3),i*32,dtype=np.uint8))for i in range(4)]
    r._flush()
    closure=dict(schema='Data-direct-third-view-raw-closure-v1',state_replay_or_rerender_used=False,
        origin=raw.SOFTWARE,metadata_sha256=raw.sha(rawroot/'metadata.json'),
        camera_spec_sha256=raw.spec_sha(spec),chunks=r.chunks,archived_frames=4,
        actual_run_end_time_s=.3,complete_for_capture_grid=True,direct_from_current_live_runtime=False)
    write_json(budget,rawroot/'closure.json',closure)
    budget.begin_finalization()
    result=encode_raw_master(raw,rawroot,budget,ffmpeg='/usr/bin/ffmpeg',
        ffmpeg_sha256='36d94a605d612e4090d1b8aec889d0c0801c6eafb1593c90f5c0dfd2e2966a45',
        ffprobe='/usr/bin/ffprobe',ffprobe_sha256=hashlib.sha256(Path('/usr/bin/ffprobe').read_bytes()).hexdigest(),
        enabled=True,allow_software_fixture=True)
    assert result['software_fixture']and result['actual_raw_frames']==4
    write_json(budget,root/'video-encoding-result.json',result)
    budget.reconcile()
    assert result['ffprobe']['streams'][0]['nb_read_frames']=='4'
    assert encode_raw_master(None,'/nonexistent',None,ffmpeg='',ffmpeg_sha256='',ffprobe='',ffprobe_sha256='')is None
    print(json.dumps(dict(role='SOFTWARE_SYNTHETIC_MASTER_NOT_EXPERIMENT_FOOTAGE',result=result,
        budget=budget.snapshot(),Runtime_Actor_model_renderer_GPU_physics_calls=0)))
