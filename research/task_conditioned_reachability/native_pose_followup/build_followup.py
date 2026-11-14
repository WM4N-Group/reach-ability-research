"""Create a NEW, unapproved six-case real-skill source; never launch anything."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PARENT=REPO.parent/'artifacts/go2-piper/pose-entry-gated-release-20261020-v1'
PARENT_SHA='55190212ff9b6cafcd9536a0c6397fc1132b1d9505cde2a6c838b5d9883fd0a1'
INFLUENCE=HERE.parent/'pose_conditioned_entry'
SCENES=[dict(scene_id='new-zero-offset-control',seed=120601,box_default_world_x_offset_m=0.),
        dict(scene_id='new-14mm-world-x-offset',seed=120602,box_default_world_x_offset_m=-.014),
        dict(scene_id='new-28mm-world-x-offset',seed=120603,box_default_world_x_offset_m=-.028)]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def once(text,old,new):
    if text.count(old)!=1:raise ValueError('Source anchor drift: '+old[:100])
    return text.replace(old,new,1)


def parent_snapshot():
    source=PARENT/'source'
    if sha(source/'manifest.json')!=PARENT_SHA:raise ValueError('Wrong closed parent source')
    for name,digest in read(source/'manifest.json')['files'].items():
        if Path(name).name!=name or sha(source/name)!=digest:raise ValueError('Parent source changed: '+name)
    if read(PARENT/'physical_ledger.json')['status']!='COMPLETED_REGISTERED_EIGHT':
        raise ValueError('Prior eight are not closed; do not duplicate or compete')
    return source


def transform_probe(text):
    text=once(text,"choices=('P0','P1','P2','P3')","choices=('P2','P3')")
    text=once(text,'from prospective_support import prospective_support',
                   'from prospective_support import prospective_support\nfrom scene_contract import apply_scene, observe_plan')
    text=once(text,'    configure(cfg,a,training=False)',
                   "    configure(cfg,a,training=False)\n    scene_receipt=apply_scene(cfg,a.seed,Path(__file__).with_name('protocol.json'))")
    text=once(text,"    plan['box_approach_preview']=preview\n    return plan",
                   "    plan['box_approach_preview']=preview\n    observe_plan(plan,preview,evaluation_role)\n    return plan")
    text=once(text,"                seed=a.seed,source=str(a.source),nav_sha256=NAV_SHA,",
                   "                seed=a.seed,source=str(a.source),nav_sha256=NAV_SHA,study_scene_receipt=scene_receipt,")
    text=once(text,"    verify_physics(b,a.output)",
                   "    verify_physics(b,a.output)\n    (a.output/'actual-initial-state.json').write_text(json.dumps(dict(\n        seed=a.seed,scene_receipt=scene_receipt,\n        robot_position=b.scene['robot'].data.root_pos_w[0].tolist(),\n        robot_quaternion=b.scene['robot'].data.root_quat_w[0].tolist(),\n        box_position=b.scene['box'].data.root_pos_w[0].tolist(),\n        box_quaternion=b.scene['box'].data.root_quat_w[0].tolist(),\n        push_target=b.box_push_target[0].tolist(),\n        scope='actual state immediately after initial native reset; no later teleport'),indent=2)+'\\n')")
    text=once(text,'reach-pose-entry-cpu-v1-', 'reach-native-pose-six-')
    text=text.replace('pose_factorial_development_NEW_protocol_not_old16_completion_or_generalization',
                      'native_pose_singlefactor_six_NEW_development_not_generalization')
    ast.parse(text)
    return text


def authority_source(text):
    replacements=[
        ("budgets.get('physical_starts')!=8", "budgets.get('physical_starts')!=6"),
        ("budgets.get('reallocated_from_old14')!=8", "budgets.get('reallocated_from_remaining6')!=6"),
        ('No explicit8-of14 reallocation','No explicit6-of-remaining6 reallocation'),
        ('len(checks)!=8','len(checks)!=4'),
        ("sum(r['max_starts'] for r in reservations)+8>16", "sum(r['max_starts'] for r in reservations)+6>16"),
        ('explicit8-of14-reservation-v1','explicit-six-remaining-reservation-v1'),
        ('max_starts=8','max_starts=6'),
        ("r['max_starts']!=8", "r['max_starts']!=6"),
        ('No matching8-start reservation','No matching6-start reservation'),
        ("len(list(claims.glob('*.json')))>=8", "len(list(claims.glob('*.json')))>=6"),
        ('Eight claims already consumed','Six claims already consumed')]
    for old,new in replacements:text=once(text,old,new)
    anchor='    return family,old'
    extra="""    prior=Path(p['prior_phase_root'])
    if (sha(prior/'physical_ledger.json')!=p['prior_closed_ledger_sha256']
            or sha(prior/'source/manifest.json')!=p['prior_source_manifest_sha256']):
        raise PermissionError('Prior closed-eight identity changed; no reallocation')
    closed=load(prior/'physical_ledger.json')
    if closed.get('status')!='COMPLETED_REGISTERED_EIGHT' or closed.get('starts')!=8 or closed.get('active') is not None:
        raise PermissionError('Prior eight still active or incomplete')
    return family,old"""
    text=once(text,anchor,extra);ast.parse(text);return text


def evaluator_source(text):
    text=once(text,"    value['native_outcome']=r.get('outcome')", """    value['native_outcome']=r.get('outcome')
    receipt=r.get('study_scene_receipt',{})
    if (receipt.get('scene_id')!=item['scene_id'] or receipt.get('seed')!=item['seed']
            or receipt.get('box_default_world_x_offset_m')!=item['box_default_world_x_offset_m']
            or receipt.get('applied_before_environment_construction') is not True
            or receipt.get('native_reset_unchanged') is not True):
        return dict(value,protocol_valid=False,unknown_reason='missing_or_wrong_registered_scene')""")
    text=once(text,"[('P0','P1'),('P2','P3'),('P0','P2'),('P1','P3')]","[('P2','P3')]")
    return text.replace('pose-factorial-eight-cell-evaluation-v1','native-pose-six-cell-evaluation-v1')


def build(root, execution_root):
    root=Path(root);execution_root=Path(execution_root)
    if root.exists():raise FileExistsError('Never overwrite source, approval or trial evidence')
    if not execution_root.is_absolute():raise ValueError('Execution root must be absolute')
    source=parent_snapshot();root.mkdir(parents=True);target=root/'source';shutil.copytree(source,target)
    # Original support/geometry/controller bytes remain except prospective_entry
    # passive observation, main pre-construction scene config and case metadata.
    (target/'probe.py').write_text(transform_probe((source/'probe.py').read_text()))
    (target/'release_authority.py').write_text(authority_source((source/'release_authority.py').read_text()))
    text=(source/'run_supervisor.py').read_text()
    for old,new in [('max_starts=8','max_starts=6'),('new-pose-factorial-eight-start-ledger-v1','native-pose-six-start-ledger-v1')]:
        text=once(text,old,new)
    text=text.replace('COMPLETED_REGISTERED_EIGHT','COMPLETED_REGISTERED_SIX')
    text=once(text,"        count=0;last=None;travel=0.;previous=None",
        "        if not (out/'actual-initial-state.json').exists():severe=True\n        count=0;last=None;travel=0.;previous=None")
    text=once(text,"        return dict(outcome=r.get('outcome'),severe=severe,terminal_missing=False,terminal=terminal,error=r.get('error'),",
        "        return dict(initial_state_sha256=sha(out/'actual-initial-state.json') if (out/'actual-initial-state.json').exists() else None,\n            geometry_sha256=sha(out/'entry_geometry.jsonl') if (out/'entry_geometry.jsonl').exists() else None,\n            outcome=r.get('outcome'),severe=severe,terminal_missing=False,terminal=terminal,error=r.get('error'),")
    (target/'run_supervisor.py').write_text(text)
    (target/'evaluate_pose_pilot.py').write_text(evaluator_source((source/'evaluate_pose_pilot.py').read_text()))
    text=once((source/'sdk_check.py').read_text(),"for arm in ['P0','P1','P2','P3']:","for arm in ['P2','P3']:")
    text=once(text,'    assert cfg.episode_length_s==96.',
        "    assert cfg.episode_length_s==96.\n    assert getattr(cfg,'_reach_scene_applied',False)\n    assert ns['scene_receipt']['native_reset_unchanged'] is True")
    (target/'sdk_check.py').write_text(text)
    shutil.copyfile(HERE/'scene_contract.py',target/'scene_contract.py')
    shutil.copyfile(INFLUENCE/'native_influence.py',target/'native_influence.py')
    protocol=read(source/'protocol.json')
    schedule=[]
    for i,scene in enumerate(SCENES):
        for arm in (('P2','P3') if i%2==0 else ('P3','P2')):
            schedule.append(dict(scene,arm=arm,source_id=f"reach-native-pose-six-{arm}-seed{scene['seed']}",output_name=f"seed{scene['seed']}-{arm}"))
    protocol.update(schema='actual-skill-native-pose-six-release-v1',role='mechanism-targeted development; NOT approved or physically validated',
        execution_root=str(execution_root),allocation_id='native-pose-singlefactor-six-20261021-v1',
        seeds=[s['seed'] for s in SCENES],arms=['P2','P3'],schedule=schedule,scene_specs=SCENES,
        execution_authorized=False,approved_budgets=dict(SDK_Apps=0,physical_starts=0),
        prior_phase_root='/mnt/yuanyue/data/go2-piper/pose-entry-gated-release-20261020-v1',
        prior_closed_ledger_sha256=sha(PARENT/'physical_ledger.json'),prior_source_manifest_sha256=PARENT_SHA,
        original_parent_consumed=10,original_unspent14_NOT_reallocated=False,
        original_remaining6_NOT_reallocated=True,
        implemented_launch_contract=dict(explicit_new_SDK_approval_required=1,SDK_wall_s=180,
            explicit_new_physical_reallocation_required=6,parent_total_max=16,parent_already_used=10,
            old_ledger_never_edited=True,reservations_count_toward_parent_cap=True,
            no_retry_or_replacement_or_auto_expansion=True,claim_ticket_consumed_before_App=True),
        planned_budgets=dict(additional_SDK_Apps=1,SDK_wall_s=180,physical_starts=6,reallocated_from_remaining6=6,additional_total_physical_starts=0),
        scene_scope='world-x default shift before construction; native jitter/target/reset unchanged; not a frozen-query local-x move',
        actual_scene_and_mechanism_validated=False,source_parent_manifest_sha256=PARENT_SHA,
        mechanism_strata_are_exclusion_rules=False,all_registered_failure_refusal_and_masked_cases_retained=True,
        stopping_rule='technical/severe stops future dispatch; ordinary failure retained; no retries, replacements or automatic expansion',
        no_action_contrast_rule='report null, do not automatically expand pose-retreat line',
        SDK_completed_roles_required=4)
    # Remove descriptive parent eight-case budget/proposal fields, not history files.
    for key in ['proposed_budgets','incomplete_release_requirements','proposal_sha256']:protocol.pop(key,None)
    write(target/'protocol.json',protocol)
    # No source file is executed by this builder.
    for p in target.glob('*.py'):ast.parse(p.read_text())
    hashes={p.name:sha(p) for p in sorted(target.iterdir()) if p.is_file() and p.name!='manifest.json'}
    write(target/'manifest.json',dict(schema='native-pose-six-source-manifest-v1',files=hashes))
    request=dict(schema='native-pose-six-execution-request-v1',approved=False,release_root=str(execution_root),
        source_manifest_sha256=sha(target/'manifest.json'),source_protocol_sha256=sha(target/'protocol.json'),
        allocation_id=protocol['allocation_id'],budgets=protocol['planned_budgets'],
        original_family_root=protocol['original_family_root'],prior_phase_root=protocol['prior_phase_root'],
        parent_consumed=10,parent_cap=16,scene_specs=SCENES,
        no_approval_file_created=True,no_claim_or_App_started=True,
        scope='1 source-bound SDK0env gate, then at most6 paired real-skill development starts; no training or test/generalization claim')
    write(root/'execution-request-NOT-APPROVED.json',request)
    return request


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--execution-root',type=Path,required=True)
    a=p.parse_args();print(json.dumps(build(a.output_root,a.execution_root),ensure_ascii=False,indent=2))
