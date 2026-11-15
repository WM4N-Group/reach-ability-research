from pathlib import Path
import json,base64,subprocess,shlex
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;D=B/'development/complex-live-video-postprocess-20261115-v2';rows={p.name:base64.b64encode(p.read_bytes()).decode()for p in D.glob('*.py')}
code=r'''from pathlib import Path
import sys,json,base64,os,hashlib,time,subprocess
x=json.load(sys.stdin);B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');R=B.parent;D=B/'development/complex-live-video-postprocess-20261115-v2';D.mkdir(parents=True,exist_ok=False)
for name,raw in x.items():
 assert Path(name).name==name
 with(D/name).open('xb')as f:f.write(base64.b64decode(raw))
sys.path.insert(0,str(D));os.nice(15)
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('torch','mujoco','onnxruntime'):raise RuntimeError('Postprocess only, no Runtime/Actor/renderer')
sys.addaudithook(fence)
from same_clock_pair import encode_same_clock_pair
from raw_video_encode import decoded_rgb_digest
from raw_third_view import sha
h=R/'workspace/registry/handoff_current_status_20261115.json';before=json.loads(h.read_bytes());co=before['new_critic_cohort_v1'];ids=co['order'][:2];roots=[R/'runtime/workers'/co['branches'][c]['scope_id']/'main/raw-third-view'for c in ids];old=B/'manifests/T-COMPLEX-01-intake-20261115-v1/QA_TRAIN01_02_NOT_COMPLEX_RESULT';singles=[]
for label,root in zip(('A','B'),roots):
 p=old/('QA_TRAIN_'+label+'-original1x.mkv');s=json.loads(p.with_suffix('.mkv.json').read_bytes());assert sha(p)==s['output_sha256']and s['source_master_root']==str(root)and s['actual_encoded_output_exact_RGB_roundtrip_verified'];singles.append(s)
out=B/'manifests/T-COMPLEX-01-intake-20261115-v1/QA_TRAIN01_02_NOT_COMPLEX_RESULT_PAIR_V2';out.mkdir(exist_ok=False);start=time.monotonic();pair=encode_same_clock_pair(*roots,out/'QA_TRAIN_same-clock-pair1x-FFV1-slices4.mkv',ffmpeg_path='/usr/bin/ffmpeg',speed=1,timeout_s=240)
# HD encoder smoke is EXPLICIT SOFTWARE pixels, not a new captured frame/video.
p=out/'SOFTWARE_HD_CODEC_SMOKE_NOT_EXPERIMENT.mkv';cmd=['/usr/bin/ffmpeg','-hide_banner','-loglevel','error','-nostdin','-n','-f','rawvideo','-pixel_format','rgb24','-video_size','960x540','-framerate','10.0','-i','pipe:0','-an','-c:v','ffv1','-level','3','-pix_fmt','bgr0','-slices','4','-threads','1',str(p)];raw=bytes(960*540*3);r=subprocess.run(cmd,input=raw,capture_output=True,timeout=30);assert r.returncode==0,r.stderr;decoded,_=decoded_rgb_digest('/usr/bin/ffmpeg',p,expected_bytes=len(raw),timeout_s=30);assert decoded==hashlib.sha256(raw).hexdigest()
assert all(json.loads(h.read_bytes())['new_critic_cohort_v1']['branches'][c]==before['new_critic_cohort_v1']['branches'][c]for c in ids)
proof=dict(status='POSTPROCESS_ENGINEERING_QA_ONLY_NOT_T_COMPLEX_EXPERIMENT',old_encoder_problem='FFV1 level3 slices1 rejected at paired384x160 geometry; stderr/partial output preserved. Use supported4-slice encoding, unchanged exactRGB decode checks.',single_encodes_reused_no_raw_modified=singles,pair=pair,software_HD_fixture=dict(origin='EXPLICIT_SOFTWARE_CODEC_SMOKE_NOT_EXPERIMENT',width=960,height=540,frames=1,exact_RGB_roundtrip=True,new_capture_or_native_calls=0),wall_s=time.monotonic()-start,current_active_TRAIN_scope_not_touched=True,H_not_written=True,task_T_COMPLEX_actual_videos_still0=True,new_physical_calls=0,outputs_remote_only=True,source_code_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in D.glob('*.py')})
with(out/'QA_RECEIPT_NOT_T_COMPLEX_RESULT.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(proof))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','CUDA_VISIBLE_DEVICES="" MUJOCO_GL=disable OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(rows),capture_output=True,text=True,timeout=330)
for suf,t in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:(M/('video-postprocess-QA-v2.'+suf)).write_text(t)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);(M/'POSTPROCESS_QA_V2_NOT_COMPLEX_RESULT.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(dict(status=v['status'],wall_s=v['wall_s'],pair_frames=v['pair']['frames'],pair_exact=v['pair']['exact_RGB_codec_roundtrip_verified'],source_resolution=v['pair']['source_panel_resolution'],software_HD_fixture=v['software_HD_fixture'],task_complex_videos=0),indent=2))
