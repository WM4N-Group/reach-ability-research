"""Budgeted same-oracle CPU comparison. Standard algorithms, no novelty claim.

The candidate is a conservative sequential LP with slack restoration. Its
implicit upstream projection retains downstream r as an existential LP witness;
this is NOT a new projection algorithm or globally valid Benders cut.
"""
from dataclasses import dataclass
import time
import numpy as np
from scipy.optimize import linprog, minimize
from ..handover_envelope import tightened_deficit
from .model import MODE


class StopBudget(Exception):
    pass


class Oracle:
    def __init__(self, problem, max_calls=96, max_wall_s=3.):
        if max_calls < 1 or not np.isfinite(max_wall_s) or max_wall_s <= 0:
            raise ValueError('Positive evaluation/wall budget required')
        self.problem, self.max_calls, self.max_wall_s = problem, max_calls, max_wall_s
        self.began = time.perf_counter()
        self.cache, self.rows = {}, []
        self.best = None
        self.first_feasible_s = None
        self.first_feasible_call = None
        self.derivative_requests = 0

    def check(self):
        if time.perf_counter()-self.began >= self.max_wall_s:
            raise StopBudget('wall_budget')

    def evaluate(self, u):
        self.check()
        u = np.array(u, dtype=float, copy=True)
        key = u.tobytes()
        if key in self.cache:
            return self.cache[key]
        if len(self.rows) >= self.max_calls:
            raise StopBudget('full_evaluation_budget')
        value = self.problem.values(u)
        f, g, grad, J = value
        feasible = bool(np.all(u>=self.problem.lower-1e-8) and
                        np.all(u<=self.problem.upper+1e-8) and np.min(g)>=-1e-8)
        elapsed = time.perf_counter()-self.began
        row = dict(call=len(self.rows)+1, wall_s=elapsed, u=u.tolist(),
                   parameters_m=(u*np.array([.4,.25,.2])).tolist(),
                   cost_s=f, margins_normalized=g.tolist(), feasible=feasible)
        self.rows.append(row)
        self.cache[key] = value
        if feasible:
            if self.first_feasible_s is None:
                self.first_feasible_s, self.first_feasible_call = elapsed, len(self.rows)
            if self.best is None or f < self.best['cost_s']:
                self.best = row.copy()
        return value

    def derivative(self, u, slot):
        self.derivative_requests += 1
        return self.evaluate(u)[slot]

    def report(self, method, reason, internal, algorithm_events):
        return dict(method=method, status='MODEL_FEASIBLE_NUMERICAL' if self.best else 'UNKNOWN',
                    reason=reason, best=self.best, first_feasible_s=self.first_feasible_s,
                    first_feasible_call=self.first_feasible_call, full_evaluations=len(self.rows),
                    derivative_requests=self.derivative_requests, internal_solves=internal,
                    wall_s=time.perf_counter()-self.began, trace=self.rows,
                    algorithm_events=algorithm_events, execution_authorized=False,
                    global_infeasibility_claim=False, dynamic_safety_certificate=False)


@dataclass
class LocalFeedback:
    problem_id: str
    mode: str
    anchor: np.ndarray
    radius: np.ndarray
    margins: np.ndarray
    jacobian: np.ndarray
    remainder: np.ndarray | None

    @classmethod
    def build(cls, problem, anchor, radius, value, *, bound_available=True):
        radius = np.asarray(radius, dtype=float)
        if radius.shape != (3,) or not np.isfinite(radius).all() or (radius<=0).any():
            raise ValueError('Finite positive local radius required')
        # Exact quadratic Hessian on this declared analytic domain, not sampled max.
        eta = .5*np.einsum('i,kij,j->k',radius,np.abs(problem.hessians()),radius)
        return cls(problem.fingerprint, MODE, np.array(anchor,copy=True),radius.copy(),
                   value[1].copy(),value[3].copy(),eta if bound_available else None)

    def lower_margin(self, problem, point, mode=MODE):
        if problem.fingerprint != self.problem_id or mode != self.mode:
            return None
        step = np.asarray(point)-self.anchor
        if self.remainder is None or (np.abs(step)>self.radius+1e-12).any():
            return None
        return self.margins+self.jacobian@step-self.remainder


def starts(problem, seed):
    rng = np.random.default_rng(seed)
    return [problem.initial.copy()]+[rng.uniform(problem.lower,problem.upper) for _ in range(7)]


def slsqp_run(oracle, initial, free=(0,1,2), maxiter=80):
    p = oracle.problem
    free = np.array(free)
    def whole(v):
        u=np.array(initial,copy=True);u[free]=v;return u
    return minimize(lambda v:oracle.evaluate(whole(v))[0],initial[free],
                    jac=lambda v:oracle.derivative(whole(v),2)[free],method='SLSQP',
                    bounds=list(zip(p.lower[free],p.upper[free])),
                    constraints=[dict(type='ineq',fun=lambda v:oracle.evaluate(whole(v))[1],
                                      jac=lambda v:oracle.derivative(whole(v),3)[:,free])],
                    options=dict(maxiter=maxiter,ftol=1e-10,disp=False))


