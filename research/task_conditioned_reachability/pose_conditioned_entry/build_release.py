"""Immutable new source with gated launchers; building is NOT run authorization."""
import argparse,hashlib,json,shutil
from pathlib import Path
from build_pose_package import build as build_cpu,REPO
HERE=Path(__file__).resolve().parent
OLD_LEDGER_SHA='831cc68c5302d576ea4942c7e1519bcbc9a8dabc0cedd072a5ab771622842997'


def build(root,execution_root):
    root=Path(root);execution_root=Path(execution_root)
    if root.exists():raise FileExistsError('Never overwrite a release, failed output, approval or claims')
    if not execution_root.is_absolute():raise ValueError('Execution root must be absolute')
    root.mkdir(parents=True);source=root/'source';p=build_cpu(source)
    (source/'CPU-protocol.original.json').write_text((source/'protocol.json').read_text())
    (source/'CPU-manifest.original.json').write_text((source/'manifest.json').read_text())
    # Change only descriptive scope; actual authority remains external and exact-source.
    probe=source/'probe.py';text=probe.read_text().replace('Pose-conditional factorial candidate; CPU snapshot has no execution authority; not confirmatory acceptance','Pose-conditional factorial candidate; source-bound SDK/physical admission required; not confirmatory acceptance')
    probe.write_text(text)
    for src,dst in [('release_admission.py','entry_admission.py'),('release_authority.py','release_authority.py'),
                    ('release_supervisor.py','run_supervisor.py'),('release_sdk_check.py','sdk_check.py'),('evaluate_pose_pilot.py','evaluate_pose_pilot.py')]:
        shutil.copyfile(HERE/src,source/dst)
    shutil.copyfile(HERE.parent/'native_pilot/sdk_evidence_io.py',source/'sdk_evidence_io.py')
    p.update(schema='pose-conditioned-entry-gated-release-v1',role='post-exposure development isolated release NOT approved or executed',
        execution_root=str(execution_root),allocation_id='pose-entry-global-goal-20261020-p1',old_physical_ledger_sha256=OLD_LEDGER_SHA,
        SDK_and_physical_dispatch_implemented=True,execution_authorized=False,approved_budgets=dict(SDK_Apps=0,physical_starts=0),
        implemented_launch_contract=dict(explicit_new_SDK_approval_required=1,SDK_wall_s=180,explicit_new_physical_reallocation_required=8,
            parent_total_max=16,parent_already_used=2,old_ledger_never_edited=True,reservations_count_toward_parent_cap=True,
            no_retry_or_replacement_or_auto_expansion=True,claim_ticket_consumed_before_App=True),incomplete_release_requirements=[],
        reference_runtime_coverage='SDK only uses explicit adapter; actual same-query action manager/read timing and nonzero request consumption must be checked from new physical logs')
    (source/'protocol.json').write_text(json.dumps(p,indent=2)+'\n')
    hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(source.iterdir()) if f.is_file() and f.name!='manifest.json'}
    (source/'manifest.json').write_text(json.dumps(dict(schema='pose-entry-executable-source-manifest-v1',files=hashes),indent=2)+'\n')
    manifest_sha=hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest()
    request=dict(schema='source-bound-pose-entry-execution-request-v1',approved=False,release_root=str(execution_root),
        source_manifest_sha256=manifest_sha,source_protocol_sha256=hashlib.sha256((source/'protocol.json').read_bytes()).hexdigest(),
        allocation_id=p['allocation_id'],budgets=dict(additional_SDK_Apps=1,SDK_wall_s=180,physical_starts=8,reallocated_from_old14=8,additional_total_physical_starts=0),
        original_family_root=p['original_family_root'],old_physical_ledger_sha256=OLD_LEDGER_SHA,
        no_approval_file_created=True,no_App_or_start_claimed=True,old_E0_success_E1_runtime_error_and14_unknown_preserved=True,
        scope='one source-exact SDK App then conditional8 new protocol starts; no complete obstacle-navigation or confirmation claim')
    (root/'execution-request-NOT-APPROVED.json').write_text(json.dumps(request,indent=2)+'\n')
    return request

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',required=True,type=Path);p.add_argument('--execution-root',required=True,type=Path);a=p.parse_args();print(json.dumps(build(a.output_root,a.execution_root),indent=2))
