from pathlib import Path
import json,hashlib,base64,datetime,subprocess,fcntl,os
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='E20-prearrival40-direct-live-46308-20261116-v3';M=B/'manifests'/N;S=R/'runtime/workers/data-46308-E20-prearrival40-direct-live-20261116-v3';T=S/'main';raw=(B/'registry/handoff_current_status_20261115.json').read_bytes();q=json.loads(raw)['active_E20_prearrival40_v3_scope'];assert not q['active']and q['main_dispatch_count']==q['zero_dispatch_count']==1 and not Path('/proc/248453').exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();files={}
for rel in ['main/result.json','main/ledger.json','main/direct-third-view/metadata.json','main/direct-third-view/closure.json','main/video-encoding-result.json','zero/result.json','zero/ledger.json']:
 p=S/rel;v=p.read_bytes();assert len(v)<128*1024;files[rel]=dict(remote=str(p),sha256=sha(p),base64=base64.b64encode(v).decode())
r=json.loads((T/'result.json').read_bytes());l=json.loads((T/'ledger.json').read_bytes());assert l['result_sha256']==q['result_sha256']==sha(T/'result.json');enc=json.loads((T/'video-encoding-result.json').read_bytes());video=Path(enc['video_path']);assert sha(video)==enc['video_sha256'];cl=json.loads((T/'direct-third-view/closure.json').read_bytes());assert cl['complete_for_capture_grid']and cl['captured_frames']==275
for row in cl['chunks']:assert sha(T/'direct-third-view'/row['path'])==row['sha256']
probe=json.loads(subprocess.check_output(['/usr/bin/ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(video)],text=True,timeout=60));v=probe['streams'][0];assert(v['width'],v['height'],v['avg_frame_rate'],int(v['nb_read_frames']))==(1280,720,'10/1',275)
locks=[]
for kind,ino in [('physics',3428729629),('sdk',3428729630)]:
 p=R/f'resource-locks/native-observer-{kind}-gpu0.lock';fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  st=os.fstat(fd);assert(st.st_dev,st.st_ino)==(51,ino);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN);locks.append(dict(kind=kind,device=st.st_dev,inode=st.st_ino,free=True))
 finally:os.close(fd)
markers=[]
with(T/'events.jsonl').open()as f:
 for line in f:
  rec=json.loads(line);p=rec['payload']
  if p.get('event')in ['DEV_pre_arrival_original_brake_entry','placement_original_native_clock_confirmed','ainav_chain_hard_stop','ainav_native_receipt','intent_actual_native_outcome']:markers.append(rec)
tree=[dict(path=str(p.relative_to(S)),bytes=p.stat().st_size)for p in sorted(S.rglob('*'))if p.is_file()];print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),H_sha256=hashlib.sha256(raw).hexdigest(),H_scope=q,original_files=files,video=dict(remote=str(video),sha256=sha(video),bytes=video.stat().st_size,ffprobe=probe,raw_chunks_all_SHA_verified=True,raw_frames=275,raw_master_retained=True),original_markers=markers,GPU0_locks=locks,closed_scope_tree_sizes=tree,no_Runtime_or_renderer_or_physics_imports=True,full_command_FIFO_PD_cold_not_yet_claimed=True),ensure_ascii=False))
