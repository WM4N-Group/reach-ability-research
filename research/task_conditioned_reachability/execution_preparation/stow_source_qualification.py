"""Pure post-close declared-source qualification for the FIXED v2 profile.

Not a launcher, execution permit, proof of live import IDs or safety certificate.
New program identity must be derived from exact freeze/fork/current hashes, not
from 'v2' in a name or a reusable True flag. No recorded outcome enters planning.
"""
import hashlib
import json
from pathlib import PurePosixPath

BASE_RELEASE_SHA='3098297041dbfa50dd1928ee81ce28c68d3458ed544cc494dea7374177b7c49e'
BASE_SOURCE_MANIFEST_SHA='314b6650918cbf88c6bd7166ad3f2d26f9c3b30f92094db98d6f8832f8d1fd8c'
BASE_PROGRAM_SHA='d149701b7d843e8dd7ea657cebd0ea7815b4548d7f1c0d09e3d950bf368c2dd6'
BASE_RESULT_SHA='44fda7ca5e066a826e03a7c189f0409159d4bfee12ac06b8d3dcc2027efa7a60'
V2_BUNDLE_SHA='3016ec488de48bad06a8a8a7d4719b0079a8315a9f789fd50e8ae21dca2d64ba'
REQUESTS_SHA='9d8134082ae0ca634df7a32fff4b5d544dcc00b20fc9c1108abbda37029e8d47'
ALIASES=('mujoco_zyh/stall_stow.py','ainav/native/current_stall_stow.py')


def need(ok,msg):
    if not ok:raise ValueError(msg)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def expected_consumer_adapter(original,delta_pins):
    """Independently reproduce only the declared two-alias source-verifier delta."""
    clause='file_sha(p) == digest'
    need(original.count(clause)==1 and original.count('    return root\n')==1,'Exact baseline source verifier')
    pins={rel:delta_pins[rel] for rel in ALIASES}
    header='DATA_SOURCE_DELTA_PINS = '+repr(pins)+'\n'
    inverse="""    from reach_stow_choice.native_stow_path_binding import restore_stall_source
    for name in DATA_SOURCE_DELTA_PINS:
        need(hashlib.sha256(restore_stall_source((root/name).read_text()).encode()).hexdigest()
             == manifest['files'][name], 'Declared delta does not invert to original source: '+name)
"""
    adapted=header+original.replace(clause,'file_sha(p) == DATA_SOURCE_DELTA_PINS.get(name, digest)',1)
    adapted=adapted.replace('    return root\n',inverse+'    return root\n',1)
    restored=adapted.removeprefix(header).replace(inverse,'',1).replace('file_sha(p) == DATA_SOURCE_DELTA_PINS.get(name, digest)',clause,1)
    need(restored==original,'Source-verifier inverse changed unrelated consumer code')
    return adapted.encode()


