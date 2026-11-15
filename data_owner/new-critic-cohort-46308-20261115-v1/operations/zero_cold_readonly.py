"""One explicit new zero cold read. No native/model/Runtime import or replay."""
from pathlib import Path
import json,hashlib,sys,os
import numpy as np
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';C=os.environ['DATA_PREFIX_CONDITION'];W=B/'workers/new-critic-cohort-46308-20261115-v1'
sys.path.insert(0,str(W));from prepare_prefix import SCOPES
SCOPE=SCOPES[C];ROOT=R/'runtime/workers'/SCOPE;Z=ROOT/'zero';M=B/'manifests/new-critic-cohort-46308-20261115-v1'/C
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_bytes())
program=sha(M/'program-freeze.json');v=read(Z/'result.json');ledger=read(ROOT/'accounting/ledger.json');before={str(p):sha(p) for p in [Z/'result.json',ROOT/'accounting/ledger.json',Z/'episode/index.json',Z/'review-state/closure.json']}
assert v['condition_qualification_not_critic_training'] is True
assert v['passed'] is True and v['status']=='OWN_ZERO_PASS' and v['program_sha256']==program
assert len(ledger['rows'])==1 and ledger['rows'][0]['closed'] is True and ledger['rows'][0]['report_sha256']==sha(Z/'result.json') and ledger['stopped'] is False
assert v['actual_main_world_sim_s']==0 and v['task_physics_steps']==0 and v['actual_recorded_commands']==0 and v['actual_recorded_visual_frames']==1 and not v['close_errors']
assert v['actual_auxiliary_calibration']['worlds']==1 and v['actual_auxiliary_calibration']['sim_seconds']<=10.5 and v['actual_auxiliary_calibration']['main_world_unchanged'] is True
assert v['new_waypoint_choice_control_enabled'] is True and v['actual_selection_recorded'] is False and v['actual_choice_changed'] is False
bindings=read(Z/'prefix-common-choice-binding.json');assert bindings['candidate_id']=='original' and bindings['preparation']['installed'] is True and any(r['installed'] is True and r['module']=='mujoco_zyh.stall_stow' for r in bindings['common_stow_aliases'])
ix=read(Z/'episode/index.json');cl=read(Z/'episode/closure.json');assert cl['storage_complete'] is True and ix['commands']==[] and len(ix['visual'])==1
row=ix['visual'][0];p=Z/'episode'/row['path'];assert sha(p)==row['sha256']
with np.load(p,allow_pickle=False) as d:
 assert d['rgb'].shape==(1,1,128,192,3) and d['rgb'].dtype==np.uint8 and d['depth_m'].shape==(1,1,128,192,1)
 assert float(d['timestamps_s'][0,0])==0. and np.array_equal(d['action_valid'],np.zeros((1,1),dtype=bool))
 assert np.array_equal(d['actions_previous'],np.zeros((1,1,18),dtype=d['actions_previous'].dtype))
 assert hashlib.sha256(d['rgb'].tobytes()).hexdigest()==v['actual_RGB_array_sha256']
 for key,digest in v['actual_INPUT8_sha256'].items():assert hashlib.sha256(d[key].tobytes()).hexdigest()==digest
review=read(Z/'review-state/closure.json');assert review['metadata_sha256']==sha(Z/'review-state/metadata.json') and review['model_sha256']==sha(Path(review['model_path']))
assert all(sha(Path(p))==s for p,s in before.items())
camera=read(Z/'raw-third-view/closure.json') if (Z/'raw-third-view/closure.json').exists() else {'status':'VIDEO_UNAVAILABLE'}
if camera.get('complete_for_capture_grid') is True:
 sys.path.insert(0,str(W));from raw_third_view import raw_frames,ACTUAL
 frames=list(raw_frames(Z/'raw-third-view'));assert camera['origin']==ACTUAL and len(frames)==1 and frames[0][0]==0 and frames[0][1]==0.
out={'camera_status':camera.get('status'),'camera_qualified_on_actual_live_world':camera.get('complete_for_capture_grid') is True,'camera_failure_not_native_main_gate':True,'schema':'Data-new-stow-choice-own-zero-cold-readonly-v1','passed':True,'scope_id':SCOPE,'program_sha256':program,'zero_result_sha256':sha(Z/'result.json'),'zero_model_numeric_sha256':v['actual_model_numeric_sha256'],'actual_original8_RGBD_and_review':True,'new_selected_class_callback_installed':True,'task_command_steps':0,'selection_not_yet_exercised':True,'main_not_started':True,'actual_auxiliary_sim_s':v['actual_auxiliary_calibration']['sim_seconds'],'actual_zero_wall_s':v['wall_s'],'raw_sources_unchanged':True,'new_Runtime_Actor_Renderer_or_physics_from_this_reader':False,'native_geometry_or_optimizer_effect_qualification_from_zero':False}
with (M/'actual-zero-cold-validation.json').open('x') as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(out,ensure_ascii=False))
