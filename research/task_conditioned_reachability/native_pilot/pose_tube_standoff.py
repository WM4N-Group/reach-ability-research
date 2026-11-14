"""Offline finite-cloud pose-tube bound, NOT imported by any frozen pilot source.

An error bound must be justified before a decision. A bound reconstructed after
an episode is diagnostic only, never an online certificate or budget authority.
"""
import math


def _vector(value, name):
    out = tuple(float(v) for v in value)
    if len(out) != 3 or not all(math.isfinite(v) for v in out):
        raise ValueError(name + ' must be a finite three-vector')
    return out


def rigid_pose_error_bound(translation_bound_m, rotation_bound_rad, radius_m):
    """||delta_b + (Q_actual-Q_predicted)v|| <= p + 2 L sin(theta/2).

    delta_b includes relative-origin/box/retreat tracking error in the declared
    comparison frame; theta bounds relative orientation, not just robot yaw.
    All bounds are external assumptions, not inferred here from observations.
    """
    p, theta, radius = map(float, (translation_bound_m, rotation_bound_rad, radius_m))
    if not all(math.isfinite(v) for v in (p, theta, radius)) or p < 0 or radius < 0 or not 0 <= theta <= math.pi:
        raise ValueError('Invalid external rigid-pose uncertainty bounds')
    return p + 2 * radius * math.sin(theta / 2)


def robust_request(points, half_size, axis, inflation_m, error_bound_m=None, cap_m=.04):
    """Sufficient retreat for ell_actual_i(d)=ell_pred_i-d*a+e_i(d).

    Assumption: |e_ij(d)|<=epsilon_j for EVERY provided i and d in [0,D].
    No claim about continuous residuals, dynamic execution, full body or support.
    Out-of-cap is absence of this sufficient request, not robot infeasibility.
    """
    half = _vector(half_size, 'half_size'); axis = _vector(axis, 'axis')
    cloud = [_vector(p, 'point') for p in points]
    inflation, cap = float(inflation_m), float(cap_m)
    if not cloud or any(h <= 0 for h in half) or axis[0] < .95:
        raise ValueError('Empty cloud, invalid box or outside original aligned domain')
    if not math.isfinite(inflation) or inflation < 0 or not math.isfinite(cap) or not 0 <= cap <= .04:
        raise ValueError('Invalid inflation or outside original40mm cap')
    result = dict(schema='offline-finite-cloud-pose-tube-bound-v1',runtime_control_authority=False,
                  point_count=len(cloud),cap_m=cap,required_shift_m=None,sufficient_within_cap=None,
                  prospective_bound_verified=False,
                  scope='Finite supplied cloud + externally justified pose tube only; no dynamic/full-body/continuous certificate')
    if error_bound_m is None:
        return dict(result,status='UNKNOWN_external_pose_error_bound_not_declared')
    eps = _vector(error_bound_m, 'error_bound')
    if any(e < 0 for e in eps):raise ValueError('Negative error bound')
    ids = [i for i,p in enumerate(cloud) if all(abs(p[j]) <= half[j]+inflation+eps[j]+cap*abs(axis[j]) for j in (1,2))]
    maximum = max((cloud[i][0] for i in ids), default=None)
    needed = 0. if maximum is None else max(0.,(maximum+half[0]+inflation+eps[0])/axis[0])
    return dict(result,status='CONDITIONAL_finite_cloud_bound_only',error_bound_m=list(eps),selected_indices=ids,
                maximum_selected_x_m=maximum,required_shift_m=needed,sufficient_within_cap=needed <= cap)
