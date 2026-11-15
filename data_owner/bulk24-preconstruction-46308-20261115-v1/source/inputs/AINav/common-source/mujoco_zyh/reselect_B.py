"""Explicit research A-failure recovery -> real B-local original PUSH attempt.

Only new candidate-local software epochs are made. The global A scene alias,
failed A goal/controller/history and the physical world/FIFO remain unchanged.
"""
from collections import deque
from pathlib import Path
from types import SimpleNamespace,MethodType,ModuleType
import hashlib,json,sys
import numpy as np
from .resume_nav import ResumeNavRouter,NAV_ARM
from .failure_capsules import emit as emit_capsule
from .stall_stow import ProtectedStow,history_sha,SoftStall
from initial_contact_progress_monitor import ContactProgressConfig,ContactProgressSample,InitialContactProgressMonitor

DEPENDENCIES=('mujoco_selected_target_context.py','native_target_context.py','native_candidate_contact_layout.py')


def dependency_hashes():return {n:hashlib.sha256((Path(__file__).parents[1]/n).read_bytes()).hexdigest() for n in DEPENDENCIES}


def validate_protocol(p):
    filename=('reselect_B_recorded_protocol_v2.json' if p.get('schema')=='piper-mujoco-A-recovery-selected-B-recorded-protocol-v2' else 'reselect_B_protocol_v1.json')
    expected=json.loads(Path(__file__).with_name(filename).read_text())
    if p!=expected:raise ValueError('Exact new research-B admission protocol required')
    if filename.endswith('_v2.json'):
        from .failure_capsules import validate_config
        validate_config(p['private_failure_capsules'])
    from .resume_nav import validate_protocol as validate_resume
    validate_resume(json.loads(Path(__file__).with_name('resume_nav_protocol_v5.json').read_text()))
    return p


def compile_entry_and_machine(bundle):
    root=Path(bundle)/'switch';entry=(root/'push_entry.py').read_text();machine=(root/'machine.py').read_text()
    entry_changes={
        'and np.max(abs(p.data.qpos[p.qids[12:]]))<.08)':'and np.max(abs(p.data.qpos[p.qids[12:]]-_wm_NAV_ARM))<.04)',
        '        anchors=self.anchors.copy()':'        arm.position[12:]=_wm_NAV_ARM\n        anchors=self.anchors.copy()'}
    machine_changes={
        '            from push_entry import PushEntry':'            PushEntry = _wm_selected_entry',
        'np.max(abs(p.data.qpos[p.qids[12:]]))>.12':'np.max(abs(p.data.qpos[p.qids[12:]]-_wm_NAV_ARM))>.04'}
    def apply(source,changes):
        out=source
        for old,new in changes.items():
            if out.count(old)!=1:raise ValueError('Pinned selected-target caller hook mismatch:'+old)
            out=out.replace(old,new,1)
        inverse=out
        for old,new in reversed(list(changes.items())):inverse=inverse.replace(new,old,1)
        if inverse!=source:raise ValueError('Selected-target source hook inverse differs')
        return out
    ep=ModuleType('_wm_compact_selected_push_entry');ep.__file__=str(root/'push_entry.py');ep.__dict__['_wm_NAV_ARM']=NAV_ARM
    sys.modules[ep.__name__]=ep;exec(compile(apply(entry,entry_changes),ep.__file__+'[compact-target]','exec'),ep.__dict__)
    mp=ModuleType('_wm_compact_selected_push_machine');mp.__file__=str(root/'machine.py');mp.__dict__.update(_wm_NAV_ARM=NAV_ARM,_wm_selected_entry=ep.PushEntry)
    sys.modules[mp.__name__]=mp;exec(compile(apply(machine,machine_changes),mp.__file__+'[compact-target]','exec'),mp.__dict__)
    return mp.Machine,dict(entry_original_sha256=hashlib.sha256(entry.encode()).hexdigest(),machine_original_sha256=hashlib.sha256(machine.encode()).hexdigest(),entry_hunks=2,machine_hunks=2,inverse_restores_exact_original=True,compact_arm_target=NAV_ARM.tolist(),original_arm_zero_gates_not_claimed=True,all_other_native_actor_entry_router_guard_code_unchanged=True)


