"""T-COMPLEX-01 physical constructor + finite task declarations, no policies.

Only Data may call construct_into_native_spec on a fresh original SDK spec.
There is no Runtime/Actor import, world creation, stepping, private planner state,
old-world resume, or admission grant here. Full native integration is separate.
"""
from pathlib import Path
from copy import deepcopy
import hashlib,json,math
SCENE=Path(__file__).with_name('scene.json')

def need(ok,message):
    if not ok:raise ValueError(message)

def load_scene(path=SCENE):
    v=json.loads(Path(path).read_bytes());validate(v);return v

def validate(s):
    need(s['schema']=='AINav-T-COMPLEX-01-native-scene-v1','Exact scene schema')
    need(s['seed']==4301 and s['robot_initial_yaw_rad']==0.,'Original registered initialization and world +X only')
    need(len(s['objects'])in(2,3) and len({o['public_ref']for o in s['objects']})==len(s['objects']),'Two/three distinct original-prototype task objects')
    need(len({o['body_name']for o in s['objects']})==len(s['objects']),'No body aliases')
    for o in s['objects']:
        need(o['size_m']==[2.4,1.4,.2] and o['mass_kg']==.5 and o['bottom_mu']==.4 and o['foot_top_mu']==.8,'Original full4 B prototype, not heavy/overheight trap')
        x,y=o['initial_xy_m'];need(all(math.isfinite(v)for v in(x,y,*o['allowed_placement_x_m'])),'Finite source floats')
        need(o['required_goal_xy_m'][1]==y and o['required_goal_xy_m'][0]in o['allowed_placement_x_m'],'Same-lane +X targets, not side push')
        need(all(0.<g+.11-x<=.8 for g in o['allowed_placement_x_m']),'Original declared drive stroke including .11m offset')
    need(s['task']['minimum_distinct_reconstructions']==len(s['objects']) and set(s['task']['required_final_placements'])=={o['public_ref']for o in s['objects']},'Both environment reconstructions actually required')
    return s

def public_task(s):
    validate(s)
    return dict(scene_id=s['scene_id'],floor=deepcopy(s['floor']),walls=deepcopy(s['walls']),
        objects=[{k:deepcopy(o[k])for k in('public_ref','size_m','initial_xy_m','allowed_placement_x_m','required_goal_xy_m')}for o in s['objects']],
        task=deepcopy(s['task']),public_waypoints_xy_m=deepcopy(s['public_waypoints_xy_m']),
        current_object_pose_is_not_declared_initial_pose=True,object_association_requires_original_current_query=True,
        static_geometry_not_dynamic_success_probability=True,correct_order_or_route_not_provided=True)

def finite_placements(s):
    """Common finite declared goals; NOT currently admitted options or a route."""
    validate(s);return tuple(dict(public_ref=o['public_ref'],skill='PUSH',goal_world_x_m=x,goal_world_y_m=o['initial_xy_m'][1],surface_height_m=0.,
        native_direction='WORLD_PLUS_X_ONLY',original_goal_and_entry_and_stop_guards_required=True,actual_native_admission=False)
        for o in s['objects']for x in o['allowed_placement_x_m'])

def registry(s,*,source_root):
    """Use existing source registry, not legacy full4 C-on-.4 assumptions."""
    import importlib,sys
    root=Path(source_root).resolve(strict=True);sys.path.insert(0,str(root))
    api=importlib.import_module('ainav.native.scene_registry')
    need(Path(api.__file__).resolve()==root/'ainav/native/scene_registry.py','Exact same-source registry')
    g=s['task']['goal_bounds_xy_m'];floor=s['floor']
    return api.SceneRegistry([api.ObjectSpec(o['public_ref'],o['body_name'],tuple(o['size_m']),'ground')for o in s['objects']],
        [api.SurfaceSpec('ground','ground',tuple(floor['native_ground_bounds_xy_m']),0.)],api.GoalSpec('ground',tuple(g)))

