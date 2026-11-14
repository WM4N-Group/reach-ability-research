"""Incremental observed-value comparison; shared absent fields are UNKNOWN.

Keeps the initial binding output unchanged. Its first field difference can be
missing coverage, not a differing measured value; this sidecar separates them.
No metadata/outcome replay, physics, tolerances, or numeric rounding.
"""
import argparse
import json
from pathlib import Path
import time

from bind_executed_navigation_baseline import compare_rows, read_through_step, sha, dump


def partition_changes(a,b,fields):
    changes=compare_rows(a,b,fields)
    observed={k:v for k,v in changes.items() if v['status']!='missing_field'}
    unobserved={k:v for k,v in changes.items() if v['status']=='missing_field'}
    return observed,unobserved


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    here=Path(__file__).resolve().parent
    protocol_path=here/'v316_v317_historical_binding_protocol_v1.json'
    protocol=json.loads(protocol_path.read_text())
    root=Path(protocol['source_root'])
    files=[root/f'transition-arm-entry-v{v}'/'seed3703-native-entry/control.jsonl' for v in [316,317]]
    old=here.parents[1]/'evidence/2026-10-20/executed-v316-v317-navigation-binding-v1/mechanism_prefix_comparison.json'
    bound=json.loads(old.read_text());end=bound['bounded_end_step'];decision=min(bound['planning_steps'])
    deadline=time.perf_counter()+10
    rows=[read_through_step(f,end,1000,deadline) for f in files]
    before_count=0;first=None;unobserved=[];changed_rows=0
    for a,b in zip(*rows):
        if a['step']!=b['step']:raise ValueError('Different physical step')
        values,missing=partition_changes(a,b,protocol['mechanism_prefix']['fields'])
        if missing:unobserved.append(dict(step=a['step'],fields=missing))
        if values:
            changed_rows+=1
            if first is None:first=dict(step=a['step'],time_s=a['time_s'],fields=values)
            if a['step']<=decision:before_count+=1
    out=dict(schema='historical-prefix-observed-values-r1',role='incremental_diagnostic_coverage_fix_NOT_new_robot_experiment',
             previous_output_unchanged=str(old),previous_sha256=sha(old),
             source_hashes={str(f):sha(f) for f in files},code_sha256=sha(Path(__file__)),
             bounded_rows=sum(map(len,rows)),decision_step=decision,end_step=end,
             missing_coverage_rows=unobserved,first_observed_value_difference=first,
             observed_difference_rows_at_or_before_decision=before_count,
             observed_difference_rows_through_limit=changed_rows,
             new_physics=0,no_floating_tolerance_or_imputation=True,
             note='Initial row0 lacks action/phase in both runs. It is unknown coverage, NOT evidence of a physical/control mismatch.')
    dump(args.output,out)
    print(json.dumps({k:v for k,v in out.items() if k not in ['source_hashes','missing_coverage_rows']},indent=2))


if __name__=='__main__':main()
