"""Bounded R1/R2 smoke examples; explicit SYNTHETIC results, no robot trials.

Published owner availability is tabulated separately; no real observation or
causal prediction is fabricated. Old archive/held-out outcomes are not opened.
"""
import argparse
from copy import deepcopy
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from .native_domain_v0 import load_domain,OWNER_DOCS
from .discrete_selection import select_from_bundle
from .test_discrete_selection import problem,effect
from .discrete_selection import COST_TERMS,DISTANCES


def write(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')


def fixtures():
    allsmall={d:effect(d,cost=c) for d,c in zip(DISTANCES,(2.,4.,7.))}
    support={d:effect(d,front=f,cost=c) for d,f,c in zip(DISTANCES,(.9,1.,1.3),(1.,2.,4.))}
    exitcoupling={.2:effect(.2,front=1.3,robot=1.,cost=1.),
                  .4:effect(.4,front=1.3,robot=.6,cost=4.),
                  .6:effect(.6,front=1.4,robot=.6,cost=6.)}
    goal={d:effect(d) for d in DISTANCES}
    for row in goal.values():
        row['source']['tier']='requested_goal_only';row['requested_box_front_m']=[1.3,1.3]
    missingcost={d:effect(d) for d in DISTANCES}
    for row in missingcost.values():row['costs']['terms']['successor_preparation']=None
    straddles={.2:effect(.2),.4:effect(.4)}
    straddles[.2]['box_exit_front_m']=[1.,1.3]
    return dict(all_known_smallest_cost=allsmall,necessary_support_selects_largest=support,
                exit_robot_object_coupling_selects_middle=exitcoupling,
                one_evaluated_subset_only={.4:effect(.4)},no_effects={},
                requested_goal_only_not_prediction=goal,unknown_cost_not_zero=missingcost,
                no_candidate_meets_declared_relation={d:effect(d,front=.1) for d in DISTANCES},
                interval_indeterminate_and_partial_coverage=straddles)


def pack_fixture(records):
    """Preserve source role; synthetic packaging must not promote a goal to prediction."""
    roles={r['source']['tier'] for r in records.values()}
    if len(roles)>1:raise ValueError('Mixed-role artifact must be split, not silently relabeled')
    source=dict(tier=next(iter(roles)) if roles else 'synthetic_test',
                online_use_allowed=True,information_time_s=9.,
                assumptions=['explicit_numeric_fixture; not a real current observation or robot effect'])
    rows=[]
    for record in records.values():
        row=deepcopy(record);row.pop('source');rows.append(row)
    return dict(schema='reach-normalized-effect-input-v1',source=source,records=rows)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();r=args.output;r.mkdir(parents=True,exist_ok=False)
    domain=load_domain();cases=fixtures();src=Path(__file__).resolve().parent
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
          [src/n for n in ('native_domain_v0.py','discrete_selection.py','test_discrete_selection.py','run_discrete_selection.py')]}
    write(r/'protocol.json',dict(at=datetime.now().astimezone().isoformat(),source_sha256=pins,
                                owner_contract_sha256=domain['contract_sha256'],owner_manifest_sha256=domain['manifest_sha256'],
                                executor_version=domain['executor_version'],scope='SYNTHETIC_NUMERIC_LOGIC_ONLY_NOT_ROBOT_RANKINGS',
                                case_names=list(cases),candidate_distances_m=list(DISTANCES),
                                old_180_row_comparison_NOT_rerun=True,GPU_physics_WM_Actor_API_training_render=0))
    outputs={};flat=[];case_summary=[]
    for name,records in cases.items():
        bundle=pack_fixture(records)
        path=r/(name+'-input.json');write(path,bundle)
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        result=select_from_bundle(domain,problem(),path,expected_sha256=sha,allow_synthetic=True)
        write(r/(name+'-result.json'),result);outputs[name]=result
        winner=result['best_evaluated_candidate'];distance=winner['parameter_template']['parameters']['push_distance_m'] if winner else None
        case_summary.append(dict(case=name,data_tier='synthetic_test',status=result['status'],best_distance_m=distance,
                                 best_model_cost_upper_s=winner['score_upper_s'] if winner else None,
                                 complete_model_enumeration=result['complete_model_enumeration'],
                                 actual_next_ready=None,physical_dispatch=False))
        for row in result['rows']:
            flat.append(dict(case=name,data_tier='synthetic_test',push_distance_m=row['push_distance_m'],
                             status=row['status'],reason=row['reason'],rankable=row['rankable'],
                             total_cost_lower_s=row['cost_interval_s'][0] if row['cost_interval_s'] else None,
                             total_cost_upper_s=row['cost_interval_s'][1] if row['cost_interval_s'] else None,
                             longitudinal_support_margin_m=json.dumps(row['relations']['longitudinal_support_overlap']['margin_m']) if row['relations'] else None,
                             exit_separation_margin_m=json.dumps(row['relations']['exit_reference_separation']['margin_m']) if row['relations'] else None,
                             actual_next_ready=None,physical_dispatch=False))
    for name,rows in (('synthetic_per_candidate.csv',flat),('synthetic_case_summary.csv',case_summary)):
        with (r/name).open('x') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    # Declaration table, not an executed real query or reuse of old outcomes.
    coverage=[dict(data_tier='owner_published_v0_capability_NOT_CURRENT_QUERY',push_distance_m=d,
                   exposed_domain=True,current_observation_ref=None,current_effect_query='NOT_RUN_NO_DECISION_INPUT',
                   box_exit_front_m='NOT_READY',robot_exit_x_m='NOT_READY',
                   current_preparation_s='NOT_READY',push_including_Finish_s='NOT_READY',
                   successor_preparation_s='NOT_READY',actual_next_ready='NOT_READY',ranking='UNKNOWN',
                   source_contract_sha256=domain['contract_sha256']) for d in DISTANCES]
    with (r/'published_availability_NOT_CURRENT_RESULTS.csv').open('x') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(coverage[0]));writer.writeheader();writer.writerows(coverage)
    write(r/'summary.json',dict(synthetic_cases=case_summary,synthetic_candidate_rows=len(flat),
                              real_current_query_count=0,real_nominal_model_results=0,new_physical_trials=0,
                              public_input_missing_not_fabricated=True,synthetic_inputs_never_real_results=True,
                              research_reference_adopted_per_user_plan='go2-piper-mission-v9-ae1c724-full4',
                              new_continuous_algorithm='NO_GO_no_new_structure_or_domain_evidence',
                              dispatch_or_safety_admission=False))
    print(json.dumps(case_summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    def fence(event,args):
        if event in ('socket.connect','subprocess.Popen'):raise PermissionError('CPU fixture: no network or child execution')
    sys.addaudithook(fence)
    main()