class ReselectBRouter:
    def __init__(self,r,native,root,protocol,bundle):
        self.r=r;self.native=native;self.protocol=protocol;self.bundle=bundle
        self.resume=ResumeNavRouter(r,native,root);self.resume.registered_goal_xy=np.array([-.08,-1.8])
        self.stage=None;self.done_at=None;self.view=None;self.bound_runtime=None;self.bmachine=None;self.exit=None
        self.extra_events=[];self.binding=None;self.B_original_goal=None;self.B_result=None;self.B_abort=None
        self.monitor=InitialContactProgressMonitor(ContactProgressConfig(window_s=.06));self.tick=0
        self.last_two=deque([r.last.position.copy(),r.last.position.copy()],maxlen=2)
        self.log=(Path(root)/'selected-B-50hz.jsonl').open('x');self.actual_log=(Path(root)/'selected-B-200hz.jsonl').open('x')
        self.A_receipt=None;self.view_original_termination=None
    @property
    def complete(self):return self.exit is not None and self.exit.complete
    @property
    def phase(self):return self.stage or self.resume.phase
    @property
    def kind(self):return 'push' if self.stage else self.resume.kind
    @property
    def index(self):return 2 if self.stage else self.resume.index
    @property
    def events(self):return self.resume.events+self.extra_events+(self.bmachine.events if self.bmachine else [])+(self.exit.events if self.exit else [])
    @property
    def results(self):return self.resume.results+(self.bmachine.results if self.bmachine else [])
    @property
    def switch_metrics(self):return self.resume.switch_metrics+(self.bmachine.switch_metrics if self.bmachine else [])
    @property
    def finish(self):return self.bmachine.finish if self.bmachine else self.resume.finish
    def event(self,name,**kw):
        value=dict(time=float(self.r.sim.data.time),event=name,**kw);self.extra_events.append(value);print(value,flush=True)
    def bind_B(self):
        from mujoco_selected_target_context import make_target_context
        r,p=self.r,self.r.sim
        self.A_receipt=json.loads(json.dumps(self.resume.report()))
        if np.linalg.norm(p.data.qpos[:2]-[-.08,-1.8])>.16 or np.linalg.norm(p.data.qvel[:3])>.12:raise RuntimeError('B actual NAV approach outside unchanged native domain')
        before=np.r_[p.data.qpos,p.data.qvel].copy();queue=[x.copy() for x in p.queue]
        self.view,self.binding=make_target_context(r,r.wm_candidate_contacts,'middle');self.view.refresh()
        self.B_original_goal=self.view.box_push_target.clone();Machine,hook=compile_entry_and_machine(self.bundle)
        proxy=SimpleNamespace(**vars(r));proxy.sim=self.view;proxy.box_y=-1.8;proxy.last=r.last
        proxy.push_enter=MethodType(type(r).push_enter,proxy)
        self.bound_runtime=proxy;self.binding['caller_hook']=hook
        self.view_original_termination=self.view.termination;self.view.termination=self.B_termination
        self.bmachine=Machine(proxy,[dict(skill='push')]);self.bmachine.enter()
        r.wm_active_candidate='middle';self.stage='B_PUSH_PREPARE'
        if not np.array_equal(before,np.r_[p.data.qpos,p.data.qvel]) or len(queue)!=len(p.queue) or any(not np.array_equal(a,b) for a,b in zip(queue,p.queue)):raise RuntimeError('B context entry changed physical state/queue')
        self.event('explicit_B_controller_observation_contact_authority_bound',binding=self.binding)
    def B_termination(self):
        view=self.view;flags=self.view_original_termination()
        if self.exit is not None or self.bmachine.phase=='prepare':return flags
        bad=[k for k,v in flags.items() if k!='box_settled' and v]
        legal=bool(self.r.push['bridge'].box_push.hand_contact(view,view.hand_cfg)[0])
        near=bool(np.linalg.norm(view.data.xpos[view.box_id,:2]-view.box_push_target[0,:2].numpy())<.12)
        result=self.monitor.observe(ContactProgressSample(self.tick,float(view.data.time),True,bool(view.controller.motion_ready[0]),legal,True,float(view.data.xpos[view.box_id,0]),near,bool(flags['box_settled']),bool(bad)))
        if result.new_soft_abort_request:
            self.B_abort=dict(time_s=float(view.data.time),dx_m=result.observed_forward_dx_m,contact_window_s=result.elapsed_contact_s,native_hard_flags=bad,original_B_goal=view.box_push_target.tolist())
            emit_capsule(self.r,'selected_b_soft_progress_abort',view=view,extra=dict(abort=self.B_abort,native_flags=flags))
            raise SoftStall('selected_B_current_attempt_insufficient_progress')
        return flags
    def start_exit(self,successful):
        self.B_result=dict(native_PUSH_goal_reached=successful,soft_failure=self.B_abort,goal=self.B_original_goal.tolist(),terminal_time_s=float(self.r.sim.data.time))
        self.exit=ProtectedStow(self.bound_runtime,list(self.last_two),compact_goal=NAV_ARM)
        self.stage='B_SUCCESS_PROTECTED_STOW' if successful else 'B_FAILED_PROTECTED_STOW'
        self.event('B_native_attempt_retired_for_protected_exit',result=self.B_result)
    def update(self):
        if not self.stage:
            self.resume.update()
            if self.resume.complete:
                now=float(self.r.sim.data.time)
                if self.done_at is None:self.done_at=now
                if now-self.done_at>=5.-1e-9:self.bind_B()
            return
        self.bound_runtime.last=self.r.last;self.view.refresh()
        self.view.target_context._env.common_step_counter=self.r.step_count
        if history_sha(self.r.sim)!=self.resume.prefix.recovery.retired_history_sha:raise RuntimeError('retired_A_history_changed_by_B')
        if not np.array_equal(self.view.box_push_target.numpy(),self.B_original_goal.numpy()):raise RuntimeError('B goal changed')
        if self.exit:
            flags=self.view_original_termination();bad=[k for k,v in flags.items() if k!='box_settled' and v]
            if bad:raise RuntimeError('selected_B_exit_native_guard:'+','.join(bad))
            self.exit.update()
            if self.exit.complete:self.stage='B_SAFE_TERMINAL_VERIFIED'
            return
        obs_before=None
        try:self.bmachine.update()
        except SoftStall:self.start_exit(False)
        if self.exit is None and self.bmachine.finish is not None:self.start_exit(True)
        if self.exit is None:self.stage='B_PUSH_'+self.bmachine.phase.upper()
        self.tick+=1
        self.log.write(json.dumps(dict(time_s=float(self.view.data.time),stage=self.stage,selected_target='middle',B_body_id=self.view.box_id,B_pose=self.view.data.xpos[self.view.box_id].tolist(),B_goal=self.view.box_push_target.tolist(),controller_env_candidate=self.view.controller.env.candidate,history_terms=[h.tolist() for h in self.view.history] if self.view.history else None,native_targets=self.view.targets.tolist(),last_actually_issued=self.r.last.array().tolist(),A_original_history_preserved=True))+'\n');self.log.flush()
    def next_command(self):
        if not self.stage:return self.resume.next_command()
        self.bound_runtime.last=self.r.last
        return self.exit.command() if self.exit else self.bmachine.next_command()
    def after_step(self):
        if not self.stage:self.resume.after_step();return
        r,p=self.r,self.r.sim;self.bound_runtime.last=r.last;self.view.refresh();self.last_two.append(r.last.position.copy())
        limits=p.model.jnt_range[p.jids];q=p.data.qpos[p.qids];dq=p.data.qvel[p.dids]
        if not np.isfinite(np.r_[p.data.qpos,p.data.qvel]).all() or np.any(q<limits[:,0]) or np.any(q>limits[:,1]) or np.any(abs(dq)>r.push['model'].SPEED):raise RuntimeError('selected_B_actual_range_speed')
        box=r.push['bridge'].box_push
        for name,call in [('box_contact',lambda:box.forbidden_box_contact(self.view)),('invalid_hand_contact',lambda:box.invalid_hand_contact(self.view,self.view.hand_cfg)),('box_tipped',lambda:box.box_tipped(self.view))]:
            if bool(call()[0]):
                error=RuntimeError('selected_B_'+name+'_200Hz')
                emit_capsule(r,'selected_b_hard_guard',view=self.view,extra=dict(error=repr(error),native_guard=name),preserve_primary_failure=True)
                raise error
        if self.exit:self.exit.after_step()
        else:self.bmachine.after_step()
        if history_sha(p)!=self.resume.prefix.recovery.retired_history_sha:raise RuntimeError('retired_A_history_changed_after_B_step')
        if self.B_result and self.B_result['native_PUSH_goal_reached'] and np.linalg.norm(self.view.data.xpos[self.view.box_id,:2]-self.B_original_goal[0,:2].numpy())>=.12:raise RuntimeError('selected_B_left_original_success_goal_during_stow')
        self.actual_log.write(json.dumps(dict(time_s=float(p.data.time),stage=self.stage,q=q.tolist(),dq=dq.tolist(),selected_target='middle',selected_box_body=self.view.box_id,B_pose=p.data.xpos[self.view.box_id].tolist(),B_hand_force=self.view.scene.sensors['box_contact_hand'].data.force_matrix_w.tolist(),metrics=self.exit.metrics if self.exit else None,A_failed_goal_and_history_preserved=True))+'\n')
        if self.log.tell()+self.actual_log.tell()>64*1024*1024:raise RuntimeError('selected_B_private_log_quota')
    def diagnostics(self):return dict(phase=self.phase,abort=self.resume.prefix.abort,selected_target='middle' if self.stage else 'light',B_result=self.B_result)
    def report(self):
        out=self.A_receipt or self.resume.report()
        out['selected_B']=dict(binding=self.binding,stage=self.stage,result=self.B_result,protected_exit=self.exit.report() if self.exit else None,A_original_goal_and_history_preserved=self.resume.prefix.recovery is not None and history_sha(self.r.sim)==self.resume.prefix.recovery.retired_history_sha,live_B_execution_pass=self.B_result is not None,scope='actual B original NN PUSH attempt and safe result only, no CLIMB/full route/WM validation')
        if out['selected_B']['protected_exit'] and self.B_result and self.B_result['native_PUSH_goal_reached']:
            out['selected_B']['protected_exit']['native_PUSH_attempt_failed']=False
        return out
    def close(self):self.resume.close();self.log.close();self.actual_log.close()
