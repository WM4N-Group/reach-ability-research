"""Offline analytic bounds for a root-fixed serial hinge chain; no FK or control.

Every hinge must be at its body origin. Arbitrary rigid rotations preserve edge
lengths. Bounds cover ALL joint angles, hence also clipped residual paths and
segments joining actual/nominal joints. They are not measured tracking bounds.
Decimal arithmetic rounds upper quantities outward; physical/model errors and
runtime floating-point evaluation remain separate, unverified assumptions.
"""
from decimal import Decimal, localcontext, ROUND_CEILING
import math


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Expected finite real number, not bool')
    return Decimal(value) if isinstance(value, int) else Decimal.from_float(value)


def _vector(value):
    if len(value) != 3:
        raise ValueError('Expected three-vector')
    return tuple(_number(v) for v in value)


def _norm_upper(values):
    # Decimal.sqrt is correctly rounded (half-even); next_plus makes it upper.
    squared = sum((v*v for v in values), Decimal(0))
    return squared.sqrt().next_plus() if squared else Decimal(0)


def _float_upper(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('Bound overflow')
    return math.nextafter(result, math.inf) if Decimal.from_float(result) < value else result


def chain_bounds(chain, *, tool_offset_m=(0., 0., 0.), attached_point_radius_m=0.):
    """chain lists bodies AFTER the chosen root, ordered toward the tool.

    Each entry: name, parent, translation_m, joint=None or
    {name, kind='hinge', pivot_m=[0,0,0]}. Fixed transforms may be interleaved.
    Root-relative radius sums every edge. Hinge j's lever sums only edges AFTER
    its body plus the tool offset/radius; J's column norm <= that lever.
    Lq is the Frobenius bound sqrt(sum(levers**2)) for Euclidean joint error.
    """
    if not chain:
        raise ValueError('Empty serial chain')
    with localcontext() as ctx:
        ctx.prec = 60
        ctx.rounding = ROUND_CEILING
        radius = _number(attached_point_radius_m)
        if radius < 0:
            raise ValueError('Negative attached point radius')
        offset = _norm_upper(_vector(tool_offset_m)) + radius
        lengths, joints, names = [], [], set()
        for index, body in enumerate(chain):
            name = body['name']
            if not isinstance(name, str) or not name or name in names:
                raise ValueError('Invalid or duplicate body name')
            names.add(name)
            if index and body['parent'] != chain[index-1]['name']:
                raise ValueError('Not an ordered serial chain')
            lengths.append(_norm_upper(_vector(body['translation_m'])))
            joint = body.get('joint')
            if joint is not None:
                if joint['kind'] != 'hinge' or any(_vector(joint['pivot_m'])):
                    raise ValueError('Only origin-pivot hinges are supported')
                if any(joint['name'] == old[1] for old in joints):
                    raise ValueError('Duplicate joint name')
                joints.append((index, joint['name']))
        if not joints:
            raise ValueError('No hinge joints')
        levers = [sum(lengths[i+1:], offset) for i, _ in joints]
        rmax = sum(lengths, offset)
        lq = _norm_upper(levers)
        return dict(schema='analytic-origin-hinge-chain-bounds-v1',
                    derivation='triangle edge lengths + revolute Jacobian column + Frobenius norm',
                    root=chain[0]['parent'], point_body=chain[-1]['name'],
                    joint_names=[name for _, name in joints],
                    edge_length_upper_m=[_float_upper(x) for x in lengths],
                    joint_lever_upper_m=[_float_upper(x) for x in levers],
                    point_radius_m=_float_upper(rmax),
                    point_jacobian_operator_bound_m_per_rad=_float_upper(lq),
                    attached_point_radius_m=float(radius),
                    domain='all real hinge angles; fixed root; declared attached point set only',
                    arithmetic='60-digit Decimal outward upper bounds on supplied binary64 model constants',
                    execution_authorized=False, physical_safety_certified=False)


def linear_path_bound(chain_result, waypoints, phases=None):
    """Global u in [0,1]; each waypoint segment is linear in its phase interval.

    Ku <= max_s sum_j b_j*abs(delta_q_sj)/(phase[s+1]-phase[s]).
    The same bound holds for clip(q(u)+c, lower, upper) for EVERY fixed c.
    It does not hold for a freely time-varying residual c(u) without a new bound.
    """
    count = len(waypoints)
    if count < 2:
        raise ValueError('At least two waypoints required')
    if phases is None:
        # Exact equal-phase rational spans are handled separately below.
        phases = [i/(count-1) for i in range(count)]
        equal = True
    else:
        equal = False
    if len(phases) != count:
        raise ValueError('Phase count mismatch')
    with localcontext() as ctx:
        ctx.prec = 60
        ctx.rounding = ROUND_CEILING
        u = [_number(x) for x in phases]
        if u[0] != 0 or u[-1] != 1 or any(b <= a for a, b in zip(u, u[1:])):
            raise ValueError('Phases must increase from zero to one')
        b = [_number(x) for x in chain_result['joint_lever_upper_m']]
        if any(x < 0 for x in b):
            raise ValueError('Negative lever')
        rows = [[_number(x) for x in row] for row in waypoints]
        if any(len(row) != len(b) for row in rows):
            raise ValueError('Waypoint joint count mismatch')
        values = []
        for index, (start, end) in enumerate(zip(rows, rows[1:])):
            # Absolute differences computed with an upward rounding direction.
            dq = [max(x, y)-min(x, y) for x, y in zip(start, end)]
            numerator = sum((lever*d for lever, d in zip(b, dq)), Decimal(0))
            # Phase differences exact for binary64 endpoints within 60 digits
            # in normal use; round denominator DOWN for a conservative ratio.
            with localcontext() as lower:
                lower.rounding = 'ROUND_FLOOR'
                span = u[index+1]-u[index]
            value = numerator*(count-1) if equal else numerator/span
            values.append(_float_upper(value))
        return dict(schema='analytic-linear-joint-path-bound-v1',
                    nominal_point_path_lipschitz_m_per_u=max(values),
                    segment_lipschitz_m_per_u=values,
                    phases=phases, equal_phase_intervals=equal,
                    parameter='global normalized geometric u, NOT physical seconds',
                    fixed_residual_clipping_covered=True,
                    varying_residual_or_tracking_covered=False,
                    execution_authorized=False)
