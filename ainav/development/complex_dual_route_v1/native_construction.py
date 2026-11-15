"""Data-owned native construction entry points, disabled unless explicit.

There is no CLI or launch/lease authority here. Data must freeze these functions
in a NEW scene preflight/program, invoke the supplied real guard and use fresh
paths. Merely importing/running software tests never creates a native world.
"""
from pathlib import Path
import hashlib,importlib.util,json,sys,os,tempfile
from complex_scene import load_scene,construct_into_native_spec,registry,need
SHA_ROBOT_SIGNATURE_SOURCE='706c9c7c254e7611526af17e7107ad8a4ba788e6a4e9631d400a7476a1a43abd'
SHA_REGISTERED_RUNTIME='ad04b58361e0256e4dc1b95441a38b4b37befe8f31e7d9a6ec9efdae47e202d9'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def _source(root):
    root=Path(root).resolve(strict=True)
    for rel,pin in [('build_transfer_scene_native.py',SHA_ROBOT_SIGNATURE_SOURCE),('ainav/native/registered_runtime.py',SHA_REGISTERED_RUNTIME)]:need(sha(root/rel)==pin,'Exact original constructor/helper source: '+rel)
    sys.path.insert(0,str(root));return root

def compile_static_asset(*,source_root=None,bundle=None,output_model=None,guard=None,enabled=False):
    if type(enabled)is not bool:raise ValueError('Explicit owner opt-in')
    if not enabled:return None
    need(callable(guard),'Data actual new authority/resource guard callback required');guard()
    root=_source(source_root);bundle=Path(bundle).resolve(strict=True);out=Path(output_model).resolve()
    need(not out.exists()and out.parent.is_dir(),'Fresh exclusive owner asset path; never overwrite a sealed model')
    import mujoco
    from mujoco_zyh.source_bundle import verify_bundle
    receipt=verify_bundle(bundle);switch=bundle/'switch';sys.path.insert(0,str(switch))
    from plugins import Plugin
    p=root/'build_transfer_scene_native.py';spec=importlib.util.spec_from_file_location('_cx_original_robot_signature_helper',p);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    native=Plugin('push',['bridge','model'])
    with native.active():sim=native['bridge'].PushBridge(seed=4301,delay_ms=20,push_distance=.6)
    need(float(sim.data.time)==0. and not sim.queue,'Original SDK constructor must be zero-step')
    original=helper.robot_signature(sim.model);scene=load_scene();construction=construct_into_native_spec(sim,scene=scene,main_steps=0);model=sim.spec.compile();guard()
    need(helper.robot_signature(model)==original,'Robot/actuator/engine signature changed')
    # Visual capacity is fixed on this NEW static model before any task Runtime.
    model.vis.global_.offwidth=max(int(model.vis.global_.offwidth),scene['third_view']['width']);model.vis.global_.offheight=max(int(model.vis.global_.offheight),scene['third_view']['height'])
    registry(scene,source_root=root).verify_compiled(model)
    need(not out.exists(),'Exclusive model path changed during construction')
    fd,tmp=tempfile.mkstemp(prefix='.complex-static-',suffix='.mjb',dir=out.parent);os.close(fd)
    try:
        mujoco.mj_saveModel(model,tmp)
        os.link(tmp,out)  # Atomic no-replace publication; a raced existing path refuses.
    finally:
        os.unlink(tmp)
    guard()
    return dict(model_path=str(out),model_sha256=sha(out),scene_sha256=sha(Path(__file__).with_name('scene.json')),robot_engine_signature_sha256=original,source_verification=receipt,construction=construction,offscreen_capacity=[int(model.vis.global_.offwidth),int(model.vis.global_.offheight)],actual_main_steps=0,Actor_forwards=0,source_dynamic_or_task_qualification=False)

def construct_cold_components(*,source_root=None,bundle=None,model_path=None,model_sha256=None,guard=None,journal=None,actor_device=None,enabled=False):
    if type(enabled)is not bool:raise ValueError('Explicit owner opt-in')
    if not enabled:return None
    need(callable(guard)and callable(journal),'Real owner guard and original evidence journal required');guard();root=_source(source_root)
    from ainav.native.registered_runtime import construct_cold_runtime
    from ainav.native.registered_observer import RegisteredObserver
    from ainav.native.registered_target_context import register_candidate_channels
    from ainav.native.supported_capture import SupportedCapture
    from mujoco_zyh.stall_stow import STOW_ARM
    s=load_scene();runtime,construction=construct_cold_runtime(bundle,model_path,model_sha256=model_sha256,
        initial_robot=dict(xy_m=s['robot_initial_xy_m'],yaw_rad=s['robot_initial_yaw_rad'],support='ground'),initial_surface_height_m=0.,seed=4301,initial_arm_reference=STOW_ARM,actor_device=actor_device)
    need(runtime.step_count==0 and float(runtime.sim.data.time)==0. and not runtime.sim.queue,'Fresh real task Runtime only')
    r=registry(s,source_root=root);r.verify_compiled(runtime.sim.model);runtime.wm_candidate_contacts=register_candidate_channels(runtime,r);runtime.wm_completion_clock_journal=journal
    observer=RegisteredObserver(runtime,dict(width=192,height=128,scene_recipe='registered'),r)
    capture=SupportedCapture(runtime,r,support_ref='ground',journal=journal);guard()
    return dict(runtime=runtime,registry=r,observer=observer,capture=capture,construction=construction,
        capture_is_not_yet_complete=True,actual_capture_steps_required=True,initial_witness=None,physical_task_admission=False)

