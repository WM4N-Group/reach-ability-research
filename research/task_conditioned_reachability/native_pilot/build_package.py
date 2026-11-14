"""Assemble an isolated source-bound v317 experiment; never edit owner source."""
import argparse,ast,difflib,hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
OWNER=Path('/home/yuanyue/re-nav -piper-deploy/artifacts/go2-piper/sim2sim-current-20261008-a/transition-arm-entry-v317')
PARENT_SHA='4753fa761aea0054cf98d6d720afcf553bb825b71a972a55d6d12084bce0b9e1'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def once(text,old,new):
    if text.count(old)!=1:raise ValueError('Unexpected source patch anchor: '+old[:100])
    return text.replace(old,new,1)

def transform_probe(original):
    s=once(original,"p.add_argument('--seconds', type=float, default=18.)", "p.add_argument('--seconds', type=float, default=18.)\np.add_argument('--entry-geometry-arm',choices=('E0','E1','E2','E3'),required=True)")
    s=once(s,'from box_approach_standoff import required_standoff','from box_approach_standoff import required_standoff, configure_study, set_query_context, record_source_hand_guard\nconfigure_study(a.entry_geometry_arm,a.output)')
    s=once(s,"    box=c.env.scene['box']\n    preview=required_standoff", "    box=c.env.scene['box']\n    set_query_context(c.env,joint_ids,joint_names)\n    preview=required_standoff")
    s=once(s,"    if float(__import__('numpy').linalg.norm(measured-preview.pop('source_hand_position_w')))>.0002:raise ValueError('Box-approach hand FK source mismatch')", "    fk_error=float(__import__('numpy').linalg.norm(measured-preview.pop('source_hand_position_w')))\n    record_source_hand_guard(fk_error)\n    if fk_error>.0002:raise ValueError('Box-approach hand FK source mismatch')")
    s=once(s,"    report=dict(scope='", "    report=dict(scope='User-approved new-initial-state native-entry common-global-goal pilot; not confirmatory acceptance',study_arm=a.entry_geometry_arm,study_global_goal_se2=[-.25,0.,0.],study_role='new_global_goal_development_pilot_not_historical_v317_reproduction',baseline_scope='")
    s=s.replace("'v212-nav-legs-push-entry-arm-v317'", "f'reach-entry-pilot-v1-{a.entry_geometry_arm}-seed{a.seed}'")
    old="""                    term.return_nav_orientation=r.data.root_quat_w.clone()
                    term.return_nav_goal=term.return_nav_origin.clone()
                    w,x,y,z=r.data.root_quat_w.unbind(-1);yaw=torch.atan2(2*(w*z+x*y),1.-2*(y*y+z*z))
                    term.return_nav_goal[:,0]-=.25*torch.cos(yaw);term.return_nav_goal[:,1]-=.25*torch.sin(yaw)"""
    new="""                    # COMMON preregistered goal command for every variant. Never physical state.
                    term.return_nav_orientation=torch.zeros_like(r.data.root_quat_w)
                    term.return_nav_orientation[:,0]=1.
                    term.return_nav_goal=term.return_nav_origin.clone()
                    term.return_nav_goal[:,:2]=torch.tensor([-.25,0.],device=b.device)"""
    s=once(s,old,new);ast.parse(s)
    return s


