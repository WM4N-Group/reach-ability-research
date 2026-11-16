"""Cold-only actual registered terrain ABI for the ORIGINAL selected PUSH.

The selected original API eagerly reads runtime.staircase before constructing
its own AttemptTerrain. A registered cold Runtime does not install legacy
integrated-course Terrain. Supply actual registry geometry, NOT None/flat-map/
dummy success. Diagnostics use the ORIGINAL immutable PlacementContract reader.
No original source/controller/guard is replaced; no world/Actor/step is created.
"""
from pathlib import Path
import hashlib, importlib
from types import MappingProxyType
from v4_native_asset import require, load_scene, SCENE_SHA256

PINS = {
    'scene_registry.py': '1d5baefee91a46d0b92f72663eff59b49eb7e7cc18754f95ef036458502566bf',
    'placement_contract.py': '882481668854468a59ec4aacfc44f7912286fdece8c4d91e11ce010f6dc98511',
    'registered_push_api.py': '02b3ed66ec750a793e4806d6e23126dc98e821935255be119f9bdd65fc38d025',
}


def _original(root):
    root = Path(root).resolve(strict=True)
    modules = {}
    for name, pin in PINS.items():
        path = root / 'ainav/native' / name
        require(not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == pin,
                'Exact selected original terrain/PUSH/placement ABI: ' + name)
        # registered_push_api imports native modules; its source is verified only.
        if name != 'registered_push_api.py':
            module = importlib.import_module('ainav.native.' + name[:-3])
            require(Path(module.__file__).resolve() == path, 'No ambient original terrain/placement module')
            modules[name] = module
    return modules['scene_registry.py'], modules['placement_contract.py']


def _snapshot(r):
    p = r.sim
    return (r.step_count, float(p.data.time), p, p.model, p.data, p.queue,
            p.data.qpos.tobytes(), p.data.qvel.tobytes(), tuple(v.tobytes() for v in p.queue),
            r.last.array().tobytes(), p.controller, p.box_push_target)


def install_cold_registered_terrain(components=None, *, source_root=None, guard=None, journal=None, enabled=False):
    require(type(enabled) is bool, 'Explicit cold constructor opt-in')
    if not enabled:
        return None
    require(callable(guard) and callable(journal) and guard() is not False, 'Actual Data cold owner guard/journal')
    require(type(components) is dict and components['scene_sha256'] == SCENE_SHA256
            and components['scene'] == load_scene(), 'Exact same V4 scene, not a changed live layout')
    r, registry = components['runtime'], components['registry']
    require(r.step_count == 0 and float(r.sim.data.time) == 0. and not r.sim.queue
            and not hasattr(r, 'staircase'),
            'Fresh cold Runtime only: never replace a live/existing terrain or recover a failed root')
    api, placement = _original(source_root)
    from execution_entry import finite_placement_contracts
    from v4_native_asset import registry as make_registry
    expected = make_registry(components['scene'], api)
    require(type(registry) is api.SceneRegistry and registry.surfaces == expected.surfaces
            and registry.objects == expected.objects and registry.goal == expected.goal
            and not registry.retired_objects, 'Actual original registry and exact unretired V4 geometry')
    contracts = finite_placement_contracts(components['scene'], source_root=source_root)
    require(all(type(c) is placement.PlacementContract for c in contracts.values()), 'Original six immutable placement contracts')
    contract_sha = tuple(sorted(contracts))
    before = _snapshot(r)
    world = (r.sim, r.sim.model, r.sim.data, r.sim.queue)

    class V4RegisteredColdTerrain(api.RegisteredTerrain):
        def __init__(self):
            super().__init__(registry)
            self.placement_contracts = MappingProxyType(dict(contracts))

        def dock_metrics(self, view):
            # This is PRIVATE measured diagnostics, not a new success predicate.
            require(all(a is b for a, b in zip(world, (r.sim, view.model, view.data, view.queue)))
                    and getattr(r, 'staircase', None) is self and self.registry is registry,
                    'Original same-world selected view/FIFO and installed actual registered terrain')
            require(tuple(sorted(c.sha256 for c in self.placement_contracts.values())) == contract_sha,
                    'No modified/rebased original placement contract')
            name = view.model.body(view.box_id).name
            objects = [obj for obj in registry.objects.values() if obj.body_name == name]
            require(len(objects) == 1 and objects[0].ref not in registry.retired_objects,
                    'Actual selected registered body, never old fixed B/C or an unregistered box')
            goal = view.box_push_target.detach().cpu().numpy()[0, :2].tolist()
            matched = [c for c in self.placement_contracts.values() if c.target_ref == objects[0].ref
                       and c.box_size_m == objects[0].size_m
                       and all(abs(a-b) <= 1e-6 for a,b in zip(c.drive_goal_xy_m,goal))]
            require(len(goal) == 2 and len(matched) == 1, 'Unique original frozen native drive goal; no initial-pose guess')
            return placement.PlacementTerrain(matched[0]).dock_metrics(view)

    terrain = V4RegisteredColdTerrain()
    # Both actual geometry methods are inherited BYTE-FOR-BYTE, including original20cm.
    require(type(terrain).height_at is api.RegisteredTerrain.height_at
            and type(terrain).climb_geometry is api.RegisteredTerrain.climb_geometry
            and type(terrain).surface_geometry is api.RegisteredTerrain.surface_geometry,
            'No flat terrain/ray stub/height-domain extension')
    require(_snapshot(r) == before and guard() is not False, 'Cold terrain assembly must not change world/FIFO/commands')
    ref = journal(dict(event='V4_cold_original_registered_terrain_ABI_installed_SOURCE_NOT_PUSH_qualified',
        original_source_sha256=PINS, exact_six_placement_contracts=list(contract_sha),
        original_registered_height_and20cm_geometry_inherited=True,
        original_selected_AttemptTerrain_push_ready_and_native_guards_unchanged=True,
        dock_metrics_is_original_PlacementTerrain_reader_not_new_success=True,
        Runtime_world_Actor_command_or_step_created=False, model_input=False,
        PUSH_native_success_or_NN_or_full_task_claimed=False))
    require(type(ref) is str and bool(ref), 'Durable cold ABI assembly receipt')
    require(_snapshot(r) == before and not hasattr(r, 'staircase') and guard() is not False,
            'No competing/hot terrain replacement or physical change')
    r.staircase = terrain
    return dict(original_registered_terrain_bound=True, original_source_sha256=PINS,
                six_contract_sha256=list(contract_sha), installation_evidence_ref=ref,
                cold_task_steps=0, model_input=False, actual_PUSH_constructor_qualified=False)
