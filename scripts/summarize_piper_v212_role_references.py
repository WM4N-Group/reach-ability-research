"""Score the frozen current-clearance reference separately by registered data role."""
import argparse
import json
from pathlib import Path
from collections import defaultdict

from bind_piper_v212_registry import sha,read
from audit_piper_v212_phase_reference import PHASES,causal_phases,summarize


def audit(paths,split_path):
    split=read(split_path);loaded=[read(p) for p in paths]
    episodes=[e for data in loaded for e in data['episodes']]
    ids=[e['episode_id'] for e in episodes]
    if len(ids)!=len(set(ids)):raise ValueError('Same physical episode provided twice')
    roles={}
    for e in episodes:
        role=e['owner_recorded_role'];group=e['group_id'];info=split['measured_groups'].get(group,{})
        if role not in ('train','development_calibration') or info.get('role')!=role or e['episode_id'] not in info.get('episodes',[]):
            raise ValueError('Only registered train/development roles may be read')
        if group in roles and roles[group]!=role:raise ValueError('Group appears in incompatible roles')
        roles[group]=role
    scores=defaultdict(list);coverage=defaultdict(lambda:dict(episodes=0,queries=0,valid_targets=0,censored_targets=0,successes=0))
    for e in episodes:
        role=e['owner_recorded_role'];source=Path(e['source_path'])
        if sha(source)!=e['source_sha256']:raise ValueError('Source changed')
        rows=[json.loads(line) for line in source.read_text().splitlines()]
        phases=causal_phases(rows);dt=e['actual_sample_period_s'];c=coverage[role]
        c['episodes']+=1;c['queries']+=len(e['queries']);c['successes']+=int(e['verified_task_success'])
        for q in e['queries']:
            step=round(q['query_time_s']/dt);phase,contact=phases[step]
            if q['inputs']['legal_contact_seen']!=contact:raise ValueError('Causal phase mismatch')
            for t in q['targets']:
                c['valid_targets']+=int(t['valid']);c['censored_targets']+=int(not t['valid'])
                if not q['history_0p4s_available'] or not t['valid']:continue
                h=t['requested_horizon_s'];error=t['constant_reference_m']-t['value']
                item=(e['group_id'],e['episode_id'],error)
                scores[(role,h,'all')].append(item);scores[(role,h,phase)].append(item)
    summaries={}
    for role in ('train','development_calibration'):
        metrics=[]
        for h in (.4,1.):
            phases={phase:summarize(scores[(role,h,phase)]) for phase in PHASES}
            assert sum(v['query_count'] for k,v in phases.items() if k!='all')==phases['all']['query_count']
            metrics.append(dict(horizon_s=h,phases=phases))
        summaries[role]=dict(coverage=dict(coverage[role]),metrics=metrics)
    return dict(schema='reach-v212-role-reference-summary-v1',reference='current_actual_clearance_minus_35mm',
        label_sources=[dict(path=str(p.resolve()),sha256=sha(p)) for p in paths],
        split=dict(path=str(split_path.resolve()),sha256=sha(split_path),policy=split['version']),
        roles=summaries,analysis_sha256=sha(Path(__file__)),
        aggregation_kernel_sha256=sha(Path(__file__).with_name('audit_piper_v212_phase_reference.py')),
        new_physical_episodes=0,reserved_source_outcomes_read=False,threshold_or_model_fitting=False,
        limitations=['Training and development results are separate; neither is a reserved diagnostic test.',
          'New increments remain subject to independent consumer alignment; this report is an offline rule diagnostic.',
          'All observed outcomes succeed; no risk calibration or model benefit inferred.',
          'Phases are conditioned on observed origin history, not future transitions.'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--labels',type=Path,action='append',required=True)
    p.add_argument('--split',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Refusing to overwrite reference result')
    result=audit(a.labels,a.split)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    for role,v in result['roles'].items():
        metric=v['metrics'][1]['phases']['legal_contact_seen']
        print(role,v['coverage'],'contact_1s_MAE_mm',metric['mean_group_mae_m']*1000)


if __name__=='__main__':main()
