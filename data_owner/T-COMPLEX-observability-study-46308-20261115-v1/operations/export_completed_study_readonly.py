"""Export every fixed original boundary and encode all direct raw RGB once.
CPU only, no world/native/Actor/Renderer calls, no H mutation. Not a success film.
"""
from pathlib import Path
import os,json,hashlib,datetime,base64,shutil,subprocess
import numpy as np
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
allowed=os.sched_getaffinity(0); assert {36,37}.issubset(allowed); os.sched_setaffinity(0,{36,37})
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114'); B=R/'workspace'; M=B/'manifests/T-COMPLEX-observability-study-46308-20261115-v1'; ROOT=R/'runtime/workers/data-46308-T-COMPLEX-observability-only-20261115-v1';S=ROOT/'main'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest(); read=lambda p:json.loads(Path(p).read_bytes()); canonical=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
v=read(S/'result.json');L=read(ROOT/'accounting/ledger.json');a=read(M/'OBS/actual-main-cold-audit-v2.json');close=read(M/'OBS/CAS-close-main-v2.json')
assert v['passed'] and v['observation_qualification_complete'] and not v['task_success'] and not v['AB_comparison'] and not Path('/proc/'+str(v['PID'])).exists()
assert len(L['rows'])==2 and all(r['closed']and r['usage_known']for r in L['rows']) and a['passed'] and a['source_result_sha256']==sha(S/'result.json')==close['source_result_sha256']
records=[];last='0'*64
for line in(S/'events.jsonl').read_text().splitlines():
 r=json.loads(line);pin=r['sha256'];base={k:x for k,x in r.items()if k!='sha256'};assert r['sequence']==len(records)and r['previous_sha256']==last and hashlib.sha256(canonical(base)).hexdigest()==pin;records.append(r);last=pin
obs=[r['payload']for r in records if r['payload'].get('event')=='observability_qualification_actual_public_observation'];assert len(obs)==3 and [x['accepted_current_public_aliases']for x in obs]==[[],['cuboid_a'],[]]
D=B/'consumer-deliveries/AINAV-DATA-T-OBS-THREE-FIXED-BOUNDARIES-COMPLETE-NOT-TASK-20261115-v1';D.mkdir();files={};pins={};queries=[]
def copy(p,rel):
 p=Path(p); assert not p.is_symlink() and p.stat().st_size<2*1024**2
 out=D/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out);files[rel]=sha(out);pins[str(p)]=sha(p);assert files[rel]==pins[str(p)]
for p,rel in [(S/'result.json','main/result.json'),(ROOT/'zero/result.json','zero/result.json'),(ROOT/'accounting/ledger.json','ledger.json'),(M/'OBS/actual-main-cold-audit-v2.json','actual-main-cold-audit-v2.json'),(M/'OBS/CAS-close-main-v2.json','CAS-close-main-v2.json'),(S/'actual-config.json','main/actual-config.json'),(S/'actual-model-identity.json','main/actual-model-identity.json'),(S/'native-asset-construction.json','main/native-asset-construction.json'),(S/'resource-lease.json','main/resource-lease.json'),(S/'episode/index.json','episode/index.json'),(S/'episode/closure.json','episode/closure.json'),(S/'episode/episode.json','episode/episode.json'),(S/'review-state/metadata.json','review/metadata.json'),(S/'review-state/closure.json','review/closure.json'),(S/'raw-third-view/metadata.json','raw-third-view/metadata.json'),(S/'raw-third-view/closure.json','raw-third-view/closure.json')]:copy(p,rel)
for i,e in enumerate(obs):
 matches=[p for p in S.glob('intent-observation-*.json')if hashlib.sha256(canonical(read(p))).hexdigest()==e['observation_sha256']];assert len(matches)==1;p=matches[0];value=read(p);rgb=Path(value['rgb']['path']);Q=rgb.parent
 assert Q.resolve().is_relative_to((S/'query-observations').resolve()) and value['time_s']==value['rgb']['time_s']==e['time_s'] and sha(rgb)==e['RGB_file_sha256']
 assert [len(value['public_state'][k])for k in('q','dq','gravity','angular_velocity','linear_velocity')]==[18,18,3,3,3]
 cal=read(Q/'calibration.json');assert cal['public_packet_only'] and cal['acquisition_time_s']==e['time_s']
 prefix=f'public-boundaries/{i+1:02d}-{e["boundary"]}'
 for original,name in [(p,'actual-intent-observation.json'),(rgb,'rgb.png'),(Q/'depth_m.npy','depth_m.npy'),(Q/'calibration.json','calibration.json'),(Q/'observation.json','base-observation.json')]:copy(original,prefix+'/'+name)
 queries.append(dict(boundary=e['boundary'],actual_time_s=e['time_s'],actual_Observation_semantic_sha256=e['observation_sha256'],original_current_public_aliases=e['accepted_current_public_aliases'],original_query_sha256=sha(p),relative_directory=prefix,no_nearest_grid_substitution=True))
