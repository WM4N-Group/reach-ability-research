"""Conditional path-tube / finite-candidate theory, NOT runtime authority.

Reuses the existing pose_tube_standoff bound rather than inventing another
collision rule. All error/Jacobian/Lipschitz bounds are external assumptions over
the ENTIRE declared path, tracking and retreat domain, not sample maxima. No FK,
actors, calibration, probability or dynamics integration is performed here.
"""
import math
from pose_tube_standoff import rigid_pose_error_bound, robust_request

BOUND_KEYS = (
    'relative_translation_error_m', 'relative_rotation_error_rad', 'point_radius_m',
    'joint_tracking_error_norm_rad', 'point_jacobian_operator_bound_m_per_rad',
    'nominal_point_path_lipschitz_m_per_u', 'unrepresented_geometry_error_m',
)


def number(value, name, *, nonnegative=True):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(name+' must be a finite number')
    if nonnegative and value < 0:
        raise ValueError(name+' must be nonnegative')
    return float(value)


def path_budget(knots, bounds=None):
    """Uniform epsilon = et + 2*r*sin(etheta/2) + Lq*eq + Ku*h/2 + em.

    Parameter u runs 0..1, NOT seconds. Nearest knot distance is <= h/2 when
    endpoints are included. Ku bounds each nominal point's full derivative in u.
    A witness string records provenance; it does not validate any supplied bound.
    """
    u=[number(x,'path knot') for x in knots]
    if len(u)<2 or u[0]!=0. or u[-1]!=1. or any(b<=a for a,b in zip(u,u[1:])):
        raise ValueError('Strictly increasing path knots must cover endpoints0 and1')
    h=max(b-a for a,b in zip(u,u[1:]))
    result=dict(schema='conditional-continuous-path-budget-v1',status='UNKNOWN_missing_external_bounds',
                max_parameter_gap=h,epsilon_m=None,components_m=None,
                bounds_independently_validated=False,execution_authorized=False,
                domain='all represented point trajectories, u in[0,1], retreat d in[0,40mm], fixed comparison box frame',
                numeric_scope='ordinary floating point algebra, not interval-arithmetic certification')
    if bounds is None:return dict(result,missing=list(BOUND_KEYS)+['provenance'])
    missing=[k for k in BOUND_KEYS if bounds.get(k) is None]
    if not isinstance(bounds.get('provenance'),str) or not bounds['provenance'].strip():missing.append('provenance')
    if missing:return dict(result,missing=missing)
    b={k:number(bounds[k],k) for k in BOUND_KEYS}
    if b['relative_rotation_error_rad']>math.pi:raise ValueError('Rotation error must lie in[0,pi]')
    rigid=rigid_pose_error_bound(b['relative_translation_error_m'],b['relative_rotation_error_rad'],b['point_radius_m'])
    terms=dict(relative_rigid_pose=rigid,
               joint_tracking=b['point_jacobian_operator_bound_m_per_rad']*b['joint_tracking_error_norm_rad'],
               between_samples=b['nominal_point_path_lipschitz_m_per_u']*h/2.,
               unrepresented_geometry=b['unrepresented_geometry_error_m'])
    if not all(math.isfinite(v) for v in terms.values()) or not math.isfinite(sum(terms.values())):
        raise ValueError('Derived error bound overflowed')
    return dict(result,status='CONDITIONAL_external_bounds_assumed',epsilon_m=sum(terms.values()),
                components_m=terms,missing=[],bounds=b,provenance=bounds['provenance'])


