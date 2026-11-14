"""Necessary public-geometry checks for HYPOTHETICAL plans, not a world model.

No MuJoCo, learned dynamics, hidden material truth, task-world writes, robot
trajectory prediction or action selection. A declared PUSH successor is treated
as a conditional placement ASSUMPTION solely while checking a proposed plan;
this is never an observed pose or an executor admission certificate.
"""
from copy import deepcopy
import math

EPS=1e-7


def interval_gap(a,b):return max(0.,a[0]-b[1],b[0]-a[1])
def horizontal_gap(a,b):return [interval_gap(a[:2],b[:2]),interval_gap(a[2:],b[2:])]
def adjacent(a,b):return max(horizontal_gap(a,b))<=EPS

def contains(rect,xy):return rect[0]-EPS<=xy[0]<=rect[1]+EPS and rect[2]-EPS<=xy[1]<=rect[3]+EPS


def patches(public):
    result={}
    for s in public['surfaces']:
        result[s['id']]=dict(id=s['id'],kind='fixed_surface',bounds_xy_m=list(s['bounds_xy_m']),top_z_m=s['top_z_m'])
    for o in public['objects']:
        x,y,z=o['initial_center_xyz_m'];L,W,H=o['size_m']
        result[o['id']]=dict(id=o['id'],kind='initial_cuboid_top',bounds_xy_m=[x-L/2,x+L/2,y-W/2,y+W/2],top_z_m=z+H/2,
            bottom_z_m=o['initial_support_height_m'],center_xy_m=[x,y],size_m=list(o['size_m']))
    if len(result)!=len(public['surfaces'])+len(public['objects']):raise ValueError('Unique public patch identities required')
    for p in result.values():
        r=p['bounds_xy_m']
        if len(r)!=4 or not all(math.isfinite(x) for x in (*r,p['top_z_m'])) or not r[0]<r[1] or not r[2]<r[3]:raise ValueError('Finite public support rectangles required')
    return result


def connected_same_height(ps,start):
    reached={start};pending=[start]
    while pending:
        a=ps[pending.pop()]
        for key,b in ps.items():
            if key not in reached and abs(a['top_z_m']-b['top_z_m'])<=EPS and adjacent(a['bounds_xy_m'],b['bounds_xy_m']):
                reached.add(key);pending.append(key)
    return reached


def geometry_facts(public):
    ps=patches(public);pairs=[];entries=[]
    for key,a in ps.items():
        if a['kind']=='initial_cuboid_top':
            entries.append(dict(target_ref=key,front_side_NAV_viewpoint=[a['bounds_xy_m'][0]-.58,a['center_xy_m'][1],a['bottom_z_m']],
                source='original public reference template; not native entry admission'))
        for other,b in ps.items():
            if key>=other:continue
            gap=horizontal_gap(a['bounds_xy_m'],b['bounds_xy_m'])
            pairs.append(dict(a=key,b=other,horizontal_gap_xy_m=gap,height_b_minus_a_m=b['top_z_m']-a['top_z_m'],
                footprints_touch_or_overlap=max(gap)<=EPS,
                same_height_continuous_possible=abs(a['top_z_m']-b['top_z_m'])<=EPS and max(gap)<=EPS))
    return dict(schema='public-initial-geometric-relations-only-v1',patches=list(ps.values()),pairwise_relations=pairs,front_side_viewpoints=entries,
        rules=['Equal top height does NOT imply connection. A positive horizontal gap is not traversable by the original NAV.',
               'CLIMB needs .20m relative rise AND touching/overlapping source/target footprints, not a jump over a positive gap.',
               'NAV at a cuboid center on its BOTTOM layer intersects the cuboid; approach from its front side instead.',
               'Only an EXPLICIT successful PUSH in the proposed ancestor trace may change that cuboid placement. Recompute geometry after it; this remains conditional, not observed.',
               'These are necessary geometric conditions, not proof of actuator, entry, stability, contact or task success.'],
        dynamic_prediction=False,native_admission=False,preferred_object_or_skill_order=None)


