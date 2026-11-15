"""Data-only V4 same-world native execution assembly AFTER genuine capture.

No world creation, step, dispatch, planner choice, terrain extension or terminal
success. Reuse the original resolver/backend/executor and placement evidence;
connect the V4 selected task factory rather than the old NAV/PUSH-only factory.
"""
from pathlib import Path
import hashlib
import importlib
import sys

from native_entry import _exact_base
from public_candidates import declarations
from task_factory import factory_class
from v4_native_asset import SCENE_SHA256, load_scene, require, validate

PLACEMENT_EVIDENCE_SHA = '461d4146aeed1622be01f1952a1b4d582eab631cbf14f9defbdc3e0a78099196'


def finite_placement_contracts(scene, *, source_root):
    """Original immutable contracts for precisely the common public PUSH domain."""
    validate(scene)
    require(scene == load_scene(), 'Exact confirmed V4 geometry, not an amended live layout')
    root = Path(source_root).resolve(strict=True)
    sys.path.insert(0, str(root))
    module = importlib.import_module('ainav.native.placement_contract')
    require(Path(module.__file__).resolve() == root / 'ainav/native/placement_contract.py',
            'Same original placement contract source')
    objects = {o['public_ref']: o for o in scene['objects']}
    contracts = []
    for row in declarations(scene):
        if row['skill'] != 'PUSH':
            continue
        obj = objects[row['target_ref']]
        params = row['parameters']
        goal = (params['goal_world_x_m'], params['goal_world_y_m'])
        require(params['surface_height_m'] == 0., 'No unqualified elevated PUSH')
        contracts.append(module.PlacementContract(target_ref=row['target_ref'],
            public_goal_xy_m=goal, docking_plane_x_m=goal[0] + obj['size_m'][0] / 2,
            box_size_m=tuple(obj['size_m']), source_surface_height_m=0.,
            native_stop_distance_m=.11, mode='declared_native_stop_offset'))
    require(len(contracts) == 6 and len({c.sha256 for c in contracts}) == 6,
            'Precisely six shared immutable original placement contracts')
    return {c.sha256: c for c in contracts}


def _current_contact_owners(owners, runtime, registry, climb_type):
    """Private contact authority comes ONLY from the installed original session.

    Selecting/declaring CLIMB or simply seeing a box never admits its contacts.
    This does NOT authorize subsequent NAV on a dynamic box; that owner transfer
    still needs its own implementation. Original forbidden-body policy remains.
    """
    executor = owners.get('executor')
    if executor is None or executor.option is None:
        return None, frozenset()
    require(executor.runtime is runtime and executor.factory is owners['factory'],
            'Contact authority belongs to actual same-world executor/factory')
    option, session = executor.option, executor.session
    if option.skill == 'PUSH':
        native = owners['factory'].native_option_for(option)
        binding = owners['backend']._bindings.get(native.sha256)
        if binding is None:
            return None, frozenset()
        matches = [o.ref for o in registry.objects.values() if o.body_name == binding.target.body_name]
        require(len(matches) == 1, 'One actual selected original PUSH body')
        return matches[0], frozenset()
    if option.skill != 'CLIMB':
        return None, frozenset()
    require(session is not None and session.runtime is runtime and session.entered
            and isinstance(session.machine, climb_type),
            'CLIMB contact authority requires the actually entered original CLIMB session')
    machine = session.machine
    binding = machine.binding
    native = owners['factory'].native_option_for(option)
    require(machine.global_runtime is runtime and machine.r.sim.data is runtime.sim.data
            and machine.r.sim.queue is runtime.sim.queue
            and binding.option_sha256 == native.sha256
            and binding.opaque_ref == native.target_ref
            and binding.object_ref in registry.objects
            and registry.objects[binding.object_ref].body_name == binding.body_name,
            'Original entered CLIMB target/body/hash/world/FIFO identity required')
    return None, frozenset((binding.object_ref,))


