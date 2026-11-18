"""Default-OFF actual original metadata constructor qualification, not native.

Explicit sentinel model + fake compiled verifier/witness, real public declaration
and original resolver/backend/factory/executor classes. No Model/MjData/Runtime,
Actor, renderer, lease, world or physics is constructed or called here.
"""
from pathlib import Path
import hashlib,importlib,resource,time,types

def qualify(config=None,freeze=None,*,enabled=False):
    if enabled is not True:return None
    start=time.monotonic()
    from public_geometry_provenance import public_geometry,DECLARING_SOURCE_SHA256
    import standard_runtime
    def pinned(module):
        p=Path(module.__file__)
        if p.is_symlink()or freeze['files'].get(str(p))!=hashlib.sha256(p.read_bytes()).hexdigest():
            raise ValueError('Metadata CPU source not pinned: '+module.__name__)
        return hashlib.sha256(p.read_bytes()).hexdigest()
    pinned(standard_runtime)
    binding=importlib.import_module('ainav.native.registered_bindings')
    mods={name:importlib.import_module(name)for name in binding._SOURCES}
    context=importlib.import_module('ainav.native.registered_target_context')
    sources={name:pinned(m)for name,m in mods.items()}
    sources['mujoco_selected_target_context']=pinned(context)
    sources['registered_context_adapter']=sources['mujoco_selected_target_context']
    scene_api=importlib.import_module('ainav.native.scene_registry');pinned(scene_api)
    declared=standard_runtime.registry(scene_api)  # Real immutable metadata only.
    sentinel=object();runtime=types.SimpleNamespace(sim=types.SimpleNamespace(model=sentinel))
    checks=[]
    def fake_verify(model):
        if model is not sentinel:raise ValueError('Foreign metadata sentinel')
        checks.append('FAKE_COMPILED_VERIFIER_NOT_ACTUAL_MODEL')
    registry=types.SimpleNamespace(objects=declared.objects,
        body_to_candidate=declared.body_to_candidate,verify_compiled=fake_verify)
    shapes,source_pin=public_geometry(registry,source_path=Path(standard_runtime.__file__),enabled=True)
    kwargs=dict(proposals=mods['visual_box_proposals'],geometry=mods['native_visual_target_binding'],
        contexts=context,native_api=mods['mujoco_zyh.native_behavior_executor'],
        native_history_sha=mods['mujoco_zyh.stall_stow'].history_sha,registry=registry,public_geometry=shapes)
    try:binding.RegisteredBindingResolver(runtime,source_sha256=sources,**kwargs)
    except binding.NotAdmitted as exc:
        if str(exc)!='not_admitted: frozen public task geometry/body registry and source SHA required':raise
        rejected=True
    else:raise ValueError('Original missing public provenance predicate must refuse')
    resolver=binding.RegisteredBindingResolver(runtime,source_sha256=dict(sources,public_task_geometry=source_pin),**kwargs)
    if (resolver.public_geometry!=shapes or source_pin!=DECLARING_SOURCE_SHA256 or len(checks)!=2):
        raise ValueError('Real declared public source provenance not preserved')
    push_api=importlib.import_module('ainav.native.registered_push_api')
    session=importlib.import_module('ainav.native.session_factory')
    factory_api=importlib.import_module('ainav.native.registered_skill_factory')
    api=mods['mujoco_zyh.native_behavior_executor']
    for module in (binding,push_api,session,factory_api,api):pinned(module)
    backend=session.BehaviorSessionFactory(runtime,Path(config['SDK']),resolver,lambda:True,
        native_api=push_api.RegisteredPushAPI(registry,api))
    witness_calls=[]
    class FakeWitness:
        def validate(self,r):
            if r is not runtime:raise ValueError('Foreign fake witness runtime')
            witness_calls.append('FAKE_WITNESS_NOT_PHYSICAL_SUPPORT');return True
    witness=FakeWitness();contract=standard_runtime.placement_contract(config['common_source'])
    factory=factory_api.RegisteredSkillSessionFactory(runtime,registry,initial_witness=witness,
        journal=lambda row:None,push_backend=backend,placement_contracts={'sdk_box':contract},native_api=api)
    executor=api.NativeOptionExecutor(runtime,factory,lambda row:None)
    factory.attach_executor(executor)
    if factory._current_completed_witness()is not witness or len(witness_calls)!=1:
        raise ValueError('Original metadata constructor/attach/witness dispatch ABI')
    import torch
    if torch.cuda.is_initialized():raise ValueError('CPU metadata qualification initialized CUDA')
    return dict(schema='ORIGINAL_METADATA_CONSTRUCTORS_CPU_SENTINELS_NOT_NATIVE_v1',
        original_resolver_SHA256=pinned(binding),public_task_geometry_declaring_source_SHA256=source_pin,
        original_resolver_missing_pin_negative_rejected=rejected,
        original_resolver_real_declaring_pin_positive_returned=True,
        original_backend_factory_executor_constructor_and_attach_ABI_returned=True,
        fake_model_verifier_calls=2,fake_witness_validate_calls=1,
        actual_compiled_model_or_physical_witness_verification=False,
        Runtime_Model_MjData_Actor_renderer_lease_world_or_physics_constructed=False,
        CUDA_initialized=False,not_native_admission_or_zero=True,
        wall_sample_s=time.monotonic()-start,
        process_RSS_peak_inclusive_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        wall_excludes_return_receipt_serialization=True)
