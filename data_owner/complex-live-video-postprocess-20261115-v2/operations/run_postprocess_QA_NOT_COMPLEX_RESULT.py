from pathlib import Path
import json,base64,subprocess,shlex,hashlib
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;D=B/'development/complex-live-video-postprocess-20261115-v1';rows={p.name:base64.b64encode(p.read_bytes()).decode()for p in D.glob('*.py')}
code=r'''from pathlib import Path
import sys,json,base64,os,hashlib,time
x=json.load(sys.stdin);B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');R=B.parent;D=B/'development/complex-live-video-postprocess-20261115-v1';D.mkdir(parents=True,exist_ok=False)
for name,raw in x.items():
 assert Path(name).name==name
 with(D/name).open('xb')as f:f.write(base64.b64decode(raw))
sys.path.insert(0,str(D));os.nice(15)
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('torch','mujoco','onnxruntime'):raise RuntimeError('Postprocess only, never Runtime/Actor/renderer')
sys.addaudithook(fence)
from raw_video_encode import encode_ffv1
from same_clock_pair import encode_same_clock_pair
h=R/'workspace/registry/handoff_current_status_20261115.json';before=json.loads(h.read_bytes());co=before['new_critic_cohort_v1'];ids=co['order'][:2];roots=[]
for c in ids:
 assert co['branches'][c]['status']=='CLOSED_ACTUAL_MAIN_PASS';roots.append(R/'runtime/workers'/co['branches'][c]['scope_id']/'main/raw-third-view')
out=B/'manifests/T-COMPLEX-01-intake-20261115-v1/QA_TRAIN01_02_NOT_COMPLEX_RESULT';out.mkdir(parents=True,exist_ok=False);start=time.monotonic();reports=[]
for label,root in zip(('A','B'),roots):reports.append(encode_ffv1(root,out/('QA_TRAIN_'+label+'-original1x.mkv'),ffmpeg_path='/usr/bin/ffmpeg',speed=1,timeout_s=180))
pair=encode_same_clock_pair(*roots,out/'QA_TRAIN_same-clock-pair1x.mkv',ffmpeg_path='/usr/bin/ffmpeg',speed=1,timeout_s=240)
assert all(json.loads(h.read_bytes())['new_critic_cohort_v1']['branches'][c]==before['new_critic_cohort_v1']['branches'][c]for c in ids)
proof=dict(status='POSTPROCESS_ENGINEERING_QA_ONLY_NOT_T_COMPLEX_EXPERIMENT',source='Closed genuine NEW-TRAIN01/02 direct192x128 masters only; NOT HD or complex scene',single_encodes=reports,pair=pair,wall_s=time.monotonic()-start,current_active_TRAIN_scope_not_touched=True,H_not_written=True,task_T_COMPLEX_actual_videos_still0=True,new_physical_calls=0,outputs_remote_only=True,source_code_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in D.glob('*.py')})
with(out/'QA_RECEIPT_NOT_T_COMPLEX_RESULT.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(proof))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','CUDA_VISIBLE_DEVICES="" MUJOCO_GL=disable OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(rows),capture_output=True,text=True,timeout=690)
for suf,t in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:(M/('video-postprocess-QA.'+suf)).write_text(t)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);(M/'POSTPROCESS_QA_NOT_COMPLEX_RESULT.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(dict(status=v['status'],wall_s=v['wall_s'],singles=[dict(frames=s['frames'],RGB_exact=s['actual_encoded_output_exact_RGB_roundtrip_verified'])for s in v['single_encodes']],pair_frames=v['pair']['frames'],pair_exact=v['pair']['exact_RGB_codec_roundtrip_verified'],task_complex_videos=0),indent=2))
