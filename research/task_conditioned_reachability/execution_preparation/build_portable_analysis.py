"""Build source-only, sealed, relocatable OFFLINE analysis bundle.

No source tree/weights/NPZ/old outcome archives or runtime are transported.
All included external code/JSON retains its original hash and owner provenance.
Outputs can be copied by an owner as analysis code, not execution qualification.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from .observed_handover_analysis import DATA_ROOT,PINS
from .native_climb_continuation import DOCS,MANIFEST_SHA,CONTRACT_SHA
from .recorded_v9_diagnostics import RELEASE_SHA
from .consume_authorized_A import RELEASE as A_RELEASE,RELEASE_SHA as A_RELEASE_SHA

CODE=Path(__file__).resolve().parent
MODULES=('analysis_paths.py','observed_handover_analysis.py','exit_repair_evidence.py',
         'native_climb_continuation.py','discrete_selection.py','native_domain_v0.py',
         'recorded_v9_diagnostics.py','run_observed_handover.py','run_exit_repair_evidence.py')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def copy_exact(source,target,digest=None):
    if source.is_symlink():raise ValueError('No symlink/source-owner substitution in package')
    raw=source.read_bytes()
    if digest is not None and hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Original source identity changed: '+str(source))
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
    return dict(source_path=str(source),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))


def build(output):
    output=Path(output).absolute();output.mkdir(parents=True,exist_ok=False)
    files={};mappings={}
    for name in MODULES:
        destination=output/'code/research/task_conditioned_reachability/execution_preparation'/name
        files[str(destination.relative_to(output))]=copy_exact(CODE/name,destination)
    for name,digest in PINS.items():
        dst=output/'data-passive'/name
        files[str(dst.relative_to(output))]=copy_exact(DATA_ROOT/name,dst,digest)
    mappings[str(DATA_ROOT)]='data-passive'
    docpins={'skill_executor_manifest_v0.json':MANIFEST_SHA,'skill_interface_contract_v0_1_1.json':CONTRACT_SHA,
             'common_v9_effect_source_release_v1.json':RELEASE_SHA,'common_v9_A_three_candidate_predictions_v4.json':A_RELEASE_SHA}
    for name,digest in docpins.items():
        dst=output/'source-docs'/name;files[str(dst.relative_to(output))]=copy_exact(DOCS/name,dst,digest)
    mappings[str(DOCS)]='source-docs'
    manifest=json.loads((output/'source-docs/skill_executor_manifest_v0.json').read_text())
    for name in ('mujoco_zyh/skill_execution_judge.py','mujoco_zyh/judged_scene_options.py',
                 'mujoco_zyh/native_climb_support_seam.py','mujoco_zyh/integrated_course.py'):
        ref=manifest['frozen_source_excerpts'][name];src=Path(ref['path']);prefix=src.parents[1]
        dst=output/'frozen-excerpts'/name
        files[str(dst.relative_to(output))]=copy_exact(src,dst,ref['sha256'])
        if str(prefix) in mappings and mappings[str(prefix)]!='frozen-excerpts':raise ValueError('Ambiguous source roots')
        mappings[str(prefix)]='frozen-excerpts'
    release=json.loads((output/'source-docs/common_v9_A_three_candidate_predictions_v4.json').read_text())
    prefix=Path(release['source_qualification']['source_snapshot_root'])
    n='mujoco_zyh/behavior_authority.py';dst=output/'option-source'/n
    files[str(dst.relative_to(output))]=copy_exact(prefix/n,dst,manifest['source_manifest'][n])
    mappings[str(prefix)]='option-source'
    launcher=CODE/'portable_analysis_entry.py';dst=output/'analyze.py'
    files['analyze.py']=copy_exact(launcher,dst)
    info=dict(schema='reach-sealed-offline-analysis-bundle-v1',at=datetime.now().astimezone().isoformat(),
              purpose='OFFLINE_DEV_EVALUATION_ONLY_NOT_DISPATCH_OR_DATA_ADMISSION',files=files,
              source_root_mappings=mappings,third_party_installs_required=False,
              original_expected_hashes_not_rewritten=True,
              included_historical_actual_archives=False,published_manifest_evidence_summary_metadata_preserved=True,
              included_checkpoint_or_sensor_arrays=False,
              includes_actual_after_Finish_data=False,
              task_execution_or_GPU_permission=False,
              data_source_roles_unchanged=True)
    with (output/'bundle.json').open('x') as f:json.dump(info,f,indent=2);f.write('\n')
    receipt=dict(root=str(output),bundle_manifest_sha256=sha(output/'bundle.json'),
                 files=len(files),source_bytes=sum(r['bytes'] for r in files.values()),
                 bootstrap_sha256=sha(dst),physical_dispatch=False)
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(build(a.output),indent=2))