def qualify_source_pair(*,baseline_result_bytes,candidate_result_bytes,baseline_freeze_bytes,
                        candidate_freeze_bytes,fork_manifest_bytes,baseline_release_bytes,
                        baseline_consumer_bytes,v2_bundle_manifest_bytes):
    need(sha(baseline_result_bytes)==BASE_RESULT_SHA,'Exact closed P2 baseline result')
    need(sha(baseline_freeze_bytes)==BASE_PROGRAM_SHA,'Exact P2 program freeze')
    need(sha(baseline_release_bytes)==BASE_RELEASE_SHA,'Exact complete-v6 release')
    need(sha(v2_bundle_manifest_bytes)==V2_BUNDLE_SHA,'Only independently reviewed v2 bundle; no arbitrary descendant')
    baseline,candidate,base_freeze,freeze,fork,release,bundle=map(json.loads,(
        baseline_result_bytes,candidate_result_bytes,baseline_freeze_bytes,candidate_freeze_bytes,
        fork_manifest_bytes,baseline_release_bytes,v2_bundle_manifest_bytes))
    program=sha(candidate_freeze_bytes);fork_sha=sha(fork_manifest_bytes)
    need(candidate.get('phase')=='main' and candidate.get('program_sha256')==program,'Candidate result/freeze identity')
    need(candidate.get('scope_id')==freeze.get('scope_id') and candidate['scope_id']!=baseline['scope_id'], 'Distinct same-bound candidate scope')
    need(candidate.get('source_fork_manifest_sha256')==fork_sha and freeze.get('current_source_fork_manifest_sha256')==fork_sha,
         'Current source-fork manifest, not baseline lineage reused as current pin')
    need(candidate.get('baseline_release_sha256')==BASE_RELEASE_SHA and candidate.get('reference_source_manifest_sha256')==BASE_SOURCE_MANIFEST_SHA,
         'Original baseline lineage identity')
    need(candidate.get('new_waypoint_choice_control_enabled') is True,'Explicit frozen control arm, not name inference')
    need(candidate.get('actual_model_numeric_sha256')==baseline.get('actual_model_numeric_sha256') and baseline.get('actual_model_numeric_sha256') is not None,
         'Recorded actual numeric model identity')
    need(fork.get('Reach_bundle_manifest_sha256')==V2_BUNDLE_SHA and fork.get('baseline_release_sha256')==BASE_RELEASE_SHA and
         fork.get('baseline_manifest_lineage_sha256')==BASE_SOURCE_MANIFEST_SHA,'Exact v2 current fork lineage')
    need(set(fork.get('changed_original_source_files',[]))==set(ALIASES) and
         len(fork['changed_original_source_files'])==2,'Only declared two original alias changes')
    expected=dict(release['complete_reference_source_files_sha256'])
    need(len(expected)==283,'Complete selected source inventory')
    delta={rel:bundle['files_sha256']['source-delta/'+rel] for rel in ALIASES}
    expected.update(delta)
    need(fork.get('source_delta_pins')==delta and fork.get('current_source_files_sha256')==expected,'Exact current 283-source inventory')
    need(fork.get('unchanged_source_files')==281,'Other 281 original sources remain identical')
    for name,wanted in (('same_program_for_zero_and_main',True),('one_original_Host_and_Runtime_only',True),
                        ('new_Runtime_step_or_research_WM',False),('original_guards_QP_FIFO_goal_and_four_second_verification_retained',True)):
        need(freeze.get(name) is wanted,'Declared source/lifecycle boundary: '+name)
    files=freeze['files']
    need(all(type(k) is str and PurePosixPath(k).is_absolute() and '..' not in PurePosixPath(k).parts for k in files),'Unambiguous absolute frozen paths')
    suffix='/source/ainav/__init__.py'
    roots=[k[:-len('source/ainav/__init__.py')] for k in files if k.endswith(suffix)]
    need(len(roots)==1,'One complete source root, not mixed source imports')
    worker=roots[0];source=worker+'source/'
    current={k[len(source):]:v for k,v in files.items() if k.startswith(source)}
    need(current=={**expected,'ainav-source.json':BASE_SOURCE_MANIFEST_SHA}, 'Freeze must pin complete current source plus explicit lineage manifest')
    need(files.get(worker+'fork-manifest.json')==fork_sha,'Frozen current fork manifest file identity')
    for rel,digest in bundle['files_sha256'].items():
        if rel.startswith('reach_stow_choice/'):
            need(files.get(worker+rel)==digest,'Exact current v2 runtime pin: '+rel)
    need(files.get(worker+'requests.json')==REQUESTS_SHA,'Same two-request task declaration')
    need(sha(baseline_consumer_bytes)==release['consumer_code_sha256'],'Original consumer source identity')
    adapted_sha=sha(expected_consumer_adapter(baseline_consumer_bytes.decode(),delta))
    need(fork.get('consumer_original_sha256')==release['consumer_code_sha256'] and
         fork.get('consumer_adapter_sha256')==adapted_sha and files.get(worker+'overlay_consumer.py')==adapted_sha,
         'Only exact invertible two-alias source-verifier adaptation')
    sdk_suffix='/native-sdk-340d7d8/MANIFEST.json'
    sdk=[v for k,v in base_freeze['files'].items() if k.endswith(sdk_suffix)]
    new_sdk=[v for k,v in files.items() if k.endswith(sdk_suffix)]
    need(len(sdk)==len(new_sdk)==1 and sdk==new_sdk,'Same native SDK/actor source manifest pin')
    return dict(schema='reach-exact-v2-declared-source-pair-qualification-v1',
        status='DECLARED_V2_SOURCE_PAIR_QUALIFIED_NOT_EXECUTION_ADMISSION',source_pair_verified=True,
        baseline_result_sha256=sha(baseline_result_bytes),candidate_result_sha256=sha(candidate_result_bytes),
        baseline_program_sha256=BASE_PROGRAM_SHA,candidate_program_sha256=program,
        baseline_release_sha256=BASE_RELEASE_SHA,v2_bundle_manifest_sha256=V2_BUNDLE_SHA,
        candidate_fork_manifest_sha256=fork_sha,original_source_manifest_is_lineage_not_current_pin=True,
        exact_changed_original_aliases=list(ALIASES),unchanged_original_source_files=281,
        optimizer_reference_law_original_guards_goal_and_four_second_verification_unchanged=True,
        live_import_ids_or_native_safety_or_actual_success_proven=False,
        actual_command_prefix_and_terminal_consumption_still_separate_evidence=True,
        actual_zero_or_main_execution_authorized=False,method_advantage_or_generalization_proven=False)
