"""Augment explicit, already-verified offline outcomes; never run acquisition.

Input list binds one old consumer result SHA plus the original pinned sidecar.
The old result remains untouched. No observation/exit LABEL is synthesized.
"""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from .analysis_paths import resolve as analysis_path
from .observed_handover_analysis import read_pinned
from .exit_repair_evidence import supplement_from_verified_sidecar,repair_comparison,repair_against_original_option,original_check_feedback


def run(invocation_path,invocation_sha256,output):
    invocation=read_pinned(invocation_path,invocation_sha256)
    if invocation['schema']!='reach-offline-repair-demand-invocation-v1' or invocation['purpose']!='offline_dev_outcome_analysis':
        raise ValueError('Explicit offline invocation, not prediction or fit request')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    records={}
    for item in invocation['items']:
        prior=read_pinned(item['analysis_path'],item['analysis_sha256'])
        obs=prior['normalized_observation']
        if obs is None:
            records[item['name']]=None;continue
        if obs['analysis_role']!='OFFLINE_DEV_EVALUATION_ONLY' or obs['online_input_allowed'] is not False:
            raise ValueError('Already verified OFFLINE source measurement required')
        repair=supplement_from_verified_sidecar(obs,sidecar=item['sidecar'],sidecar_pins=item['sidecar_pins'])
        obs['original_entry_check_feedback']=original_check_feedback(item['sidecar'],item['sidecar_pins'])
        obs['exit_repair_snapshot']=repair
        obs['native_option_bound_repair']=dict(status='UNKNOWN_MISSING_ORIGINAL_SELECTED_CLIMB_OPTION',translation_lower_bound_m=None)
        reference=item.get('original_next_option_ref')
        if reference is not None:
            # Optional source PUBLIC semantic option is not synthesized from box
            # geometry. It must independently hash-match the original check.
            option=read_pinned(reference['path'],reference['sha256'])
            sidecar=analysis_path(item['sidecar'])
            for name,h in item['sidecar_pins'].items():
                if hashlib.sha256((sidecar/name).read_bytes()).hexdigest()!=h:raise ValueError('Original sidecar changed')
            events=[json.loads(line) for line in (sidecar/'events.jsonl').read_text().splitlines()]
            exits=[e for e in events if e['kind']=='EXIT_GEOMETRY']
            checks=[e for e in events if e['kind']=='NEXT_ENTRY_CHECK']
            if len(exits)==1 and len(checks)==1:
                if checks[0]['time_s']<exits[0]['time_s']:raise ValueError('Earlier check cannot bind after-exit reference')
                obs['native_option_bound_repair']=repair_against_original_option(exits[0]['payload'],option,
                    checked_option_sha256=checks[0]['payload']['original_next_option_sha256'],purpose=invocation['purpose'])
        records[item['name']]=obs
        with (output/(item['name']+'-repair.json')).open('x') as f:json.dump(obs,f,indent=2);f.write('\n')
    groups={}
    for group in invocation['comparison_groups']:
        rows=[records[name] for name in group['items']]
        if any(x is None for x in rows):
            groups[group['name']]=dict(status='INCOMPLETE_SOURCE_NOT_DROPPED',best_online_action=None)
        else:groups[group['name']]=repair_comparison(rows,comparison_scope=group['scope'])
    with (output/'comparisons.json').open('x') as f:json.dump(groups,f,indent=2);f.write('\n')
    flat=[]
    for name,row in records.items():
        repair=row['exit_repair_snapshot'] if row else {}
        flat.append(dict(name=name,source_provenance=row['provenance'] if row else None,
            status=repair.get('status','INCOMPLETE_SOURCE'),translation_lower_bound_m=repair.get('translation_lower_bound_m'),
            conditional_geometric_reference_lower_bound_m=repair.get('conditional_geometric_reference_lower_bound_m'),
            native_option_bound_translation_lower_m=row['native_option_bound_repair']['translation_lower_bound_m'] if row else None,
            heading_correction_lower_bound_rad=repair.get('heading_correction_lower_bound_rad'),
            seconds_lower_bound=None,actual_next_ready=None,online_input_allowed=False))
    with (output/'per-case.csv').open('x') as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    summary=dict(at=datetime.now().astimezone().isoformat(),input_sha256=invocation_sha256,
                 evaluated_existing_source_records=len(records),new_scientific_samples=0,new_physics_or_model_calls=0,
                 no_exit_state_or_time_fabricated=True,source_measurements_not_modified=True)
    with (output/'summary.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--expected-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    def fence(event,args):
        if event in ('socket.connect','subprocess.Popen'):raise PermissionError('No runtime/remote/model call in offline exit-repair analysis')
    sys.addaudithook(fence);print(json.dumps(run(a.manifest,a.expected_sha256,a.output),indent=2))