def construct_into_native_spec(sim,*,scene=None,main_steps):
    """Actual MjSpec geometry edits ONLY before first task step (owner calls).

    Uses original SDK robot/actuators unmodified. Original non-task push_box is
    parked OUTSIDE the arena at construction, never teleported after a step.
    Caller must compare robot/engine signature, exact compiled model, resource
    lease and own-zero; this function grants none of those qualifications.
    """
    s=load_scene()if scene is None else validate(scene)
    need(main_steps==0 and float(sim.data.time)==0. and not sim.queue,'Fresh actual simulator clock/FIFO only; never hot change a physical world')
    spec=sim.spec;native_model=sim.model
    import mujoco
    names={b.name for b in spec.bodies}
    need(not any(o['body_name']in names for o in s['objects']),'No repeated asset install')
    ground=spec.geom('ground');old=spec.body('push_box')
    need(ground.name=='ground'and old.name=='push_box','Original native SDK spec identity')
    old.pos=[-8.,-8.,.1]  # Construction-only out-of-task original object.
    x0,x1,y0,y1=s['floor']['native_ground_bounds_xy_m'];h=s['floor']['thickness_m'];ground.type=mujoco.mjtGeom.mjGEOM_BOX;ground.pos=[(x0+x1)/2,(y0+y1)/2,-h/2];ground.size=[(x1-x0)/2,(y1-y0)/2,h/2];ground.friction=[.7,0.,0.];ground.group=1
    foot_ids={int(native_model.body(n+'_foot').id)for n in('FR','FL','RR','RL')}
    need(len(foot_ids)==4,'Four original native foot bodies, no naming heuristic')
    foot_names={native_model.geom(i).name for i in range(native_model.ngeom)if int(native_model.geom_bodyid[i])in foot_ids}
    need(foot_names and all(foot_names),'Exact original compiled foot geom identities required')
    for w in s['walls']:
        a,b,c,d=w['bounds_xy_m'];z=w['height_m'];spec.worldbody.add_geom(name=w['name'],type=mujoco.mjtGeom.mjGEOM_BOX,pos=[(a+b)/2,(c+d)/2,z/2],size=[(b-a)/2,(d-c)/2,z/2],contype=2,conaffinity=3,friction=[.7,0.,0.],group=1,rgba=[.35,.4,.45,1.])
    mappings={}
    for o in s['objects']:
        L,W,H=o['size_m'];x,y=o['initial_xy_m'];body=spec.worldbody.add_body(name=o['body_name'],pos=[x,y,H/2]);body.add_freejoint(name=o['body_name']+'_free')
        geom=body.add_geom(name=o['body_name']+'_geom',type=mujoco.mjtGeom.mjGEOM_BOX,size=[L/2,W/2,H/2],mass=o['mass_kg'],contype=2,conaffinity=3,condim=3,priority=2,friction=[o['bottom_mu'],0.,0.],group=1,rgba=[.55,.36,.19,1.])
        for other in list(spec.geoms):
            if other.name==geom.name or not(other.contype or other.conaffinity):continue
            mu=o['foot_top_mu']if other.name in foot_names else o['bottom_mu'];pair=spec.add_pair(geomname1=geom.name,geomname2=other.name,condim=3);pair.friction=[mu,mu,0.,0.,0.]
        mappings[o['public_ref']]=dict(body=o['body_name'],geom=o['body_name']+'_geom')
    return dict(bindings=mappings,construction_only=True,robot_or_actuators_modified=False,world_steps_issued=0,actual_compilation_or_dynamic_admission=False)

def placement_contract(s,candidate,*,source_root):
    """Existing PlacementContract for one exact finite goal; no controller call.

    Multiple targets require the common factory's per-query contract lookup to
    bind the chosen goal, NOT its current object-only single-contract lookup.
    """
    need(candidate in finite_placements(s),'Exact common finite public candidate')
    import sys,importlib
    root=Path(source_root).resolve(strict=True);sys.path.insert(0,str(root));api=importlib.import_module('ainav.native.placement_contract')
    need(Path(api.__file__).resolve()==root/'ainav/native/placement_contract.py','Exact original placement contract')
    o=next(o for o in s['objects']if o['public_ref']==candidate['public_ref']);goal=(candidate['goal_world_x_m'],candidate['goal_world_y_m'])
    return api.PlacementContract(target_ref=o['public_ref'],public_goal_xy_m=goal,docking_plane_x_m=goal[0]+o['size_m'][0]/2,box_size_m=tuple(o['size_m']),source_surface_height_m=0.,native_stop_distance_m=.11,mode='declared_native_stop_offset')
