"""Only a genuine OriginalL0Witness can connect this PUSH-only registered host."""
from pathlib import Path
import hashlib,importlib
from standard_runtime import need
from l0_witness import OriginalL0Witness
from registered_trace import assemble


def connect(components=None,*,witness=None,source_root=None,bundle=None,trace=None,guard=None,journal=None,enabled=False):
    need(type(enabled)is bool,'Explicit qualified future L0 opt-in')
    if not enabled:return None
    need(type(witness)is OriginalL0Witness and witness.r is components['runtime'],'Genuine L0 witness, NOT synthetic SupportedCapture')
    witness.validate(components['runtime']);root=Path(source_root).resolve(strict=True)
    from ainav.native.registered_bindings import RegisteredBindingResolver,_SOURCES
    from ainav.native.registered_guards import check_object_contacts
    from ainav.native.session_factory import BehaviorSessionFactory
    from ainav.native.registered_skill_factory import RegisteredSkillSessionFactory
    from mujoco_zyh import native_behavior_executor as api,stall_stow
    r,reg=components['runtime'],components['registry'];hooks=assemble(source_root=root,bundle=bundle,trace=trace,enabled=True)
    modules={name:importlib.import_module(name)for name in _SOURCES}
    context=importlib.import_module('ainav.native.registered_target_context')
    for module in [*modules.values(),context]:need(Path(module.__file__).resolve().is_relative_to(root),'No ambient source')
    pins={name:hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()for name,m in modules.items()}
    pins['mujoco_selected_target_context']=hashlib.sha256(Path(context.__file__).read_bytes()).hexdigest()
    pins['registered_context_adapter']=pins['mujoco_selected_target_context']
    from public_geometry_provenance import public_geometry
    public_shapes,declaring_sha=public_geometry(reg,source_path=Path(importlib.import_module('standard_runtime').__file__),enabled=True)
    pins['public_task_geometry']=declaring_sha
    resolver=RegisteredBindingResolver(r,proposals=modules['visual_box_proposals'],geometry=modules['native_visual_target_binding'],
        contexts=context,native_api=api,native_history_sha=stall_stow.history_sha,source_sha256=pins,registry=reg,
        public_geometry=public_shapes)
    owners={}
    def guards():
        need(guard()is not False,'Actual current original authority/lease/watch')
        selected=None;executor=owners.get('executor')
        if executor is not None and executor.option is not None:
            need(executor.option.skill=='PUSH','L0 host never emits NAV or another task')
            binding=owners['backend']._bindings.get(executor.option.sha256)
            if binding is not None:
                matched=[o.ref for o in reg.objects.values()if o.body_name==binding.target.body_name]
                need(matched==['sdk_box'],'Actual selected original body');selected=matched[0]
        return check_object_contacts(r,reg,selected_push_ref=selected)
    backend=BehaviorSessionFactory(r,bundle,resolver,guards,native_api=hooks['push_api_class'](reg,api));owners['backend']=backend
    factory=RegisteredSkillSessionFactory(r,reg,initial_witness=witness,journal=journal,push_backend=backend,
        placement_contracts={'sdk_box':components['placement_contract']},native_api=api,nav_constructor=hooks['nav_constructor'])
    executor=api.NativeOptionExecutor(r,factory,journal);factory.attach_executor(executor);owners['executor']=executor
    need(guard()is not False,'Original postconnection guard')
    return dict(factory=factory,executor=executor,resolver=resolver,guards=guards,initial_witness=witness,
        world_steps_issued_by_connection=0,advertised_skills=('PUSH',),original_12N_full_exit_not_replaced=True)
