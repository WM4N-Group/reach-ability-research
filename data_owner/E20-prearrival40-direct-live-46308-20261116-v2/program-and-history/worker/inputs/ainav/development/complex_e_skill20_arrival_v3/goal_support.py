"""Declared DYNAMIC box-top goal, never a fixed-surface or support witness.

Original static registry geometry verification is inherited unchanged. Only its
constructor schema is extended to name a required movable object as task goal.
The NAV registry is built later from a genuine current CLIMB source, not from
this nominal declaration. Goal contact forces/placement/CLIMB/stop stay real.
"""
from pathlib import Path
import hashlib
from v4_native_asset import require,load_scene

API_SHA='1d5baefee91a46d0b92f72663eff59b49eb7e7cc18754f95ef036458502566bf'
_CLASSES={}


def goal_object(scene):
    require(scene==load_scene() and scene['task']['goal_surface_ref']=='cuboid_c'
            and scene['task']['goal_surface_height_m']==.2,'Exact authorized20cm task, not old V4 or arbitrary goal')
    return next(o for o in scene['objects']if o['public_ref']=='cuboid_c')


def registry_type(api):
    p=Path(api.__file__)
    require(not p.is_symlink()and hashlib.sha256(p.read_bytes()).hexdigest()==API_SHA,'Exact original registry source')
    if api.SceneRegistry not in _CLASSES:
        class DynamicGoalRegistry(api.SceneRegistry):
            dynamic_goal_is_declaration_not_current_support=True
            def __init__(self,objects,surfaces,goal,*,retired_objects=()):
                objects=tuple(objects);surfaces=tuple(surfaces);scene=load_scene();obj=goal_object(scene)
                found=[o for o in objects if o.ref==obj['public_ref']and o.body_name==obj['body_name']and o.size_m==tuple(obj['size_m'])]
                require(len(found)==1 and goal.surface_ref==obj['public_ref']and goal.bounds_xy_m==tuple(scene['task']['goal_bounds_xy_m']),
                        'Only declared required C placement/top goal, not arbitrary movable-surface alias')
                x,y=obj['required_goal_xy_m'];length,width,_=obj['size_m'];g=goal.bounds_xy_m
                require(x-length/2<=g[0]<g[1]<=x+length/2 and y-width/2<=g[2]<g[3]<=y+width/2,'Declared goal inside required box footprint')
                # Run ALL original object/fixed-surface checks with an actual ground
                # declaration; then install the explicitly typed dynamic task goal.
                # No dynamic geom is inserted into the FIXED surfaces dictionary.
                super().__init__(objects,surfaces,api.GoalSpec('ground',goal.bounds_xy_m),retired_objects=retired_objects)
                self.goal=goal
            def with_retired(self,refs):
                return type(self)(self.objects.values(),self.surfaces.values(),self.goal,retired_objects=self.retired_objects|set(refs))
        _CLASSES[api.SceneRegistry]=DynamicGoalRegistry
    return _CLASSES[api.SceneRegistry]


def assert_declared_goal(registry,scene):
    obj=goal_object(scene)
    require(registry.goal.surface_ref==obj['public_ref'] and registry.goal.bounds_xy_m==tuple(scene['task']['goal_bounds_xy_m'])
            and registry.goal.surface_ref in registry.objects and registry.goal.surface_ref not in registry.surfaces
            and getattr(registry,'dynamic_goal_is_declaration_not_current_support',False) is True,
            'Dynamic task goal must NOT masquerade as a fixed declared support')
    return True


def actual_nav_goal_registry(original,surface,object_ref):
    from ainav.native import scene_registry as api
    scene=load_scene();assert_declared_goal(original,scene);obj=goal_object(scene)
    require(type(original)is registry_type(api)and object_ref==obj['public_ref']
            and surface.ref=='climb_nav_source__'+object_ref
            and surface.geom_name==obj['body_name']+'_geom'and surface.top_z_m==.2,
            'Only actual same-object CLIMB source supplies final NAV goal support')
    # Caller is the existing sealed LiveClimbNavSourceWitness, AFTER actual
    # original witness/contact/placement checks; this function cannot make one.
    return api.SceneRegistry(original.objects.values(),(*original.surfaces.values(),surface),
        api.GoalSpec(surface.ref,original.goal.bounds_xy_m),retired_objects=original.retired_objects)


def final_nav_source_ref(scene):
    return 'climb_nav_source__'+goal_object(scene)['public_ref']


def check_current_goal_geometry(scene,*,box_size,actual_geom_body_id,selected_body_id,geom_is_box,xyz,rotation):
    """Necessary measured geometry only; never provenance/contacts/task success."""
    import math
    obj=goal_object(scene)
    require(type(selected_body_id)is int and selected_body_id>0 and actual_geom_body_id==selected_body_id
            and geom_is_box is True,'Actual movable C geom owner, never fixed deck/ground')
    require(len(box_size)==3 and len(xyz)==3 and len(rotation)==3 and all(len(row)==3 for row in rotation),
            'Actual finite cuboid geometry shapes')
    require(all(type(v)in(int,float)and math.isfinite(v)for v in [*box_size,*xyz,*[v for row in rotation for v in row]]),
            'No UNKNOWN/NaN actual goal geometry')
    require(all(abs(a-b)<=1e-10 for a,b in zip(box_size,obj['size_m']))
            and all(abs(rotation[i][j]-(1. if i==j else 0.))<=.08 for i in range(3)for j in range(3)),
            'Original dimensions and original axis-aligned CLIMB domain')
    require(abs(xyz[2]+box_size[2]/2-.2)<=.01
            and math.hypot(xyz[0]-obj['required_goal_xy_m'][0],xyz[1]-obj['required_goal_xy_m'][1])<.02,
            'Original measured placement/top gate, not declared initial pose')
    return True
