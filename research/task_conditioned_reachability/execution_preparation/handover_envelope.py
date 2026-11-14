"""Numerical check of preparation--handover cost-envelope mathematics only.

No robot/WM/geometry producer. LP coefficients, error sets and observation cells
are EXTERNAL assumptions. LP duality/support functions are standard tools, not
claimed as new theorems. Results are numerical, not interval certificates.
"""
import numpy as np
from scipy.optimize import linprog


def array(value, ndim, name):
    raw=np.asarray(value,dtype=object)
    if raw.ndim!=ndim or not raw.size:
        raise ValueError(name+' shape invalid')
    if any(isinstance(v,(bool,np.bool_)) or not isinstance(v,(int,float,np.number)) for v in raw.flat):
        raise ValueError(name+' must contain finite reals, not bools')
    result=np.asarray(value,dtype=float)
    if not np.isfinite(result).all():
        raise ValueError(name+' must be finite')
    return result


def tightened_deficit(margin, error_jacobian, box_radius, remainder):
    """g >= m + A z + D e - eta; |e_i|<=r_i => Az >= -m+|D|r+eta.

    Box and remainder must hold uniformly in the declared state/repair domain;
    no standard deviation, finite sampled max, or provenance label proves this.
    """
    m=array(margin,1,'margin');D=array(error_jacobian,2,'error Jacobian')
    radius=array(box_radius,1,'error radius');eta=array(remainder,1,'remainder')
    if D.shape!=(m.size,radius.size) or eta.shape!=m.shape:
        raise ValueError('Margin/error/remainder dimensions differ')
    if (radius<0).any() or (eta<0).any():
        raise ValueError('Negative uncertainty/remainder')
    answer=-m+np.abs(D)@radius+eta
    if not np.isfinite(answer).all():raise ValueError('Tightening overflow')
    return answer.tolist()


def solve_envelope(cost, matrix, deficit, *, residual_tolerance=1e-8):
    """min c'z subject to Az>=d, z FREE; bounds/epigraphs are rows of A.

    Solves primal and dual max lambda'd, A'lambda=c, lambda>=0 explicitly.
    A contains every trust/rate/support constraint needed by the chosen mode.
    Infeasible means no certified repair IN THIS MODEL, never global inability.
    """
    result=dict(status='UNKNOWN',value_s=None,repair=None,dual_prices=None,
                execution_authorized=False,physical_feasibility_proven=False,
                externally_supplied_model_verified=False)
    if any(v is None for v in (cost,matrix,deficit)):
        return dict(result,reason='missing_physical_model_or_bounds')
    if isinstance(residual_tolerance,bool) or not np.isfinite(residual_tolerance) or residual_tolerance<=0:
        raise ValueError('Positive numerical residual tolerance required')
    c=array(cost,1,'cost');A=array(matrix,2,'matrix');d=array(deficit,1,'deficit')
    if A.shape!=(d.size,c.size):raise ValueError('LP dimensions differ')
    primal=linprog(c,A_ub=-A,b_ub=-d,bounds=[(None,None)]*c.size,method='highs')
    if primal.status==2:return dict(result,status='NO_CERTIFIED_REPAIR_IN_DECLARED_LP')
    if not primal.success:return dict(result,reason='primal_solver_status_'+str(primal.status))
    dual=linprog(-d,A_eq=A.T,b_eq=c,bounds=[(0.,None)]*d.size,method='highs')
    if not dual.success:return dict(result,reason='dual_solver_status_'+str(dual.status))
    checks=dict(primal_violation=float(max(0.,np.max(d-A@primal.x))),
                dual_stationarity=float(np.max(np.abs(A.T@dual.x-c))),
                dual_nonnegative_violation=float(max(0.,-np.min(dual.x))),
                primal_dual_gap=float(abs(primal.fun-d@dual.x)))
    if any(value>residual_tolerance for value in checks.values()):
        return dict(result,reason='numerical_primal_dual_residual_failed',residuals=checks)
    if primal.fun < -residual_tolerance:
        raise ValueError('Model permits negative repair time; invalid duration epigraph')
    return dict(result,status='CONDITIONAL_LP_ENVELOPE',value_s=float(primal.fun),
                repair=primal.x.tolist(),dual_prices=dual.x.tolist(),residuals=checks,
                arithmetic='ordinary floating point LP checks, not exact/interval proof')


