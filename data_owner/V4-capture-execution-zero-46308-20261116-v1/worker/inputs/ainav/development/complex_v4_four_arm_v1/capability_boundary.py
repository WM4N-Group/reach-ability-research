"""Pure exact-source capability checks, not native stepping or an admission gate."""
import ast,hashlib,math
from pathlib import Path
from types import SimpleNamespace

FROZEN_TERRAIN_SHA='1d5baefee91a46d0b92f72663eff59b49eb7e7cc18754f95ef036458502566bf'
def selected_climb_rise_audit(scene,*,common_source_root):
    """Execute ONLY the existing pure climb_geometry predicate on declarations.

    surface_geometry is supplied from the declared scene to this isolated
    predicate. This is NOT a sensor/GT substitute for a real native query.
    """
    path=Path(common_source_root)/'ainav/native/scene_registry.py';raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=FROZEN_TERRAIN_SHA:raise ValueError('Exact selected original terrain source required')
    tree=ast.parse(raw);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='RegisteredTerrain');fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='climb_geometry')
    namespace={'math':math};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path)+':pure-climb_geometry-only','exec'),namespace)
    c=next(o for o in scene['objects']if o['public_ref']=='cuboid_c');deck=scene['platforms'][0];legs=[]
    for source_ref,source_z,target_ref,target_z in [('ground',0.,'cuboid_c',c['size_m'][2]),('cuboid_c',c['size_m'][2],deck['name'],deck['top_z_m'])]:
        holder=SimpleNamespace(surface_geometry=lambda sim,ref,z=target_z:dict(top=z))
        try:namespace['climb_geometry'](holder,None,target_ref,source_surface_height_m=source_z);accepted=True;error=None
        except ValueError as e:accepted=False;error=str(e)
        legs.append(dict(source_ref=source_ref,source_z_m=source_z,target_ref=target_ref,target_z_m=target_z,declared_rise_m=target_z-source_z,original_pure_height_predicate_accepts=accepted,original_rejection=error,not_a_dynamic_or_target_binding_test=True))
    return dict(exact_selected_terrain_source_sha256=hashlib.sha256(raw).hexdigest(),legs=legs,
        planned_two_leg_chain_in_selected_height_domain=all(l['original_pure_height_predicate_accepts']for l in legs),
        static_goal_deck_not_a_registered_movable_object=deck['name']not in {o['public_ref']for o in scene['objects']},
        original_registered_CLIMB_bind_requires_current_RGBD_registered_object=True,
        no_native_qualification_or_physics=True)

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
