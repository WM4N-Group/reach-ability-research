"""Prove source-scoped compatibility without pretending to rerun old datasets.

This NEW experiment certificate is not the legacy whole-source feedback replay
receipt. No private replay frames/labels are opened; old original gates/data stay
unchanged. It proves exact unchanged components plus the declared PHE input-path
intervention and metadata ID change, not calibrated errors or dynamic safety.
"""
import argparse,ast,hashlib,json,sys
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def id_literal(text):
    for n in ast.parse(text).body:
        if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='SOURCE_ID' for x in n.targets):return ast.literal_eval(n.value)
    raise ValueError('Original explicit source ID required')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--release',type=Path,required=True);ap.add_argument('--arm',choices=('A','B'),required=True);a=ap.parse_args()
    r=a.release.resolve();source=r/a.arm/'source';out=r/a.arm/'source-scope-qualification.json'
    if out.exists():raise ValueError('Do not overwrite qualification evidence')
    cfg=json.loads((r/'cpu-context-pins.json').read_text());old=Path(cfg['context_root'])/'source/scripts/piper_world_model';pins=cfg['source_pins']
    sys.path.insert(0,str(source))
    if a.arm=='B':
        from mujoco_zyh.reach_phe_hook import transform_stall_source
    changed=[]
    for name,h in pins.items():
        if sha(old/name)!=h:raise ValueError('Original qualified source changed')
        now=sha(source/name)
        if now==h:continue
        before=(old/name).read_text();after=(source/name).read_text()
        if name=='mujoco_zyh/deepseek_mission_task_NAV_request_physical_protocol.py':
            if after.replace(repr(id_literal(after)),repr(id_literal(before)),1)!=before:raise ValueError('Not source-ID-only metadata delta')
            changed.append(dict(file=name,scope='new source/episode ID only',controls_or_task_changed=False))
        elif a.arm=='B' and name=='mujoco_zyh/stall_stow.py':
            if transform_stall_source(before)!=after:raise ValueError('Not exact declared protected-stow hook')
            changed.append(dict(file=name,scope='one private path-selection input hook; original native hard gate predicates unchanged',intermediate_path_is_intentionally_changed=True))
        else:raise ValueError('Unreviewed runtime/model/test delta: '+name)
    additions=sorted(str(p.relative_to(source)) for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts and str(p.relative_to(source)) not in pins)
    expected=['mujoco_zyh/reach_phe_hook.py'] if a.arm=='B' else []
    if additions!=expected:raise ValueError('Unexpected source additions '+str(additions))
    physical=['mujoco_zyh/behavior_public_feedback.py','mujoco_zyh/behavior_scene_state.py','mujoco_zyh/behavior_model_query.py','mujoco_zyh/behavior_scene_router.py','visual_latent_behavior.py','visual_latent_world_model.py']
    for name in physical:
        if sha(source/name)!=pins[name]:raise ValueError('Public feedback/model source changed')
    oldroot=Path('/mnt/yuanyue/data/go2-piper-world-model/own-WM-DeepSeek-full-mission-task-NAV-request-physical-20261104-v9')
    oldfreeze=json.loads((oldroot/'freeze.json').read_text());oldreceipt=oldroot/'behavior-feedback-admission.json'
    if sha(oldreceipt)!=oldfreeze['inputs']['behavior-feedback-admission.json']:raise ValueError('Old component admission changed')
    record=dict(schema='reach-PHE-declared-source-delta-and-unchanged-public-component-v1',passed=True,
                arm=a.arm,baseline_old_pass_freeze_sha256=sha(oldroot/'freeze.json'),source_parent_context=str(old),
                current_source_manifest={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts},
                changed=changed,added=additions,public_and_WM_components_byte_identical=physical,
                historical_feedback_component_receipt_sha256=sha(oldreceipt),
                original_whole_source_feedback_replay_revalidated=False,private_replay_data_read=False,
                new_prediction_uncertainty_or_actual_behavior_calibration_verified=False,
                source_compatibility_not_physical_or_model_efficacy_certificate=True,
                explicit_study_profile='seen-development nominal H-only control ablation, not strict/general deployment',
                native_guards_and_actual_same_compact_goal_still_required=True,
                new_native_zero_or_physical_authority=False)
    out.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(arm=a.arm,changed=changed,added=additions,new_replay_claimed=False),indent=2))


if __name__=='__main__':main()
