"""Private task completion using REAL original successful NAV/placement owners.

Reuses the existing bounded RegisteredHoldMachine, not a new ground controller
or synthetic pose. No stepping/teleporting, model features, route oracle or fit.
"""
import hashlib,math
from pathlib import Path
from complex_scene import load_scene,need
HOLD_SHA='b3f96a16f580589c30093551df986498e7423900e097a340c5dda0597fce3c98'

def sample_inside_stopped_goal(scene,sample):
    cfg=scene['private_terminal_acceptance'];feet=sample['feet_world_m'];loads=sample['foot_normal_N'];speeds=sample['foot_speed_m_s'];x0,x1,y0,y1=scene['task']['goal_bounds_xy_m']
    if len(feet)!=4 or any(len(f)!=3 for f in feet)or len(loads)!=4 or len(speeds)!=4:return False
    values=[*loads,*speeds,sample['base_linear_speed_m_s'],sample['base_angular_speed_rad_s'],sample['tilt_rad'],*[v for f in feet for v in f]]
    if not all(isinstance(v,(int,float))and math.isfinite(v)for v in values):return False
    return (all(x0<f[0]<x1 and y0<f[1]<y1 and abs(f[2]-.022)<.04 for f in feet)
        and min(loads)>=cfg['foot_normal_min_N']and all(0<=v<cfg['foot_speed_max_m_s']for v in speeds)
        and 0<=sample['base_linear_speed_m_s']<cfg['base_linear_speed_max_m_s']
        and 0<=sample['base_angular_speed_rad_s']<cfg['base_angular_speed_max_rad_s']and 0<=sample['tilt_rad']<cfg['tilt_max_rad'])

class GoalDwell:
    """Private 200Hz observation accumulator; it is not proof of sample origin."""
    def __init__(self,scene=None):self.scene=load_scene()if scene is None else scene;self.last=None;self.since=None;self.ready=False;self.samples=0
    def observe(self,*,time_s,tick,sample,placements_current):
        need(math.isfinite(time_s)and time_s>=0 and type(tick)is int and tick>=0,'Actual clock/tick required')
        if self.last is not None:
            old_t,old_tick=self.last
            need(time_s>=old_t and tick>=old_tick,'No clock/history rewind')
            if time_s==old_t and tick==old_tick:
                if not placements_current or not sample_inside_stopped_goal(self.scene,sample):self.since=None;self.ready=False
                return self.ready
            if tick-old_tick!=1 or abs(time_s-old_t-.005)>1e-7:self.since=None
        self.last=(time_s,tick);self.samples+=1
        if placements_current and sample_inside_stopped_goal(self.scene,sample):
            if self.since is None:self.since=time_s
            self.ready=time_s-self.since>=self.scene['private_terminal_acceptance']['dwell_s']-1e-8
        else:self.since=None;self.ready=False
        return self.ready

class ActualPlacementEvidence:
    """Record only genuine original succeeded boundaries, never plan outcomes."""
    def __init__(self,runtime,registry,scene=None):self.r=runtime;self.registry=registry;self.scene=load_scene()if scene is None else scene;self.records={};self.world=(runtime.sim.model,runtime.sim.data,runtime.sim.queue)
    def record_current(self,executor,option,receipt):
        from ainav.native.behavior_authority import NativeReceipt
        from ainav.native.placement_handoff import TwoPhasePlacementMachine
        from ainav.native.push_stow_witness import require_live_success_boundary
        session=executor.session;require_live_success_boundary(self.r,session,executor)
        need(option is executor.option and option.skill=='PUSH'and isinstance(receipt,NativeReceipt)and receipt.status=='succeeded'and receipt.option_sha256==option.sha256,'Actual original matching PUSH receipt/owner required')
        need(isinstance(session.machine,TwoPhasePlacementMachine),'Original two-phase placement/stow machine required')
        results=[v for v in session.machine.results if v.get('skill')=='push'and v.get('successful')is True and v.get('finish',{}).get('phase')=='STOW_VERIFIED']
        need(len(results)==1,'Original NN + placement + STOW_VERIFIED result required')
        contract=session.machine.services.contract;need(contract.target_ref in self.registry.objects,'Actual selected registered object required')
        self.records[contract.target_ref]=dict(session=session,contract=contract,contract_sha256=contract.sha256,option_sha256=option.sha256,receipt=receipt)
    def current_required(self):
        need(all(a is b for a,b in zip((self.r.sim.model,self.r.sim.data,self.r.sim.queue),self.world)),'Same model/data/FIFO required')
        for o in self.scene['objects']:
            row=self.records.get(o['public_ref'])
            if row is None:return False
            c=row['contract'];need(c.sha256==row['contract_sha256'],'Original placement contract changed')
            if c.public_goal_xy_m!=tuple(o['required_goal_xy_m']):return False
            services=row['session'].machine.services;services.assert_immutable()
            if not services.measure()['placement_geometry_verified']:return False
        return len(self.records)>=self.scene['task']['minimum_distinct_reconstructions']

