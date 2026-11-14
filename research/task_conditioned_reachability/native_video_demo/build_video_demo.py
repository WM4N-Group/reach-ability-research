"""Freeze one native-video demo, preserving the existing physical controller."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PARENT=REPO.parent/'artifacts/go2-piper/native-pose-singlefactor-six-20261021-r2'
EXPECTED='149ac2b4c25138b035efc68fccb948c544bdab4e842426d080b75ee27821054b'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(text,old,new):
    if text.count(old)!=1:raise ValueError('Source anchor changed: '+old)
    return text.replace(old,new,1)

def build(root,execution_root):
    if root.exists():raise FileExistsError('No overwrite')
    source=PARENT/'source';manifest=json.loads((source/'manifest.json').read_text())
    if sha(source/'manifest.json')!=EXPECTED:raise ValueError('Wrong parent')
    for name,h in manifest['files'].items():
        if sha(source/name)!=h:raise ValueError('Parent file changed')
    root.mkdir(parents=True);dst=root/'source';shutil.copytree(source,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    text=(source/'probe.py').read_text()
    text=once(text,'from scene_contract import apply_scene, observe_plan','from scene_contract import apply_scene, observe_plan\nfrom native_recording import configure_view, NativeRecording')
    text=once(text,"    scene_receipt=apply_scene(cfg,a.seed,Path(__file__).with_name('protocol.json'))", "    scene_receipt=apply_scene(cfg,a.seed,Path(__file__).with_name('protocol.json'))\n    configure_view(cfg)")
    text=once(text,'    env=gym.make(TASK,cfg=cfg);b=env.unwrapped',"    env=gym.make(TASK,cfg=cfg,render_mode='rgb_array');b=env.unwrapped")
    text=once(text,'    obs,_=env.reset(seed=a.seed)','    obs,_=env.reset(seed=a.seed)\n    video=NativeRecording(env,a.output)')
    text=once(text,"    log.write(json.dumps(first)+'\\n')", "    log.write(json.dumps(first)+'\\n')\n    video.capture(first)")
    text=once(text,"                log.write(json.dumps(row)+'\\n')", "                log.write(json.dumps(row)+'\\n')\n                video.capture(row)")
    text=once(text,'        env.close()',"        if video.last_row is not None:video.capture(video.last_row,force=True)\n        video.close(report)\n        env.close()")
    text=text.replace('native_pose_singlefactor_six_NEW_development_not_generalization','user_requested_native_video_exposed_seed_demo_NOT_independent_experiment')
    text=once(text,'reach-native-pose-six-','reach-native-video-demo-')
    (dst/'probe.py').write_text(text)
    (dst/'entry_admission.py').write_text('from video_authority import require_execution_authority\n')
    for name in ['native_recording.py','video_authority.py']:shutil.copyfile(HERE/name,dst/name)
    sdk=(source/'sdk_check.py').read_text()
    sdk=once(sdk,"    assert cfg.episode_length_s==96.","    assert cfg.episode_length_s==96.\n    assert tuple(cfg.viewer.resolution)==(960,640)\n    assert tuple(cfg.viewer.eye)==(3.,-4.,2.5)")
    sdk=once(sdk,'    result.update(passed=True,actual_native_definitions_executed=True,actual_main_CFG_prefix_executed=True,','    result.update(passed=True,native_video_cfg_verified=True,actual_native_definitions_executed=True,actual_main_CFG_prefix_executed=True,')
    (dst/'sdk_check.py').write_text(sdk)
    p=json.loads((source/'protocol.json').read_text());item=p['schedule'][1]
    assert item['seed']==120601 and item['arm']=='P3'
    p.update(schema='user-requested-one-native-video-demo-v1',execution_root=str(execution_root),
        stopped_parent_root=str(Path('/mnt/yuanyue/data/go2-piper/native-pose-singlefactor-six-20261021-r2')),
        parent_manifest_sha256=EXPECTED,allocation_id='native-recording-demo-20261021-v1',
        role='explicit native-camera demo of already-exposed successful start; not an independent test',
        schedule=[dict(item,source_id='reach-native-video-demo-P3-seed120601')],
        budgets=dict(SDK_Apps=1,SDK_wall_s=180,physical_starts=1,physical_wall_s=1800),
        approved_budgets=dict(SDK_Apps=0,physical_starts=0),
        video=dict(original_live_Isaac_frames=True,reconstruction=False,fps=10,width=960,height=640),
        budget_transfer='withdraw original never-started seed120603/P3 slot, append-only one-slot release and one demo reservation; net parent cap16',
        execution_authorized=False)
    (dst/'protocol.json').write_text(json.dumps(p,indent=2)+'\n')
    for file in dst.glob('*.py'):ast.parse(file.read_text())
    files={f.name:sha(f) for f in sorted(dst.iterdir()) if f.is_file() and f.name!='manifest.json'}
    (dst/'manifest.json').write_text(json.dumps(dict(schema='native-video-source-manifest-v1',files=files),indent=2)+'\n')
    request=dict(root=str(execution_root),source_manifest_sha256=sha(dst/'manifest.json'),source_protocol_sha256=sha(dst/'protocol.json'),
                 budgets=p['budgets'],approved=False,role=p['role'],budget_transfer=p['budget_transfer'])
    (root/'request-NOT-APPROVED.json').write_text(json.dumps(request,indent=2)+'\n')
    return request

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--execution-root',type=Path,required=True);a=p.parse_args()
    print(json.dumps(build(a.output_root,a.execution_root),indent=2))
