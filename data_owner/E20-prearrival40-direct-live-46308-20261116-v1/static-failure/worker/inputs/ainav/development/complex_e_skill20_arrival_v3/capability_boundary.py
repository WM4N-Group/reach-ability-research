"""Necessary scalar elevated stop gate; actual contacts/owners are separate."""
import math

def elevated_stop_sample_only(scene,sample):
    """Necessary private sample predicate, NEVER task-complete/native authority.

    The future actual reader must prove contact provenance/CLIMB receipts,
    same-world owners and three immutable placements separately. A positive
    dict/fixture here is not a runtime witness, dwell or complete mission.
    """
    cfg=scene['private_terminal_acceptance'];goal=scene['task'];feet=sample['feet_world_m'];loads=sample['foot_normal_N'];speeds=sample['foot_speed_m_s']
    if len(feet)!=4 or any(len(f)!=3 for f in feet)or len(loads)!=4 or len(speeds)!=4:return False
    if sample.get('foot_support_refs')!=[goal['goal_surface_ref']]*4:return False
    values=[*loads,*speeds,sample['base_linear_speed_m_s'],sample['base_angular_speed_rad_s'],sample['tilt_rad'],*[v for f in feet for v in f]]
    if any(type(v)not in(int,float)or not math.isfinite(v)for v in values):return False
    x0,x1,y0,y1=goal['goal_bounds_xy_m'];z=goal['goal_surface_height_m']
    return (all(x0<f[0]<x1 and y0<f[1]<y1 and abs(f[2]-z-.022)<.04 for f in feet)
        and min(loads)>=cfg['foot_normal_min_N']and all(0<=v<cfg['foot_speed_max_m_s']for v in speeds)
        and 0<=sample['base_linear_speed_m_s']<cfg['base_linear_speed_max_m_s']
        and 0<=sample['base_angular_speed_rad_s']<cfg['base_angular_speed_max_rad_s']and 0<=sample['tilt_rad']<cfg['tilt_max_rad'])
