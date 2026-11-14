"""Install ALL actually loaded common-stow aliases and one immutable preparation selection.
No host/Runtime/world constructor or step. Called only on future guarded NEW host.
Partial installation is fatal to that process; NEVER rollback/reuse/hot switch.
"""
from pathlib import Path
import importlib,sys
from prepare_prefix import A,SOURCE,load_package,need


def install_preexecution_choices(host,*,candidate_id,emit):
    consumer,source,_=load_package()
    caller=importlib.import_module('ainav.native.execution_judged_course')
    from climb_preparation_candidates import bind_to_host as bind_preparation,selection_from_payload,CALLBACK as PREP
    from reach_stow_choice.native_stow_path_binding import bind_to_host as bind_stow,CALLBACK as STOW,restore_stall_source
    need(type(host) is caller.ExecutionJudgedFullCourse and caller.ExecutionJudgedFullCourse._native_nav.__globals__ is vars(caller),'Exact current full Host/caller identity')
    need(callable(emit),'Existing evidence journal sink')
    need(not hasattr(host,'_Data_stageB_binding_state'),'A prior binding attempt is never reusable')
    need(host.tick==0 and host.r.step_count==0 and float(host.r.sim.data.time)==0. and not host.r.sim.queue,'Fresh empty zero world, no hot install')
    need(host.executor.runtime is host.r and host.factory.runtime is host.r and host.executor.factory is host.factory and
         host.executor.session is None and host.executor.option is None and host.executor.fatal is False and
         host.coordinator.intent is None,'Exact fresh root/executor/factory/no active owner')
    selection=selection_from_payload(dict(schema='AINav-finite-CLIMB-preparation-selection-v1',target_ref='cuboid-2:upper-entry',candidate_id=candidate_id))
    need(PREP not in vars(caller),'No preparation callback replacement')
    # Two source paths are frozen, but an archived extraction alias is not
    # necessarily importable as ainav.native.* (its relative deps are native
    # mujoco_zyh). NEVER manufacture a second package/namespace to import it.
    # Match original host's already-loaded namespaces by exact __file__ path.
    allowed={SOURCE/'mujoco_zyh/stall_stow.py',SOURCE/'ainav/native/current_stall_stow.py'}
    aliases=[];seen=set()
    for module in tuple(sys.modules.values()):
        path=getattr(module,'__file__',None)
        if path is not None and id(module) not in seen and Path(path).resolve() in allowed:
            seen.add(id(module));aliases.append(module)
    need(any(Path(m.__file__).resolve()==SOURCE/'mujoco_zyh/stall_stow.py' for m in aliases),'Actual selected original stow module must already be loaded by host')
    for module in aliases:
        restore_stall_source(Path(module.__file__).read_text())
        need(STOW not in vars(module) and module.ProtectedStow.update.__globals__ is vars(module),'Every actually loaded common alias must be unbound before first installation')
    moving=importlib.import_module('mujoco_zyh.moving_push_exit')
    selected=next(m for m in aliases if Path(m.__file__).resolve()==SOURCE/'mujoco_zyh/stall_stow.py')
    need(moving.ProtectedStow is selected.ProtectedStow,'Actual selected MovingPushExit consumes the same ProtectedStow')
    before=host.api.world_snapshot(host.r)
    host._Data_stageB_binding_state='INSTALLING_NOT_ADMITTED'
    try:
        stow=[dict(module=m.__name__,path=str(Path(m.__file__).resolve()),**bind_stow(host,m,enabled=True,emit=emit)) for m in aliases]
        prep=bind_preparation(host,caller,selection=selection,enabled=True,emit=emit)
        need(all(v['installed'] for v in stow) and prep['installed'],'All choices installed once before first capture/step')
        need(host.api.world_snapshot(host.r)==before and host.tick==0 and host.r.step_count==0 and not host.r.sim.queue,'Installing callbacks changed actual state/FIFO')
    except BaseException:
        host._Data_stageB_binding_state='FAILED_UNUSABLE_NEW_PROCESS_REQUIRED'
        raise  # No module rollback or second attempt in a tainted process.
    host._Data_stageB_binding_state='INSTALLED_NOT_PHYSICAL_ADMISSION'
    return dict(schema='Data-common-v2-stow-and-preparation-installer-v1',candidate_id=candidate_id,
        common_stow_aliases=stow,preparation=prep,same_stow_for_every_branch=True,
        world_and_queue_unchanged=True,partial_failure_never_reusable=True,
        actual_capture_constructor_or_dynamic_feasibility_proven=False,execution_authorized=False)
