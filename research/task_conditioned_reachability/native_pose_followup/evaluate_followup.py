"""Read-only six-cell evaluation, with separate observed and attributable effects.

Missing cases are unknown, never zero successes. Matching initial/predecision
packets is an attribution check, not an excuse to drop failures or replace cases.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def canonical_hash(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def finite_vector(value, length):
    return (isinstance(value,list) and len(value)==length and
            all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in value))


def comparison_witness(folder,report):
    initial_path=folder/'actual-initial-state.json'
    if not initial_path.exists() or report is None:return None
    initial=read(initial_path)
    keys=('robot_position','robot_quaternion','box_position','box_quaternion','push_target')
    if not all(finite_vector(initial.get(k),4 if 'quaternion' in k else 3) for k in keys):return None
    query_id=report.get('prospective_support_plan',{}).get('box_approach_preview',{}).get('query_id')
    geometry=folder/'entry_geometry.jsonl'
    if not query_id or not geometry.exists():return None
    matches=[]
    with geometry.open() as stream:
        for line in stream:
            row=json.loads(line)
            if row.get('event')=='finite_tip_query' and row.get('query_id')==query_id:matches.append(row)
    if len(matches)!=1 or matches[0].get('evaluation_role')!='planning':return None
    query=matches[0]
    query_keys=('step','time_s','joint_names','q_rad','dq_rad_s','root_position_w','root_quaternion_wxyz',
                'box_position_w','box_quaternion_wxyz','box_size_m','waypoints_rad','residual_limit_rad',
                'nominal_translation_w','forecast_margin_m','reference_quaternion_wxyz')
    if not all(k in query for k in query_keys):return None
    names=query['joint_names']
    if not isinstance(names,list) or not names or not all(isinstance(n,str) for n in names):return None
    dims={'q_rad':len(names),'dq_rad_s':len(names),'root_position_w':3,'root_quaternion_wxyz':4,
          'box_position_w':3,'box_quaternion_wxyz':4,'box_size_m':3,
          'nominal_translation_w':3,'reference_quaternion_wxyz':4}
    if not all(finite_vector(query[k],n) for k,n in dims.items()):return None
    if not isinstance(query['waypoints_rad'],list) or not query['waypoints_rad'] or not all(finite_vector(v,6) for v in query['waypoints_rad']):return None
    for k in ('time_s','residual_limit_rad','forecast_margin_m'):
        if isinstance(query[k],bool) or not isinstance(query[k],(int,float)) or not math.isfinite(query[k]) or query[k]<0:return None
    if isinstance(query['step'],bool) or not isinstance(query['step'],int) or query['step']<0:return None
    return dict(initial_packet_sha256=canonical_hash({k:initial[k] for k in keys}),
                planning_packet_sha256=canonical_hash({k:query[k] for k in query_keys}),
                evidence_sha256={p.name:sha(p) for p in (initial_path,geometry)})


def evaluate(root):
    root=Path(root);source=root/'source';protocol=read(source/'protocol.json');manifest=read(source/'manifest.json')
    for name,digest in manifest['files'].items():
        if Path(name).name!=name or sha(source/name)!=digest:raise ValueError('Candidate source changed: '+name)
    if protocol['arms']!=['P2','P3'] or len(protocol['schedule'])!=6 or len(protocol['seeds'])!=3:
        raise ValueError('Not the registered single-factor six-cell candidate')
    spec=importlib.util.spec_from_file_location('bound_six_cell_evaluator',source/'evaluate_pose_pilot.py')
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    ledger_path=root/'physical_ledger.json';ledger=read(ledger_path) if ledger_path.exists() else None
    entries={} if ledger is None else {(e['seed'],e['arm']):e for e in ledger['entries']}
    reports={};witnesses={}
    for item in protocol['schedule']:
        key=(item['seed'],item['arm']);folder=root/'runs'/item['output_name'];path=folder/'report.json'
        if key not in entries:continue
        if path.exists():
            if entries[key].get('report_sha256') and sha(path)!=entries[key]['report_sha256']:
                raise ValueError('Recorded raw report SHA mismatch')
            for filename,field in [('actual-initial-state.json','initial_state_sha256'),('entry_geometry.jsonl','geometry_sha256')]:
                if entries[key].get(field) and sha(folder/filename)!=entries[key][field]:
                    raise ValueError('Recorded raw initial/geometry SHA mismatch')
            reports[key]=read(path);witnesses[key]=comparison_witness(folder,reports[key])
    result=native.summarize(protocol,ledger,reports);pairs=[]
    for seed in protocol['seeds']:
        left,right=witnesses.get((seed,'P2')),witnesses.get((seed,'P3'))
        comparable=None if left is None or right is None else (
            left['initial_packet_sha256']==right['initial_packet_sha256'] and
            left['planning_packet_sha256']==right['planning_packet_sha256'])
        pairs.append(dict(seed=seed,common_input_witnesses_equal=comparable,left=left,right=right))
    attributable=all(p['common_input_witnesses_equal'] is True for p in pairs)
    return dict(schema='native-pose-six-readonly-evaluation-v1',
        state='PREPARED_NOT_EXECUTED' if ledger is None else ledger['status'],
        source_manifest_sha256=sha(source/'manifest.json'),native_evaluation=result,
        input_pairs=pairs,descriptive_success_delta=result['effects']['P3_minus_P2'],
        matched_input_success_delta=result['effects']['P3_minus_P2'] if attributable else None,
        attribution_limit='packet equality is necessary here, not proof of deterministic execution or causal sufficiency',
        registered_cases_filtered=0,dispatch_enabled=False,
        scope='mechanism-targeted development, not independent generalization or real-world acceptance')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    print(json.dumps(evaluate(a.root),ensure_ascii=False,indent=2,allow_nan=False))