def build(output):
    if output.exists():raise ValueError('Never overwrite an experiment package')
    if sha(OWNER/'plan.json')!=PARENT_SHA:raise ValueError('Parent source changed')
    parent=json.loads((OWNER/'plan.json').read_text())
    for n,h in parent['files'].items():
        if sha(OWNER/n)!=h:raise ValueError('Parent candidate file changed '+n)
    output.mkdir(parents=True)
    for n in parent['files']:
        if n not in ('run-screen.py','function-provenance.json'):
            shutil.copyfile(OWNER/n,output/n)
    shutil.copyfile(OWNER/'plan.json',output/'parent_plan.original.json')
    shutil.copyfile(OWNER/'box_approach_standoff.py',output/'box_approach_standoff_frozen_v317.py')
    shutil.copyfile(HERE/'runtime_tip_envelope.py',output/'box_approach_standoff.py')
    fixture_path=OWNER/'seed3701-native-entry/report.json'
    fixture=json.loads(fixture_path.read_text())
    state=fixture['entry_state']
    (output/'fixture_robot_state.json').write_text(json.dumps(dict(joint_names=fixture['joint_names'],q=state['q'],root_position=state['root_position'],root_quaternion=state['root_quaternion'],role='already_exposed_historical_robot_only_SDK_fixture_NOT_pilot_outcome',source_report_sha256=sha(fixture_path)),indent=2)+'\n')
    original=(OWNER/'probe.py').read_text();new=transform_probe(original)
    (output/'probe.py').write_text(new)
    (output/'common_probe.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),new.splitlines(True),fromfile='frozen_v317/probe.py',tofile='pilot/probe.py')))
    for n in ['sdk_check.py','sdk_evidence_io.py','run_supervisor.py']:
        shutil.copyfile(HERE/n,output/n)
    schedule=[]
    for i,seed in enumerate([120401,120402,120403,120404]):
        arms=['E0','E1','E2','E3'];arms=arms[i:]+arms[:i]
        for arm in arms:schedule.append(dict(seed=seed,arm=arm,source_id=f'reach-entry-pilot-v1-{arm}-seed{seed}',output_name=f'seed{seed}-{arm}'))
    protocol=dict(schema='user-approved-native-entry-global-goal-pilot-v1',approval='user 2026-10-20: 批准，继续; conditional SDK pass before physics',
        source_parent_plan_sha256=PARENT_SHA,role='new_development_global_goal_paired_pilot_NOT_confirmatory_or_old_data_rerun',
        physical_budget_family_root='/mnt/yuanyue/data/go2-piper/reachability-native-entry-global-goal-20261020-v1',
        common_global_goal_se2=[-.25,0.,0.],physical_engine='IsaacLab',seeds=[120401,120402,120403,120404],arms=['E0','E1','E2','E3'],schedule=schedule,
        budgets=dict(SDK0env_apps=1,SDK0env_wall_s=180,max_physical_starts=16,sim_s_per_start=96,wall_s_per_start=1800),
        primary='original native goal/retracted-stable predicate at new COMMON preassigned global goal; include all started failures/refusals/exceptions',
        original_stops=dict(return_s=16,push_s=48,total_sim_s=96),native_safety_unchanged=True,
        common_instrumentation='all arms build/log the same uncensored41x64 cloud; observe cost separately and include it in full wall cost',
        arm_difference='ONLY minimum_shift_m from support-only / endpoint fixed-gate / full fixed-gate / full swept-gate; common caller bookkeeping/goal/guards',
        no_retry_or_replacement_or_automatic_expansion=True,
        stop_scheduling_on=['missing_report','initialization_or_runtime_error','source_hash_changed','base_contact','bad_orientation','low_posture','arm_effort_safety'],
        ordinary_native_contact_failure='current episode ends natively and remains in denominator; may continue preregistered other cases',
        source_refs=dict(train='/mnt/yuanyue/data/go2-piper/sim2sim-current-20261008-a/push-direct-approach-v212/train',
            source_plan='/mnt/yuanyue/data/go2-piper/sim2sim-current-20261008-a/push-direct-approach-v212/plan.json',
            geometry='/mnt/yuanyue/data/go2-piper/sim2sim-current-20261008-a/runtime-push-detour-v1/mujoco',
            nav='/mnt/yuanyue/data/go2-piper/2026-09-15/eval-t8FO0a/piper-nav-baseline-bundle/policy.pt',
            push='/mnt/yuanyue/data/go2-piper/sim2sim-current-20261008-a/push-warmstart-train-v205/train/logs/rsl_rl/go2_piper_box_push_hybrid/2026-10-13_05-16-06_full_light_train_8052/model_255.pt',
            legs='/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt'),
        weight_sha256=dict(nav='72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8',push='4d1a4616928b4d06002285e870a1d6dd114e27b8cafcdd9a41dbdae1aceed419',legs='b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721'))
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2,ensure_ascii=False)+'\n')
    files={p.name:sha(p) for p in output.iterdir() if p.is_file()}
    (output/'manifest.json').write_text(json.dumps(dict(schema='native-entry-pilot-source-manifest-v1',files=files),indent=2)+'\n')
    return protocol


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',required=True,type=Path)
    args=p.parse_args();print(json.dumps(build(args.output_dir),indent=2))