selected=[r for r in records if r['payload'].get('event')in ('complex_actual_cold_capture_completed','observability_qualification_actual_public_observation','observability_qualification_fixed_NAV_selected','observability_qualification_original_NAV_succeeded','observability_qualification_complete_not_task')or(r['payload'].get('event')=='ainav_native_receipt'and r['payload']['receipt']['status']=='succeeded')]
(D/'selected-original-journal-records.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2)+'\n');files['selected-original-journal-records.json']=sha(D/'selected-original-journal-records.json');pins[str(S/'events.jsonl')]=sha(S/'events.jsonl')
# Direct original RGB, all 276 frames, no interpolation/cropping/re-rendering.
rawbase=S/'raw-third-view';rc=read(rawbase/'closure.json');p=D/'OBSERVABILITY-ONLY-direct-raw-1x.mp4';count=0
cmd=['/usr/bin/ffmpeg','-nostdin','-hide_banner','-loglevel','error','-n','-f','rawvideo','-pixel_format','rgb24','-video_size','960x540','-framerate','10','-i','pipe:0','-an','-c:v','libx264','-threads','2','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(p)]
with(D/'ffmpeg.stderr').open('xb')as err:
 proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=err)
 try:
  for row in rc['chunks']:
   chunk=rawbase/row['path'];assert not chunk.is_symlink() and chunk.resolve().is_relative_to(rawbase.resolve()) and sha(chunk)==row['sha256'];pins[str(chunk)]=sha(chunk)
   with np.load(chunk,allow_pickle=False)as x:
    assert x['rgb'].dtype==np.uint8 and x['rgb'].shape[1:]==(540,960,3)and np.array_equal(x['physics_tick'],np.arange(count,count+len(x['rgb']))*20)
    assert np.allclose(x['actual_sim_time_s'],x['physics_tick']*.005,rtol=0,atol=1e-7) and hashlib.sha256(x['rgb'].tobytes()).hexdigest()==row['raw_RGB_bytes_sha256']
    for frame in x['rgb']:proc.stdin.write(frame.tobytes());count+=1
  proc.stdin.close();assert proc.wait(timeout=120)==0
 finally:
  if proc.poll()is None:proc.kill();proc.wait()
assert count==a['direct_raw_frames']==rc['archived_frames']==276 and p.stat().st_size<64*1024**2
probe=json.loads(subprocess.check_output(['/usr/bin/ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_read_frames','-of','json',str(p)],text=True,timeout=30));stream=probe['streams'][0];assert int(stream['nb_read_frames'])==count and stream['r_frame_rate']=='10/1' and (stream['width'],stream['height'])==(960,540)
video=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size,frames=count,probe=probe,source='DIRECT_CURRENT_LIVE_MUJOCO_RGB',role='OBSERVABILITY_QUALIFICATION_ONLY_NOT_TASK_SUCCESS_OR_AB',lossy_H264_from_original_RGB=True,no_interpolation_or_duplicate_or_selected_best_frames=True,all_fixed_views_and_history_included=True,native_terminal_time_s=v['actual_main_world_sim_s'],container_duration_grid_quantized=True,large_video_remote_only=True)
(D/'video-manifest.json').write_text(json.dumps(video,indent=2)+'\n');files['video-manifest.json']=sha(D/'video-manifest.json');files[p.name]=sha(p)
interpretation=dict(measurement_complete=True,initial_left_right_aliases=[[],['cuboid_a'],[]],public_association_at_one_preregistered_view_under_unchanged_original_binding=True,not_independent_private_GT_validation=True,no_PUSH_READY_or_PUSH_execution_or_T_task_success=True,not_three_meaningful_choices_or_AB_or_lookahead_advantage=True,no_original_failed_A_or_B_or_any_closed_scope_reopened=True,no_new_query_or_native_Renderer_Actor_calls=True,no_current_critic_fit_or_CAL_VAL_permission=True,whole_artifact_model_input_allowed=False,audit_v1_missing_camera_descriptor_lookup_failed_only=True,audit_v1_stderr_preserved='manifests/T-COMPLEX-observability-study-46308-20261115-v1/OBS/completed-study-cold.stderr',audit_v2_exact_frozen_scene_and_original_actual_config_camera_match=True,no_original_record_modified=True,original_control_caps_and_gates_unchanged=True)
(D/'interpretation.json').write_text(json.dumps(interpretation,indent=2)+'\n');files['interpretation.json']=sha(D/'interpretation.json')
assert all(sha(p)==pin for p,pin in pins.items())
release=dict(schema='Data-complete-three-fixed-original-observability-release-v1',at=datetime.datetime.now().astimezone().isoformat(),scope_id=v['scope_id'],program_sha256=v['program_sha256'],source_owner_commit=v['source_owner_commit'],source_result_sha256=sha(S/'result.json'),role='COMPLETE_OBSERVABILITY_MEASUREMENT_NOT_TASK_SUCCESS_OR_AB',measurement_complete=True,task_success=False,AB_comparison=False,actual_task_sim_s=v['actual_main_world_sim_s'],actual_physics_steps=v['task_physics_steps'],actual_original_queries=3,actual_fixed_NAV_succeeded_receipts=a['actual_native_terminal_receipts'],actual_reconstructions=0,original_boundaries=queries,nine_stream_checks=a['checks'],direct_HD_raw_frames=count,video=video,actual_scope_including_zero_aux_sim_s=sum(r['sim_s']for r in L['rows']),actual_scope_ledger_wall_s=sum(r['wall_s']for r in L['rows']),actual_scope_output_highwater_bytes=max(r['output_highwater_bytes']for r in L['rows']),all_usage_known=True,resource_censored=False,journal_verified_rows=len(records),journal_last_sha256=last,original_full_journal_remote_path=str(S/'events.jsonl'),original_full_journal_sha256=sha(S/'events.jsonl'),source_files_and_records_not_rewritten=True,no_H_mutation=True,files=files)
(D/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n')
small={str(p.relative_to(D)):base64.b64encode(p.read_bytes()).decode()for p in D.rglob('*')if p.is_file()and p.suffix!='.mp4'and p.stat().st_size<2*1024**2};assert sum(len(base64.b64decode(x))for x in small.values())<5*1024**2
print(json.dumps(dict(release_path=str(D/'release.json'),release_sha256=sha(D/'release.json'),summary={k:x for k,x in release.items()if k not in('files','original_boundaries','video','actual_fixed_NAV_succeeded_receipts')},small_files=small)))
