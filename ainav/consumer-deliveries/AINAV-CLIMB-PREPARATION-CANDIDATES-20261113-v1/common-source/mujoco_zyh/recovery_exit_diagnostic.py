"""Two NEW instrumented diagnostic executions of KNOWN development conditions.

NOT attempts to repair recovery or improve heldout metrics. Expected refusals
remain failures. Reused old train seeds control initial conditions; these are
NOT new independent generalization samples, and no old episode is reopened.
"""
import json
from pathlib import Path
from .failure_capsules import CONFIG

SCHEMA='piper-mujoco-recovery-exit-capsule-protocol-v3'
CASES={
    'joint2':dict(seed=5403,mass_kg=4.,geometry=dict(initial_box_dx_m=.025,initial_box_dy_m=.06,initial_box_yaw_rad=.06),
                  known_condition='train-3',expected_refusal='unload_coupled_reference_intersection_empty:1'),
    'base-speed':dict(seed=5405,mass_kg=20.,geometry=dict(initial_box_dx_m=-.025,initial_box_dy_m=-.06,initial_box_yaw_rad=-.06),
                      known_condition='train-5',expected_refusal='measured_unload_retreat_outside_original_envelope'),
}


def case_protocol(name):
    case=CASES[name]
    p=json.loads(Path(__file__).with_name('soft_stall_stow_protocol_v7.json').read_text())
    p.update(schema=SCHEMA,purpose='ONE newly registered instrumented diagnostic of a known development PUSH condition. Capture exact soft-exit/terminal evidence; expected protection refusal is a FAILURE, not retry-until-success or a new independent sample.',
        source_id='exit-capsule-'+name+'-20261025-v3',episode_id='exit-capsule-'+name+'-20261025-v3-episode0',
        source_group='known-development-exit-capsule-diagnostics-20261025-v3',role='development',training_allowed=False,
        forecast_study_training_authorized=False,recovery_exit_diagnostic_case=name,
        known_condition_NOT_independent_new_sample=case['known_condition'],expected_refusal_diagnostic_only=case['expected_refusal'],
        resource_lock_dir='/mnt/yuanyue/data/go2-piper-world-model',seed=case['seed'],
        probe_physics=dict(mass_kg=case['mass_kg'],friction=.45),initial_probe_geometry=dict(case['geometry']),
        max_sim_seconds=22,max_wall_seconds=600,max_payload_bytes=32*1024*1024,max_total_episode_bytes=64*1024*1024,
        full_state_review=False,private_failure_capsules=dict(CONFIG),
        review_scope='Actual onboard RGB only, no new MJB/external-state renderer. NOT research A/B/C or a new successful recovery claim.',
        revision_reason='Previously missing exact exit base/COM/FIFO and refusal-call gravity. Instrumentation only; original executor/control/thresholds unchanged.',
        prior_failed_root_readonly='/mnt/yuanyue/data/go2-piper-world-model/terminated-option-forecast-study-20261025-v3/episodes/'+case['known_condition'])
    return p


def validate_protocol(p):
    name=p.get('recovery_exit_diagnostic_case')
    if name not in CASES or p!=case_protocol(name):
        raise ValueError('Exact NEW bounded diagnostic protocol required; no case/role/threshold/budget flips')
    return p
