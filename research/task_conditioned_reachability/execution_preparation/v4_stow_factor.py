"""V4 arm-specific startup binding for the EXISTING Reach stow path kernel.

In explicit treatment-specific mode, default OFF; A/C/E cannot opt in.
Do not use this helper to silently remove an already fixed legacy-common layer
or weaken the complete original AINav baseline. A pre-existing all-arm installer
must NOT run first: disabling a second bind does not remove its callback. This
helper installs no controller/command and changes no native success/safety gate.
Source owner calls it in a fresh zero-step NEW worker, never an active/closed run.
"""
import hashlib
from pathlib import Path
import sys
from .native_stow_path_binding_v2 import bind_to_host,restore_stall_source,CALLBACK
from .v4_successor_choice import need


def install_v4_stow_factor(host, *, arm, enabled=False, emit):
    need(arm in ('A','B','C','D','E') and type(enabled)is bool, 'Explicit frozen five-arm identity and component factor')
    need(not enabled or arm in ('B','D'), 'A/C/E cannot activate the Reach preparation-path optimizer')
    need(callable(emit), 'Original source journal, not an execution dispatcher')
    need(not hasattr(host,'_v4_stow_factor'), 'One startup factor binding only; no live factor switch')
    runtime=host.r;sim=runtime.sim
    need(type(runtime.step_count)is int and runtime.step_count==0 and float(sim.data.time)==0. and not sim.queue,
         'Fresh task-zero runtime only; no post-capture/closed-worker rebind')
    root=Path(host.source_root).resolve(strict=True)
    allowed={root/'mujoco_zyh/stall_stow.py',root/'ainav/native/current_stall_stow.py'}
    modules=[];seen=set()
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name is not None and id(module)not in seen and Path(name).resolve()in allowed:
            seen.add(id(module));modules.append(module)
    need(any(Path(m.__file__).resolve()==root/'mujoco_zyh/stall_stow.py'for m in modules),
         'Source must preload the selected original transformed stow module')
    witnesses=[]
    # Check EVERY loaded alias before installing anything. Do not remove an old
    # callback to make a supposedly disabled baseline pass.
    for module in modules:
        path=Path(module.__file__)
        need(path.is_file()and not path.is_symlink(), 'Regular exact source alias')
        raw=path.read_bytes();restore_stall_source(raw.decode())
        ns=vars(module);update=ns['ProtectedStow'].update
        need(update.__globals__ is ns and CALLBACK in update.__code__.co_consts,
             'Loaded original update consumes its own optional callback')
        need(CALLBACK not in ns, 'Pre-existing callback would contaminate OFF arms; reject, never hot-uninstall')
        witnesses.append(dict(path=str(path.resolve()),sha256=hashlib.sha256(raw).hexdigest()))
    host.common_choice_records=[];host.common_stow_bindings=[]
    host._stow_callback_name=CALLBACK;host._stow_allowed=allowed;host._stow_installed={}
    def record(row):
        value=dict(row,v4_arm=arm,v4_preparation_component_enabled=enabled)
        emit(value);host.common_choice_records.append(value)
    for module,witness in zip(modules,witnesses):
        key=witness['path']
        if enabled:
            binding=bind_to_host(host,module,enabled=True,emit=record)
            need(binding['installed']is True, 'Exact original opt-in binder')
            callback=vars(module)[CALLBACK]
        else:
            # Keep the original _native_guards identity check: a known alias
            # must have exactly None, so any later hidden callback is rejected.
            binding=dict(status='V4_ARM_FACTOR_OFF_ORIGINAL_PATH',installed=False,
                         optimizer_kernel_calls=0,execution_authorized=False)
            callback=None
        host._stow_installed[key]=callback
        host.common_stow_bindings.append(dict(witness,**binding))
    host._v4_stow_factor=(arm,enabled)
    report=dict(event='reach_v4_stow_treatment_bound_at_task_zero',arm=arm,
        preparation_component_enabled=enabled,source_aliases=witnesses,
        installed_optimization_callbacks=len(modules)if enabled else 0,
        original_guard_slew_endpoint_and_four_second_verify_unchanged=True,
        old_all_arm_true_installer_must_not_have_run=True,
        native_or_complete_successor_method_qualified=False,physical_commands_issued=0)
    emit(report)
    return report
