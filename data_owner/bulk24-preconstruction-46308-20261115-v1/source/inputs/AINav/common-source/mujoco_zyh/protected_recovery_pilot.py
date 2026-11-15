"""ONE conservative prequeue-protection engineering pilot, NOT reliability test."""
import json
from pathlib import Path
from dataclasses import asdict
from .failure_capsules import CONFIG as CAPSULES
from .push_protection import CONFIG,MODE

SCHEMA='piper-mujoco-prequeue-protected-recovery-pilot-v1'


def protocol():
    p=json.loads(Path(__file__).with_name('soft_stall_stow_protocol_v7.json').read_text())
    p.update(schema=SCHEMA,purpose='ONE protected PUSH engineering pilot with frozen actors. Pre-queue early support/speed retirement followed by existing protected real retreat/stow. Early interruption BEFORE contact is NOT failed-PUSH recovery acceptance.',
        source_id='protected-recovery-prequeue-20261025-v1',episode_id='protected-recovery-prequeue-20261025-v1-episode0',
        source_group='protected-recovery-engineering-knownTRAIN5-v1',role='development',training_allowed=False,
        forecast_study_training_authorized=False,push_protection_mode=MODE,protection_config=asdict(CONFIG),
        resource_lock_dir='/mnt/yuanyue/data/go2-piper-world-model',seed=5405,
        known_condition_NOT_new_independent_sample='old TRAIN5 geometry/seed, NEW protected executed option',
        probe_physics=dict(mass_kg=20.,friction=.45),initial_probe_geometry=dict(initial_box_dx_m=-.025,initial_box_dy_m=-.06,initial_box_yaw_rad=-.06),
        max_sim_seconds=80,max_wall_seconds=900,grace_seconds=10,max_payload_bytes=64*1024*1024,
        max_total_episode_bytes=128*1024*1024,full_state_review=False,private_failure_capsules=dict(CAPSULES),
        review_scope='Onboard RGBD10Hz plus200Hz motor/recovery/protection logs, noMJB. Independent20kgPROBE not researchA/B/C.',
        revision_reason='User authorized explicit PUSH support/speed protection on2026-10-25; do not allow known10ms speed refusal to be misattributed to new late recovery commands. This changes executed option/labels.',
        prior_failed_root_readonly='/mnt/yuanyue/data/go2-piper-world-model/exit-capsule-base-speed-20261025-v3',
        source_router='Original frozen NN proposal can be replaced BEFORE enqueue by existing real ProtectedStow/native QP. No future state used, no physical write/reset/FIFO clearing. All native hard guards retained.',
        max_protection_private_log_bytes=8*1024*1024)
    return p


def validate_protocol(p):
    if p!=protocol():raise ValueError('Exact ONE authorized protection pilot protocol required')
    return p
