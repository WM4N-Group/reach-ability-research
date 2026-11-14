"""P1 public-information extraction and bounded re-observation decision.

Uses existing AINav Observation.value and its current publisher field meanings.
No predictor, result labels, simulator/private catalog, fit, file IO, action or
observation call. A request is NOT an executed observation/HOLD/NAV or a permit.
Fresh measured motion is descriptive, never successor success/cost/READY proof.
"""
import math
from .successor_aware_choice import need, number, digest, pin

TOP={'time_s','rgb','objects','public_state','declared_map','goal','events'}
VECTOR_LENGTHS={'q':18,'dq':18,'gravity':3,'angular_velocity':3,'linear_velocity':3}
CATEGORICAL={'support_surface','task_status','skill_status'}
MISSING_CAPABILITIES=(
    'Current registered-reference-relative pose is not wired as a public numerical feature',
    'Native navigation position/yaw hysteresis memory is not public',
    'Validated conditional complete-successor outcome/cost evaluator is absent',
)


def public_snapshot(observation, *, now_s, source_role):
    """Conservative subset extraction from the current owner public publisher.

    Source role is caller provenance, NOT source authentication. Owner must supply
    the genuine online observation, never relabel a DEV/audit row as online data.
    Current host captures packet proprio and RGB together. Without explicit
    separate proprio clock, only equal publication/camera clocks identify the
    default same-packet acquisition; otherwise timing stays UNKNOWN, not padded.
    """
    need(source_role=='ONLINE_PUBLIC','No audit-only/future outcome data in prospective information')
    need(type(observation) is dict and set(observation)==TOP,'Existing exact public Observation.value schema')
    need(number(now_s) and now_s>=0,'Actual current acquisition/decision clock')
    published=observation['time_s'];rgb=observation['rgb']
    need(number(published) and 0<=published<=now_s+1e-9 and type(rgb) is dict,
         'Causal publication, no future timestamp')
    need(set(rgb)=={'path','sha256','time_s','width','height'} and
         type(rgb['path']) is str and bool(rgb['path']) and pin(rgb['sha256']) and
         all(type(rgb[k]) is int and rgb[k]>0 for k in ('width','height')),
         'Existing RGB metadata shape; no image/clock fabrication')
    acquired=rgb.get('time_s')
    need(number(acquired) and 0<=acquired<=published+1e-9,'Causal original RGB/packet timestamp')
    state=observation['public_state']
    need(type(state) is dict and set(state)<=set(VECTOR_LENGTHS)|CATEGORICAL,
         'Only actually published robot fields; no private pose/contact/history')
    values={};missing=[]
    for name,size in VECTOR_LENGTHS.items():
        if name not in state:
            missing.append(name);continue
        vector=state[name]
        need(type(vector) is list and len(vector)==size and all(number(v) for v in vector),
             'Original finite public vector shape: '+name)
        values[name]=vector[:]
    for name in CATEGORICAL & set(state):
        need(type(state[name]) is str,'Categorical public status, never native predicate: '+name)
        values[name]=state[name]
    age=now_s-acquired
    synchronous=abs(published-acquired)<=1e-9
    fresh=age<=.100001 and synchronous and not missing
    descriptors={}
    if fresh:
        v=values['linear_velocity'];w=values['angular_velocity'];g=values['gravity']
        norm=math.hypot(*g)
        descriptors=dict(body_planar_speed_m_s=math.hypot(v[0],v[1]),
            body_speed_m_s=math.hypot(*v),body_angular_speed_rad_s=math.hypot(*w),
            body_yaw_rate_abs_rad_s=abs(w[2]),joint_speed_max_abs_rad_s=max(map(abs,values['dq'])),
            body_tilt_from_projected_gravity_rad=(math.acos(max(-1.,min(1.,-g[2]/norm))) if norm>0 else None))
        need(all(v is None or number(v) for v in descriptors.values()),'No numerical overflow in public descriptors')
    reason=('FRESH_COMPLETE_SAME_PACKET_PUBLIC_KINEMATICS' if fresh else
            'MISSING_PUBLISHED_KINEMATIC_FIELDS' if missing else
            'PROPRIO_ACQUISITION_CLOCK_UNKNOWN' if not synchronous else 'STALE_PUBLIC_PACKET')
    return dict(source_role='ONLINE_PUBLIC',source_observation_sha256=digest(observation),
        decision_time_s=now_s,published_time_s=published,packet_time_s=acquired,
        packet_age_s=age,public_vectors=values,missing_measurement_fields=missing,
        status=reason,fresh_complete_kinematic_measurement=fresh,
        descriptors=descriptors,
        descriptor_semantics='Current measured body-frame motion/joints, NOT native gates or future settling',
        unavailable_predictive_capabilities=list(MISSING_CAPABILITIES),
        categorical_support_is_not_dynamic_qualification=True,
        private_world_pose_or_contact_or_latch_exported=False,
        native_READY_or_success_inferred=False,current_or_future_completion_cost_s=None,
        permission_to_fit_train_or_use_audit_outcomes=False)


def information_action(snapshot, *, reobservations_used, max_reobservations=1):
    """Bounded closed-loop information decision; no observation or action issued.

    One request may refresh stale/missing allowed measurements. It cannot expose
    unpublished state or create a dynamics predictor. Caller accounts each actual
    acquisition, real clock/CPU/storage cost and original safe-boundary ownership.
    Re-observations are NEVER policy retries, new worlds or extra forced NAV.
    """
    need(type(snapshot) is dict and snapshot.get('source_role')=='ONLINE_PUBLIC',
         'Extracted legal public snapshot, not audit result')
    need(type(reobservations_used) is int and type(max_reobservations) is int and
         0<=reobservations_used<=max_reobservations<=1,'At most one actual legal refresh, no retry loop')
    fresh=snapshot['fresh_complete_kinematic_measurement']
    if not fresh and reobservations_used<max_reobservations:
        action='REQUEST_ONE_FRESH_EXISTING_PUBLIC_ACQUISITION'
        reason=snapshot['status']
    elif not fresh:
        action='KEEP_ORIGINAL_OR_ABSTAIN_MEASUREMENT_UNRESOLVED'
        reason='Re-observation budget exhausted; never pad timestamps or infer missing values'
    else:
        action='KEEP_ORIGINAL_OR_ABSTAIN_PREDICTION_UNRESOLVED'
        reason='Fresh motion descriptors do not resolve missing relative pose/latch/dynamic successor evaluator; repeated capture not justified'
    return dict(action=action,reason=reason,
        request_public_acquisition=action=='REQUEST_ONE_FRESH_EXISTING_PUBLIC_ACQUISITION',
        acquisition_call_budget_remaining=max_reobservations-reobservations_used,
        native_OWNER_safe_boundary_still_required=True,
        next_snapshot_may_update_measurements_not_claim_success=True,
        reobservation_cpu_wall_storage_and_sim_elapsed_cost='ACTUAL_CALLER_ACCOUNTING_REQUIRED_NOT_ESTIMATED',
        original_candidate_domain_and_native_gates_unchanged=True,
        model_prediction_available=False,optimized_candidate_id=None,
        native_action_or_observation_executed=False,execution_authorized=False,
        request_is_not_HOLD_or_NAV_or_retry_or_new_world=True)