def path_request(points, half_size, axis, inflation_m, knots, bounds=None):
    """Tighten x AND enlarge yz membership with the same supplied path tube.

    With missing error bounds this returns unknown even if nominal clearance is
    positive. The backend's >40mm means no certificate in this restricted model,
    NOT physical unreachability. No assumed bounds are inferred from real data.
    """
    budget=path_budget(knots,bounds)
    common=dict(schema='conditional-robust-preparation-v1',path_budget=budget,
                status='UNKNOWN_missing_external_bounds',required_shift_m=None,
                conditional_within_cap=None,execution_authorized=False,
                whole_robot_dynamic_safety_certified=False)
    if budget['epsilon_m'] is None:return common
    if len(axis)!=3:raise ValueError('Retreat axis must have three components')
    axis=[number(x,'axis component',nonnegative=False) for x in axis]
    if not math.isclose(sum(x*x for x in axis),1.,rel_tol=0.,abs_tol=1e-8):
        raise ValueError('Retreat axis must be unit in an orthonormal box frame')
    eps=budget['epsilon_m']
    # In an orthonormal box frame ||e||2<=eps implies componentwise |ej|<=eps.
    result=robust_request(points,half_size,axis,inflation_m,[eps]*3,cap_m=.04)
    return dict(common,status='CONDITIONAL_path_and_geometry_bounds_only',
                required_shift_m=result['required_shift_m'],
                conditional_within_cap=result['sufficient_within_cap'],finite_cloud_bound=result)


def select_candidate(candidates, required_shift_m):
    """Min nominal cost over a fixed finite support/geometry candidate table.

    Every support/reserve/other witness must concern the SAME final returned
    shift, not a smaller pre-reserve grid value. Support need not be monotone in
    retreat. Missing evidence blocks certification, never becomes a false failure.
    The cost is an external nominal total, not a measured task improvement.
    """
    result=dict(schema='conditional-finite-preparation-selection-v1',status='UNKNOWN',
                selected=None,classified=[],conditional_optimal_value_proven=False,
                execution_authorized=False,task_success=None,
                scope='finite supplied candidates and explicitly supplied nominal witnesses only; no continuous optimality or dynamic guarantee')
    if required_shift_m is None:return dict(result,reason='missing_required_shift')
    minimum=number(required_shift_m,'required_shift_m')
    if not candidates:return dict(result,reason='no_candidate_domain_not_physical_infeasibility')
    seen=set();eligible=[];unknown=[]
    for raw in candidates:
        identifier=raw.get('id')
        if not isinstance(identifier,str) or not identifier or identifier in seen:raise ValueError('Unique nonempty candidate IDs required')
        seen.add(identifier)
        shift=number(raw.get('shift_m'),'candidate shift')
        if shift>.04:raise ValueError('Candidate outside original40mm domain')
        cost=None if raw.get('nominal_total_cost') is None else number(raw['nominal_total_cost'],'nominal_total_cost')
        row=dict(id=identifier,shift_m=shift,nominal_total_cost=cost,status='UNKNOWN')
        # Geometry failure of this SUFFICIENT rule says not certified, not truth.
        if shift<minimum:row.update(status='not_certified_by_geometry_rule')
        else:
            witness=raw.get('witness',{})
            checks=[witness.get(k) for k in ('support_passed','reserve_passed','other_original_gates_passed')]
            if any(v is not None and not isinstance(v,bool) for v in checks):raise ValueError('Witness checks must be bool or None')
            evaluated=witness.get('evaluated_shift_m')
            bound_to_shift=(not isinstance(evaluated,bool) and isinstance(evaluated,(int,float))
                            and math.isfinite(evaluated) and evaluated==shift and
                            isinstance(witness.get('source'),str) and bool(witness['source'].strip()))
            if bound_to_shift and any(v is False for v in checks):row['status']='not_certified_by_nominal_witness'
            elif bound_to_shift and all(v is True for v in checks) and cost is not None:
                row['status']='conditionally_eligible';eligible.append(row)
            else:unknown.append(row)
        result['classified'].append(row)
    if not eligible:return dict(result,status='UNKNOWN' if unknown else 'NO_CERTIFIED_FINITE_CANDIDATE',
                                reason='not_a_global_infeasibility_proof')
    best=min(eligible,key=lambda x:(x['nominal_total_cost'],x['shift_m'],x['id']))
    # Unknown rows may be cheaper. Equal-cost ambiguity does not change the value.
    blockers=[x for x in unknown if x['nominal_total_cost'] is None or x['nominal_total_cost']<best['nominal_total_cost']]
    return dict(result,status='CONDITIONAL_best_known_candidate' if blockers else 'CONDITIONAL_finite_cost_optimum',
                selected=dict(best),conditional_optimal_value_proven=not blockers,
                unknown_cheaper_candidate_ids=[x['id'] for x in blockers])
