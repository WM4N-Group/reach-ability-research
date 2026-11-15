"""Independent, user-authorized narrow PUSH study; old roots/roles never changed."""
import hashlib,json
from pathlib import Path

SCHEMA='piper-narrow-push-displacement-case-v1'
PLAN_NAME='push_forecast_plan_v1.json'

def load_plan():return json.loads(Path(__file__).with_name(PLAN_NAME).read_text())
def plan_sha():return hashlib.sha256(Path(__file__).with_name(PLAN_NAME).read_bytes()).hexdigest()

def case_protocol(case):
    base=json.loads(Path(__file__).with_name('migration_protocol_v1.json').read_text())
    base.update(schema=SCHEMA,scenario='nav-push',scene_recipe='zyh_native_single_box',
        selected_object_id='probe_object',role=case['split'],training_allowed=case['split']=='train',
        forecast_study_training_authorized=True,forecast_study_sha256=plan_sha(),
        probe_physics=dict(mass_kg=case['mass_kg'],friction=case['friction']),
        source_id='narrow-push-20261024-v1-'+case['id'],episode_id=case['id'],
        source_group='narrow-push-condition-'+case['id'],seed=case['seed'],
        max_sim_seconds=35,max_wall_seconds=65,max_payload_bytes=48*1024*1024,
        push_probe_max_active_s=12.,box_height_m=0.,resource_lock_dir='/mnt/yuanyue/data/go2-piper-world-model',full_state_review=True,
        max_review_state_bytes=32*1024*1024,max_total_episode_bytes=192*1024*1024,max_compiled_model_cache_bytes=512*1024*1024,purpose='Independent short PUSH dynamics sampling; not full task safety acceptance',
        review_scope='ONE probe object, never A/B/C. Only native PUSH continuation windows may train; strict unsafe windows excluded.')
    return base


def validate_case(p):
    from .collect import validate_protocol
    if p['schema']!=SCHEMA or p.get('forecast_study_sha256')!=plan_sha():raise ValueError('Independent study freeze required')
    found=[c for c in load_plan()['cases'] if c['id']==p['episode_id']]
    if len(found)!=1 or p!=case_protocol(found[0]):raise ValueError('Case/source/split/budget/physics changed since plan')
    shadow=dict(p,schema='piper-zyh-mujoco-collection-protocol-v1',selected_object_id='upstream_demo',role='development',training_allowed=False,full_state_review=False)
    validate_protocol(shadow)
    return p


def configure_probe(spec,physics):
    # COMPILE-TIME ONLY. Mass/colors/poses of research A/B/C are not involved.
    spec.geom('push_box_geom').mass=physics['mass_kg']
    spec.geom('push_box_geom').friction=[physics['friction'],0.,0.]
    count=0
    for pair in spec.pairs:
        if 'push_box_geom' in (pair.geomname1,pair.geomname2):
            pair.friction=[physics['friction'],physics['friction'],0.,0.,0.];count+=1
    if count<1:raise ValueError('Explicit physical box pairs missing; geom friction alone insufficient')
    return count
