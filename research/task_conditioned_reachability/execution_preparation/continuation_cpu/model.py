"""EXACT ANALYTIC FIXTURE, NOT robot dynamics/WM/registered executor domain.

One hypothetical mode, x=(push displacement d, lateral preparation p), z=retreat r.
Physical-unit equations include object drag during exit. All coefficients below
are declared analytic assumptions, never fitted to successful/held-out runs.
"""
from dataclasses import dataclass
import hashlib
import json
import numpy as np

SCALES = np.array([.4, .25, .2])  # m per normalized coordinate
MARGIN_SCALE = .1  # m, fixed for ALL methods
MODE = 'ANALYTIC_fixed_unload_retreat_NOT_native_mode'


@dataclass(frozen=True)
class Problem:
    name: str
    family: str
    support_need: float
    clearance_need: float
    prep_gain: float = .7
    drag: float = .25
    drag_quadratic: float = .15  # 1/m; box moves during exit
    retreat_upper: float = .10
    initial_d: float = .12
    operation_seconds_per_m: float = 4.
    preparation_seconds_per_m: float = 6.
    retreat_seconds_per_m: float = 3.

    @property
    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.__dict__, sort_keys=True).encode()).hexdigest()

    @property
    def lower(self):
        return np.zeros(3)

    @property
    def upper(self):
        return np.array([1., 1., self.retreat_upper/SCALES[2]])

    @property
    def initial(self):
        return np.array([self.initial_d, 0., 0.])/SCALES

    @property
    def constraint_names(self):
        return ('exit_end_box_support', 'exit_end_robot_box_standoff',
                'exit_mid_box_support')

    def coefficients(self):
        # o_exit = o0+d-k*r-c*r^2, b_exit=b0+d-a*p-r.
        # g_support = d-k*r-c*r^2 - required translation.
        # g_standoff = a*p+(1-k)*r-c*r^2 - required added separation.
        # midpoint support is checked ONLY during exit, not at PUSH start.
        c = np.array([-self.support_need, -self.clearance_need, -self.support_need])
        A = np.array([[1., 0., -self.drag],
                      [0., self.prep_gain, 1.-self.drag],
                      [1., 0., -.5*self.drag]])
        H = np.zeros((3, 3, 3))
        H[:, 2, 2] = [-2*self.drag_quadratic, -2*self.drag_quadratic,
                      -.5*self.drag_quadratic]
        return c, A*SCALES, H*SCALES[None, :, None]*SCALES[None, None, :]

    def values(self, u):
        u = np.asarray(u, dtype=float)
        if u.shape != (3,) or not np.isfinite(u).all():
            raise ValueError('Finite normalized (d,p,r) required')
        c, A, H = self.coefficients()
        g = (c+A@u+.5*np.einsum('i,kij,j->k', u, H, u))/MARGIN_SCALE
        J = (A+np.einsum('kij,j->ki', H, u))/MARGIN_SCALE
        w = u*SCALES
        # Seconds: common nominal base time + operation + prep + exit.
        prices = np.array([self.operation_seconds_per_m, self.preparation_seconds_per_m,
                           self.retreat_seconds_per_m])
        f = float(5.+prices@w+2.*(w@w))
        grad = (prices+4.*w)*SCALES
        return f, g, grad, J

    def hessians(self):
        return self.coefficients()[2]/MARGIN_SCALE

    def feasible(self, u, tol=1e-8):
        return bool(np.all(np.asarray(u)>=self.lower-tol) and
                    np.all(np.asarray(u)<=self.upper+tol) and
                    np.min(self.values(u)[1])>=-tol)

    def analytic_witness(self):
        # A simple constructive witness, NOT supplied as an optimizer start.
        # Full constraints, not family strings, determine its feasibility.
        p = self.clearance_need/self.prep_gain
        return np.array([max(0., self.support_need), max(0., p), 0.])/SCALES


def cases():
    """18 predeclared analytic instances, no seed/threshold selection from data."""
    rows = []
    for i in range(6):
        k = .20+.02*i
        prices = dict(preparation_seconds_per_m=3.+2*i,
                      retreat_seconds_per_m=2.+.8*(i%3))
        rows += [Problem(f'exit-{i}', 'exit_only_suffices', .05+.002*i,
                         .03+.003*i, drag=k, drag_quadratic=.1+.02*i, **prices),
                 Problem(f'prep-{i}', 'preparation_necessary', .04+.002*i,
                         .115+.004*i, drag=k, drag_quadratic=.1+.02*i, **prices),
                 Problem(f'joint-{i}', 'target_and_preparation_necessary', .19+.006*i,
                         .12+.004*i, drag=k, drag_quadratic=.1+.02*i, **prices)]
    return rows
