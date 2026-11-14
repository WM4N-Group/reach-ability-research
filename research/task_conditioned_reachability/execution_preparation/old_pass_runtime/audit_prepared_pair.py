"""Own fresh A/B configuration/source/zero audit. No task/physics/API calls."""
import argparse,hashlib,json,subprocess
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--release',type=Path,required=True);a=ap.parse_args();release=a.release.resolve()
    roots={};protocols={};records={};sources={}
    for arm in ('A','B'):
        own=release/arm;admission=json.loads((own/'main-admission.json').read_text());root=Path(admission['new_physical_root']);roots[arm]=root
        if sha(root/'freeze.json')!=admission['physical_freeze_sha256']:raise ValueError('Own main freeze changed')
        freeze=json.loads((root/'freeze.json').read_text())
        for n,h in freeze['inputs'].items():
            if sha(root/n)!=h:raise ValueError('Actual prepared input changed '+n)
        p=json.loads((root/'protocol.json').read_text());protocols[arm]=p
        zero=json.loads((own/'native-zero-v1/report.json').read_text());probe=json.loads((own/'native-zero-v1/native-probe.json').read_text())
        if zero.get('status')!='OWN_ACTUAL_NATIVE_ZERO_PASS' or probe['native_physics_steps']!=0 or probe['actual_world_time_s']!=0.:raise ValueError('Own zero incomplete')
        video=json.loads((own/'native-zero-v1/native-camera-provenance.json').read_text())
        ff=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,nb_read_frames','-of','json',str(own/'native-zero-v1/native-camera-1x.mp4')],text=True))['streams'][0]
        if int(ff['nb_read_frames'])!=video['frames'] or video['log_or_state_reconstruction']:raise ValueError('Actual native camera encode mismatch')
        cpu=json.loads((own/'cpu-qualified-v6/CPU-qualified.json').read_text())
        records[arm]=dict(source_id=p['source_id'],prepared_root=str(root),actual_own_zero_pass=True,
                          actual_task_physics_steps=probe['native_physics_steps'],actual_zero_world_time=probe['actual_world_time_s'],
                          CPU_unique_cases=cpu['unique_required_cases'],CPU_clean_single_pass=cpu['clean_single_pass_full_suite'],
                          native_camera_frames=video['frames'],native_camera_shape=[ff['height'],ff['width']],
                          native_capture_not_reconstruction=True,checkpoint_sha256=sha(root/'model/M64B-behavior-final.pt'),
                          actual_main_attempt_exists=(root/'attempt.claim').exists(),actual_wrapper_claim_exists=(root/'own-wrapper.claim').exists())
        sources[arm]={str(p.relative_to(root/'source')):sha(p) for p in (root/'source').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    pa={k:v for k,v in protocols['A'].items() if k not in ('source_id','episode_id')};pb={k:v for k,v in protocols['B'].items() if k not in ('source_id','episode_id')}
    if pa!=pb:raise ValueError('Unmatched task/model/parameters beyond own run identifiers')
    if records['A']['checkpoint_sha256']!=records['B']['checkpoint_sha256'] or records['A']['checkpoint_sha256']!=protocols['A']['behavior_model']['checkpoint_sha256']:raise ValueError('Deployed WM differs')
    modified=[n for n in sources['A'] if n in sources['B'] and sources['A'][n]!=sources['B'][n]]
    added=sorted(set(sources['B'])-set(sources['A']))
    expected_modified=['mujoco_zyh/deepseek_mission_task_NAV_request_physical_protocol.py','mujoco_zyh/stall_stow.py']
    if set(modified)!=set(expected_modified) or added!=['mujoco_zyh/reach_phe_hook.py']:raise ValueError('Unexpected actual deployment delta')
    result=dict(schema='reach-old-pass-own-actual-zero-prepared-pair-invariance-v1',passed=True,
                arms=records,protocols_equal_except_run_identifiers=True,deployed_model_exactly_same=True,
                actual_source_modified_between_arms=modified,actual_source_added_in_B=added,
                source_identifier_file_is_metadata_only=True,optimized_variable='H-only protected same-compact reference path',
                base_support_task_model_control_parameters_NOT_changed=True,
                original_whole_repo_feedback_replay_claimed=False,
                feedback_qualification='explicit unchanged component byte proof, not new private replay',
                strict_safety_or_general_deployment_certified=False,old_baseline_task_pass_NOT_relabelled_safe=True,
                main_runs_started=sum(int(r['actual_main_attempt_exists']) for r in records.values()),
                API_calls_started=0,actual_task_effect='UNKNOWN_main_not_started',
                live_pair_requires_original_secure_credential_and_fresh_canonical_locks=True,
                legacy_source_commit_field_is_parent_commit_not_claimed_clean_research_git_state=True)
    output=release/'prepared-pair-invariance.json'
    if output.exists():raise ValueError('Never overwrite an audit')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(passed=True,zero_arms=list(records),protocol_equal=True,model_equal=True,
                         native_camera_frames={k:v['native_camera_frames'] for k,v in records.items()},main_runs_started=result['main_runs_started']),indent=2))


if __name__=='__main__':main()
