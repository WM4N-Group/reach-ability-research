"""Build a new CPU-only source snapshot; old source/results/ledger stay immutable."""
import argparse,ast,difflib,hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PARENT=REPO.parent/'artifacts/go2-piper/reachability-native-entry-global-goal-20261020-v1/revisions/sdk-report-r2/source'
PARENT_SHA='169e0d15b0ec0b23ff5b73f8d31745007834433a091388270e0f43e7c6f4b518'
PROPOSAL=REPO/'evidence/2026-10-20/native-pilot-stopped-pose-diagnosis-v1/pose-aware-new-protocol-proposal-NOT-APPROVED.json'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(text,old,new):
    if text.count(old)!=1:raise ValueError('Unexpected frozen-source anchor: '+old[:90])
    return text.replace(old,new,1)


def transform_probe(original):
    text=once(original,"choices=('E0','E1','E2','E3')","choices=('P0','P1','P2','P3')")
    text=once(text,'from isaaclab.app import AppLauncher','from entry_admission import require_execution_authority\nrequire_execution_authority()  # Before any Isaac import/App, even a direct invocation.\nfrom isaaclab.app import AppLauncher')
    text=once(text,'reserve_for_late_parking=False,nominal_translation_w=None):','reserve_for_late_parking=False,nominal_translation_w=None,evaluation_role="planning"):')
    text=once(text,'set_query_context(c.env,joint_ids,joint_names)','set_query_context(c.env,joint_ids,joint_names,evaluation_role=evaluation_role)')
    text=once(text,'verified=prospective_entry(c,r,ids,joint_names,reserve_for_late_parking=False)',
              'verified=prospective_entry(c,r,ids,joint_names,reserve_for_late_parking=False,evaluation_role="final_actual")')
    old="                    if verified['shift_m']!=0.:raise ValueError('Forecast support reserve insufficient at measured final pose')"
    new="""                    if verified['shift_m']!=0.:
                        # NEW protocol only: retain the same refusal before activation,
                        # but report its expected cause rather than an unhandled crash.
                        report['outcome']='entry_final_preview_refused'
                        refusal=dict(step=row['step'],time_s=row['time_s'],required_shift_m=verified['shift_m'],
                            criterion='COMMON_original_full_cloud_fixed_yz',physics_advanced=False,command_issued=False,
                            reason='Forecast support reserve insufficient at measured final pose')
                        report['entry_final_preview_refusal']=refusal
                        report.setdefault('control_events',[]).append(dict(event='entry_final_preview_refused',**refusal))
                        break"""
    text=once(text,old,new)
    text=text.replace('reach-entry-pilot-v1-','reach-pose-entry-cpu-v1-')
    text=once(text,"scope='User-approved new-initial-state native-entry common-global-goal pilot; not confirmatory acceptance'",
              "scope='Pose-conditional factorial candidate; CPU snapshot has no execution authority; not confirmatory acceptance'")
    text=once(text,"study_role='new_global_goal_development_pilot_not_historical_v317_reproduction'",
              "study_role='pose_factorial_development_NEW_protocol_not_old16_completion_or_generalization'")
    ast.parse(text)
    return text


def verify_parent():
    if sha(PARENT/'manifest.json')!=PARENT_SHA:raise ValueError('Executed parent manifest changed')
    manifest=json.loads((PARENT/'manifest.json').read_text())
    for name,digest in manifest['files'].items():
        if sha(PARENT/name)!=digest:raise ValueError('Executed parent file changed: '+name)
    return manifest


def build(output):
    if output.exists():raise FileExistsError('Never overwrite a source snapshot')
    manifest=verify_parent();output.mkdir(parents=True)
    omit={'sdk_check.py','sdk_evidence_io.py','run_supervisor.py','protocol.json','common_probe.patch','box_approach_standoff.py','probe.py'}
    for name in manifest['files']:
        if name not in omit:shutil.copyfile(PARENT/name,output/name)
    shutil.copyfile(PARENT/'manifest.json',output/'parent_manifest.original.json')
    shutil.copyfile(PARENT/'protocol.json',output/'parent_protocol.original.json')
    shutil.copyfile(PARENT/'box_approach_standoff.py',output/'finite_cloud_sampler_frozen.py')
    shutil.copyfile(PARENT/'probe.py',output/'parent_probe.original.py.txt')
    original=(PARENT/'probe.py').read_text();changed=transform_probe(original)
    (output/'probe.py').write_text(changed)
    (output/'pose_probe.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile='executed_r2/probe.py',tofile='pose_cpu/probe.py')))
    for src,dst in [('runtime_pose_entry.py','box_approach_standoff.py'),('pose_entry_selection.py','pose_entry_selection.py'),('entry_admission.py','entry_admission.py')]:
        shutil.copyfile(HERE/src,output/dst)
    proposal=json.loads(PROPOSAL.read_text());parent_protocol=json.loads((PARENT/'protocol.json').read_text())
    schedule=[dict(item,source_id=f'reach-pose-entry-cpu-v1-{item["arm"]}-seed{item["seed"]}',output_name=f'seed{item["seed"]}-{item["arm"]}') for item in proposal['schedule_order']]
    protocol=dict(schema='pose-conditioned-entry-CPU-snapshot-v1',role='post-exposure development implementation, NOT new trial or SDK release',
        execution_authorized=False,SDK_and_physical_dispatch_implemented=False,source_parent_manifest_sha256=PARENT_SHA,
        source_refs=parent_protocol['source_refs'],weight_sha256=parent_protocol['weight_sha256'],
        seeds=proposal['proposed_new_seeds'],arms=list(proposal['arms']),schedule=schedule,common_global_goal_se2=[-.25,0.,0.],
        approved_budgets=dict(SDK_Apps=0,physical_starts=0),proposed_budgets=proposal['budgets_requested'],
        original_family_root=proposal['parent_original_pilot_root'],original_parent_consumed=2,original_unspent14_NOT_reallocated=True,
        old_14_not_run_and_E1_runtime_error_untouched=True,common_final_verifier='original_full_cloud_fixed_yz_for_ALL_arms',
        planning_factor_only='endpoint/full x translation/reference; same swept-yz, original margin/support/reserve',
        reference_provenance='existing last-issued controller orientation target read before decision; generation timestamp/freshness NOT independently certified',
        uncertainty_bound_status='UNKNOWN; no posthoc epsilon calibration',common_instrumentation='all planning arms build both clouds and all4 scalars; no artificial runtime saving claim',
        ordinary_refusal_NEW_protocol_only='exact common measured_final positive shift -> episode false/refused beforePUSH; no next physics/command from refusal',
        original_stops=dict(sim_s=96,wall_s=1800,return_s=16,push_s=48),
        incomplete_release_requirements=['exact new SDK admission code and one App authority','explicit8-of14 allocation ledger/launcher preserving old ledger and parent16 cap'],
        proposal_sha256=sha(PROPOSAL))
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    files={p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()}
    (output/'manifest.json').write_text(json.dumps(dict(schema='pose-entry-CPU-source-manifest-v1',files=files),indent=2)+'\n')
    return protocol

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.output_dir),indent=2))
