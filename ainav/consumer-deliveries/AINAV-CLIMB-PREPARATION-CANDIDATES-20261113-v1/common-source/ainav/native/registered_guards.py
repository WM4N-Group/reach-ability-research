"""Registry-based contact policy and target-region gate; no action routing.

Same >1N object-contact and >3N final support thresholds. A named/visible object
is NEVER automatically a legal support. The caller must provide actual native
PUSH ownership or an entered CLIMB surface. Native selected-target guards remain
mandatory; this does not replace fall/effort/clearance/FIFO checks.
"""
import math


def contact_authorized(*,object_ref,registered_objects,retired_objects,robot_is_descendant,
                       force_norm_N,robot_body_forbidden,selected_push_ref=None,entered_climb_refs=()):
    if not math.isfinite(force_norm_N) or force_norm_N<0:raise ValueError('Finite actual contact norm required')
    if object_ref not in registered_objects:raise ValueError('Unregistered object cannot get contact authority')
    if selected_push_ref is not None and (selected_push_ref not in registered_objects or selected_push_ref in retired_objects):
        raise ValueError('Actual registered non-retired PUSH owner required')
    if set(entered_climb_refs)-set(registered_objects):raise ValueError('Entered object surfaces must be registered')
    if not robot_is_descendant or force_norm_N<=1.:return True
    if object_ref==selected_push_ref:return True  # Selected native hand/non-hand guards still run separately.
    return object_ref in entered_climb_refs and not robot_body_forbidden


def check_object_contacts(runtime,registry,*,selected_push_ref=None,entered_climb_refs=()):
    import numpy as np
    import mujoco
    p=runtime.sim;objects={p.model.body(o.body_name).id:o.ref for o in registry.objects.values()}
    forbidden=set(runtime.c.forbidden);observed=0
    for i,contact in enumerate(p.data.contact):
        a,b=map(int,p.model.geom_bodyid[[contact.geom1,contact.geom2]])
        obj=a if a in objects else b if b in objects else None
        if obj is None:continue
        robot=b if obj==a else a;parent=robot
        while parent and parent!=p.base_id:parent=int(p.model.body_parentid[parent])
        force=np.zeros(6);mujoco.mj_contactForce(p.model,p.data,i,force);norm=float(np.linalg.norm(force[:3]))
        observed+=1
        if not contact_authorized(object_ref=objects[obj],registered_objects=set(registry.objects),retired_objects=registry.retired_objects,
            robot_is_descendant=parent==p.base_id,force_norm_N=norm,robot_body_forbidden=robot in forbidden,
            selected_push_ref=selected_push_ref,entered_climb_refs=entered_climb_refs):
            raise RuntimeError('registered_unselected_or_native_forbidden_contact:'+objects[obj]+':'+p.model.body(robot).name)
    return dict(object_contact_records=observed,original_force_threshold_N=1.,all_registered_objects_guarded=True,
        selected_target_native_guards_still_required=True,model_input=False)


def goal_region_gate(registry,*,feet_world_m,foot_vertical_load_N,base_linear_speed_m_s,
                     base_angular_speed_rad_s,tilt_rad,require_stop):
    """Geometric/force endpoint, independent of bridge-order and dwell witnesses."""
    if len(feet_world_m)!=4 or any(len(f)!=3 for f in feet_world_m) or len(foot_vertical_load_N)!=4:
        raise ValueError('Four actual feet/loads required')
    scalars=[v for f in feet_world_m for v in f]+list(foot_vertical_load_N)+[base_linear_speed_m_s,base_angular_speed_rad_s,tilt_rad]
    if not all(math.isfinite(v) for v in scalars):raise ValueError('Finite actual goal measurements required')
    x0,x1,y0,y1=registry.goal.bounds_xy_m;z=registry.surfaces[registry.goal.surface_ref].top_z_m+.022
    feet_inside=all(x0<f[0]<x1 and y0<f[1]<y1 for f in feet_world_m)
    loads=all(v>3. for v in foot_vertical_load_N)
    height=all(abs(f[2]-z)<.04 for f in feet_world_m)
    stable=0<=base_linear_speed_m_s<.03 and 0<=base_angular_speed_rad_s<.12 and 0<=tilt_rad<.03
    return dict(passed=feet_inside and loads and height and (stable or not require_stop),
        all_four_feet_in_goal=feet_inside,all_four_feet_loaded=loads,correct_support_height=height,
        stopped=stable,goal_surface_height_m=z-.022,model_input=False,
        dwell_and_route_witness_still_required=True)
