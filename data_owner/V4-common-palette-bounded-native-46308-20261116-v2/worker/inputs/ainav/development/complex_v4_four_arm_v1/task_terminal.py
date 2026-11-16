"""Actual V4 task endpoint: original placements + CLIMB chain + high stop.

No planner/route/GT input or task success from a string, pose, process exit or
single frame. The original final NAV continues its genuine protected owner for
a bounded stop; the exact current deck contacts are sampled on every real step.
Static40cm/source capability remains a separate unqualified prerequisite.
"""
from dataclasses import asdict
from pathlib import Path
import hashlib,math
from v4_native_asset import require,load_scene
from elevated_terminal import read_current_goal_sample,ElevatedGoalDwell

HOLD_SHA='b3f96a16f580589c30093551df986498e7423900e097a340c5dda0597fce3c98'
_SEAL=object()


def check_chain_rows(rows,*,goal_ref,goal_height):
    """Check actual recorded transitions, not a proposed/privileged route table."""
    require(len(rows)>=2,'At least two genuine successful CLIMB transitions required')
    height=0.;last=-math.inf
    for row in rows:
        require(all(type(row[k])in(int,float)and math.isfinite(row[k])for k in('time_s','source_height_m','destination_height_m')), 'Finite actual chain clocks/heights')
        require(row['time_s']>last and abs(row['source_height_m']-height)<=.01
                and row['destination_height_m']>row['source_height_m']
                and row['native_stop_success']is True,'Actual CLIMB chain clock/source/rise/stop discontinuity')
        last=row['time_s'];height=row['destination_height_m']
    require(rows[-1]['target_ref']==goal_ref and abs(height-goal_height)<=.01,
            'Actual CLIMB chain must end on the registered elevated goal surface')
    return True


class ActualClimbChain:
    def __init__(self,runtime,registry,scene,*,source_root,guard,journal):
        require(scene==load_scene()and callable(guard)and callable(journal),'Exact shared V4 scene/actual owner guard')
        self.r,self.registry,self.scene=runtime,registry,scene
        self.source_root,self.guard,self.journal=Path(source_root).resolve(),guard,journal
        self.world=(runtime.sim.model,runtime.sim.data,runtime.sim.queue);self.records=[]
    def _world(self):
        require(self.guard()is not False,'Actual Data owner/resource guard refused')
        require(all(a is b for a,b in zip(self.world,(self.r.sim.model,self.r.sim.data,self.r.sim.queue))),
                'All task evidence must belong to one live model/data/FIFO')
    def record_current(self,executor,option,receipt,witness):
        from ainav.native.behavior_authority import NativeReceipt
        from ainav.native.registered_climb import RegisteredClimbMachine,ActualClimbSupportWitness
        from ainav.native.push_stow_witness import require_live_success_boundary
        from mujoco_zyh import native_behavior_executor as api
        from ainav.contracts import sha
        self._world();session=executor.session;require_live_success_boundary(self.r,session,executor)
        require(type(session)is api.NativeOptionSession and isinstance(session.machine,RegisteredClimbMachine)
                and type(witness)is ActualClimbSupportWitness and witness.r is self.r and witness.session is session
                and witness.registry is self.registry and option is executor.option and option.skill=='CLIMB'
                and type(receipt)is NativeReceipt and receipt.status=='succeeded'and receipt.option_sha256==option.sha256,
                'Genuine current original CLIMB session/option/receipt/witness required')
        require(session.entered and executor.previous_tick==self.r.step_count
                and executor.first_command_time is not None
                and float(self.r.sim.data.time)-executor.first_command_time>=.005-1e-7
                and receipt.time_s==float(self.r.sim.data.time)
                and receipt.issued_command_sha256==api.array_sha(self.r.last.array()),
                'Actual CLIMB command boundary, never constructor/completion flag alone')
        before=api.world_snapshot(self.r);witness.validate(self.r)
        native=executor.factory.native_option_for(option);binding=session.machine.binding;geometry=dict(binding.geometry)
        require(binding.option_sha256==native.sha256 and native.parameters==option.parameters
                and abs(geometry['top']-dict(option.parameters)['surface_height_m'])<=.01,
                'Original CLIMB private native binding/public destination match')
        require(not any(row['session']is session for row in self.records),'No duplicate CLIMB receipt/owner')
        row=dict(time_s=receipt.time_s,source_height_m=geometry['base_height'],
            destination_height_m=dict(option.parameters)['surface_height_m'],target_ref=binding.object_ref,
            native_stop_success=True,session=session,option=option,receipt=receipt,binding=binding,
            binding_sha256=sha(asdict(binding)))
        require(api.world_snapshot(self.r)==before,'Recording actual CLIMB evidence changed world/FIFO')
        self.records.append(row)
        self.journal(dict(event='V4_actual_CLIMB_chain_boundary_recorded',time_s=row['time_s'],
            source_height_m=row['source_height_m'],destination_height_m=row['destination_height_m'],
            target_ref=row['target_ref'],public_option_sha256=option.sha256,native_option_sha256=native.sha256,
            receipt_issued_command_sha256=receipt.issued_command_sha256,model_input=False))
    def verify(self):
        from ainav.contracts import sha
        self._world()
        for row in self.records:
            require(row['session'].runtime is self.r and row['session'].machine.binding is row['binding']
                    and sha(asdict(row['binding']))==row['binding_sha256']and row['receipt'].status=='succeeded'
                    and row['receipt'].option_sha256==row['option'].sha256,
                    'Retained actual CLIMB bindings/receipts changed')
        return check_chain_rows(self.records,goal_ref=self.registry.goal.surface_ref,
            goal_height=self.registry.surfaces[self.registry.goal.surface_ref].top_z_m)


