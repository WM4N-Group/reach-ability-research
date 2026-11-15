"""Nominal scene-geometry existence check; PRIVATE qualification, not a policy.

Enumerates finite monotone placements and visibility paths from public geometry.
No oracle sequence/relations are added to public_task or model inputs. This is
not MuJoCo collision, dynamic feasibility, a planner comparison or success.
"""
from collections import deque
import json,math
from complex_scene import load_scene,finite_placements,validate

def rectangle(o,x=None):
    L,W,_=o['size_m'];a,b=o['initial_xy_m'];a=a if x is None else x
    return (a-L/2,a+L/2,b-W/2,b+W/2)

def overlaps(a,b):return a[0]<b[1]and b[0]<a[1]and a[2]<b[3]and b[2]<a[3]

def expanded(r,margin):return(r[0]-margin,r[1]+margin,r[2]-margin,r[3]+margin)

def segment_clear(a,b,obstacles,margin):
    # Exact closed segment vs conservative expanded axis-aligned rectangles.
    for rect in obstacles:
        lo,hi=0.,1.;r=expanded(rect,margin)
        for v,d,mn,mx in[(a[0],b[0]-a[0],r[0],r[1]),(a[1],b[1]-a[1],r[2],r[3])]:
            if abs(d)<1e-12:
                if mn<=v<=mx:pass
                else:lo,hi=1.,0.;break
            else:
                t0,t1=sorted(((mn-v)/d,(mx-v)/d));lo=max(lo,t0);hi=min(hi,t1)
        if lo<=hi:return False
    return True

def path_between(s,positions,start,goal):
    margin=s['static_qualification_only']['conservative_planar_robot_radius_m']+s['static_qualification_only']['body_clearance_m']
    obstacles=[rectangle(o,positions[o['public_ref']])for o in s['objects']]+[w['bounds_xy_m']for w in s['walls']]
    points=[tuple(start),tuple(goal),*map(tuple,s['public_waypoints_xy_m'])]
    q=deque([0]);parent={0:None}
    while q:
        a=q.popleft()
        if a==1:
            route=[]
            while a is not None:route.append(list(points[a]));a=parent[a]
            return route[::-1]
        for b in range(len(points)):
            if b not in parent and segment_clear(points[a],points[b],obstacles,margin):parent[b]=a;q.append(b)
    return None

def evaluate(s=None):
    s=load_scene()if s is None else validate(s);objects={o['public_ref']:o for o in s['objects']};initial={k:o['initial_xy_m'][0]for k,o in objects.items()};goals={k:o['required_goal_xy_m'][0]for k,o in objects.items()};checks=[]
    def actions(pos,robot):
        for c in finite_placements(s):
            k=c['public_ref'];o=objects[k];x=c['goal_world_x_m'];delta=x-pos[k]
            if not 0<delta or delta+.11>.8:continue
            y=o['initial_xy_m'][1];approach=[pos[k]-o['size_m'][0]/2-.58,y]
            path=path_between(s,pos,robot,approach)
            # Swept movable box vs every other object/wall, no guessed side push.
            sweep=(pos[k]-o['size_m'][0]/2,x+o['size_m'][0]/2,y-o['size_m'][1]/2,y+o['size_m'][1]/2)
            blocked=any(overlaps(sweep,rectangle(other,pos[j]))for j,other in objects.items()if j!=k)or any(overlaps(sweep,w['bounds_xy_m'])for w in s['walls'])
            if path is not None and not blocked:
                p=dict(pos);p[k]=x;end=[x-o['size_m'][0]/2-.58,y]
                yield p,end,dict(public_ref=k,goal_xy=[x,y],approach_xy=approach,nominal_navigation_path=path,source_surface_m=0.)
    start=tuple(initial[k]for k in sorted(initial));q=deque([(initial,s['robot_initial_xy_m'],[])]);seen=set();witness=None
    while q:
        pos,robot,hist=q.popleft();key=(tuple(pos[k]for k in sorted(pos)),tuple(robot))
        if key in seen:continue
        seen.add(key)
        if pos==goals:
            finish=[sum(s['task']['goal_bounds_xy_m'][:2])/2,0.];path=path_between(s,pos,robot,finish)
            if path is not None:witness=dict(placements=hist,terminal_nominal_path=path);break
        for p,r,a in actions(pos,robot):q.append((p,r,hist+[a]))
    assert witness is not None,'No common nominal existence witness; do not dispatch A/B'
    # Inspect the ACTUAL geometry consequence of doing A's required placement first.
    after=dict(initial,cuboid_a=goals['cuboid_a']);later=list(actions(after,[goals['cuboid_a']-objects['cuboid_a']['size_m'][0]/2-.58,0.]))
    a_first_blocks_B=not any(a['public_ref']=='cuboid_b'for _,_,a in later)
    assert a_first_blocks_B,'Chosen geometry does not exhibit the declared manipulation-space conflict'
    return dict(role='PRIVATE_NOMINAL_EXISTENCE_QUALIFICATION_NOT_ONLINE_POLICY_OR_MUJOCO_SUCCESS',native_runtime_constructed=False,task_goals=goals,static_existence_witness=witness,states_visited=len(seen),A_required_placement_first_blocks_B_nominal_approach=a_first_blocks_B,body_margin_is_conservative_assumption_not_verified_bound=True,physical_dynamic_feasible_plan_verified=False,policy_A_or_B_run=False,physical_dispatches=0,videos=0)

if __name__=='__main__':print(json.dumps(evaluate(),ensure_ascii=False,indent=2))