def observable_cell_value(cells):
    """Different OBSERVABLE cells may choose different repairs.

    Each LP must already stack constraints for all hidden states within its
    cell, using ONE common z. Distinct cells being distinguishable from actual
    post-skill observation is an unverified caller assumption, not inferred here.
    """
    if not isinstance(cells,list) or not cells:raise ValueError('Nonempty observable cells required')
    ids=[row.get('observation_cell_id') for row in cells]
    if any(not isinstance(k,str) or not k for k in ids) or len(ids)!=len(set(ids)):
        raise ValueError('Unique declared observation cells required')
    rows=[dict(observation_cell_id=row['observation_cell_id'],
               result=solve_envelope(row.get('cost'),row.get('matrix'),row.get('deficit')))
          for row in cells]
    status=[r['result']['status'] for r in rows]
    if any(s=='NO_CERTIFIED_REPAIR_IN_DECLARED_LP' for s in status):
        return dict(status='NO_CERTIFIED_CELLWISE_POLICY',value_s=None,cells=rows,
                    execution_authorized=False)
    if not all(s=='CONDITIONAL_LP_ENVELOPE' for s in status):
        return dict(status='UNKNOWN',value_s=None,cells=rows,execution_authorized=False)
    return dict(status='CONDITIONAL_OBSERVATION_RECOURSE',
                value_s=max(row['result']['value_s'] for row in rows),cells=rows,
                observable_partition_independently_verified=False,
                execution_authorized=False)


def skew(value):
    v=array(value,1,'three-vector')
    if v.shape!=(3,):raise ValueError('Three-vector required')
    x,y,z=v
    return np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])


def relative_hand_linearization(object_rotation,base_rotation,hand_base,joint_jacobian,hand_object):
    """Rigid-transform differential, NOT FK or a complete path/error certificate.

    z=[delta base translation WORLD, delta base angle BODY, delta joint q].
    e=[delta object translation WORLD, delta object angle OBJECT].
    hand_base and J refer to the SAME root/tool; hand_object is the current
    object-frame point. Unknown true/source/model remainders stay external.
    """
    Ro=array(object_rotation,2,'object rotation');Rb=array(base_rotation,2,'base rotation')
    f=array(hand_base,1,'hand in base');p=array(hand_object,1,'hand in object')
    J=array(joint_jacobian,2,'point Jacobian')
    if Ro.shape!=(3,3) or Rb.shape!=(3,3) or f.shape!=(3,) or p.shape!=(3,) or J.shape[0]!=3:
        raise ValueError('Rigid point/Jacobian dimensions differ')
    for R in (Ro,Rb):
        if not np.allclose(R.T@R,np.eye(3),rtol=0.,atol=1e-10) or abs(np.linalg.det(R)-1.)>1e-10:
            raise ValueError('Proper orthonormal frame required')
    return dict(repair_matrix=np.column_stack((Ro.T,-Ro.T@Rb@skew(f),Ro.T@Rb@J)),
                object_error_matrix=np.column_stack((-Ro.T,skew(p))))


def support_moment_linearization(feet_world,com_world,hand_world,feet_forces,hand_force):
    """Differential of sum (foot-com)xforce + (hand-com)xF.

    Fixed admitted foot anchors, one contact mode. Forces are static witness
    variables, not free actuator outputs or measured future contact forces.
    Remainder includes -sum dc x dfi + (dh-dc) x dF, plus any source-model error.
    """
    feet=array(feet_world,2,'feet');forces=array(feet_forces,2,'forces')
    c=array(com_world,1,'COM');hand=array(hand_world,1,'hand');F=array(hand_force,1,'hand force')
    if feet.shape!=(4,3) or forces.shape!=(4,3) or any(v.shape!=(3,) for v in (c,hand,F)):
        raise ValueError('One fixed four-foot mode and three-vectors required')
    return dict(foot_force_matrix=np.column_stack([skew(p-c) for p in feet]),
                com_matrix=skew(forces.sum(axis=0)+F),
                hand_position_matrix=-skew(F),
                hand_force_matrix=skew(hand-c))