def solve(problem, method, seed=0, max_calls=96, max_wall_s=3.):
    allowed=('joint_sqp','alternating_sqp','random_search','local_projection',
             'linearized_feedback')
    if method not in allowed:
        raise ValueError('Unknown implemented method')
    oracle=Oracle(problem,max_calls,max_wall_s)
    internal=0;events=[];reason='bounded_iterations_finished'
    seeds=starts(problem,seed)
    try:
        oracle.evaluate(problem.initial)
        if method=='joint_sqp':
            for initial in seeds:
                oracle.check();internal+=1
                result=slsqp_run(oracle,initial)
                oracle.evaluate(result.x)
        elif method=='alternating_sqp':
            for initial in seeds:
                u=initial.copy()
                for _ in range(6):
                    before=u.copy()
                    for free in ((2,),(0,1)):
                        oracle.check();internal+=1
                        result=slsqp_run(oracle,u,free=free,maxiter=30)
                        u[np.array(free)]=result.x
                        oracle.evaluate(u)
                    if np.linalg.norm(u-before)<1e-9:
                        break
        elif method=='random_search':
            # Shared eight starts, followed by additional same-box uniform samples.
            for initial in seeds[1:]:
                oracle.evaluate(initial)
            rng=np.random.default_rng(seed+10000)
            while True:
                oracle.evaluate(rng.uniform(problem.lower,problem.upper))
        else:
            conservative=method=='local_projection'
            for initial in seeds:
                u=initial.copy();radius=np.full(3,.5)
                for iteration in range(16):
                    oracle.check()
                    value=oracle.evaluate(u);f,g,grad,J=value
                    fb=LocalFeedback.build(problem,u,radius,value)
                    eta=fb.remainder if conservative else np.zeros_like(g)
                    lo=np.maximum(problem.lower-u,-radius)
                    hi=np.minimum(problem.upper-u,radius)
                    # Reuse the PHE tightening convention Az >= -margin+eta.
                    deficit=np.array(tightened_deficit(g,np.zeros((len(g),1)),[0.],eta))
                    common=dict(A_ub=-J,b_ub=-deficit,bounds=list(zip(lo,hi)),method='highs',
                                options={'time_limit':max(.001,max_wall_s-(time.perf_counter()-oracle.began))})
                    internal+=1
                    proposal=linprog(grad,**common)
                    slack=None
                    if not proposal.success:
                        # Local inner set empty != global infeasibility; restore only.
                        internal+=1
                        restored=linprog(np.r_[np.zeros(3),1.],
                            A_ub=np.c_[-J,-np.ones(len(g))],b_ub=-deficit,
                            bounds=list(zip(lo,hi))+[(0,None)],method='highs',
                            options={'time_limit':max(.001,max_wall_s-(time.perf_counter()-oracle.began))})
                        if not restored.success:
                            radius*=.5;events.append(dict(local_set_unresolved=True,global_cut_created=False));continue
                        step=restored.x[:3];slack=float(restored.x[3])
                    else:
                        step=proposal.x
                    candidate=np.clip(u+step,problem.lower,problem.upper)
                    actual=oracle.evaluate(candidate)
                    predicted=g+J@step-eta
                    verified=bool(np.min(actual[1])>=-1e-8)
                    event=dict(iteration=iteration,anchor=u.tolist(),candidate=candidate.tolist(),
                               radius=radius.tolist(),mode=MODE,problem_id=problem.fingerprint,
                               remainder=eta.tolist(),diagnostic_slack=slack,
                               predicted_feasible=bool(np.min(predicted)>=-1e-8),
                               actual_feasible=verified,
                               min_actual_minus_predicted=float(np.min(actual[1]-predicted)),
                               certificate_scope='analytic_local_model_only' if conservative else 'nominal_linearization_only',
                               global_cut_created=False)
                    violation=max(0.,-float(np.min(g)))
                    newviolation=max(0.,-float(np.min(actual[1])))
                    accept=(verified and (not bool(np.min(g)>=-1e-8) or actual[0]<f-1e-10)) or (not bool(np.min(g)>=-1e-8) and newviolation<violation-1e-9)
                    event['accepted']=bool(accept);events.append(event)
                    if accept:
                        u=candidate
                    else:
                        radius*=.5
                    if np.max(radius)<1e-5:
                        break
    except StopBudget as exc:
        reason=str(exc)
    return oracle.report(method,reason,internal,events)
