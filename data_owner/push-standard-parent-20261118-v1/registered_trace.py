"""Private original registered NAV/PUSH call-site assembly, no execution.

Keep registered source support/12N/goal/FF/STOW and native class chains intact.
No rewriting of imported/shared modules, Actor objects, native settled readers,
or frozen files. The final parent still owns actual query/receipt/IO/guards.
"""
from pathlib import Path
import importlib
import types

from actor_trace import INFER_SHA, NAV_SHA, instrument_callsite, copy_infer_method
from standard_runtime import _import_pinned, need

PUSH_SHA = '02b3ed66ec750a793e4806d6e23126dc98e821935255be119f9bdd65fc38d025'


def _private_function(original, **overrides):
    need(type(original) is types.FunctionType and not original.__closure__,
         'Original non-closure private-copy boundary')
    namespace = dict(original.__globals__)
    need(all(k in namespace for k in overrides), 'No invented original constructor hook')
    namespace.update(overrides)
    result = types.FunctionType(original.__code__, namespace, original.__name__, original.__defaults__)
    result.__kwdefaults__ = original.__kwdefaults__
    return result


def assemble(*, source_root=None, bundle=None, trace=None, enabled=False):
    need(type(enabled) is bool, 'Explicit new source assembly')
    if not enabled:
        return None
    root = Path(source_root).resolve(strict=True)
    sdk = Path(bundle).resolve(strict=True)
    push = _import_pinned(root, 'ainav.native.registered_push_api', PUSH_SHA)
    nav = _import_pinned(root, 'ainav.native.registered_compact_nav', NAV_SHA)
    original_infer = importlib.import_module('runtime').infer
    traced_infer = instrument_callsite(original_infer, source_path=sdk/'switch/runtime.py',
        source_sha256=INFER_SHA, function_name='infer', actor_expression='actor', trace=trace)
    nav_update = instrument_callsite(nav.RegisteredCompactNav.update,
        source_path=root/'ainav/native/registered_compact_nav.py', source_sha256=NAV_SHA,
        function_name='update', class_name='RegisteredCompactNav', actor_expression='r.nav_actor', trace=trace)

    class TracedRegisteredNav(nav.RegisteredCompactNav):
        update = nav_update

    original_compile = push._compile_registered_push_machine
    def compile_private(*args, **kwargs):
        cls, proof = original_compile(*args, **kwargs)
        module = importlib.import_module('sys').modules.get(cls.__module__)
        need(module is not None and getattr(module, 'Machine', None) is cls and
             cls.__module__.startswith('_wm_behavior_machine_') and
             'update' in cls.__dict__ and 'infer' in cls.update.__globals__,
             'Only a freshly generated private Machine BEFORE wrapping/session creation')
        # This fresh class is owned by this compiler invocation. Do NOT set
        # session.machine.update to a base method: that would skip derived checks.
        cls.update = copy_infer_method(cls.__dict__['update'], traced_infer)
        return cls, dict(proof, Data_actual_actor_callsite=True,
                         original_update_bytecode_and_class_chain_retained=True)

    selected = _private_function(push._selected_registered_push_session,
                                 _compile_registered_push_machine=compile_private)
    method = _private_function(push.RegisteredPushAPI.selected_push_session,
                              _selected_registered_push_session=selected)
    class TracedRegisteredPushAPI(push.RegisteredPushAPI):
        selected_push_session = method
    # No instance/session/controller/world constructed, even on enabled assembly.
    return dict(nav_constructor=TracedRegisteredNav, push_api_class=TracedRegisteredPushAPI,
                compile_private_push=compile_private,
                actor_call_metadata_complete_for_final_parent=False,
                physical_admission=False)


def connect_after_capture(components=None, *, source_root=None, bundle=None,
                          guard=None, journal=None, trace=None, enabled=False):
    """Original same-world registered NAV/PUSH factory, no route/step/success.

    Must follow REAL SupportedCapture commands in the future parent. This cannot
    make own-zero pass by inventing a witness or run the unused SDK whole loop.
    """
    need(type(enabled) is bool, 'Explicit future parent connection')
    if not enabled:
        return None
    need(callable(guard) and callable(journal) and guard() is not False,
         'Actual original parent authority/lease/watch and journal')
    root = Path(source_root).resolve(strict=True)
    from ainav.native.supported_capture import SupportedCapture, ActualCaptureWitness
    from ainav.native.registered_bindings import RegisteredBindingResolver, _SOURCES
    from ainav.native.registered_guards import check_object_contacts
    from ainav.native.session_factory import BehaviorSessionFactory
    from ainav.native.registered_skill_factory import RegisteredSkillSessionFactory
    from mujoco_zyh import native_behavior_executor as api, stall_stow
    r, reg, capture = components['runtime'], components['registry'], components['capture']
    need(type(capture) is SupportedCapture and capture.r is r and capture.s is r.sim and
         capture.complete and capture.actual_issued_steps >= 2 and
         r.step_count == capture.actual_issued_steps and
         abs(float(r.sim.data.time)-r.step_count*.005) < 1e-7,
         'Actual completed initial capture accounting, no admission/witness fabrication')
    witness = ActualCaptureWitness(capture)
    witness.validate(r)
    hooks = assemble(source_root=root, bundle=bundle, trace=trace, enabled=True)
    modules = {name: importlib.import_module(name) for name in _SOURCES}
    context = importlib.import_module('ainav.native.registered_target_context')
    import hashlib
    for module in [*modules.values(), context]:
        need(Path(module.__file__).resolve().is_relative_to(root), 'No ambient target/source modules')
    pins = {name: hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for name, m in modules.items()}
    pins['mujoco_selected_target_context'] = hashlib.sha256(Path(context.__file__).read_bytes()).hexdigest()
    pins['registered_context_adapter'] = pins['mujoco_selected_target_context']
    contract = components['placement_contract']
    resolver = RegisteredBindingResolver(r, proposals=modules['visual_box_proposals'],
        geometry=modules['native_visual_target_binding'], contexts=context, native_api=api,
        native_history_sha=stall_stow.history_sha, source_sha256=pins, registry=reg,
        public_geometry={o.body_name: o.size_m for o in reg.objects.values()})
    owners = {}
    def guards():
        need(guard() is not False, 'Current original authority/resource guard')
        selected = None
        executor = owners.get('executor')
        if executor is not None and executor.option is not None and executor.option.skill == 'PUSH':
            binding = owners['backend']._bindings.get(executor.option.sha256)
            if binding is not None:
                matches = [o.ref for o in reg.objects.values() if o.body_name == binding.target.body_name]
                need(matches == ['sdk_box'], 'Actual current original PUSH body identity')
                selected = matches[0]
        return check_object_contacts(r, reg, selected_push_ref=selected)
    backend = BehaviorSessionFactory(r, bundle, resolver, guards,
        native_api=hooks['push_api_class'](reg, api))
    owners['backend'] = backend
    factory = RegisteredSkillSessionFactory(r, reg, initial_witness=witness, journal=journal,
        push_backend=backend, placement_contracts={'sdk_box': contract}, native_api=api,
        nav_constructor=hooks['nav_constructor'])
    executor = api.NativeOptionExecutor(r, factory, journal)
    factory.attach_executor(executor)
    owners['executor'] = executor
    need(guard() is not False, 'Original connection postguard')
    return dict(factory=factory, executor=executor, resolver=resolver, guards=guards,
                initial_witness=witness, world_steps_issued_by_connection=0,
                root_route_selected=False, actual_dynamic_qualification=False)