def build_after_actual_capture(components=None, *, source_root=None, bundle=None,
                               guard=None, journal=None, enabled=False):
    require(type(enabled) is bool, 'Explicit owner opt-in')
    if not enabled:
        return None
    require(callable(guard) and callable(journal), 'Original Data owner guard/journal required')
    guard()  # No source/native imports or resource work before the actual owner.
    original, _ = _exact_base()
    root = original._source(source_root)
    require(type(components) is dict and components['scene_sha256'] == SCENE_SHA256
            and components['scene'] == load_scene(), 'Exact actual V4 cold-component scene')
    runtime, registry = components['runtime'], components['registry']
    require(registry.goal.surface_ref == 'goal_deck'
            and registry.surfaces['goal_deck'].top_z_m == .6,
            'Actual elevated V4 registry, never old ground-goal fallback')
    # This ORIGINAL helper requires SupportedCapture type, complete owner,
    # >=2 actually issued steps, exact same runtime/data and accounted clock.
    witness = original.completed_initial_witness(components)
    from ainav.native.registered_bindings import RegisteredBindingResolver, _SOURCES
    from ainav.native.registered_push_api import RegisteredPushAPI
    from ainav.native.session_factory import BehaviorSessionFactory
    from ainav.native.registered_guards import check_object_contacts
    from ainav.native.registered_climb import RegisteredClimbMachine
    from mujoco_zyh import native_behavior_executor as api, stall_stow
    modules = {name: importlib.import_module(name) for name in _SOURCES}
    contexts = importlib.import_module('ainav.native.registered_target_context')
    for module in [*modules.values(), contexts]:
        require(Path(module.__file__).resolve().is_relative_to(root), 'No foreign selected native source')
    pins = {name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for name, module in modules.items()}
    pins['mujoco_selected_target_context'] = pins['registered_context_adapter'] = hashlib.sha256(Path(contexts.__file__).read_bytes()).hexdigest()
    pins['public_task_geometry'] = SCENE_SHA256
    resolver = RegisteredBindingResolver(runtime, proposals=modules['visual_box_proposals'],
        geometry=modules['native_visual_target_binding'], contexts=contexts, native_api=api,
        native_history_sha=stall_stow.history_sha, source_sha256=pins, registry=registry,
        public_geometry={o.body_name: o.size_m for o in registry.objects.values()})
    before = api.world_snapshot(runtime)
    world = (runtime.sim, runtime.sim.model, runtime.sim.data, runtime.sim.queue)
    owners = {}
    def guards():
        guard()
        require(all(a is b for a, b in zip(world, (runtime.sim, runtime.sim.model,
                    runtime.sim.data, runtime.sim.queue))), 'Original same-world/FIFO aliases changed')
        selected, entered = _current_contact_owners(owners, runtime, registry, RegisteredClimbMachine)
        # Retain >1N threshold, native forbidden bodies and guards. Only a real
        # entered selected CLIMB can admit feet on its selected movable object.
        return check_object_contacts(runtime, registry, selected_push_ref=selected,
                                     entered_climb_refs=entered)
    backend = BehaviorSessionFactory(runtime, bundle, resolver, guards,
                                    native_api=RegisteredPushAPI(registry, api))
    owners['backend'] = backend
    cls = factory_class(source_root=root, enabled=True)
    climb = cls.destination_adapter_class(runtime, registry, resolver, journal=journal)
    contracts = finite_placement_contracts(components['scene'], source_root=root)
    factory = cls(runtime, registry, initial_witness=witness, journal=journal,
                  push_backend=backend, placement_contracts=contracts, native_api=api, climb_adapter=climb)
    executor = api.NativeOptionExecutor(runtime, factory, journal)
    factory.attach_executor(executor)
    owners.update(executor=executor, factory=factory)
    evidence_path = Path(__file__).resolve().parent.parent / 'complex_dual_route_v1/terminal_stop.py'
    require(not evidence_path.is_symlink() and hashlib.sha256(evidence_path.read_bytes()).hexdigest() == PLACEMENT_EVIDENCE_SHA,
            'Exact original placement-evidence consumer, not the ground terminal wrapper')
    sys.path.insert(0, str(evidence_path.parent))
    evidence_module = importlib.import_module('terminal_stop')
    require(Path(evidence_module.__file__).resolve() == evidence_path, 'No ambient terminal module')
    placements = evidence_module.ActualPlacementEvidence(runtime, registry, components['scene'])
    require(api.world_snapshot(runtime) == before, 'Execution assembly changed actual physical world/FIFO')
    journal(dict(event='V4_actual_capture_to_original_execution_assembled',
                 time_s=float(runtime.sim.data.time), actual_capture=witness.report(),
                 connected_skills=list(factory.connected_skills),
                 current_controller_constructed=False, native_commands_issued=0,
                 static_deck_40cm_dynamic_box_NAV_or_task_ready=False, model_input=False))
    return dict(factory=factory, executor=executor, resolver=resolver, initial_witness=witness,
                placement_catalogue=contracts, placements=placements, guards=guards,
                source_provenance=pins, world_steps_issued=0, actual_dynamic_qualification=False,
                full_V4_driver_and_task_terminal_integrated=False)
