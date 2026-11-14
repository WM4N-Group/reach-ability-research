"""Read one explicit, pinned Data artifact list; no discovery/launch or fitting.

The input list is an analysis invocation, not a data-role or physical permit.
A caller must state offline_dev_outcome_analysis and opt into any fixture rows.
"""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from .observed_handover_analysis import consume_closed,consume_lifecycle,retrospective_compare,handover_tradeoff_table


def write(path,value):
    with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')


def run(manifest_path,expected_sha256,output_root,*,allow_fixture=False):
    raw=Path(manifest_path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('Explicit Data artifact list SHA required')
    invocation=json.loads(raw)
    if invocation['schema']!='reach-offline-Data-artifact-list-v1' or invocation['purpose']!='offline_dev_outcome_analysis':raise ValueError('Offline evaluation invocation required')
    output_root=Path(output_root);output_root.mkdir(parents=True,exist_ok=False)
    results={}
    for item in invocation['items']:
        if item['name'] in results:raise ValueError('Do not overwrite a case with a repeated name')
        kwargs=dict(sidecar=item['sidecar'],sidecar_pins=item['sidecar_pins'],purpose=invocation['purpose'],allow_fixture=allow_fixture)
        if item['kind']=='phase_evaluation':
            observation=consume_closed(evaluation_path=item['evaluation_path'],evaluation_sha256=item['evaluation_sha256'],**kwargs)
            row=dict(normalized_observation=observation,status='NORMALIZED_OBSERVED_SCOPE')
        elif item['kind']=='lifecycle':
            row=consume_lifecycle(lifecycle_path=item['lifecycle_path'],lifecycle_sha256=item['lifecycle_sha256'],**kwargs)
        else:raise ValueError('Only explicit owner phase-evaluation/lifecycle sources are supported')
        results[item['name']]=row
        write(output_root/(item['name']+'-analysis.json'),row)
    comparisons={}
    for group in invocation.get('comparison_groups',[]):
        members=[results[name]['normalized_observation'] for name in group['items']]
        if any(row is None for row in members):
            comparisons[group['name']]=dict(status='UNKNOWN_INCOMPLETE_SOURCE_NOT_DROPPED',items=group['items'],
                                           best_online_action=None,execution_authorized=False)
        else:
            value=retrospective_compare(members,comparison_scope=group['scope'])
            value['handover_tradeoff_relations']=handover_tradeoff_table(members);comparisons[group['name']]=value
    write(output_root/'comparisons.json',comparisons)
    flat=[]
    for name,row in results.items():
        obs=row['normalized_observation']
        flat.append(dict(name=name,role='OFFLINE_EVALUATION_NOT_PREDICTION',status=row['status'],
                         provenance=obs['provenance'] if obs else row['provenance'],
                         observed_issued_count=row.get('observed_issued_count',obs['command_steps'] if obs else None),
                         persisted_issued_count=row.get('persisted_issued_count'),
                         PUSH_and_Finish_completed=obs['PUSH_and_normal_Finish_complete'] if obs else None,
                         native_push_including_Finish_s=obs['native_push_including_Finish_s'] if obs else None,
                         query_to_successor_preparation_end_s=obs['query_to_successor_preparation_end_s'] if obs else None,
                         actual_next_ready=None,online_input_allowed=False))
    with (output_root/'per-case.csv').open('x') as f:
        writer=csv.DictWriter(f,fieldnames=list(flat[0]));writer.writeheader();writer.writerows(flat)
    summary=dict(at=datetime.now().astimezone().isoformat(),input_list_path=str(manifest_path),input_list_sha256=expected_sha256,
                 owner_evaluations_consumed=len(results),provenances=sorted({x['provenance'] for x in flat}),
                 new_physics_or_model_calls=0,online_actions=0,training_or_norm=False,
                 report_scope='closed source measurements; table minima do not define an online causal planner')
    write(output_root/'summary.json',summary)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--expected-sha256',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--allow-fixture',action='store_true');a=p.parse_args()
    def fence(event,args):
        if event in ('socket.connect','subprocess.Popen'):raise PermissionError('This offline consumer cannot launch or connect to runtime')
    sys.addaudithook(fence)
    print(json.dumps(run(a.manifest,a.expected_sha256,a.output,allow_fixture=a.allow_fixture),ensure_ascii=False,indent=2))
