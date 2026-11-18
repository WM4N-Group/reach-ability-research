"""Exact first callback CPU reachability and privacy-bounded chain readiness."""
import hashlib,sys
from pathlib import Path
from types import SimpleNamespace as NS
STOP='ainav.native.stop_actor_trace'
PIN='0e3a913491aba296ca620c107582f15c768aa74de44a6fa1a7c9f05795f9a330'

def verify_preloaded(freeze):
    mod=sys.modules[STOP];p=Path(mod.__file__)
    assert not p.is_symlink() and freeze['files'].get(str(p))==hashlib.sha256(p.read_bytes()).hexdigest()==PIN
    assert mod.run_after_step_with_audit.__code__.co_filename==str(p)
    return PIN

def qualify_first_callback(freeze):
    import numpy as np
    import torch
    import indexed_guard as ig
    from ainav.native import placement_handoff,completion_clock
    from standard_runtime import bounded_exception
    from first_failure_chain import capture_failure,AUDIT_MESSAGE
    assert not torch.cuda.is_initialized()
    verify_preloaded(freeze)
    class FakeCPURead:
        def detach(self):return self
        def cpu(self):return self
        def numpy(self):return np.asarray([[1.7,0.,0.]],dtype=np.float32)
    class HookState:
        pass
    sim=NS(box_push_target=FakeCPURead(),settled=object.__new__(completion_clock.ClockedNativeSettled),data=NS(time=6.510),observation=lambda:None,set_action=lambda *_:None)
    calls=[]
    s=NS(machine=NS(r=NS(sim=sim)),after_step=lambda:calls.append('synthetic callback'),runtime=NS(last=object(),step_count=1302))
    placement_handoff.wrap_two_phase_placement(s,NS(sha256='a'*64),lambda x:None,arm_policy='reconciled_unload',leg_policy='reverse_after_native_confirmation')
    owner=HookState();owner.state='RUNNING';owner.failure=None;ig._install_hook(owner)
    try:
        s.after_step()
        assert owner.state=='RUNNING' and owner.failure is None and calls==['synthetic callback']
    finally:
        owner.state='CLOSED'
    try:
        try:raise ig.GuardViolation(AUDIT_MESSAGE)
        finally:raise ig.GuardViolation('masked first reason fixture')
    except ig.GuardViolation as exc:
        chain=capture_failure(exc,NS(state='FAILED',failure=AUDIT_MESSAGE),bounded_exception)
        assert chain['first_audit_latch_label']=='UNPLANNED_CODE_OR_IMPORT' and len(chain['outer_then_cause_or_context'])==2
        assert [r['link']for r in chain['outer_then_cause_or_context']]==['outer','context']
        assert all(not r['metadata']['exception_text_locals_or_headers_recorded'] for r in chain['outer_then_cause_or_context'])
    assert not torch.cuda.is_initialized()
    return dict(CPU_fixture_only=True,preloaded_frozen_original_module_sha256=PIN,real_original_after_step_wrapper_running_hook_reaches_synthetic_callee=True,
        masked_exception_type_path_line_chain_preserved_bounded=True,no_physics_or_resource_qualification=True)