def completed_initial_witness(components):
    """After the owner actually issues original capture commands on its loop."""
    from ainav.native.supported_capture import ActualCaptureWitness
    r=components['runtime'];capture=components['capture']
    need(capture.r is r and capture.complete and capture.actual_issued_steps>=2,'No zero-step/forged cold owner')
    witness=ActualCaptureWitness(capture);witness.validate(r);return witness

def build_common_execution_after_capture(components,*,source_root,bundle,guard,journal):
    """Connect existing original same-world components after ACTUAL capture.

    No steps or controller choice are issued here. Query observation/finite
    proposal construction and Reach selection still belong to the new host.
    """
    import importlib
    from complex_scene import finite_placements,placement_contract
    from multi_goal_factory import factory_class
    root=_source(source_root);need(callable(guard)and callable(journal),'Real new-scope guard/journal');guard()
    runtime=components['runtime'];reg=components['registry'];witness=completed_initial_witness(components)
    from ainav.native.registered_bindings import RegisteredBindingResolver,_SOURCES
    from ainav.native.registered_push_api import RegisteredPushAPI
    from ainav.native.session_factory import BehaviorSessionFactory
    from ainav.native.registered_guards import check_object_contacts
    from mujoco_zyh import native_behavior_executor as api,stall_stow
    modules={name:importlib.import_module(name)for name in _SOURCES}
    contexts=importlib.import_module('ainav.native.registered_target_context')
    for mod in [*modules.values(),contexts]:need(Path(mod.__file__).resolve().is_relative_to(root),'No foreign source modules')
    pins={name:sha(mod.__file__)for name,mod in modules.items()}
    # Record the ACTUAL context adapter, not a misleading old file's fingerprint.
    pins['mujoco_selected_target_context']=sha(contexts.__file__);pins['registered_context_adapter']=sha(contexts.__file__)
    pins['public_task_geometry']=sha(Path(__file__).with_name('scene.json'))
    resolver=RegisteredBindingResolver(runtime,proposals=modules['visual_box_proposals'],geometry=modules['native_visual_target_binding'],contexts=contexts,native_api=api,native_history_sha=stall_stow.history_sha,source_sha256=pins,registry=reg,public_geometry={o.body_name:o.size_m for o in reg.objects.values()})
    owners={}
    def guards():
        guard();selected=None;executor=owners.get('executor')
        if executor is not None and executor.option is not None and executor.option.skill=='PUSH':
            binding=owners['backend']._bindings.get(executor.option.sha256)
            if binding is not None:
                matches=[o.ref for o in reg.objects.values()if o.body_name==binding.target.body_name];need(len(matches)==1,'Exact current selected PUSH body');selected=matches[0]
        check_object_contacts(runtime,reg,selected_push_ref=selected)
    backend=BehaviorSessionFactory(runtime,bundle,resolver,guards,native_api=RegisteredPushAPI(reg,api));owners['backend']=backend
    contracts=[placement_contract(load_scene(),c,source_root=root)for c in finite_placements(load_scene())]
    cls=factory_class(source_root=root,enabled=True)
    factory=cls(runtime,reg,initial_witness=witness,journal=journal,push_backend=backend,placement_contracts={c.sha256:c for c in contracts},native_api=api)
    executor=api.NativeOptionExecutor(runtime,factory,journal);factory.attach_executor(executor);owners['executor']=executor
    # The inner PUSH backend does not own a different executor. Its NAV/compact
    # branch is unused; all NAV/owner transfers go through the common factory.
    from terminal_stop import ActualPlacementEvidence
    placements=ActualPlacementEvidence(runtime,reg)
    return dict(factory=factory,executor=executor,resolver=resolver,initial_witness=witness,placement_catalogue={c.sha256:c for c in contracts},placements=placements,guards=guards,source_provenance=pins,world_steps_issued=0,actual_dynamic_qualification=False)
