"""Finite tip-cloud retreat geometry, NO FK/controller/physics or online release.

Formalizes the existing v317 scalar standoff and adds a swept lateral-membership
sufficient bound. Both operate ONLY on an explicitly supplied finite cloud.
No continuous joint/path/actual tracking/full-robot guarantee is inferred.
"""
from __future__ import annotations

import math


def finite(x):
    if type(x) not in (int,float) or not math.isfinite(x):
        raise ValueError('Expected a finite scalar')
    return float(x)


def vec3(x):
    if len(x)!=3:raise ValueError('Expected three coordinates')
    return tuple(finite(v) for v in x)


def preview_tip_retreat(points_box, half_size, world_x_in_box, *, tip_radius_m=.01,
                        planning_margin_m=.005, forecast_margin_m=.005,
                        max_shift_m=.04, lateral_membership='swept'):
    """Return finite-cloud request, never state writes or execution authorization.

    For a world -x retreat d: each point in box coordinates becomes p - d*a,
    where a=R_box.T*e_world_x. 'fixed' reproduces the finite S0 plane expression,
    not the old FK/SDK pipeline. 'swept' includes every potentially entering tip
    point up to D by inflating yz with D*abs(a_y/z). More conservative != task gain.
    """
    points=tuple(vec3(p) for p in points_box)
    half=vec3(half_size);axis=vec3(world_x_in_box)
    if not points:raise ValueError('Missing cloud is unknown, not an empty safe set')
    if min(half)<=0:raise ValueError('Box half sizes must be positive')
    if abs(sum(v*v for v in axis)-1)>1e-9 or axis[0]<.95:
        raise ValueError('Outside frozen aligned positive-retreat frame domain')
    radius,margin,forecast,cap=map(finite,(tip_radius_m,planning_margin_m,forecast_margin_m,max_shift_m))
    if radius<=0 or margin<0 or not 0<=forecast<=.005 or not 0<=cap<=.04:
        raise ValueError('Invalid inflation or original 40mm retreat domain')
    if lateral_membership not in ('fixed','swept'):raise ValueError('Unknown membership rule')
    inflation=radius+margin+forecast
    dy=cap*abs(axis[1]) if lateral_membership=='swept' else 0.
    dz=cap*abs(axis[2]) if lateral_membership=='swept' else 0.
    ids=[i for i,p in enumerate(points) if abs(p[1])<=half[1]+inflation+dy and abs(p[2])<=half[2]+inflation+dz]
    maxx=max((points[i][0] for i in ids),default=None)
    request=0. if maxx is None else max(0.,(maxx+half[0]+inflation)/axis[0])
    within=request<=cap
    return dict(schema='finite-tip-envelope-standoff-preview-v1',membership=lateral_membership,
                points=len(points),critical_point_ids=ids,critical_points=len(ids),
                inflation_m=inflation,additional_y_band_m=dy,additional_z_band_m=dz,
                maximum_critical_x_m=maxx,minimum_front_plane_request_m=request,
                max_original_shift_m=cap,
                status=('finite_cloud_sufficient_at_final_retreat' if lateral_membership=='swept' else 'fixed_subset_front_plane_only') if within else 'no_sufficient_request_within_cap_UNKNOWN_feasibility',
                request_within_original_domain=within,
                execution_authorized=False,
                proof_in_exact_arithmetic_NOT_machine_interval_verified=True,
                scope='finite tip-sphere cloud in final translated fixed configuration only',
                not_certified=['continuous interpolation','residual interior','actual tracking error','retreat motion itself',
                               'other robot geometry','support','torque','contact skill','overall navigation'])


def translate_cloud(points, axis, shift):
    a=vec3(axis);d=finite(shift)
    return tuple(tuple(v-d*w for v,w in zip(vec3(p),a)) for p in points)


def tip_sphere_box_gap(point, half_size, radius):
    """Exact sphere-center signed AABB distance minus radius, synthetic checks only."""
    p,h=vec3(point),vec3(half_size)
    q=[abs(v)-w for v,w in zip(p,h)]
    return math.sqrt(sum(max(v,0)**2 for v in q))+min(max(q),0)-finite(radius)