class ElevatedSupportedStop:
    def __init__(self,runtime,source_session,witness,placements,chain,*,source_root,journal):
        path=Path(source_root)/'ainav/native/registered_hold.py'
        require(not path.is_symlink()and hashlib.sha256(path.read_bytes()).hexdigest()==HOLD_SHA,'Exact original completed-owner HOLD')
        from ainav.native.registered_hold import RegisteredHoldMachine
        require(placements.r is runtime and chain.r is runtime and chain.registry is placements.registry,
                'Same-world original task evidence')
        chain.verify();require(placements.current_required(),'Three actual original required placements still true')
        self.native=RegisteredHoldMachine(runtime,source_session,witness,hold_s=2.)
        self.r,self.placements,self.chain,self.source_root,self.journal=runtime,placements,chain,source_root,journal
        self.monitor=ElevatedGoalDwell(chain.scene);self.complete=False
    @property
    def phase(self):return 'V4_ACTUAL_TASK_VERIFIED'if self.complete else'V4_VERIFY_ACTUAL_ELEVATED_OWNER_STOP'
    def enter(self):self.native.enter()
    def update(self):self.native.update()
    def next_command(self):return self.native.next_command()
    def after_step(self):
        self.native.after_step();self.native.witness.validate(self.r);self.chain.verify()
        require(self.placements.current_required(),'Actual required placement geometry lost during final stop')
        sample=read_current_goal_sample(self.r,self.chain.scene,source_root=self.source_root)
        self.complete=self.monitor.observe(sample)
        self.journal(dict(event='V4_actual_goal_deck_stop_sample',time_s=sample['time_s'],physical_tick=sample['tick'],
            actual_deck_contact_normal_N=sample['deck_contact_normal_N'],continuous_stop_verified=self.complete,
            current_original_owner_verified=True,model_input=False))
        if self.native.complete and not self.complete:raise RuntimeError('Original bounded final owner did not verify elevated task stop')


def terminal_nav_session(original,placements,chain,*,source_root,journal):
    from ainav.native.registered_nav_factory import RegisteredNavMachine
    from ainav.native.registered_compact_nav import ActualArrivalSupportWitness
    from mujoco_zyh.native_behavior_executor import NativeOptionSession
    require(type(original)is NativeOptionSession and isinstance(original.machine,RegisteredNavMachine)
            and getattr(original,'_v4_terminal_source',None)is None,
            'Exact original final NAV session, not synthetic supported pose or stacked terminal wrapper')
    r=original.runtime;nav=original.machine.native_nav
    require(r is placements.r and r is chain.r and placements.registry is chain.registry,
            'Same task/world registry for final original NAV')
    chain.verify();require(placements.current_required(),'Missing original required placement boundaries')
    goal=chain.registry.goal
    require(nav.surface.ref==goal.surface_ref and nav.height==chain.scene['task']['goal_surface_height_m'],
            'Final NAV is truly on the goal_deck layer; ground same-XY forbidden')
    class FinalNAV(RegisteredNavMachine):
        # Preserve the exact NAV identity/type expected by the original contact
        # guards and live source witness. Do NOT construct/enter another NAV or
        # call the base constructor: this is the same original owner's wrapper.
        def __init__(self):self.r=r;self.tasks=list(original.machine.tasks);self.stop=None;self._task_complete=False;self.original=original
        @property
        def native_nav(self):
            require(original.machine.native_nav is nav,'Original final NAV owner changed inside terminal wrapper')
            return nav
        @property
        def entered(self):return original.machine.entered
        @property
        def complete(self):return self._task_complete
        @property
        def phase(self):return self.stop.phase if self.stop is not None else original.machine.phase
        @property
        def results(self):
            value=list(original.machine.results)
            if self.complete:value.append(dict(skill='V4_complete_task',successful=True,physical_time_s=float(r.sim.data.time),
                actual_placement_count=len(placements.records),actual_CLIMB_count=len(chain.records),actual_goal_deck_contact_and_contiguous_stop=True))
            return value
        def enter(self):original.enter()
        def update(self):original.update()if self.stop is None else self.stop.update()
        def next_command(self):return original.command()if self.stop is None else self.stop.next_command()
        def after_step(self):
            if self.stop is None:
                original.after_step()
                if original.outcome=='succeeded':
                    witness=ActualArrivalSupportWitness(nav);witness.validate(r)
                    journal(dict(event='V4_final_original_NAV_boundary_before_task_stop',time_s=float(r.sim.data.time),task_success_not_yet=True,model_input=False))
                    self.stop=ElevatedSupportedStop(r,original,witness,placements,chain,source_root=source_root,journal=journal)
                    self.stop.enter()
            else:
                self.stop.after_step();self._task_complete=self.stop.complete
    wrapped=NativeOptionSession(r,FinalNAV(),check_guards=original.check_guards)
    wrapped._v4_terminal_source=(original,placements,chain)
    return wrapped


