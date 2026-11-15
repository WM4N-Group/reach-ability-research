"""Shared-geometry greedy / bounded multi-step SEMANTIC action proposals.

T-COMPLEX-01 core, NOT a scene, native admission or a learned dynamics model.
The source owner must supply the SAME task-relevant finite arcs, public state
key and nominal geometric effects to both strategies. No callbacks may use an
isolated existence route, private poses, recorded future outcomes or a simulator.
A POSSIBLE arc means nominal geometry only; original native guards still decide
execution. A proposed terminal state never certifies actual task success.
"""
from dataclasses import dataclass
import heapq
import itertools
import math
import time


@dataclass(frozen=True)
class Arc:
    action: object
    next_state: object
    nominal_cost: object = None
    static_status: str = 'UNKNOWN'

    def __post_init__(self):
        if self.static_status not in ('POSSIBLE', 'REFUTED', 'UNKNOWN'):
            raise ValueError('Explicit nominal geometry status')
        if self.static_status == 'POSSIBLE' and not (
                type(self.nominal_cost) in (int, float) and math.isfinite(self.nominal_cost) and self.nominal_cost >= 0.):
            raise ValueError('Known finite nonnegative nominal cost; missing is not zero')


def propose(state, *, arcs, is_goal, state_key, method, cost_unit,
            max_depth=4, max_transitions=256, max_wall_s=.25):
    """Return a proposal only. Reobserve and call again after actual execution.

    greedy: minimum current nominal cost in the common task-relevant action set.
    multistep: bounded uniform-cost search for a nominal goal; return its first
    action. If no goal is found, explicitly fall back to the SAME greedy rule.
    Catalogue order breaks equal-cost ties; no action-name/manual-route tie.
    Both strategies get identical resource ceilings (actual use is recorded).
    The timer detects overshoot but cannot preempt an ill-behaved source callback.
    """
    if method not in ('greedy', 'multistep') or not isinstance(cost_unit, str) or not cost_unit:
        raise ValueError('Explicit same-domain method and nominal cost unit')
    if type(max_depth) is not int or max_depth < 3 or type(max_transitions) is not int or max_transitions < 1:
        raise ValueError('At least two future transitions, finite transition ceiling')
    if type(max_wall_s) not in (int, float) or not math.isfinite(max_wall_s) or max_wall_s <= 0.:
        raise ValueError('Finite positive common wall budget')
    started = time.perf_counter()
    examined = 0
    unknown = 0
    refuted = 0
    stopped = None
    expanded = set()
    sequence = itertools.count()

    def budget():
        nonlocal stopped
        if time.perf_counter() - started > max_wall_s:
            stopped = 'WALL_BUDGET'; return False
        if examined >= max_transitions:
            stopped = 'TRANSITION_BUDGET'; return False
        return True

    def candidates(current):
        nonlocal examined, unknown, refuted, stopped
        found = []
        for arc in arcs(current):
            if not budget():return None
            if type(arc) is not Arc:raise ValueError('Source-generated finite Arc, not a motor/runtime object')
            examined += 1
            if arc.static_status == 'UNKNOWN':unknown += 1
            elif arc.static_status == 'REFUTED':refuted += 1
            else:found.append(arc)
        if time.perf_counter()-started>max_wall_s:
            stopped = 'WALL_BUDGET';return None
        return found

    def finish(action, status, path=(), cost=None, fallback=False):
        wall = time.perf_counter()-started
        return dict(method=method, action=action, status=status,
            nominal_plan=tuple(path), nominal_plan_cost=cost, cost_unit=cost_unit,
            examined_transitions=examined, expanded_states=len(expanded),
            unknown_static_arcs=unknown, refuted_static_arcs=refuted,
            planner_wall_s=wall, budget_stop=stopped,
            wall_budget_exceeded=wall>max_wall_s, fallback_to_shared_greedy=fallback,
            search_scope='DECLARED_DEPTH_KNOWN_NOMINAL_ARCS_ONLY', dynamic_success='UNKNOWN',
            execution_authorized=False, actual_task_success_claimed=False,
            standard_search_not_algorithm_novelty=True)

    if is_goal(state):return finish(None, 'ALREADY_NOMINAL_GOAL_REQUIRES_ACTUAL_TERMINAL_CHECK')
    root = candidates(state)
    if root is None:return finish(None, 'INCOMPLETE_ROOT_DOMAIN_ABSTAIN')
    if not root:return finish(None, 'NO_KNOWN_POSSIBLE_ROOT_ARC_ABSTAIN')
    greedy = min(enumerate(root), key=lambda pair:(pair[1].nominal_cost, pair[0]))[1]
    if method == 'greedy':return finish(greedy.action, 'CURRENT_NOMINAL_COST_GREEDY', (greedy.action,), greedy.nominal_cost)
    heap = []
    for arc in root:
        heapq.heappush(heap, (float(arc.nominal_cost), next(sequence), arc.next_state, (arc.action,)))
    best = {}
    while heap:
        cost, _, current, path = heapq.heappop(heap)
        if time.perf_counter()-started>max_wall_s:
            stopped='WALL_BUDGET';break
        key = (state_key(current), len(path))
        if key in best and best[key] <= cost:continue
        best[key] = cost
        if is_goal(current):return finish(path[0], 'NOMINAL_GOAL_PLAN_NATIVE_GATES_REQUIRED', path, cost)
        if len(path) >= max_depth:continue
        if not budget():break
        expanded.add(key)
        onward = candidates(current)
        if onward is None:break
        for arc in onward:
            heapq.heappush(heap, (cost+arc.nominal_cost, next(sequence), arc.next_state, path+(arc.action,)))
    return finish(greedy.action, 'NO_NOMINAL_GOAL_WITHIN_HORIZON_SHARED_GREEDY_FALLBACK',
                  (greedy.action,), greedy.nominal_cost, True)


