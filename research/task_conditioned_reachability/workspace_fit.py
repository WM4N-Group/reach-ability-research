"""One predeclared training-only dual-ellipsoid approximation, NOT safe reach."""
from __future__ import annotations

from itertools import product
import math

import numpy as np


def position_grids(protocol):
    axes = []
    for name in ['x_m', 'y_m', 'z_m']:
        low, high, n = protocol['grid'][name]
        if not (np.isfinite([low, high]).all() and low < high and type(n) is int and n >= 2):
            raise ValueError('Grid requires finite ascending bounds and integer count>=2')
        axes.append(np.linspace(low, high, n))
    train = np.array(list(product(*axes)))
    validation = np.array(list(product(*[(a[:-1] + a[1:]) / 2 for a in axes])))
    return train, validation


def orientation_matrices():
    """12 right-handed frames; roll refers to tool x, not robot roll."""
    matrices = []
    for axis in np.eye(3):
        for sign in [1., -1.]:
            x = axis * sign
            helper = np.eye(3)[int(np.argmin(np.abs(x)))]
            y = np.cross(helper, x)
            y /= np.linalg.norm(y)
            z = np.cross(x, y)
            base = np.column_stack((x, y, z))
            for roll in [0., math.pi / 2]:
                c, s = math.cos(roll), math.sin(roll)
                matrices.append(base @ np.array([[1, 0, 0], [0, c, -s], [0, s, c]]))
    return matrices


def fit_dual_ellipsoid(points, success_fractions, config):
    p = np.asarray(points, dtype=float)
    rates = np.asarray(success_fractions, dtype=float)
    if p.ndim != 2 or p.shape[1] != 3 or rates.shape != (len(p),):
        raise ValueError('Expected Nx3 points and N success fractions')
    if not np.isfinite(p).all() or not np.isfinite(rates).all() or ((rates < 0) | (rates > 1)).any():
        raise ValueError('Invalid finite coordinate or orientation success fraction')
    threshold = config['positive_success_fraction_threshold']
    if not 0 < threshold <= 1 or config['covariance_regularizer_m2'] <= 0:
        raise ValueError('Invalid predeclared fit parameters')
    positive = p[rates >= threshold]
    if len(positive) < config['minimum_positive_points']:
        raise ValueError('Insufficient training-positive points for this predeclared fit')
    center = positive.mean(axis=0)
    delta = positive - center
    if np.linalg.matrix_rank(delta) != 3:
        raise ValueError('Training positives not full-dimensional; do not invent ellipsoid axes')
    covariance = delta.T @ delta / len(delta) + config['covariance_regularizer_m2'] * np.eye(3)
    metric = np.linalg.inv(covariance)
    outer_scale = np.einsum('ni,ij,nj->n', delta, metric, delta).max()
    outer = metric / outer_scale
    outer_dist = np.einsum('ni,ij,nj->n', delta, outer, delta)
    inner_scale = float(outer_dist.min())
    if inner_scale <= 1e-12:
        raise ValueError('No nondegenerate concentric sample-empty inner cavity; fit unsupported')
    inner = outer / inner_scale
    values, rotation = np.linalg.eigh(outer)
    return dict(center_base_m=center.tolist(), outer_metric_m_minus2=outer.tolist(),
                inner_metric_m_minus2=inner.tolist(),
                outer_semiaxes_m=(1 / np.sqrt(values)).tolist(),
                inner_semiaxes_m=(np.sqrt(inner_scale) / np.sqrt(values)).tolist(),
                axes_rotation_columns=rotation.tolist(),
                positive_training_count=len(positive), all_training_count=len(p),
                success_fraction_threshold=threshold, covariance_regularizer_m2=config['covariance_regularizer_m2'],
                numerical_quadratic_tolerance=config['quadratic_numeric_tolerance'],
                method=config['method'],
                scope='Cover training IK-positive points only; sample-empty cavity not certified unreachable, '
                      'no claim this is exact original OmniNav ellipsoid fitting algorithm or conservative physics.')


def shell_membership(points, fit):
    p = np.asarray(points, dtype=float)
    if p.ndim != 2 or p.shape[1] != 3 or not np.isfinite(p).all():
        raise ValueError('Need finite Nx3 points')
    delta = p - np.asarray(fit['center_base_m'])
    outer = np.einsum('ni,ij,nj->n', delta, fit['outer_metric_m_minus2'], delta)
    inner = np.einsum('ni,ij,nj->n', delta, fit['inner_metric_m_minus2'], delta)
    tol = fit['numerical_quadratic_tolerance']
    return (outer <= 1 + tol) & (inner >= 1 - tol)


def approximation_metrics(points, rates, fit):
    actual = np.asarray(rates) >= fit['success_fraction_threshold']
    accepted = shell_membership(points, fit)
    tp = int((accepted & actual).sum())
    fp = int((accepted & ~actual).sum())
    fn = int((~accepted & actual).sum())
    tn = int((~accepted & ~actual).sum())
    return dict(positions=len(points), sampled_IK_rate_positive=int(actual.sum()), shell_accepted=int(accepted.sum()),
                true_positive_vs_sampled_rate=tp, false_accept_vs_sampled_rate=fp,
                false_reject_vs_sampled_rate=fn, true_negative_vs_sampled_rate=tn,
                precision_vs_sampled_rate=tp/(tp+fp) if tp+fp else None,
                recall_vs_sampled_rate=tp/(tp+fn) if tp+fn else None,
                scope='Geometric interpolation error versus this bounded IK solver/sample threshold, '
                      'not task success/failure/true unreachability or statistically independent robot trials.')
