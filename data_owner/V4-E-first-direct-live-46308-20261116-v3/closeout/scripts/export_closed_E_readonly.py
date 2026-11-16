from pathlib import Path
import json,hashlib,datetime,subprocess,base64,fcntl,os,collections
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='V4-E-first-direct-live-46308-20261116-v3';S=R/'runtime/workers/data-46308-V4-E-first-direct-live-20261116-v3';M=S/'main';H=B/'registry/handoff_current_status_20261115.json';raw=H.read_bytes();q=json.loads(raw)['active_V4_E_first_main_v3_scope'];assert not q['active']and q['main_dispatch_count']==q['zero_dispatch_count']==1 and not Path('/proc/192156').exists()
files={}
for rel in ['main/result.json','main/ledger.json','main/video-encoding-result.json','main/direct-third-view/metadata.json','main/direct-third-view/closure.json','zero/result.json','zero/ledger.json']:
 p=S/rel;v=p.read_bytes();assert len(v)<128*1024;files[rel]=dict(remote=str(p),sha256=hashlib.sha256(v).hexdigest(),bytes=len(v),base64=base64.b64encode(v).decode())
video=M/'E-direct-live-1x.mp4';vhash=hashlib.sha256(video.read_bytes()).hexdigest();enc=json.loads((M/'video-encoding-result.json').read_bytes());assert vhash==enc['video_sha256'];probe=json.loads(subprocess.check_output(['/usr/bin/ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(video)],text=True,timeout=60));st=probe['streams'][0];assert st['width']==1280 and st['height']==720 and st['avg_frame_rate']=='10/1' and int(st['nb_read_frames'])==486
cl=json.loads((M/'direct-third-view/closure.json').read_bytes());chunks=cl['chunks'];frame_count=0
for c in chunks:
 p=M/'direct-third-view'/c['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==c['sha256'];frame_count+=c['frames']
assert frame_count==486 and cl['complete_for_capture_grid']
counts=collections.Counter();selected=[];lasts={}
with(M/'events.jsonl').open()as f:
 for line in f:
  x=json.loads(line);p=x.get('payload',{});e=p.get('event','');counts[e]+=1
  if e in ['ainav_native_admitted','ainav_native_receipt','intent_actual_native_outcome','V4_E_fixed_rule_selected']or any(t in e.lower()for t in ['stow','placement_handoff','legacy','hard_stop','failed']):
   if len(line)<20000:selected.append(x)
  if e in ['native_PUSH_settled_actual_clock_sample','placement_actual_20ms_measurement']:lasts[e]=x
locks=[]
for gpu,inos in [(0,[3428729629,3428729630]),(1,[3428459217,3428459218])]:
 for kind,ino in zip(['physics','sdk'],inos):
  p=R/f'resource-locks/native-observer-{kind}-gpu{gpu}.lock';fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
  try:
   stat=os.fstat(fd);assert(stat.st_dev,stat.st_ino)==(51,ino)==(p.stat().st_dev,p.stat().st_ino)
   try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);free=True;fcntl.flock(fd,fcntl.LOCK_UN)
   except BlockingIOError:free=False
   locks.append(dict(path=str(p),device=stat.st_dev,inode=stat.st_ino,unheld_at_check=free))
  finally:os.close(fd)
owned=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0]);assert owned<40*1024**3
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),H_sha256=hashlib.sha256(raw).hexdigest(),H_scope=q,original_files=files,video=dict(remote=str(video),bytes=video.stat().st_size,sha256=vhash,ffprobe=probe,raw_chunks_all_SHA_verified=True,raw_frames=frame_count,raw_master_retained=True),event_counts=counts,selected_original_events=selected,last_original_samples=lasts,locks=locks,owned_bytes=owned,owned_limit_bytes=40*1024**3,provider_quota_unknown=True,no_native_or_renderer_or_physics_run=True),ensure_ascii=False))
