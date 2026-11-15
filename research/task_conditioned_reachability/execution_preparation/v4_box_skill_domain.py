"""User-requested box parameter lock to the currently selected native prototype.

Pure scene preparation only. Copies input, never writes a live/frozen scene or
changes goals, platform, walls, controller/Actor, contacts or safety thresholds.
This is a parameter-domain check, NOT proof all V4 native actions will succeed.
"""
from copy import deepcopy
from .v4_successor_choice import need
import math

BOX_PROTOTYPE=dict(size_m=[2.4,1.4,.2],mass_kg=.5,bottom_mu=.4,foot_top_mu=.8)
NATIVE_DRIVE_OFFSET_M=.11
MAX_NATIVE_DRIVE_M=.8


def normalize_boxes(scene):
    """Only normalize box physical attributes; never silently move a goal/platform."""
    out=deepcopy(scene);changes=[]
    need(len(out['objects'])==3 and len({o['public_ref']for o in out['objects']})==3,
         'Exactly the three task boxes, no synthetic step/oracle object')
    for box in out['objects']:
        delta={}
        for key,value in BOX_PROTOTYPE.items():
            if box.get(key)!=value:delta[key]=dict(before=deepcopy(box.get(key)),after=deepcopy(value))
            box[key]=deepcopy(value)
        changes.append(dict(public_ref=box['public_ref'],changed_physical_attributes=delta))
    check_boxes(out)
    return out,changes


def check_boxes(scene):
    need(scene['task']['source_surface_height_m']==0., 'Only qualified ground PUSH; no push on box top')
    rows=[]
    for box in scene['objects']:
        need(all(box.get(k)==v for k,v in BOX_PROTOTYPE.items()), 'Current selected light20cm native box prototype only')
        x,y=box['initial_xy_m'];gx,gy=box['required_goal_xy_m']
        need(all(type(v)in(int,float)and math.isfinite(v)for v in(x,y,gx,gy)), 'Finite declared positions only')
        need(gy==y and gx in box['allowed_placement_x_m'], 'Original +X same-lane absolute target; no arbitrary side push/yaw')
        strokes=[]
        for target in box['allowed_placement_x_m']:
            need(type(target)in(int,float)and math.isfinite(target), 'Finite declared placement candidate')
            displacement=target-x;stroke=displacement+NATIVE_DRIVE_OFFSET_M
            need(0<displacement and 0<stroke<=MAX_NATIVE_DRIVE_M, 'Original native stroke includes0.11 reference offset')
            strokes.append(dict(goal_world_x_m=target,declared_box_displacement_m=displacement,declared_native_drive_m=stroke))
        rows.append(dict(public_ref=box['public_ref'],size_m=deepcopy(box['size_m']),mass_kg=box['mass_kg'],
            bottom_mu=box['bottom_mu'],foot_top_mu=box['foot_top_mu'],candidates=strokes,
            required_displacement_m=gx-x,source_support_height_m=0.,nominal_ground_to_box_top_rise_m=.2,
            native_task_success_not_inferred=True))
    return rows
