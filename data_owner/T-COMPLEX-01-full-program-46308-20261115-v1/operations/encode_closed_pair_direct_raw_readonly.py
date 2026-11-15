"""CPU-only evidence encoding from immutable live-captured RGB; NEVER render.
Not a task-success film or a replacement/extra scientific trial.
"""
from pathlib import Path
import os, json, hashlib, subprocess, datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114')
B=R/'workspace';M=B/'manifests/T-COMPLEX-01-full-program-46308-20261115-v1'
C=json.loads((B/'workers/T-COMPLEX-01-full-program-46308-20261115-v1/protocol.json').read_bytes())
D=M/'closed-pair-direct-video-evidence-v1';D.mkdir()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
rows={};pins={};frames={}
for arm in ('A','B'):
 root=R/'runtime/workers'/C['arms'][arm]['scope_id'];s=root/'main';v=read(s/'result.json');l=read(root/'accounting/ledger.json');audit=read(M/arm/'actual-main-cold-audit.json')
 assert not Path('/proc/'+str(v['PID'])).exists() and all(r['closed']for r in l['rows']) and audit['passed']
 assert audit['source_result_sha256']==sha(s/'result.json')
 raw=s/'raw-third-view';cl=read(raw/'closure.json');assert cl['origin']=='DIRECT_CURRENT_LIVE_MUJOCO_RGB'and cl['complete_for_capture_grid']and not cl['state_replay_or_rerender_used']
 for p in (s/'result.json',root/'accounting/ledger.json',raw/'closure.json',raw/'metadata.json',M/arm/'actual-main-cold-audit.json'):pins[str(p)]=sha(p)
 ff=[];mapping=[]
 for chunk in cl['chunks']:
  p=raw/chunk['path'];assert sha(p)==chunk['sha256'];pins[str(p)]=sha(p)
  with np.load(p,allow_pickle=False)as n:
   rgb=n['rgb'];assert rgb.dtype==np.uint8 and rgb.shape[1:]==(540,960,3)and hashlib.sha256(rgb.tobytes()).hexdigest()==chunk['raw_RGB_bytes_sha256']
   for i,img in enumerate(rgb):
    k=len(ff);assert int(n['physics_tick'][i])==20*k and abs(float(n['actual_sim_time_s'][i])-.1*k)<1e-7
    ff.append(img.copy());mapping.append(dict(video_frame=k,physics_tick=20*k,actual_sim_time_s=float(n['actual_sim_time_s'][i]),chunk=chunk['path'],chunk_frame=i,RGB_bytes_sha256=hashlib.sha256(img.tobytes()).hexdigest()))
 assert len(ff)==cl['archived_frames']==audit['direct_HD_frames']
 frames[arm]=ff;rows[arm]=dict(scope_id=v['scope_id'],method=v['method'],program_sha256=v['program_sha256'],result_sha256=sha(s/'result.json'),passed=v['passed'],task_success=v['task_success'],error=v.get('error'),resource_censored=v.get('resource_censored',False),actual_end_time_s=v['actual_main_world_sim_s'],last_raw_sample_time_s=mapping[-1]['actual_sim_time_s'],raw_frame_count=len(ff),native_terminal_receipts=audit.get('actual_native_terminal_receipts',[]),raw_frame_mapping=mapping)
fontpath=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
font=ImageFont.truetype(str(fontpath),17)if fontpath.exists()else ImageFont.load_default()
def panel(arm,k):
 im=Image.new('RGB',(960,620),(0,0,0));draw=ImageDraw.Draw(im);r=rows[arm]
 draw.text((8,4),f'{arm}: {r["method"]} | actual simulation clock t={k/10:.1f}s | DEV/source diagnostic',font=font,fill='white')
 if k<len(frames[arm]):
  im.paste(Image.fromarray(frames[arm][k]),(0,80))
  label='LIVE-CAPTURED RGB / 1x / NO TASK SUCCESS CLAIM'
 else:label=f'NO FURTHER OBSERVATION: original run ended at {r["actual_end_time_s"]:.3f}s'
 draw.text((8,28),label,font=font,fill=(255,220,80))
 reason='resource censor'if r['resource_censored']else('original gate failure'if not r['passed']else'original result PASS')
 draw.text((8,52),f'Outcome: {reason}; see immutable result, no missing frames invented',font=font,fill='white')
 return im
outputs={}
for kind in ('A','B','pair'):
 width=1920 if kind=='pair'else 960;count=max(map(len,frames.values()))if kind=='pair'else len(frames[kind]);p=D/(kind+'-direct-raw-1x.mp4');assert not p.exists()
 cmd=['/usr/bin/ffmpeg','-nostdin','-hide_banner','-loglevel','error','-n','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{width}x620','-framerate','10','-i','pipe:0','-an','-c:v','libx264','-threads','2','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(p)]
 with (D/(kind+'-ffmpeg.stderr')).open('xb')as err:
  proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=err)
  try:
   for k in range(count):
    im=panel(kind,k)if kind!='pair'else Image.new('RGB',(1920,620))
    if kind=='pair':im.paste(panel('A',k),(0,0));im.paste(panel('B',k),(960,0))
    proc.stdin.write(im.tobytes())
   proc.stdin.close();assert proc.wait(timeout=120)==0
  finally:
   if proc.poll()is None:proc.kill();proc.wait()
 assert p.stat().st_size<64*1024**2
 probe=json.loads(subprocess.check_output(['/usr/bin/ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_read_frames','-of','json',str(p)]))
 stream=probe['streams'][0];assert int(stream['nb_read_frames'])==count and stream['r_frame_rate']=='10/1'and(stream['width'],stream['height'])==(width,620)
 outputs[kind]=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size,frames=count,probe=probe)
# Small overview preview only; not an additional raw/video observation.
poster=Image.new('RGB',(960,620))
for j,k in enumerate((0,max(map(len,frames.values()))-1)):
 pair=Image.new('RGB',(1920,620));pair.paste(panel('A',k),(0,0));pair.paste(panel('B',k),(960,0));poster.paste(pair.resize((960,310)),(0,j*310))
poster.save(D/'preview-first-and-last.png')
assert all(sha(p)==pin for p,pin in pins.items())
v=dict(schema='Data-closed-T-pair-direct-RGB-evidence-1x-v1',at=datetime.datetime.now().astimezone().isoformat(),role='DEV_DIAGNOSTIC_NOT_FULL_SUCCESS_OR_METHOD_ADVANTAGE',arms=rows,outputs=outputs,source_pins_before_after_identical=pins,raw_region_pixels_unmodified_before_lossy_H264=True,annotation_in_added_80px_header_only=True,raw_master_not_replaced=True,original_960x540_kept_without_crop_or_zoom=True,pair_same_actual_sim_clock=True,post_end_panel_is_black_explanatory_slate_not_frozen_or_fabricated_world=True,no_interpolated_or_duplicated_world_frames=True,container_frame_period_s=.1,container_last_sample_duration_is_grid_quantized_not_precise_native_terminal_time=True,actual_terminal_time_from_result_not_video_duration=True,no_new_model_Actor_Renderer_or_physics_calls=True,task_success_or_three_decisions_or_B_advantage_inferred=False,large_video_kept_remote=True)
with(D/'manifest.json').open('x')as f:json.dump(v,f,indent=2);f.write('\n')
print(json.dumps(dict(manifest_path=str(D/'manifest.json'),manifest_sha256=sha(D/'manifest.json'),outputs=outputs,source_unchanged=True)))