class VerifiedV4TaskTerminal:
    def __init__(self,*,_seal,runtime,executor,placements,chain,guard):
        require(_seal is _SEAL,'Only actual terminal collector can construct proof')
        self.r,self.executor,self.placements,self.chain,self.guard=runtime,executor,placements,chain,guard
        self.session=executor.session;self.tick=runtime.step_count;self.time_s=float(runtime.sim.data.time);self.consumed=False
        self.validate();self._collector_seal=_SEAL
    def validate(self):
        from mujoco_zyh.native_behavior_executor import NativeOptionSession
        from ainav.native.push_stow_witness import require_live_success_boundary
        require(self.guard()is not False and self.r.step_count==self.tick and float(self.r.sim.data.time)==self.time_s,
                'Actual same-tick terminal proof expired or owner guard refused')
        require_live_success_boundary(self.r,self.session,self.executor)
        inner=getattr(self.session.machine,'original',None)
        require(type(self.session)is NativeOptionSession and inner is not None
                and getattr(self.session,'_v4_terminal_source',None)==(inner,self.placements,self.chain)
                and self.executor.option is not None and self.executor.option.skill=='NAV'
                and self.executor.option.target_ref=='v4-goal-elevated'
                and inner.machine.native_nav.goal==(dict(self.executor.option.parameters)['goal_world_x_m'],dict(self.executor.option.parameters)['goal_world_y_m'])
                and dict(self.executor.option.parameters)['surface_height_m']==self.chain.scene['task']['goal_surface_height_m']
                and self.session.machine.complete
                and self.session.machine.stop is not None and self.session.machine.stop.complete,
                'Actual original final NAV plus bounded elevated owner stop required')
        self.session.sync();self.session.check_guards()
        self.session.machine.stop.native.witness.validate(self.r)
        self.chain.verify()
        require(self.placements.current_required(),'Actual terminal required placements lost')
        sample=read_current_goal_sample(self.r,self.chain.scene,source_root=self.chain.source_root)
        require(self.session.machine.stop.monitor.observe(sample),'Actual final goal_deck stop gate lost')
        return True
    def confirm_rule(self,planner,*,evidence_ref):
        from rule_baseline import RuleBaseline
        require(getattr(self,'_collector_seal',None)is _SEAL,'Actual terminal collector provenance required')
        require(type(planner)is RuleBaseline and not self.consumed and isinstance(evidence_ref,str)and bool(evidence_ref)
                and planner.scene==self.chain.scene and not planner.complete
                and planner.awaiting_terminal and planner.pending is None and not planner.failed
                and planner.placed=={o['public_ref']for o in self.chain.scene['objects']}
                and planner.support_height==self.chain.scene['task']['goal_surface_height_m'],
                'Only genuine pending E terminal confirmation, not self-signed string/goal')
        self.validate();self.consumed=True
        return True


def collect_verified_terminal(runtime,executor,placements,chain,*,guard):
    require(callable(guard)and guard()is not False,'Actual Data terminal guard required')
    return VerifiedV4TaskTerminal(_seal=_SEAL,runtime=runtime,executor=executor,placements=placements,chain=chain,guard=guard)
