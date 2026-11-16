"""V4 native asset delta for Data's fresh spec; no world creation or dispatch.

This is NOT the full driver: a caller must also implement surface-aware CLIMB,
public observation and actual terminal checks. No credential or planner here.
"""
from pathlib import Path
import hashlib
import json
import math

SCENE = Path(__file__).with_name('scene.json')
SCENE_SHA256 = '08a260a4bda6de75e1f0012e12a4a3a04a5c682b0534f785a7b504af4a666381'
BASE_PATH = Path(__file__).resolve().parent.parent / 'complex_dual_route_v1' / 'complex_scene.py'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load_scene(path=SCENE):
    raw=Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==SCENE_SHA256,'Exact user-confirmed V4 asset, no silent geometry edit')
    scene = json.loads(raw)
    validate(scene)
    return scene


def validate(scene):
    require(scene['scene_id'] == 'staggered-corridor-push-climb-E-skill20-20261116-v1', 'Exact V4 scene')
    require(len(scene['platforms']) == 1, 'One declared deck')
    deck = scene['platforms'][0]
    require(deck['name'] == 'goal_deck' and deck['collision_required'] is True, 'Actual collision deck')
    bounds = deck['bounds_xy_m']
    require(len(bounds) == 4 and all(type(v) in (int, float) and math.isfinite(v) for v in bounds), 'Finite deck')
    require(bounds[0] < bounds[1] and bounds[2] < bounds[3], 'Positive deck size')
    require(deck['bottom_z_m'] == 0. and deck['top_z_m'] == .2, 'Original V4 deck height')
    require(scene['task']['goal_surface_ref'] == 'cuboid_c' and scene['task']['goal_surface_height_m'] == .2, 'Elevated task, not ground XY')
    g = scene['task']['goal_bounds_xy_m']
    require(g == [11.1,12.1,-3.2,-2.0], 'Exact authorized C-top goal rectangle, never ground/static-deck substitute')
    require(len(scene['objects']) == 3, 'Three actual boxes')
    require({o['public_ref'] for o in scene['objects']} == set(scene['task']['required_final_placements']), 'All boxes required')
    for o in scene['objects']:
        require(o['size_m'] == [2.4, 1.4, .2] and o['mass_kg'] == .5 and o['bottom_mu'] == .4 and o['foot_top_mu'] == .8, 'Frozen existing box prototype')
        x, y = o['initial_xy_m']
        require(o['required_goal_xy_m'][1] == y, 'No side push')
        require(all(0 < gx + .11 - x <= .8 for gx in o['allowed_placement_x_m']), 'Native stroke domain')
    c = next(o for o in scene['objects'] if o['public_ref'] == 'cuboid_c')
    require(math.isclose(c['required_goal_xy_m'][0] + 1.2, bounds[0], abs_tol=1e-9), 'C front docks deck')
    require(scene['private_terminal_acceptance']['required_distinct_original_placement_receipts'] == 3, 'Three placement terminal check')
    require(scene['private_terminal_acceptance']['requires_actual_CLIMB_success_receipts'] is True, 'Real climb required')
    return scene


def public_task(scene, base_module):
    """Same public geometry for A/B; never publishes a correct action sequence."""
    validate(scene)
    value = base_module.public_task(scene)
    value['platforms'] = [dict(surface_ref=d['name'], bounds_xy_m=list(d['bounds_xy_m']), top_z_m=d['top_z_m']) for d in scene['platforms']]
    return value


def registry(scene, registry_api):
    """Use supplied exact frozen SceneRegistry API, no dynamic state or imports."""
    validate(scene)
    surfaces = [registry_api.SurfaceSpec('ground', 'ground', tuple(scene['floor']['native_ground_bounds_xy_m']), 0.)]
    surfaces += [registry_api.SurfaceSpec(d['name'], d['name'], tuple(d['bounds_xy_m']), d['top_z_m']) for d in scene['platforms']]
    objects = [registry_api.ObjectSpec(o['public_ref'], o['body_name'], tuple(o['size_m']), 'ground') for o in scene['objects']]
    from goal_support import registry_type
    return registry_type(registry_api)(objects, surfaces, registry_api.GoalSpec('cuboid_c', tuple(scene['task']['goal_bounds_xy_m'])))


def construct_into_native_spec(sim, *, scene, main_steps, base_module, expected_base_sha256, mujoco_api):
    """Called ONLY by Data's guarded fresh constructor. Does not compile/step.

    Deck is added BEFORE boxes so original box/foot explicit contact-pair logic
    also includes it. If construction fails, discard that fresh spec; no retry
    on a partially modified spec, and no modifications to a live runtime.
    """
    validate(scene)
    require(type(main_steps) is int and main_steps == 0 and float(sim.data.time) == 0. and not sim.queue, 'Fresh zero-step spec and FIFO')
    path = Path(base_module.__file__).resolve(strict=True)
    require(hashlib.sha256(path.read_bytes()).hexdigest() == expected_base_sha256, 'Exact base constructor source')
    base_module.validate(scene)
    names = {g.name for g in sim.spec.geoms}
    require('goal_deck' not in names, 'No repeat or hot install')
    require(not any(o['body_name'] in {b.name for b in sim.spec.bodies} for o in scene['objects']), 'No previously installed boxes')
    deck = scene['platforms'][0]
    x0, x1, y0, y1 = deck['bounds_xy_m']; z0, z1 = deck['bottom_z_m'], deck['top_z_m']
    sim.spec.worldbody.add_geom(name=deck['name'], type=mujoco_api.mjtGeom.mjGEOM_BOX,
        pos=[(x0+x1)/2, (y0+y1)/2, (z0+z1)/2], size=[(x1-x0)/2, (y1-y0)/2, (z1-z0)/2],
        contype=2, conaffinity=3, friction=[.7, 0., 0.], group=1, rgba=[.56, .74, .77, 1.])
    result = base_module.construct_into_native_spec(sim, scene=scene, main_steps=main_steps)
    # This is a NEW geometry asset, not old398 render-only proof. Same public
    # review colors are explicit on the three new task geoms before compile.
    for obj in scene['objects']:
        value=obj['review_color'];sim.spec.geom(obj['body_name']+'_geom').rgba=[*(int(value[i:i+2],16)/255. for i in (1,3,5)),1.]

    return dict(base=result, added_surface='goal_deck', goal_surface_height_m=.2,
        new_physics_steps=0, native_compilation_verified=False, CLIMB_driver_integrated=False,
        actual_terminal_evaluator_integrated=False, physical_dispatch_authorized=False)
