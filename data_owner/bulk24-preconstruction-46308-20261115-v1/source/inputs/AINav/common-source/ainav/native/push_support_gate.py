"""Original registered PUSH source predicate shared by admission/construction.

Pure necessary current-state check; no controller, route, goal choice or physics.
Thresholds are byte-for-byte semantic equivalents of the existing constructor.
"""
import math


def require_push_source_support(bounds,height,feet,loads):
    if len(feet)!=4 or any(len(f)!=3 for f in feet) or len(loads)!=4:raise ValueError('Actual four-foot source sample required')
    if (not all(math.isfinite(float(v)) for f in feet for v in f)
        or not all(math.isfinite(float(v)) for v in loads) or min(loads)<12.
        or not all(abs(f[2]-height-.022)<.04 for f in feet)):
        raise ValueError('Actual four-foot loaded registered PUSH source required')
    x0,x1,y0,y1=bounds
    if not all(x0<f[0]<x1 and y0<f[1]<y1 for f in feet):
        raise ValueError('Selected PUSH source footprint outside declared support')
    return dict(four_current_feet_loaded=True,minimum_load_N=12.,height_tolerance_m=.04,
        foot_radius_m=.022,source_height_m=height,original_thresholds_unchanged=True,model_input=False)


def current_push_source_support(runtime,registry,body,height):
    from .scene_registry import declared_push_source
    obj=declared_push_source(registry,body,height);p=runtime.sim
    ids=[p.model.body(n+'_foot').id for n in ('FR','FL','RR','RL')]
    surface=registry.surfaces[obj.initial_support]
    return require_push_source_support(surface.bounds_xy_m,height,p.data.xpos[ids].tolist(),p.forces[ids,2].tolist())
