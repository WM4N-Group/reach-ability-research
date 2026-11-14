"""Consume NEW Data native-CPU and phase receipts; no replay or native import."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from .stow_choice_effects import audit_choice, audit_effect

CPU_RELEASE_SHA='bbf8973859b91184e32d28aa44a5fed4e050f090b1eec2641f019b526437e81c'
BASE_SHA='3098297041dbfa50dd1928ee81ce28c68d3458ed544cc494dea7374177b7c49e'
P2_RELEASE_SHA='d9b6198c7ea5253a23efa878af6d943fdb4fb23709b99a8c8645ceba1420df49'
DATA=Path('/home/yuanyue/main/work/data-team')
PACKAGE=Path('/home/yuanyue/main/work/ainav/consumer-deliveries/AINAV-ABSOLUTE-PLACEMENT-BASELINE-20261113-v1')


def consume(*, phase_release_sha256):
    refs=[]
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def read(p,h,lines=False):
        if sha(p)!=h:raise ValueError('Explicit publication/source pin drift: '+str(p))
        refs.append(dict(path=str(p.resolve()),sha256=h))
        return [json.loads(s) for s in p.read_text().splitlines()] if lines else json.loads(p.read_text())
    cpu_root=DATA/'consumer-deliveries/AINAV-DATA-STOW-CHOICE-NATIVE-CPU-INTAKE-20261113-v1'
    release=read(cpu_root/'release.json',CPU_RELEASE_SHA)
    cpu=read(cpu_root/'native-CPU-intake-result.json',release['files']['native-CPU-intake-result.json'])
    base=read(PACKAGE/'BASELINE_RELEASE_v1.json',BASE_SHA)
    local=Path(__file__).resolve().parents[3]/'evidence/2026-11-13/stow-path-choice-consumer-v1/delta-bundle'
    bundle_sha=sha(local/'manifest.json')
    manifest=read(local/'manifest.json',bundle_sha)
    fork=read(DATA/'manifests/ainav-stow-path-native-CPU-intake-20261113-v1/fork-manifest.json',release['fork_manifest_sha256'])
    read(DATA/'manifests/ainav-stow-path-native-CPU-intake-20261113-v1/remote-intake-v2-receipt.json',release['remote_receipt_sha256'])
    program=DATA/'workers/ainav-stow-path-native-CPU-intake-20261113-v1/native_cpu_intake.py'
    if sha(program)!=release['native_cpu_intake_program_sha256']:raise ValueError('Owner native intake source drift')
    refs.append(dict(path=str(program),sha256=sha(program)))
    if not (fork==cpu['source_fork'] and fork['Reach_bundle_manifest_sha256']==bundle_sha
            and fork['baseline_release_sha256']==BASE_SHA):raise ValueError('Receipt does not consume this frozen v1 bundle')
    originals=base['complete_reference_source_files_sha256'];current=fork['current_source_files_sha256']
    if set(originals)!=set(current):raise ValueError('Mixed or partial source inventory')
    changed={k for k in originals if originals[k]!=current[k]}
    if changed!=set(manifest['changed_original_source_files']):raise ValueError('Undeclared source mutation')
    for rel in changed:
        if current[rel]!=manifest['files_sha256']['source-delta/'+rel]:raise ValueError('Wrong changed source SHA')
    if not (cpu['explicit_overlay_verifier_passed'] is True and cpu['original_consumer_rejected_overlay']
            and cpu['default_off_exact_numeric_equality'] is True and cpu['selected_numeric_reference_changed'] is True):
        raise ValueError('Missing real-native CPU default-off/consumer evidence')
    original,off,on=(cpu[k] for k in ('original','default_off','enabled_software_case'))
    for key in ('waypoints','first_segment_assigned_seconds','actual_numeric_reference','actual_numeric_velocity','actual_original_axis_reference_receipts'):
        if original[key]!=off[key]:raise ValueError('Default-off native numeric mismatch: '+key)
    if original['actual_numeric_reference']==on['actual_numeric_reference']:raise ValueError('No enabled reference difference')
    for fixture in (original,off,on,cpu['unselected_software_case']):
        if not (fixture['original_queue_screen_used'] is True and fixture['native_collision_or_measured_capture_tested'] is False
                and fixture['full_command_or_QP_or_motor_issued'] is False and fixture['simulated_physics_steps']==0):
            raise ValueError('CPU evidence scope changed')
    events=on['events']
    if len(events)!=1:raise ValueError('One enabled selector receipt required')
    choice=audit_choice(events[0])
    phase_root=DATA/'consumer-deliveries/AINAV-DATA-ORIGINAL-STOW-PHASE-EVIDENCE-20261113-v1'
    phase_release=read(phase_root/'release.json',phase_release_sha256)
    phase=read(phase_root/'actual-stow-phase-evidence.json',phase_release['files']['actual-stow-phase-evidence.json'])
    p2=read(DATA/'consumer-deliveries/AINAV-DATA-ORIGINAL-PUSH-TO-CLIMB-ACTUAL-20261113-v1/release.json',P2_RELEASE_SHA)
    mirror=DATA/'manifests/ainav-full-host-continuation-20261113-v1/raw-main/main'
    raw=read(mirror/'result.json',p2['primary_result_sha256'])
    journal=read(mirror/'events.jsonl',p2['primary_journal_sha256'],lines=True)
    effect=audit_effect(raw,journal)
    if effect['completed_original_waypoint_count']!=phase['actually_completed_original_waypoint_count']:
        raise ValueError('Completed original waypoint cardinality mismatch')
    if abs(effect['actual_costs_s']['capture_to_compact']-phase['affected_baseline_window_s'])>1e-9:
        raise ValueError('Original affected window mismatch')
    return dict(schema='reach-consumed-Data-native-stow-CPU-and-original-phase-v1',
        role='AUDIT_ONLY_NOT_PLANNER_INPUT_OR_FIT',source_inputs=refs,
        owner_actual_loader_NumPy_queue_reference_CPU_receipt_consumed=True,
        source_changed_files=sorted(changed),source_unchanged_files=len(originals)-len(changed),
        original_manifest_is_lineage_not_current_fork_pin=True,
        native_fixture_decision_audit=choice,native_geometry_or_full_QP_or_physics_qualified=False,
        baseline_actual_effect=effect,
        observed_original_waypoint_domain_note='P2 completed two waypoints; under that fixed ordered domain only original/direct exist, not a third policy. This is not a guarantee of other future runtime domains.',
        current_observed_domain_can_establish_novel_subsequence_algorithm=False,
        affected_baseline_motion_and_settling_window_s=phase['affected_baseline_window_s'],
        affected_baseline_window_is_not_a_savings_prediction=True,
        optimization_uses_any_owner_outcome_or_CPU_fixture_labels=False,
        new_physics_or_native_cpu_replays_or_API_calls=0)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase-release-sha256',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    attempts=[]
    def fence(event,args):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.fork','os.posix_spawn'):
            attempts.append(event);raise RuntimeError('Offline receipt consumption only: '+event)
        if event=='import' and str(args[0]).split('.')[0] in ('numpy','torch','mujoco','scipy','onnxruntime','requests','httpx'):
            attempts.append(str(args[0]));raise RuntimeError('Do not replay owner native intake')
    sys.addaudithook(fence)
    result=consume(phase_release_sha256=a.phase_release_sha256);result['fence_attempts']=attempts
    out=Path(a.output)
    with out.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(dict(changed=result['source_changed_files'],unchanged=result['source_unchanged_files'],
        decision=result['native_fixture_decision_audit']['classification'],
        observed_waypoints=result['baseline_actual_effect']['completed_original_waypoint_count']),ensure_ascii=False))


if __name__=='__main__':main()
