"""Private candidate actions for one freshly started PUSH attempt.

The policy gets one bounded action per attempt: choose a preregistered brake
lead distance or leave the original brake unchanged. The adapter then asks
for the existing guarded controller at an eligible native observation. True
simulator state supplies admission/reward verification, never policy input.
"""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class BrakeAction:
    index: int
    lead_m: float

    def __post_init__(self):
        if type(self.index) is not int or self.index < 0:
            raise ValueError('Preregistered nonnegative discrete action')
        if type(self.lead_m) not in (int, float) or not isfinite(self.lead_m) or not 0 <= self.lead_m <= .20:
            raise ValueError('Bounded source candidate, no live configuration permission')
        if (self.index == 0) != (self.lead_m == 0):
            raise ValueError('Action zero delegates exactly to original policy')


PREVIEW_DELAY_S=.04   # original nominal 20ms motor delay + original 20ms control interval
PREVIEW_DECEL_MPS2=1.5  # one prospective hypothesis, no identified/guaranteed bound


def preview_lead_m(action,vx):
    if type(action) is not BrakeAction or type(vx) not in (int,float) or not isfinite(vx):
        raise ValueError('Finite current velocity from exact native position/velocity snapshot')
    if vx<=0. or not action.index:
        return 0.
    return min(action.lead_m,PREVIEW_DELAY_S*vx+vx*vx/(2.*PREVIEW_DECEL_MPS2))


def qualify_preview_CPU():
    a=BrakeAction(1,.20)
    assert preview_lead_m(a,0.)==0. and preview_lead_m(a,-.3)==0.
    assert abs(preview_lead_m(a,.60)-.144)<1e-12 and preview_lead_m(a,1.)==.20
    assert preview_lead_m(BrakeAction(0,0.),.60)==0.
    return dict(CPU_formula_only=True,one_prespecified_velocity_preview=True,delay_s=PREVIEW_DELAY_S,
                nominal_decel_mps2=PREVIEW_DECEL_MPS2,actual_at_point6_m=.144,not_native_or_training=True)


def brake_eligible(action, m, contract, *, actual_legal_hand, contact_seen):
    """Necessary read-only early request screen, never placement or admission."""
    if type(action) is not BrakeAction:
        raise TypeError('Typed fixed per-attempt action')
    if type(actual_legal_hand) is not bool or type(contact_seen) is not bool:
        raise ValueError('Observed contact predicates must be explicit')
    if action.index == 0 or not actual_legal_hand or not contact_seen:
        return False
    if m['placement_geometry_verified'] or m['task_geometry_pass']:
        return False  # original switch owner handles this branch, even if it refuses
    xyz = tuple(m['actual_box_position_m'])
    vel = tuple(m['actual_box_linear_velocity_m_s'])
    goal = tuple(contract.public_goal_xy_m)
    h = contract.source_surface_height_m
    size = tuple(contract.box_size_m)
    d = m['actual_signed_dock_gap_m']
    y_tol = contract.public_XY_tolerance_m
    if (len(xyz), len(vel), len(goal), len(size)) != (3, 3, 2, 3) or not all(
            type(v) in (float, int) and isfinite(v) for v in (*xyz, *vel, *goal, *size, h, d, y_tol)):
        raise ValueError('Unknown/incomplete current measurements are not zeros')
    if not (contract.mode == 'uncompensated' and h == 0. and size == (1.2, 1.2, .2) and y_tol > 0):
        raise ValueError('Only exact original fixed L0 geometry for this source candidate')
    return (0. < d <= preview_lead_m(action,vel[0]) and vel[0] > 0.
            and abs(xyz[1] - goal[1]) < y_tol and abs(xyz[2] - h - size[2]/2.) < .02)
