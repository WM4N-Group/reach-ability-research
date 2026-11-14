"""Package R1/R2 outputs without rerunning models, dynamics, or geometry FK.

Geometry file must already exist from the bounded 65-FK static computation.
This packaging pass is metadata/numeric analysis only, not extra trials.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import csv
from .recorded_v9_diagnostics import load_recorded_owner_sources
from .native_climb_continuation import load_requirements
from .model_sufficiency import analyze,declared_producer_sufficiency
from .projected_arm_geometry import GeometryStudyProfile,PINS,HELPER_SHA,APPROACH_SHA,CLEARANCE_SOURCE_SHA


def write(path,value):
    with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);args=parser.parse_args();r=args.root
    public,rows=load_recorded_owner_sources();req=load_requirements()
    a=analyze(public,rows,req)
    producer=Path('/home/yuanyue/re-nav/GO2-PIPER/docs/common_v9_effect_producer_preparation_v2.json')
    expected='2c13f3bd0069a5c407dac4b2190903e75fc05a08af8a35b225b92706263eacec'
    if hashlib.sha256(producer.read_bytes()).hexdigest()!=expected:raise ValueError('Published producer changed; explicit adaptation required')
    capability=declared_producer_sufficiency(json.loads(producer.read_text()))
    geometry=json.loads((r/'geometry/geometry.json').read_text());comparison=json.loads((r/'geometry/comparison.json').read_text())
    binding=dict(executor_reference='go2-piper-mission-v9-ae1c724-full4',skill_contract='0.1.1',
                 source_public_input_sha256=public['input_sha256'],decision_id=public['decision_id'],object_ref='B',
                 B_nominal_front_world_x_m=public['object_geometry']['front_world_x_m'],
                 B_front_role='registered initial prior, NOT exact current pose or error bound',
                 root_world_y_m=public['public_reference']['lane_y_m'],base_orientation_assumption='fixed identity in geometry study',
                 hypothetical_base_reference_world_x_m={str(row['standoff_m']):public['object_geometry']['front_world_x_m']-row['standoff_m'] for row in comparison['rows']},
                 native_standoff_domain_m=[.58],hypothetical_values_m=[.545,.58,.615],
                 study_values_source='baseline +/- one documented35mm geometry-clearance scale; NOT a qualified control range',
                 WM_new_standoff_profile_consumed=False,
                 profile_implementation='local default-off geometry-study profile, not a production/native profile',
                 task_target_after_translation_not_preserved_by_fixed_arm_curve=True,execution_authorized=False)
    write(r/'task-binding.json',binding)
    write(r/'cross-module-review.json',dict(at=datetime.now().astimezone().isoformat(),
             actual_owner_public_problem_and_coverage_called=True,producer_v2_capability_consumed=True,
             producer_v2_sha256=expected,owner_offline_actual_archive_opened=False,
             new_WM_real_three_candidate_output_consumed=False,new_WM_standoff_prototype_consumed=False,
             remaining_integration_breakpoint='new afternoon runner output/prototype not published at inspected entry; do not claim mock as integration',
             raw_model_responses_available=[.6],structural_limit_independent_of_missing02_04=True,
             no_new_model_forward_or_native_task=True))
    by_levels=a['levels'];fore=rows[-1]['effect']['value'];gap=3.5-(fore['box_front_world_x_m']+2.4)
    write(r/'hypothetical-sensitivity-NOT-CALIBRATION.json',dict(role='HYPOTHETICAL_MATH_ONLY_NOT_CALIBRATED_OR_STAGE_ALIGNED',
             unaligned_model_point_gap_m=gap,
             radius_needed_for_a_symmetric_gap_interval_to_intersect_native_docking_band_m=max(0.,abs(gap)-.01),
             real_error_bound=None,physical_exclusion=False,used_by_selector=False))
    table=[dict(level='1_model_action_response',current_result='single .6 only; no pairwise current comparison',
                if_three_same_kind_outputs='response comparison possible; structural fields still absent'),
           dict(level='2_scope_limited_necessary_exclusion',current_result='no valid phase-matched bounds; no physical exclusion',
                if_three_same_kind_outputs='still no certified interval; direct-entry failure does not exclude NAV repair'),
           dict(level='3_successful_time_comparison',current_result='unconditioned native-terminal event clock; no successful cost',
                if_three_same_kind_outputs='same structural gap, not solved by row count'),
           dict(level='4_executable_choice',current_result='insufficient state/stage/authorization; UNKNOWN',
                if_three_same_kind_outputs='not sufficient; independent native checks still required')]
    with (r/'four-level-decision.csv').open('x') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    with (r/'geometry/raw-same-domain-comparison.csv').open('x') as f:
        w=csv.DictWriter(f,fieldnames=list(comparison['rows'][0]));w.writeheader();w.writerows(comparison['rows'])
    src=Path(__file__).resolve().parent
    write(r/'validation.json',dict(at=datetime.now().astimezone().isoformat(),
          source_sha256={str(src/n):hashlib.sha256((src/n).read_bytes()).hexdigest() for n in ('model_sufficiency.py','projected_arm_geometry.py','run_afternoon_analysis.py','test_model_sufficiency.py','test_projected_arm_geometry.py')},
          geometry_profile_pins=PINS,original_profile_helper_sha256=HELPER_SHA,original_approach_sha256=APPROACH_SHA,
          clearance_constant_source_report_sha256=CLEARANCE_SOURCE_SHA,
          completed_subjects=['R1 four-level sufficiency analyzer','R2 one source-mesh/task-plane constraint and exact same-domain comparison'],
          actor_or_WM_model_loads=0,FK_calls_in_successful_static_run=65,geometry_compile_failed_attempts_before_FK=1,
          physics_steps=0,renderer_calls=0,API_calls=0,GPU_calls=0,
          no_new_geometry_FK_in_packaging=True,new_algorithm_advantage_established=False,
          original_native_domain_unchanged=True,geometry_projection_is_not_full_collision_safety=True))
    print(json.dumps(dict(levels=by_levels,geometry_rows=comparison['rows']),indent=2))


if __name__=='__main__':main()
