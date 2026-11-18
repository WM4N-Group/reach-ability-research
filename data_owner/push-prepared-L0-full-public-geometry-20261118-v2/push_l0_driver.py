"""Concrete original standalone initialization → registered PUSH, no NAV deletion claim."""
from pathlib import Path
import time
import hashlib,importlib.util,sys
from standard_runtime import need,bounded_exception
from l0_witness import L0StartupOwner
from connect_l0 import connect


class L0Case:
    def __init__(self,journal):self.journal=journal;self.selected=None;self.receipts=[];self.index=0;self.failed=False;self.censored=False
    @property
    def active_skill(self):return None if self.selected is None else self.selected.skill
    def select(self,batch):
        from ainav.planner import Selection
        need(self.index==0 and self.selected is None and not self.failed and len(batch.options)==1,'One original PUSH interval, not a retry')
        option=batch.options[0];need(option.skill=='PUSH','Strict L0 advertises PUSH only')
        self.selected=option
        ref=self.journal(dict(event='original_L0_single_PUSH_selected_NOT_optimizer',query_sha256=batch.sha256,option_sha256=option.sha256))
        return Selection(batch.sha256,option.token,option.sha256,'ORIGINAL_STANDARD_PUSH_L0',0,ref)
    def observe(self,option,receipt):
        from dataclasses import asdict
        need(option is self.selected and receipt.option_sha256==option.sha256,'Exact original terminal')
        self.receipts.append(dict(root_skill='PUSH',**asdict(receipt)))
        if receipt.status=='budget_expired':self.censored=True;return
        if receipt.status!='succeeded':self.failed=True;raise RuntimeError('Original PUSH terminal non-success; no retry')
        self.index=1;self.selected=None


