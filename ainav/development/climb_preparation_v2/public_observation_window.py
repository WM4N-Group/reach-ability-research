"""Source-accurate public input window, NOT a successor-cost/admission model.

Consumes existing Observation.value dictionaries from the selected publisher.
No native/private state, IO, sampling, wait, controller, policy selection or fit.
Clock repetition is not a fresh temporal sample; sparse public samples never
certify continuous native hold. Caller must establish real publisher provenance.
"""
from copy import deepcopy
import math

CHANNELS = {'q':18, 'dq':18, 'gravity':3, 'angular_velocity':3, 'linear_velocity':3}
STATUS = {'support_surface','task_status','skill_status'}
TOP = {'time_s','rgb','objects','public_state','declared_map','goal','events'}


def need(ok,message):
    if not ok:raise ValueError(message)


def number(x):
    return type(x) in (int,float) and math.isfinite(x)


def summarize_public_window(observations):
    """Validate and describe already acquired public samples, not probabilities.

    The selected FullCourse publisher uses the same 45D packet with no
    current_public_proprio override. Proprio/camera time is therefore the actual
    packet acquisition clock, NOT a later query time or an invented timestamp.
    Schema validity alone does not prove source authenticity or data-use rights.
    """
    need(type(observations) in (list,tuple) and observations,'Existing nonempty public Observation window')
    distinct=[];previous_query=None;previous_camera=None;last_vector=None;duplicates=0
    for item in observations:
        value=deepcopy(item.value if hasattr(item,'value') else item)
        need(type(value) is dict and set(value)==TOP,'Existing public Observation fields only')
        now=value['time_s'];rgb=value['rgb'];state=value['public_state']
        need(type(rgb) is dict and 'time_s' in rgb,'Existing public acquisition clock')
        camera=rgb['time_s']
        need(number(now) and number(camera) and camera>=0 and 0<=now-camera<=.100001,'Original causal acquisition-age bound; no clock padding')
        need(type(state) is dict and set(CHANNELS)<=set(state)<=set(CHANNELS)|STATUS,
             'Selected publisher numeric/categorical fields only; no schema-only localization or private GT')
        for name,length in CHANNELS.items():
            v=state[name]
            need(type(v) is list and len(v)==length and all(number(x) for x in v),'Exact finite selected publisher channel: '+name)
        need(all(type(state[k]) is str for k in set(state)&STATUS),'Original categorical status strings')
        need(previous_query is None or now>=previous_query,'Query clock regressed')
        need(previous_camera is None or camera>=previous_camera,'Acquisition clock regressed')
        vector=tuple(x for name in CHANNELS for x in state[name])
        if previous_camera==camera:
            need(vector==last_vector,'Same acquisition clock but changed physical public proprioception')
            duplicates+=1
        else:
            distinct.append(dict(acquisition_time_s=camera,query_time_s=now,
                q=state['q'],dq=state['dq'],projected_gravity_b=state['gravity'],
                angular_velocity_b_rad_s=state['angular_velocity'],linear_velocity_b_m_s=state['linear_velocity']))
        previous_camera,previous_query,last_vector=camera,now,vector
    last=distinct[-1];gaps=[b['acquisition_time_s']-a['acquisition_time_s'] for a,b in zip(distinct,distinct[1:])]
    return dict(status='PUBLIC_INPUT_WINDOW_ONLY_SUCCESSOR_MODEL_UNKNOWN',
        samples=distinct,distinct_acquisition_times=len(distinct),same_clock_republications=duplicates,
        observed_acquisition_span_s=last['acquisition_time_s']-distinct[0]['acquisition_time_s'],
        maximum_observed_sample_gap_s=max(gaps) if gaps else None,
        latest_linear_speed_norm_m_s=math.hypot(*last['linear_velocity_b_m_s']),
        latest_angular_speed_norm_rad_s=math.hypot(*last['angular_velocity_b_rad_s']),
        gravity_normalization_or_tilt_conversion_assumed=False,
        base_world_XY=None,world_yaw=None,world_foot_loads=None,controller_latches=None,
        native_stop_hold_history=None,predicted_successor_cost_s=None,
        continuous_native_hold_verified=False,success_or_safety_probability=None,
        execution_authorized=False,training_or_fit_authorized=False,
        actual_source_authenticity_verified_by_this_function=False,
        field_note='Body-frame velocities; q/dq original selected 18-joint order; no world-pose integration or GT fallback')
