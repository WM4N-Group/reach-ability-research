"""T-COMPLEX-01 adapter consuming AINav PUBLIC_TASK / FINITE_PLACEMENTS only.

No scene.json, private qualification/existence route, native engine or dataset.
States are NOMINAL reference/placement forecasts, not observed physical poses.
The future owner adapter must execute exact registered NAV/PUSH/terminal-stop
mappings and update from original verified receipts + fresh public observation;
it must NEVER advance the physical/root state merely because this model did.
"""
from copy import deepcopy
from dataclasses import dataclass
import heapq
import math
from .finite_multistep_planner import Arc, nominal_connection


@dataclass(frozen=True)
class NominalState:
    object_x_m: tuple
    robot_reference_xy_m: tuple


@dataclass(frozen=True)
class Decision:
    kind: str
    public_ref: object
    goal_xy_m: tuple
    nominal_NAV_route_xy_m: tuple
    requires_original_placement_or_terminal_stop: bool = True
    native_mapping_verified: bool = False


class PublicSceneModel:
    def __init__(self, public_task, finite_placements, *, declared_initial_reference_xy_m,
                 nominal_envelope_radius_m=.45, approach_setback_m=.58):
        self.task=deepcopy(public_task);self.placements=deepcopy(finite_placements)
        self.objects=tuple(self.task['objects']);self.refs=tuple(o['public_ref'] for o in self.objects)
        if len(set(self.refs))!=len(self.refs) or len(self.refs)<2:raise ValueError('Distinct public task objects')
        if self.task['task']['source_surface_height_m']!=0.:raise ValueError('Ground source only, no unqualified platform PUSH')
        if set(self.task['task']['required_final_placements'])!=set(self.refs):raise ValueError('Same complete reconstruction task')
        for o in self.objects:
            if o['required_goal_xy_m'][0] not in o['allowed_placement_x_m'] or o['required_goal_xy_m'][1]!=o['initial_xy_m'][1]:
                raise ValueError('Declared monotone same-lane goal, no side push/pull')
        expected=[(o['public_ref'],x,o['initial_xy_m'][1]) for o in self.objects for x in o['allowed_placement_x_m']]
        actual=[(c['public_ref'],c['goal_world_x_m'],c['goal_world_y_m']) for c in self.placements]
        if expected!=actual or any(c['skill']!='PUSH' or c['native_direction']!='WORLD_PLUS_X_ONLY' or
                                 c['surface_height_m']!=0. or c['actual_native_admission'] is not False for c in self.placements):
            raise ValueError('Exact original finite candidate order and native scope')
        self.radius=float(nominal_envelope_radius_m);self.setback=float(approach_setback_m)
        if not math.isfinite(self.radius) or self.radius<=0. or self.setback!=.58:
            raise ValueError('Explicit shared NOMINAL envelope and original registered setback')
        if declared_initial_reference_xy_m is None or len(declared_initial_reference_xy_m)!=2 or not all(
                type(v) in (int,float) and math.isfinite(v) for v in declared_initial_reference_xy_m):
            raise ValueError('Explicit common declared initial reference, not private actual base XY')
        self.initial=NominalState(tuple(o['initial_xy_m'][0] for o in self.objects),tuple(declared_initial_reference_xy_m))
        g=self.task['task']['goal_bounds_xy_m'];self.goal_xy=((g[0]+g[1])/2,(g[2]+g[3])/2)
        self.goal_x=tuple(o['required_goal_xy_m'][0] for o in self.objects)
        self.walls=tuple((w['bounds_xy_m'][0],w['bounds_xy_m'][2],w['bounds_xy_m'][1],w['bounds_xy_m'][3]) for w in self.task['walls'])
        self.points=tuple(tuple(p) for p in self.task['public_waypoints_xy_m'])

    def key(self,state):
        return (state.object_x_m,state.robot_reference_xy_m)

    def is_goal(self,state):
        return state.object_x_m==self.goal_x and state.robot_reference_xy_m==self.goal_xy

    def rectangle(self,index,x):
        o=self.objects[index];L,W,_=o['size_m'];y=o['initial_xy_m'][1]
        return (x-L/2,y-W/2,x+L/2,y+W/2)

    def obstacles(self,state,exclude=None):
        return self.walls+tuple(self.rectangle(i,x) for i,x in enumerate(state.object_x_m) if i!=exclude)

    def route(self,state,start,goal):
        """Common shortest nominal visibility route; never a stored correct path."""
        points=(tuple(start),tuple(goal))+self.points;obstacles=self.obstacles(state)
        heap=[(0.,0,())];best={0:0.}
        while heap:
            cost,a,path=heapq.heappop(heap)
            if cost!=best.get(a):continue
            if a==1:return cost,tuple(points[i] for i in path+(a,))
            for b in range(len(points)):
                if b==a:continue
                g=nominal_connection(points[a],points[b],obstacle_boxes_xyxy=obstacles,footprint_radius_m=self.radius)
                if g['static_status']!='POSSIBLE':continue
                new=cost+g['nominal_robot_path_m']
                if new<best.get(b,math.inf):
                    best[b]=new;heapq.heappush(heap,(new,b,path+(a,)))
        return None

    def arcs(self,state):
        """Finite object/goal decisions with identical geometry/cost for A/B.

        A decision bundles its necessary nominal NAV route + original PUSH, or
        a final NAV + original stop. Search depth is in these bundles, NOT a
        claim about native action counts or three meaningful observed decisions.
        """
        for candidate in self.placements:
            i=self.refs.index(candidate['public_ref']);o=self.objects[i];current=state.object_x_m[i]
            target=candidate['goal_world_x_m'];delta=target-current
            if delta<=0. or delta+.11>.8:continue
            y=o['initial_xy_m'][1];L,W,_=o['size_m']
            approach=(current-L/2-self.setback,y);end=(target-L/2-self.setback,y)
            route=self.route(state,state.robot_reference_xy_m,approach)
            if route is None:continue
            sweep=(current-L/2,y-W/2,target+L/2,y+W/2)
            obstacles=self.obstacles(state,exclude=i)
            # Closed swept-box overlap with another obstacle (zero-length segment
            # against its Minkowski-expanded box would obscure rectangular size).
            if any(not(sweep[2]<b[0] or b[2]<sweep[0] or sweep[3]<b[1] or b[3]<sweep[1]) for b in obstacles):continue
            if nominal_connection(approach,end,obstacle_boxes_xyxy=obstacles,footprint_radius_m=self.radius)['static_status']!='POSSIBLE':continue
            positions=list(state.object_x_m);positions[i]=target
            decision=Decision('PUSH_WITH_NAV_ROUTE',candidate['public_ref'],(target,y),route[1])
            yield Arc(decision,NominalState(tuple(positions),end),route[0]+delta,'POSSIBLE')
        if state.object_x_m==self.goal_x:
            route=self.route(state,state.robot_reference_xy_m,self.goal_xy)
            if route is not None:
                yield Arc(Decision('NAV_AND_ORIGINAL_TERMINAL_STOP',None,self.goal_xy,route[1]),
                          NominalState(state.object_x_m,self.goal_xy),route[0],'POSSIBLE')