def nominal_connection(start_xy, end_xy, *, obstacle_boxes_xyxy, footprint_radius_m=None):
    """Shared 2D nominal segment/clearance test from DECLARED public geometry.

    Radius-inflated AABBs conservatively overapproximate circular swept contact
    in this nominal model. Source must supply the robot/arm envelope and legal
    support/action domain; absent envelope is UNKNOWN. This is neither actual
    free-space certification nor a substitute for native collision/support/FF.
    Obstacle positions in hypothetical nodes are forecasts, never observations.
    """
    def finite_xy(value):
        return type(value) in (tuple,list) and len(value)==2 and all(
            type(v) in (int,float) and math.isfinite(v) for v in value)
    if not finite_xy(start_xy) or not finite_xy(end_xy):raise ValueError('Public finite WORLD XY')
    distance=math.hypot(end_xy[0]-start_xy[0],end_xy[1]-start_xy[1])
    if footprint_radius_m is None:
        return dict(static_status='UNKNOWN',nominal_robot_path_m=distance,
                    reason='NO_SOURCE_PUBLIC_FOOTPRINT_ENVELOPE',dynamic_success='UNKNOWN')
    if type(footprint_radius_m) not in (int,float) or not math.isfinite(footprint_radius_m) or footprint_radius_m<0.:
        raise ValueError('Explicit finite nonnegative nominal envelope')
    for index,box in enumerate(obstacle_boxes_xyxy):
        if not(type(box) in (tuple,list) and len(box)==4 and all(type(v) in (int,float) and math.isfinite(v) for v in box)
               and box[0]<=box[2] and box[1]<=box[3]):raise ValueError('Finite public nominal AABB')
        lo,hi=0.,1.
        for axis in (0,1):
            lower=box[axis]-footprint_radius_m;upper=box[axis+2]+footprint_radius_m
            delta=end_xy[axis]-start_xy[axis]
            if delta==0.:
                if not lower<=start_xy[axis]<=upper:lo,hi=1.,0.;break
            else:
                a=(lower-start_xy[axis])/delta;b=(upper-start_xy[axis])/delta
                lo=max(lo,min(a,b));hi=min(hi,max(a,b))
        if lo<=hi:
            return dict(static_status='REFUTED',nominal_robot_path_m=distance,
                        reason='NOMINAL_SWEPT_ENVELOPE_OVERLAP',blocking_box_index=index,dynamic_success='UNKNOWN')
    return dict(static_status='POSSIBLE',nominal_robot_path_m=distance,
                reason='NOMINAL_ENVELOPE_CLEAR_ONLY_NATIVE_GATES_REQUIRED',dynamic_success='UNKNOWN')
