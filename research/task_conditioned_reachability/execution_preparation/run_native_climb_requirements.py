"""One day-task result table from source-bound rules and existing public event.

No synthetic solver campaign, model forward, actual outcome archive, world,
renderer, remote connection or API call. All point-model failures conditional.
"""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from .recorded_v9_diagnostics import load_recorded_owner_sources
from .native_climb_continuation import load_requirements,adapt_recorded_rows,consume_wm_phase_v2


def write(path,value):
    with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    requirements=load_requirements();public,sources=load_recorded_owner_sources()
    result=adapt_recorded_rows(public,sources,requirements)
    write(out/'requirements.json',requirements);write(out/'native-B-discrimination.json',result)
    write(out/'WM-phase-v2-consumption.json',consume_wm_phase_v2(public,sources))
    rows=[]
    for row in result['rows']:
        requested=row['immediate_requested_CLIMB_B'];future=row['later_requested_B_HIGH'];model=row['recorded_model_diagnostic']
        rows.append(dict(distance_m=row['distance_m'],object_ref='B',frame='WORLD_POSITIVE_X',
                         input_role='recorded_pre_decision_public_NOT_live',
                         requested_CLIMB_B_approach_x_m=requested['nominal_approach_world_xy_m'][0],
                         immediate_source='GROUND',immediate_requires_B_HIGH_dock=False,
                         later_HIGH_request_gap_m=future['gap_m'],later_HIGH_request_docking_margin_m=future['symmetric_docking_margin_m'],
                         original_forecast_available=model is not None,
                         forecast_direct_CLIMB_B_distance_m=model['nominal_distance_to_approach_m'] if model else None,
                         forecast_direct_radius_margin_m=model['necessary_margins']['approach_radius_m']['margin'] if model else None,
                         forecast_later_HIGH_docking_margin_m=model['later_HIGH_point_diagnostic']['symmetric_docking_margin_m'] if model else None,
                         forecast_phase_aligned_for_entry=model['phase_matched_for_entry'] if model else None,
                         required_phase_cost_s=None,next_ready=None,actual_physical_exclusion=False,
                         dominance_certified=False,selector_eligible=False))
    with (out/'three-candidate-discrimination.csv').open('x') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    folder=Path(__file__).resolve().parent
    write(out/'validation.json',dict(at=datetime.now().astimezone().isoformat(),source_sha256={str(folder/n):hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in ('native_climb_continuation.py','test_native_climb_continuation.py','run_native_climb_requirements.py','recorded_v9_diagnostics.py')},
                                  actual_future_read=False,new_model_forward=0,GPU_physics_API_training_render=0,
                                  arbitrary_exit_distance_injected=False,old_SLP_experiment_repeated=False,
                                  real_candidate_exclusions=[],dominance_certified=False,
                                  immediate_successor_and_later_seam_separated=True))
    print(json.dumps(rows,ensure_ascii=False,indent=2))


if __name__=='__main__':
    def fence(event,args):
        if event in ('socket.connect','subprocess.Popen'):raise PermissionError('No new inference/runtime or remote operation in this CPU report')
    sys.addaudithook(fence);main()