def driver_class(*,source_root=None,legacy_base_dir=None,legacy_guard_dir=None,legacy_driver_source=None,enabled=False):
    need(type(enabled)is bool,'Explicit future L0 source opt-in')
    if not enabled:return None
    path=Path(legacy_driver_source).resolve(strict=True)
    need(not path.is_symlink()and hashlib.sha256(path.read_bytes()).hexdigest()=='d31117aa9a2f99bb119f7a8585ec231b879613fabb58ef1358c296591918a934','Exact reused Data driver source, not an old scope execution')
    name='_data_l0_original_standard_driver'
    module=sys.modules.get(name)
    if module is None:
        spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    need(Path(module.__file__).resolve()==path,'No ambient private driver alias')
    Base=module.driver_class(source_root=source_root,legacy_base_dir=legacy_base_dir,legacy_guard_dir=legacy_guard_dir,enabled=True)
    class OriginalL0Driver(Base):
        def __init__(self,components,*,bundle,output_root,writer,journal,guard,trace):
            from ainav.contracts import canonical
            self.startup=L0StartupOwner(components,bundle=bundle,trace=trace,guard=guard)
            base_components=dict(components,capture=self.startup)
            super().__init__(base_components,bundle=bundle,output_root=output_root,writer=writer,journal=journal,guard=guard,trace=trace)
            self.components=components;self.planner=L0Case(journal);self.censored=False
            self.scene=dict(task=dict(instruction='Original independent PUSH L0 startup then one registered +X .6m PUSH/public[1.7,0]/full original exit'))
            self.capabilities=canonical(dict(source_ref='Original independent PUSH L0 initialization, not natural predecessor L1',skills=['PUSH'],
                constraints=['One fixed original standard PUSH, no NAV/retry/extra settling to pass.',
                'Original startup initialization writes occur only before first Actor; not allowed as task recovery.',
                'Startup3N is not entry12N; original current support/FIFO/goal/NN/FF/complete STOW gates all retained.']))
        def actor_context(self):
            skill=self.planner.active_skill;phase=self.startup.phase
            if skill is not None:
                phase='ADMISSION'
                if self.executor is not None and self.executor.option is not None and self.executor.option.skill==skill:
                    phase=str(self.executor.session.machine.phase)
            return dict(root_skill=skill or 'ORIGINAL_L0_INITIALIZATION',native_phase=phase,
                task_step=self.r.step_count,task_sim_s=float(self.r.sim.data.time))
        def _connect_execution(self):
            from ainav.native.loop import AinavLoop
            witness=self.startup.finish()
            self.execution=connect(self.components,witness=witness,source_root=self.source_root,bundle=self.bundle,
                trace=self.trace,guard=self.owner_guard,journal=self.journal,enabled=True)
            self.factory,self.executor=self.execution['factory'],self.execution['executor']
            self.loop=AinavLoop(runtime=self.r,executor=self.executor,planner=self.planner,batch_provider=self.judge_intent,
                snapshot=self._snapshot,command_writer=self._write_command,after_step_guard=self._after_guard,journal=self.journal,physical_tick=self.tick)
        def judge_intent(self,now):
            from ainav.contracts import DecisionBatch,sha
            from ainav.native.behavior_authority import BehaviorOption
            from ainav.native.execution_judge import EntrySpec,EntryState,judge_entry
            from ainav.native.push_support_gate import current_push_source_support
            from ainav.native.registered_compact_nav import validate_support_and_goal
            self._native_guards();self._contact_guard()
            need(self.planner.index==0 and self.planner.selected is None and now==float(self.r.sim.data.time),'Single fresh L0 current query')
            packet,_private=self.observer.capture(self.tick//4,self._last_issued);resolver=self.execution['resolver']
            descriptors=resolver.observe(packet,control_tick=self.tick//4,physical_tick=self.tick)
            observation=self.publisher.publish(packet,now=now,descriptors=descriptors,
                declared_map=dict(source_ref='Original fixed L0 source, not live GT',anchors=[]),goal=self.scene['task']['instruction'],events=[])
            visible=[d['target_ref']for d in descriptors if resolver._observed[d['target_ref']][0]=='push_box']
            need(len(visible)==1,'CURRENT original RGBD association, no GT/old-ref fallback')
            p=self.r.sim;witness=self.factory._current_completed_witness();witness.validate(self.r)
            surface=self.registry.surfaces[witness.support_ref]
            current_push_source_support(self.r,self.registry,'push_box',0.)
            validate_support_and_goal(surface,p.data.xpos[p.feet_ids].tolist(),p.forces[p.feet_ids,2].tolist(),(-.08,0.))
            rotation=p.data.xmat[p.base_id].reshape(3,3)
            compatible=bool(self.np.allclose(p.data.xmat[p.box_id].reshape(3,3),self.np.eye(3),rtol=0,atol=.08))
            state=EntryState(now,sha(self.api.world_snapshot(self.r)),tuple(map(float,p.data.qpos[:2])),
                float(self.np.arctan2(rotation[1,0],rotation[0,0])),True,True,bool(self.executor.fatal))
            judgment=judge_entry(EntrySpec('PUSH',visible[0],(-.08,0.),0.,True,compatible),state)
            proof=self.journal(dict(event='original_L0_PUSH_entry_judgment',**judgment.private_record()))
            need(judgment.status=='READY','Original L0 entry not ready; no extra NAV/settle or Actor failure inference')
            contract=self.components['placement_contract']
            goal=resolver.prepare_push(visible[0],distance_m=.6,attempt_id='original-L0-single-PUSH',approach_xy=(-.08,0.),
                surface_height_m=0.,goal_xy_m=contract.drive_goal_xy_m,body_braking_goal_xy_m=contract.public_goal_xy_m)
            option=BehaviorOption('original-L0-PUSH','PUSH',visible[0],tuple(sorted(dict(goal_world_x_m=-.08,
                goal_world_y_m=0.,surface_height_m=0.,push_distance_m=.6).items())),60.,proof,
                attempt_id='original-L0-single-PUSH',original_push_goal_sha256=goal)
            self.sequence+=1;batch=DecisionBatch('original-L0-query-%d'%self.sequence,observation,(option,),self.capabilities)
            self.factory.bind_batch(batch);return batch
        def step_one(self):
            p=self.r.sim;need(self.r.step_count==self.tick and abs(float(p.data.time)-self.tick*.005)<1e-7,'Actual original200Hz clock')
            self.capture_grid();self._before=(float(p.data.time),p.data.qpos[p.qids].copy(),p.data.qvel[p.dids].copy())
            if self.loop is None:
                command=self.startup.command()
                if command is None:
                    self._write_boundary(dict(time_s=float(p.data.time),event='original_L0_startup_finished_NOT_PUSH_success',startup=self.startup.report()))
                    self._connect_execution();return False
                issued=command.array().copy();before=float(p.data.time);error=None
                try:self.r.step(command)
                except BaseException as exc:error=exc;raise
                finally:
                    if float(p.data.time)>before:
                        need(abs(float(p.data.time)-before-.005)<1e-7,'One actual original startup step')
                        self.tick+=1
                        try:self._write_command(issued,self.tick,float(p.data.time))
                        finally:
                            try:self.startup.after_step(native_error=error)
                            finally:self._after_guard()
                    elif error is not None:self.startup.after_step(native_error=error)
                return True
            self.loop._receipts()
            if self.planner.censored:self.censored=True;return False
            if self.planner.index==1:
                need(self.executor.reported_end and self.executor.last_outcome=='succeeded','Actual full original registered PUSH receipt')
                self.complete=True;return False
            try:return self.loop.step_one()
            finally:self.tick=self.loop.physical_tick
    return OriginalL0Driver


class CaseLoopError(RuntimeError):
    def __init__(self,receipt,error):super().__init__('Original L0 stopped, no retry');self.receipt=receipt;self.original_error=error


def run_case(driver=None,*,watch=None,budget=None,video=None,scope_start_mono=None,enabled=False):
    need(type(enabled)is bool,'Explicit new finite L0 main')
    if not enabled:return None
    need(driver.r.step_count==0 and float(driver.r.sim.data.time)==0. and watch.state is budget.state,'Fresh whole main, not a settled-world restore')
    calls=0;error=None;reason=None;start=time.monotonic()
    try:
        while True:
            watch()
            if driver.complete:reason='ORIGINAL_REGISTERED_L0_PUSH_FULL_EXIT_SUCCESS';break
            if driver.censored:reason='ORIGINAL_60S_INTERVAL_CENSORED_NOT_ACTOR_FAILURE';break
            if driver.r.step_count>=15000 or float(driver.r.sim.data.time)>=75. or calls>=15200 or time.monotonic()-scope_start_mono>=1800.:
                reason='FINITE_MAIN_CENSORED';break
            before=driver.r.step_count;calls+=1
            try:driver.step_one()
            finally:
                if driver.r.step_count>before:video.capture_if_due()
            need(driver.r.step_count-before in (0,1),'One original physical issue per driver call')
    except BaseException as exc:error=exc;reason='ORIGINAL_STARTUP_ENTRY_NATIVE_OR_RESOURCE_STOP'
    finally:
        if not budget.finalizing:budget.begin_finalization()
    receipt=dict(driver_calls=calls,stop_reason=reason,full_case_success=bool(driver.complete),root_terminal_receipts=list(driver.planner.receipts),
        original_error=None if error is None else bounded_exception(error),startup=driver.startup.report(),
        task_steps=driver.r.step_count,task_sim_s=float(driver.r.sim.data.time),loop_wall_s=time.monotonic()-start,
        automatic_retry=False,Actor_failure_or_training_need_not_inferred=True)
    if error is not None:raise CaseLoopError(receipt,error)from error
    return receipt
