"""Only pure CPU recorder fixtures: no Runtime, Actor restore/forward or rendering."""
from pathlib import Path
import sys,os,json,hashlib,tempfile,importlib
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');SOURCE=R/'workers/new-critic-cohort-46308-20261115-v1/inputs/AINav/common-source';sys.path.insert(0,str(SOURCE))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scoped_io import ScopeIO
from private_writer_binding import load_private_writer
import numpy as np
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
with tempfile.TemporaryDirectory(prefix='data-policy-cpu-')as td:
 root=Path(td);base=root/'baseline';base.mkdir();new=root/'candidate';new.mkdir();budget=ScopeIO(new,cap_bytes=8*1024**2,reserve_bytes=1024**2)
 pins=json.loads(Path(__file__).with_name('original_writer_pins.json').read_bytes())
 for path,pin in pins.items():assert sha(Path(path))==pin
 src=SOURCE/'mujoco_zyh/streams.py';orig=importlib.import_module('mujoco_zyh.streams');bound=load_private_writer(src,sha(src),budget,name='_data_scoped_streams_fixture',package='mujoco_zyh',enabled=True);assert orig.Path is Path
 metadata=dict(source_id='SOFTWARE_FIXTURE_NOT_NATIVE',episode_id='fixture-only',role='CPU_TEST_NOT_TASK',source_group='fixture',forecast_study_training_authorized=False,max_payload_bytes=1024**2,command_chunk_steps=4,visual_chunk_frames=4,joint_names=['j'+str(i)for i in range(18)])
 a=orig.ChunkedEpisodeWriter(base/'episode',metadata);b=bound.ChunkedEpisodeWriter(new/'episode',metadata)
 for tick in range(1,41):
  q=np.full(18,tick*.0001);issued=np.zeros((5,18));issued[0]=q;row=dict(issued=issued,delayed=issued.copy(),torque=np.zeros(18),raw_torque=np.zeros(18),q_before=q.copy(),dq_before=np.zeros(18),physical_tick=tick,time_s=tick*.005)
  a.append_command(**row);b.append_command(**row)
 a.boundary(dict(fixture=True));b.boundary(dict(fixture=True))
 with budget.open('direct-raw-fixture.npz','xb')as f:np.savez_compressed(f,rgb=np.arange(96,dtype=np.uint8).reshape(4,4,2,3))
 with np.load(new/'direct-raw-fixture.npz',allow_pickle=False)as f:assert f['rgb'].shape==(4,4,2,3)
 budget.begin_finalization();ca=a.close(outcome='SOFTWARE_FIXTURE',terminal_time_s=.2,censored=False);cb=b.close(outcome='SOFTWARE_FIXTURE',terminal_time_s=.2,censored=False)
 assert ca==cb and budget.reconcile()>0
 for p in (base/'episode').rglob('*'):
  if p.is_file():assert p.read_bytes()==(new/'episode'/p.relative_to(base/'episode')).read_bytes(),str(p)
 # A separate live state for the exact original hash-chained Journal.
 jr=root/'journal';jr.mkdir();jb=ScopeIO(jr,cap_bytes=1024**2,reserve_bytes=256*1024);jpath=SOURCE/'ainav/evidence.py';jo=importlib.import_module('ainav.evidence');jm=load_private_writer(jpath,sha(jpath),jb,name='_data_scoped_journal_fixture',package='ainav',enabled=True);oa=jo.Journal(base/'events.jsonl');ob=jm.Journal(jr/'events.jsonl')
 for i in range(100):oa(dict(event='fixture',i=i,text='字节'));ob(dict(event='fixture',i=i,text='字节'))
 jb.begin_finalization();oa.close();ob.close();assert (base/'events.jsonl').read_bytes()==(jr/'events.jsonl').read_bytes();assert jo.verify(jr/'events.jsonl')['rows']==100;jb.reconcile()
 assert load_private_writer(Path('/nonexistent'),'',None,name='disabled',enabled=False)is None
 import torch
 assert not torch.cuda.is_initialized()and'mujoco'not in sys.modules
 print(json.dumps(dict(original_40_command_recorder_fixture_byte_identical=True,direct_numpy_compressed_file_interface_pass=True,original_100_journal_rows_fixture_byte_identical=True,no_original_module_monkeypatch=True,CUDA_initialized=False,Runtime_Actor_model_restore_forward_renderer_physics_calls=0,recorder=budget.snapshot(),journal=jb.snapshot(),SOFTWARE_FIXTURE_NOT_TASK=True),ensure_ascii=False))