def check_plan(public,steps,*,initial_support):
    ps=deepcopy(patches(public));current=initial_support;events=[];assumptions=[]
    if current not in ps:raise ValueError('Declared initial support required')
    def fail(i,reason,details):
        return dict(necessary_geometry_pass=False,first_invalid_index=i,reason=reason,details=details,checked_steps=events,
            conditional_PUSH_assumptions=assumptions,physical_feasibility_proven=False,native_admission=False,world_state_written=False)
    for i,step in enumerate(steps):
        skill=step['skill'];target=step['target_ref'];params=step['parameters']
        if target=='declared_final_goal':target=public['goal']['surface']
        if target not in ps:return fail(i,'undeclared_target',dict(target=target))
        source=ps[current];dest=ps[target];source_h=source['top_z_m']
        if skill=='NAV':
            xy=[params['goal_world_x_m'],params['goal_world_y_m']];h=params['surface_height_m']
            if abs(h-source_h)>EPS:return fail(i,'NAV_cannot_change_support_height',dict(source=current,source_height=source_h,requested_height=h))
            reachable=connected_same_height(ps,current)
            landing=[k for k in sorted(reachable) if contains(ps[k]['bounds_xy_m'],xy)]
            if not landing:return fail(i,'NAV_destination_not_on_connected_same_height_support',dict(source=current,goal_xy=xy,connected_supports=sorted(reachable)))
            blocking=[k for k,b in ps.items() if b['kind']=='initial_cuboid_top' and b['bottom_z_m']-EPS<=h<b['top_z_m']-EPS and contains(b['bounds_xy_m'],xy)]
            if blocking:return fail(i,'NAV_goal_inside_cuboid_at_lower_height',dict(goal_xy=xy,blocking_cuboids=blocking))
            # On overlapping rectangles, retain the declared target when valid.
            current=target if target in landing else landing[0]
        elif skill=='CLIMB':
            rise=dest['top_z_m']-source_h
            if abs(params['surface_height_m']-dest['top_z_m'])>EPS:return fail(i,'CLIMB_wrong_declared_destination_height',dict(target=target))
            if abs(rise-.2)>.01+EPS:return fail(i,'CLIMB_relative_rise_not_original_20cm',dict(source=current,target=target,rise_m=rise))
            reachable=connected_same_height(ps,current)
            sources=[k for k in reachable if adjacent(ps[k]['bounds_xy_m'],dest['bounds_xy_m'])]
            if not sources:return fail(i,'CLIMB_requires_gap_jump_not_original_skill',dict(source=current,target=target,horizontal_gap_xy_m=horizontal_gap(source['bounds_xy_m'],dest['bounds_xy_m'])))
            current=target
        elif skill=='PUSH':
            if dest['kind']!='initial_cuboid_top':return fail(i,'PUSH_target_not_cuboid',dict(target=target))
            if abs(params['surface_height_m']-dest['bottom_z_m'])>EPS or abs(source_h-dest['bottom_z_m'])>EPS:return fail(i,'PUSH_wrong_source_support_layer',dict(source=current,target=target))
            x,y=params['goal_world_x_m'],params['goal_world_y_m'];oldx,oldy=dest['center_xy_m']
            if x<oldx-EPS or abs(y-oldy)>EPS:return fail(i,'PUSH_not_original_positive_X_motion',dict(target=target,declared_start=[oldx,oldy],requested=[x,y]))
            L,W,H=dest['size_m'];dest['bounds_xy_m']=[x-L/2,x+L/2,y-W/2,y+W/2];dest['center_xy_m']=[x,y]
            assumptions.append(dict(step_index=i,target_ref=target,assumed_goal_xy=[x,y],assumption='IF this explicit PUSH succeeds; unobserved and not physically predicted'))
        elif skill=='HOLD':
            if abs(params['surface_height_m']-source_h)>EPS:return fail(i,'HOLD_cannot_change_support_height',dict(source=current))
        else:return fail(i,'unsupported_semantic_skill',dict(skill=skill))
        events.append(dict(step_index=i,skill=skill,target_ref=target,conditional_support_after=current))
    return dict(necessary_geometry_pass=True,first_invalid_index=None,reason=None,checked_steps=events,
        conditional_PUSH_assumptions=assumptions,physical_feasibility_proven=False,native_admission=False,world_state_written=False)
