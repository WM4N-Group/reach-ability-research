"""Minimal connector-reference probe DESIGN, not a qualified new native domain.

Standard Euclidean projection inside half the declared ORIGINAL entry radius.
No task/interaction goal change, execution-reference overwrite, dynamics model,
world/force/queue write, source patch or permission for arbitrary NAV poses.
"""
import math
from .successor_aware_choice import DecisionInput,InputSchema,number,need,text


def xy(value):
    need(type(value) in (tuple,list) and len(value)==2 and all(number(x) for x in value),'Finite declared XY in one frame')
    return tuple(value)


def propose(inputs,schema,*,base_position_field,entry_center_xy,original_radius_m,frame_id,base_position_frame_id,
            original_entry_spec_ref,original_judgment_status,nav_composite_terminal_error_bound_m=None,error_bound_source_ref=None):
    need(type(inputs) is DecisionInput and type(schema) is InputSchema,'Prospective permitted input, never audit branch state')
    schema.validate(inputs)
    need(inputs.audience=='REACH_NATIVE_LOCAL','Private original entry references are not implicitly VLM inputs')
    need(text(base_position_frame_id) and base_position_frame_id==frame_id,'Current base and original entry reference must have the same declared frame')
    center=xy(entry_center_xy)
    need(number(original_radius_m) and original_radius_m>0 and text(frame_id) and text(original_entry_spec_ref),'Owner source-bound original entry region/frame')
    need(original_judgment_status in ('PREPARE','READY','BLOCKED','UNKNOWN'),'Original judge status, not a new success predicate')
    result=dict(schema='reach-successor-connector-reference-probe-design-v1',
        role='PROPOSED_MINIMAL_EXTENSION_NOT_REGISTERED_OR_EXECUTABLE',
        original_entry_spec_ref=original_entry_spec_ref,frame_id=frame_id,original_center_xy=list(center),
        original_radius_m=original_radius_m,predeclared_interior_fraction=.5,
        common_interaction_entry_spec_and_task_goal_must_remain_unchanged=True,
        original_judge_and_native_post_NAV_recheck_required=True,
        no_source_or_execution_reference_table_modified=True,
        native_domain_or_tracking_support_safety_or_success_certified=False,
        execution_authorized=False,proposals=[])
    if original_judgment_status!='PREPARE':
        result['status']={'READY':'NO_CONNECTOR_REQUEST_NO_DISTINCT_CONTROL','BLOCKED':'ORIGINAL_REFUSAL_NOT_BYPASSED','UNKNOWN':'UNRESOLVED_ORIGINAL_JUDGMENT'}[original_judgment_status]
        return result
    fields={v.name:v for v in inputs.values};value=fields.get(base_position_field)
    if value is None or value.visibility=='UNKNOWN' or value.value is None:
        return dict(result,status='UNRESOLVED_CURRENT_BASE_POSITION')
    base=xy(value.value);delta=(base[0]-center[0],base[1]-center[1]);distance=math.hypot(*delta)
    need(math.isfinite(distance),'Finite relative geometry, no overflow')
    if nav_composite_terminal_error_bound_m is not None:
        need(number(nav_composite_terminal_error_bound_m) and nav_composite_terminal_error_bound_m>=0 and text(error_bound_source_ref),
             'A sourced bound at NAV COMPOSITE terminal, not historical error or gait-arrival tolerance')
        slack=original_radius_m-nav_composite_terminal_error_bound_m
        if slack<=0:return dict(result,status='NO_EXTRA_REFERENCE_CERTIFIED_BY_SUPPLIED_ERROR_BOUND',proposals=[dict(policy='original_catalogue_reference',preparation_xy=list(center))],global_task_infeasibility_inferred=False)
        radius=.5*slack
    else:radius=.5*original_radius_m
    scale=1. if distance<=radius else radius/distance
    projected=tuple(c+scale*d for c,d in zip(center,delta))
    candidates=[dict(policy='original_catalogue_reference',preparation_xy=list(center),original_region_displacement_m=0.)]
    if math.hypot(*(a-b for a,b in zip(projected,center)))>1e-9:
        candidates.append(dict(policy='nearest_point_in_half_radius_entry_ball',preparation_xy=list(projected),
                               original_region_displacement_m=math.hypot(*(a-b for a,b in zip(projected,center)))))
    return dict(result,status='TWO_GEOMETRIC_REFERENCES_OWNER_BINDING_REQUIRED' if len(candidates)==2 else 'GEOMETRIC_ALIAS_NO_NEW_COMPARISON',
                proposals=candidates,geometric_membership_only=True,
                NAV_composite_terminal_error_bound_m=nav_composite_terminal_error_bound_m,error_bound_source_ref=error_bound_source_ref,
                necessary_XY_margin_under_supplied_bound_verified=(None if nav_composite_terminal_error_bound_m is None else
                    all(c['original_region_displacement_m']+nav_composite_terminal_error_bound_m<original_radius_m for c in candidates)),
                raw_reference_distance_is_not_actual_NAV_or_successor_cost=True)