def _actual_sample(runtime):
    import mujoco
    p=runtime.sim;feet=[p.model.body(n+'_foot').id for n in('FR','FL','RR','RL')];speeds=[]
    import numpy as np
    for body in feet:
        v=np.zeros(6);mujoco.mj_objectVelocity(p.model,p.data,mujoco.mjtObj.mjOBJ_BODY,body,v,0);speeds.append(float(np.linalg.norm(v[3:])))
    R=p.data.xmat[p.base_id].reshape(3,3)
    return dict(feet_world_m=p.data.xpos[feet].tolist(),foot_normal_N=p.forces[feet,2].tolist(),foot_speed_m_s=speeds,
        base_linear_speed_m_s=float(np.linalg.norm(p.data.qvel[:3])),base_angular_speed_rad_s=float(np.linalg.norm(p.data.qvel[3:6])),tilt_rad=float(np.arccos(np.clip(R[2,2],-1.,1.))))

class FinalSupportedStop:
    """Native session machine for terminal verification, not a planner action.

    Construct only after genuine final NAV succeeds. Data's original executor
    owns every command/step, using this SAME original completed arrival owner.
    """
    def __init__(self,runtime,source_session,witness,placements,*,source_root,journal,scene=None):
        p=Path(source_root).resolve()/'ainav/native/registered_hold.py';need(hashlib.sha256(p.read_bytes()).hexdigest()==HOLD_SHA,'Exact original native owner-hold source')
        from ainav.native.registered_hold import RegisteredHoldMachine
        self.native=RegisteredHoldMachine(runtime,source_session,witness,hold_s=2.)
        self.r=runtime;self.placements=placements;need(placements.r is runtime,'Same-world actual placement evidence')
        self.monitor=GoalDwell(scene);self.journal=journal;need(callable(journal),'Original evidence journal')
        self.complete=False;self.tasks=[dict(skill='hold',meaning='terminal actual original owner verification, not a general ground wait')]
    @property
    def phase(self):return 'COMPLEX_TASK_VERIFIED'if self.complete else 'VERIFY_ORIGINAL_SUPPORTED_STOP'
    @property
    def results(self):return [dict(skill='complex_task',successful=True,physical_time_s=float(self.r.sim.data.time),original_owner_hold=True,original_placement_count=len(self.placements.records),required_reconstructions=self.placements.scene['task']['minimum_distinct_reconstructions'])]if self.complete else []
    def enter(self):self.native.enter()
    def update(self):self.native.update()
    def next_command(self):return self.native.next_command()
    def after_step(self):
        self.native.after_step();self.native.witness.validate(self.r);current=self.placements.current_required();sample=_actual_sample(self.r)
        self.complete=self.monitor.observe(time_s=float(self.r.sim.data.time),tick=self.r.step_count,sample=sample,placements_current=current)
        self.journal(dict(event='complex_private_supported_goal_sample',time_s=float(self.r.sim.data.time),tick=self.r.step_count,placements_current=current,goal_stop_verified=self.complete,model_input=False))
        if self.native.complete and not self.complete:raise RuntimeError('complex_terminal_original_owner_goal_stop_not_verified')

def terminal_nav_session(original,placements,*,source_root,journal,scene):
    """Extend final NAV's actual protected arrival with common terminal checks.

    One NAV task, one original controller and same owner continuation; not a
    scripted compound route or a fabricated HOLD/arrival. Original inner NAV
    success time is separately journalled, task success waits for the real gate.
    """
    from ainav.native.registered_nav_factory import RegisteredNavMachine
    from ainav.native.registered_compact_nav import ActualArrivalSupportWitness
    from mujoco_zyh.native_behavior_executor import NativeOptionSession
    need(type(original)is NativeOptionSession and isinstance(original.machine,RegisteredNavMachine),'Exact original final NAV session')
    need(original.runtime is placements.r and placements.current_required(),'Final task cannot replace missing original placement boundaries')
    r=original.runtime
    class FinalNAV:
        def __init__(self):self.r=r;self.tasks=list(original.machine.tasks);self.stop=None;self.complete=False
        @property
        def phase(self):return self.stop.phase if self.stop else original.machine.phase
        @property
        def results(self):return list(original.machine.results)+([]if self.stop is None else self.stop.results)
        def enter(self):original.enter()
        def update(self):original.update()if self.stop is None else self.stop.update()
        def next_command(self):return original.command()if self.stop is None else self.stop.next_command()
        def after_step(self):
            if self.stop is None:
                original.after_step()
                if original.outcome=='succeeded':
                    witness=ActualArrivalSupportWitness(original.machine.native_nav);witness.validate(r)
                    journal(dict(event='complex_final_original_NAV_boundary',time_s=float(r.sim.data.time),original_owner_type=type(original.machine).__name__,task_success_not_yet=True,model_input=False))
                    self.stop=FinalSupportedStop(r,original,witness,placements,source_root=source_root,journal=journal,scene=scene);self.stop.enter()
            else:self.stop.after_step();self.complete=self.stop.complete
    return NativeOptionSession(r,FinalNAV(),check_guards=original.check_guards)
