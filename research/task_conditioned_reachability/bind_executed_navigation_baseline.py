"""Read-only v316/v317 source + actual snapshot and historical mechanism binding.

Never import old probe/SDK/actors or run FK, physics, fitting, model forwards.
All outcomes are known exposed development history, not confirmatory evidence.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import math
from pathlib import Path
import time
import traceback

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE/'v316_v317_historical_binding_protocol_v1.json'


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def dump(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')


def finite_numbers(x):
    if isinstance(x, list):
        return [v for a in x for v in finite_numbers(a)]
    if type(x) in (int, float):
        if not math.isfinite(x):
            raise ValueError('Nonfinite historical state')
        return [float(x)]
    raise ValueError('Not a numeric state vector')


def compare_rows(a, b, fields):
    """Exact typed comparison; numerical differences are reported, never tuned away."""
    changes = {}
    for name in fields:
        if name not in a or name not in b:
            changes[name] = dict(status='missing_field', in_left=name in a, in_right=name in b)
            continue
        va, vb = a[name], b[name]
        same = json.dumps(va, sort_keys=True, separators=(',',':')) == json.dumps(vb, sort_keys=True, separators=(',',':'))
        if same:
            continue
        entry = dict(status='different')
        try:
            aa, bb = finite_numbers(va), finite_numbers(vb)
            if len(aa) == len(bb):
                entry['max_abs_numeric_difference'] = max((abs(x-y) for x,y in zip(aa,bb)), default=0.)
        except ValueError:
            entry.update(left=va, right=vb)
        changes[name] = entry
    return changes


def original_success(r):
    outcome = r.get('outcome')
    if outcome is None:
        return None
    return outcome == 'nav_push_stow_nav_target_stable'


def metrics(pairs, horizon):
    if any(p['left']['success'] is None or p['right']['success'] is None for p in pairs):
        return dict(status='NOT_ESTIMABLE_missing_original_terminal', pairs=len(pairs))
    common = [p for p in pairs if p['left']['success'] and p['right']['success']]
    wins = [p['seed'] for p in pairs if not p['left']['success'] and p['right']['success']]
    losses = [p['seed'] for p in pairs if p['left']['success'] and not p['right']['success']]
    penalty = lambda side: sum(p[side]['end_time_s'] if p[side]['success'] else horizon for p in pairs)/len(pairs)
    return dict(status='DESCRIPTIVE_exposed_development_NOT_causal_or_confirmatory', pairs=len(pairs),
        successes_left=sum(p['left']['success'] for p in pairs), successes_right=sum(p['right']['success'] for p in pairs),
        success_difference=(len(wins)-len(losses))/len(pairs), win_case_ids=wins, loss_case_ids=losses,
        common_successes=len(common), common_success_time_delta_right_minus_left_s=
            sum(p['right']['end_time_s']-p['left']['end_time_s'] for p in common)/len(common) if common else None,
        failure_penalty_horizon_s=horizon, failure_penalized_mean_left_s=penalty('left'),
        failure_penalized_mean_right_s=penalty('right'),
        failure_penalized_time_delta_right_minus_left_s=penalty('right')-penalty('left'),
        no_pvalue_or_independent_generalization_claim=True)


def read_through_step(path, step, row_budget, deadline):
    out = []
    with path.open() as f:
        for line in f:
            if time.perf_counter() > deadline:
                raise TimeoutError('Bounded historical prefix CPU budget reached')
            row = json.loads(line)
            if row['step'] > step:
                break
            out.append(row)
            if len(out) > row_budget:
                raise RuntimeError('Historical semantic row budget exceeded')
            if row['step'] == step:
                break
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('Do not overwrite/repeat archived historical binding')
    p = json.loads(PROTOCOL.read_text())
    root = Path(p['source_root'])
    args.output_dir.mkdir(parents=True)
    (args.output_dir/'protocol.original.json').write_bytes(PROTOCOL.read_bytes())
    began = time.perf_counter()
    deadline = began+p['resources']['max_cpu_wall_s']
    refs, plans, summaries, reports, dirs = {}, {}, {}, {}, {}
    summary = dict(schema='executed-navigation-baseline-binding-v1', status='NOT_COMPLETED',
                   role=p['role'], outcomes_known_before_analysis=True,
                   code_sha256=sha(Path(__file__)), protocol_sha256=sha(PROTOCOL),
                   new_physics=0, new_FK_IK=0, actor_loads_or_forwards=0, training_runs=0)
    error = None
    try:
        for ver, spec in p['versions'].items():
            d = root/spec['directory'];dirs[ver] = d
            for file, key in [('plan.json','plan_sha256'), ('screen-summary.json','summary_sha256')]:
                if sha(d/file) != spec[key]:
                    raise ValueError('Frozen source metadata changed: '+str(d/file))
                refs[str(d/file)] = spec[key]
            plan = json.loads((d/'plan.json').read_text());plans[ver] = plan
            screen = json.loads((d/'screen-summary.json').read_text());summaries[ver] = screen
            if sorted(screen['total_starts']) != p['case_ids'] or screen['missing_terminals'] != 0:
                raise ValueError('Unexpected historical case domain or missing terminals')
            for name, expected in plan['files'].items():
                if sha(d/name) != expected:
                    raise ValueError('Source file hash mismatch: '+str(d/name))
                refs[str(d/name)] = expected
            entries = {e['seed']:e for e in screen['entries']}
            reports[ver] = {}
            for seed in p['case_ids']:
                sd = d/f'seed{seed}-native-entry';f = sd/'report.json'
                actual = sha(f)
                if actual != entries[seed]['report_sha256']:
                    raise ValueError('Historical report differs from original screen index')
                refs[str(f)] = actual
                r = json.loads(f.read_text());reports[ver][seed] = r
                if r['outcome'] != entries[seed]['outcome'] or r['physical_resets_after_initial'] != 0:
                    raise ValueError('Summary/report outcome or reset mismatch')
                for name in ['actuator-contract.json','startup-physics.json']:
                    refs[str(sd/name)] = sha(sd/name)
                launch = d/f'launch-seed{seed}.json'
                refs[str(launch)] = sha(launch)
                cmd = json.loads(launch.read_text())['command']
                if cmd[cmd.index('--seconds')+1] != '96':
                    raise ValueError('Pair has a different original whole-chain horizon')
        changed = [name for name in sorted(set(plans['316']['files']) | set(plans['317']['files']))
                   if plans['316']['files'].get(name) != plans['317']['files'].get(name)]
        pairs = []
        for seed in p['case_ids']:
            a,b = reports['316'][seed],reports['317'][seed]
            def item(ver, r):
                rplan = r.get('prospective_support_plan',{})
                return dict(success=original_success(r),outcome=r['outcome'],terminal=r['terminal'],
                    end_time_s=summaries[ver]['entries'][next(i for i,x in enumerate(summaries[ver]['entries']) if x['seed']==seed)]['end_time_s'],
                    physical_resets_after_initial=r['physical_resets_after_initial'],
                    support_shift_m=rplan.get('shift_m'),support_only_shift_m=rplan.get('support_only_shift_m'),
                    tip_preview=rplan.get('box_approach_preview'),push_activation_time_s=r.get('push_activation_time_s'))
            paths = [dirs[v]/f'seed{seed}-native-entry' for v in ['316','317']]
            pairs.append(dict(seed=seed,left=item('316',a),right=item('317',b),
                same_nav_policy_sha=a['nav_sha256']==b['nav_sha256'],
                same_control_dt=a['control_dt']==b['control_dt'],
                same_joint_order=a['joint_names']==b['joint_names'],
                same_active_native_terms=a['native_safety_terms']==b['native_safety_terms'],
                same_startup_physics_bytes=sha(paths[0]/'startup-physics.json')==sha(paths[1]/'startup-physics.json'),
                same_actuator_contract_bytes=sha(paths[0]/'actuator-contract.json')==sha(paths[1]/'actuator-contract.json')))
        dump(args.output_dir/'all8_historical_pairs.json',pairs)
        # One actual historical observation, selected by first numeric case, not performance.
        query_report = reports['317'][3701]; query = query_report['entry_state']
        log = dirs['317']/'seed3701-native-entry/control.jsonl'
        rows = read_through_step(log, query['step'], p['resources']['max_semantic_control_rows'], deadline)
        matches = [r for r in rows if r['step']==query['step']]
        if len(matches)!=1 or compare_rows(query,matches[0],p['mechanism_prefix']['fields']):
            raise ValueError('Recorded entry_state does not match actual control prefix')
        refs[str(log)] = sha(log)
        bound_fields=['root_position','root_quaternion','root_velocity','root_angular_velocity','q','dq','pd_target','torque',
                      'foot_forces','gates','clearance_m','torque_ratio','history_valid_frames','native_action','applied_joint_command','phase']
        packet=dict(schema='actual-historical-navigation-entry-observation-v1',
            data_role='already_exposed_development_snapshot_NOT_new_or_unseen',
            source_report_sha256=refs[str(dirs['317']/'seed3701-native-entry/report.json')],
            source_control_sha256=refs[str(log)],seed=3701,step=query['step'],time_s=query['time_s'],
            event='transition_ready_before_push_activation',joint_names=query_report['joint_names'],
            measured_state={k:query[k] for k in bound_fields},
            state_by_joint_name={name:dict(q_rad=q,dq_rad_s=dq) for name,q,dq in zip(query_report['joint_names'],query['q'],query['dq'])},
            known_missing=['recorded box world position/quaternion at this query','full native hand geometry snapshot in the row','original route-cost/candidate domain: v317 is an Isaac custom velocity/stance entry loop, not generic MuJoCo OraclePlanner'],
            no_box_pose_default_imputation=True,not_Ry08_synthetic_pose_task=True,
            geometry_counterfactual_ready=False,execution_authorized=False)
        dump(args.output_dir/'actual_entry_query.json',packet)
        # Fixed, already-known changed case: bounded prefix, not a new success search.
        steps=[]
        for ver in ['316','317']:
            events=reports[ver][3703]['control_events']
            steps.append(next(e['step'] for e in events if e['event']=='prospective_support_integrated_into_final_center'))
        boundary=min(steps);end=boundary+50
        streams=[]
        for ver in ['316','317']:
            f=dirs[ver]/'seed3703-native-entry/control.jsonl'
            streams.append(read_through_step(f,end,p['resources']['max_semantic_control_rows'],deadline))
            refs[str(f)]=sha(f)
        read_count=len(rows)+sum(map(len,streams))
        if read_count > p['resources']['max_semantic_control_rows']:
            raise RuntimeError('Combined semantic row budget exceeded')
        first=None; mismatches_before=[];mismatch_count=0
        for a,b in zip(*streams):
            if a['step']!=b['step'] or a['time_s']!=b['time_s']:
                raise ValueError('Control prefix time/step mismatch')
            changes=compare_rows(a,b,p['mechanism_prefix']['fields'])
            if changes:
                mismatch_count+=1
                if first is None:first=dict(step=a['step'],time_s=a['time_s'],fields=changes)
                if a['step']<=boundary:mismatches_before.append(dict(step=a['step'],fields=changes))
        dump(args.output_dir/'mechanism_prefix_comparison.json',dict(
            seed=3703,selection='sole known changed outcome_POSTHOC',planning_steps=steps,
            bounded_end_step=end,total_semantic_rows_read=read_count,
            first_exact_field_difference=first,mismatching_rows_through_limit=mismatch_count,
            differences_at_or_before_decision=mismatches_before,
            zero_new_physics=True,NOT_independent_counterfactual_causal_proof=True))
        # Bound actual native control interface and direct source diff without importing SDK.
        interface=dict(engine='IsaacLab_original_v317',generic_MuJoCo_NAV_bridge_compatible=False,
            actual_decision_hook='prospective_entry -> required_standoff -> prospective_support(minimum_shift_m)',
            actual_execution='existing native_entry_process/loaded stance final centering; no new state writer',
            original_horizon_s=96,original_per_start_wall_timeout_s=1800,
            source_changed_files=changed,intervention='box-path envelope + minimum support shift + support-only bookkeeping bundle, NOT pure one-flag ablation',
            actual_native_terms=query_report['native_safety_terms'],
            actor_sha=dict(NAV=query_report['nav_sha256'],PUSH='4d1a4616928b4d06002285e870a1d6dd114e27b8cafcdd9a41dbdae1aceed419'),
            normalizer_scope='probe loads NAV TorchScript and PUSH actor_state_dict; source observation/preprocessing contract not replaced; no extra normalizer inferred',
            runtime_source_closure_fully_verified=False,physical_ablation_ready=False,
            missing_for_new_physics=['separate allocated budget','full compatible execution/source closure and query box/geometry binding','same-caller feature-flag ablation and original gates/source admission'])
        dump(args.output_dir/'native_execution_interface.json',interface)
        for filename in ['probe.py','prospective_support.py']:
            patch=''.join(difflib.unified_diff((dirs['316']/filename).read_text().splitlines(True),(dirs['317']/filename).read_text().splitlines(True),fromfile='v316/'+filename,tofile='v317/'+filename))
            (args.output_dir/(filename+'.diff')).write_text(patch)
        summary.update(status='COMPLETED_readonly_historical_binding_NOT_new_physical_validation',
            metrics=metrics(pairs,96.),source_plan_hashes_verified=True,declared_local_candidate_source_files_verified=True,
            actual_query_step=query['step'],actual_query_time_s=query['time_s'],actual_query_height_m=query['root_position'][2],
            actual_query_joint_order_verified=True,actual_query_raw_row_matched=True,
            combined_semantic_rows_read=read_count,
            pairs_all_same_nav_policy=all(x['same_nav_policy_sha'] for x in pairs),
            pairs_all_same_native_terms=all(x['same_active_native_terms'] for x in pairs),
            pairs_all_same_startup_physics=all(x['same_startup_physics_bytes'] for x in pairs),
            pairs_all_same_actuator_contract=all(x['same_actuator_contract_bytes'] for x in pairs),
            actual_query_geometry_reconstruction_ready=False,generic_MuJoCo_NAV_bridge_ready_for_v317=False,
            source_intervention_is_bundle=True)
    except Exception as exc:
        error=traceback.format_exc()
        summary.update(status='FAILED_preserve_partial_no_retry',error_type=type(exc).__name__,error=str(exc))
    finally:
        summary['cpu_wall_s']=time.perf_counter()-began
        dump(args.output_dir/'source_hashes.json',refs)
        dump(args.output_dir/'summary.json',summary)
        if error:(args.output_dir/'error.txt').write_text(error)
        print(json.dumps(summary,indent=2,ensure_ascii=False))
    return int(error is not None)


if __name__=='__main__':
    raise SystemExit(main())
