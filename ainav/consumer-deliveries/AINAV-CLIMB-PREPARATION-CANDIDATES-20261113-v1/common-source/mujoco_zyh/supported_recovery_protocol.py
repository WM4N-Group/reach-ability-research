"""Exact source-matched compact/support protection engineering cases."""
import json
from pathlib import Path
from .failure_capsules import CONFIG
from .supported_push import MODE

CASES={
 'train5':dict(seed=5405,mass=20.,friction=.45,geometry=dict(initial_box_dx_m=-.025,initial_box_dy_m=-.06,initial_box_yaw_rad=-.06)),
 'train3':dict(seed=5403,mass=4.,friction=.45,geometry=dict(initial_box_dx_m=.025,initial_box_dy_m=.06,initial_box_yaw_rad=.06)),
 'train4':dict(seed=5404,mass=8.,friction=.30,geometry=dict(initial_box_dx_m=0.,initial_box_dy_m=0.,initial_box_yaw_rad=0.)),
}


def protocol(case='train5'):
    c=CASES[case];p=json.loads(Path(__file__).with_name('soft_stall_stow_protocol_v7.json').read_text())
    p.update(schema='piper-mujoco-compact-supported-recovery-v25',source_id='compact-supported-'+case+'-20261025-v25',
        episode_id='compact-supported-'+case+'-20261025-v25-episode0',source_group='known-TRAIN-compact-supported-engineering-v25',
        purpose='Frozen NN proposals with explicitly replaced leg motor control by native support QP; real compact entry+gravity FF+arm projection from FIRST protected command; observe actual contact/60ms failure then real retreat/stow. NOT original motor skill or reliability test.',
        supported_push_mode=MODE,supported_recovery_case=case,role='development',training_allowed=False,
        forecast_study_training_authorized=False,resource_lock_dir='/mnt/yuanyue/data/go2-piper-world-model',
        seed=c['seed'],probe_physics=dict(mass_kg=c['mass'],friction=c['friction']),initial_probe_geometry=dict(c['geometry']),
        max_sim_seconds=100,max_wall_seconds=1200,grace_seconds=10,max_payload_bytes=80*1024*1024,max_total_episode_bytes=160*1024*1024,
        private_failure_capsules=dict(CONFIG),full_state_review=False,
        original_motor_executor_unchanged=False,compact_entry_target=[0.,.30,-.30,0.,0.,0.],
        additional_reference_execution_margin_rad=.02,arm_warning_fraction=.85,original_prediction_effort_reserve_fraction=.90,original_actual_effort_hard_fraction=.98,all_original_native_hard_stow_gates_retained=True,original_gravity_compensated_position_offset_removed_before_explicit_FF=True,fixed_measured_loaded_entry_COM_target=False,measured_box_gap_target_m=.485,original_native_push_approach_distance_m=.03,protected_push_approach_distance_m=.005,
        registered_arm_contact_preload_offset_m=.025,original_native_contact_force_gate_N=1.0,original_hand_height_offset_m=0.,protected_hand_height_offset_m=-.03,max_approach_velocity_m_s=.02,arm_target_uses_actual_native_controller_uncompensated_reference=True,
        review_scope='Actual onboardRGBD + motor/support/recovery/capsule. Single known-TRAIN probe, NOT researchA/B/C or heldout efficacy.',
        revision_reason='V24 real lateral reload reached 6.58cm measured and all feet loaded, but its planar movement target carried a stale z coordinate 1.64mm below the live low-posture support floor. The 3D issued-target 1mm gate therefore never opened. V25 tests only the issued XY lateral target for completion; measured 3D target error, base speed, foot speed and >=18N load still gate arm motion. V24 terminal capsule independently admits the exact two arm paths with 38.42mm minimum planned body clearance and 26.14N minimum static foot load. All original hard/contact/recovery gates remain unchanged.',
        registered_contact_center_gate=dict(hand_local_z_center_m=-.03,abs_hand_local_z_error_m_lt=.025,abs_hand_local_y_m_lt=.04,hand_local_x_m_le=-.6,max_actual_arm_speed_rad_s_lt=.12,max_issued_reference_speed_rad_s_lt=.12,native_safe_approach_complete_required=True,native_motion_ready_required_for_precontact_body_approach=False,body_xy_speed_target_m_s=0.,precontact_alignment_wait_max_s=40.),
        registered_base_alignment=dict(retreat_hand_local_x_m=-.70,no_forward_motion_before_lateral_height_alignment=True,max_retreat_m=.12,max_alignment_leg_m=.14,max_total_displacement_m=.18,max_target_speed_m_s=.02,max_base_speed_at_stage_boundary_m_s=.015,max_lateral_height_speed_before_forward_m_s=.008,min_four_foot_load_N=12.,min_four_foot_load_for_corrective_centering_N_gt=4.,rear_left_unload_hand_local_y_balance_target_m=.03,max_measured_foot_speed_m_s=.03,original_low_posture_clearance_m=.18,protected_base_target_clearance_m=.19,cumulative_foot_anchor_drift_recorded_not_a_hard_gate=True,path_samples=42,read_only_source_collision_and_foot_IK_before_movement=True,rebalance_trigger_hand_local_x_m=-.685,actual_base_retreat_m=.05,minimum_measured_retreat_for_arm_m=.045,max_measured_lateral_retreat_drift_m=.025,max_measured_vertical_retreat_drift_m=.01,arm_lateral_reload_target_m=.07,minimum_measured_lateral_reload_m=.06,minimum_loaded_foot_at_recenter_N=18.,arm_exterior_recenter_target_x_m=-.68,arm_exterior_recenter_target_y_from_measured_lateral_shift_m=.01,arm_exterior_recenter_target_z_m=-.02,arm_contact_goal_box_local_m=[-.59,-.03,-.03],arm_contact_path_samples=101,measured_four_foot_load_required_during_arm_advance_N=12.,arm_path_single_coupled_progress=True,arm_path_speed_cap_rad_s=.25,arm_path_planning_body_clearance_reserve_m=.003),
        source_router='Explicit compact entry adapter reused; frozen actors propose, QP replaces all12leg motor channels during protected PUSH. Native waypoint, guarded retreat/alignment, bounded approach to x=-.685, real 5cm backoff, real 7cm left loaded reload, box-exterior arm recentering, separately guarded slower arm extension, then native legal contact/60ms failure recovery.',
        max_supported_push_log_bytes=64*1024*1024)
    return p


def validate_protocol(p):
    case=p.get('supported_recovery_case')
    if case not in CASES or p!=protocol(case):raise ValueError('Exact separately frozen compact/support case required')
    return p
