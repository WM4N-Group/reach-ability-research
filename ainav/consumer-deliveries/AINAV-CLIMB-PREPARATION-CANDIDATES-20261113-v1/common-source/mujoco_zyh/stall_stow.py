"""MuJoCo soft PUSH-stall -> measured unload/capture -> protected stow ONLY.

Frozen actors and native motor/QP/collision implementations are reused. New
failure exit has NO native-success Finish goal predicate, no NAV/B authority.
Only a guarded BEFORE-FIRST-STEP initializer sets robot pose. Recovery never
sets task qpos/qvel/object pose or clears queues/histories.
"""
from collections import deque
from dataclasses import replace
import hashlib,json,math
from pathlib import Path
import numpy as np
from initial_contact_progress_monitor import ContactProgressConfig,ContactProgressSample,InitialContactProgressMonitor
from .recovery_design import motor_aware_axis_interval,committed_queue_screen
from .failure_capsules import emit as emit_capsule

MODE='soft-stall-protected-stow-v7'
INITIAL_ARM=np.array([0.,.05,-.05,0.,0.,0.])
NATIVE_COMPACT_ARM=np.array([0.,.1569999908470907,-.14834999036329166,0.,0.,0.])
STOW_ARM=np.array([0.,.18,-.18,0.,0.,0.])  # INSIDE existing soft limits + .01 margin
DEPENDENCIES=('initial_contact_progress_monitor.py','recovery_reference_intersection.py','failure_exit_backoff_contract.py','contact_failure_exit_contract.py')

def dependency_hashes():
    return {n:hashlib.sha256((Path(__file__).parents[1]/n).read_bytes()).hexdigest() for n in DEPENDENCIES}

def initial_posture(reference):
    out=np.array(reference,copy=True);out[12:]=NATIVE_COMPACT_ARM;return out

def initial_base(sim,reference):
    import mujoco
    probe=mujoco.MjData(sim.model)
    probe.qpos[:3]=[-.08,0.,.33];probe.qpos[3:7]=[1.,0.,0.,0.]
    probe.qpos[sim.qids]=initial_posture(reference)
    mujoco.mj_forward(sim.model,probe)
    feet=[sim.model.body(leg+'_foot').id for leg in ('FR','FL','RR','RL')]
    z=.33+.022-float(probe.xpos[feet,2].min())
    if not .25<z<.35:raise ValueError('Registered grounded initialization height outside robot envelope')
    return np.array([-.08,0.,z])


def prepare_initialization_source(text):
    changes={
        "sim.data.qpos[:3] = [-1., box_y if scenario in ('nav-push','nav-push-climb','box-stairs') else 0., .33]":"sim.data.qpos[:3] = _wm_stow_initial_base(sim, pm.REFERENCE)",
        'sim.data.qpos[sim.qids] = pm.REFERENCE':'sim.data.qpos[sim.qids] = _wm_stow_initial(pm.REFERENCE)',
        'self.last = self.Command(pm.REFERENCE.copy(), np.zeros(18), pm.KP.copy(), pm.KD.copy(), np.zeros(18))':'self.last = self.Command(_wm_stow_initial(pm.REFERENCE), np.zeros(18), pm.KP.copy(), pm.KD.copy(), np.zeros(18))'}
    original=text
    for old,new in changes.items():
        if text.count(old)!=1:raise ValueError('Stow initialization hook source mismatch')
        text=text.replace(old,new,1)
    restored=text
    for old,new in reversed(list(changes.items())):restored=restored.replace(new,old,1)
    if restored!=original:raise ValueError('Initialization hook inverse differs')
    return text,dict(initialization_only_hunks=3,inverse_restores_native_scene_hook_source=True,
        task_initial_base='XY[-.08,0], lowest initial foot center Z=.022 via independent zero-step FK',task_initial_arm=NATIVE_COMPACT_ARM.tolist(),entry_arm=INITIAL_ARM.tolist(),
        main_physics_steps_at_initialization=0,no_recovery_state_injected=True)

def validate_protocol(p):
    from .collect import validate_protocol as base_validate
    expected=json.loads(Path(__file__).with_name('soft_stall_stow_protocol_v7.json').read_text())
    if p!=expected:raise ValueError('Exact independent soft-stall/stow protocol required')
    base_validate(dict(p,schema='piper-zyh-mujoco-collection-protocol-v1',selected_object_id='upstream_demo',full_state_review=False))
    return p


def initialize_supported_stance(runtime,require_calibration=True):
    """Registered INITIAL configuration, never callable after ANY task step.
    Only original native calibration leg positions/height are used, not its arm
    limit excursions, velocities, contact forces, queue or failed-task states.
    """
    s=runtime.sim
    if float(s.data.time)!=0. or runtime.step_count!=0 or len(s.queue)!=0:
        raise ValueError('Supported initialization is forbidden after task physics starts')
    if not hasattr(runtime,'push_reference'):
        if require_calibration:raise ValueError('Original native calibration reference missing')
        return dict(applied=False,reason='zero-step geometry fixture has no calibration physics')
    ref=runtime.push_reference;legs=np.array(ref['joints'][:12],dtype=float);height=float(ref['height'])
    limits=s.model.jnt_range[s.jids[:12]]
    if not np.isfinite(legs).all() or np.any(legs<limits[:,0]) or np.any(legs>limits[:,1]) or not .25<height<.35:
        raise ValueError('Original calibrated INITIAL leg posture/height outside physical envelope')
    original_goal=s.box_push_target.numpy().copy();box_pose=s.data.qpos[s.box_qid:s.box_qid+7].copy()
    s.data.qpos[s.qids[:12]]=legs
    s.data.qpos[2]=height
    s.refresh()
    if not np.array_equal(original_goal,s.box_push_target.numpy()) or not np.array_equal(box_pose,s.data.qpos[s.box_qid:s.box_qid+7]):raise RuntimeError('Initializer changed box pose/goal')
    return dict(applied=True,initialization_only=True,task_physics_steps=0,actual_initial_base=s.data.qpos[:3].tolist(),
        actual_initial_legs=legs.tolist(),actual_initial_arm=s.data.qpos[s.qids[12:]].tolist(),
        reference_source='original native auxiliary reference_stance',copied_velocity_force_queue_or_history=False,
        goal_and_object_pose_unchanged=True)


def history_sha(sim):
    h=hashlib.sha256()
    for array in [*(sim.history or []),sim.applied_commands,sim.targets,sim.episode_length_buf.numpy(),sim.box_push_target.numpy()]:
        x=np.ascontiguousarray(array);h.update(str(x.shape).encode());h.update(x.tobytes())
    return h.hexdigest()


def select_reference(desired,reference,velocity,q,dq,kp,kd,ff,effort,limits,dt=.02):
    """Rate/accel intersection coupled to ACTUAL outgoing PD velocity + FF.
    Existing motor_aware_axis_interval independently checks the final candidate.
    """
    vectors=(desired,reference,velocity,q,dq,kp,kd,ff,effort)
    if any(np.shape(v)!=(6,) or not np.isfinite(v).all() for v in vectors) or np.shape(limits)!=(6,2):raise ValueError('Finite exact6-axis inputs required')
    if np.max(abs(velocity))>.45 or not .0049999<=dt<=.020001:raise ValueError('Actual reference velocity/clock outside original domain')
    vmax=.4499;amax=.999  # strictly INSIDE frozen .45/1 boundaries, no floating-point relaxation
    candidates=[];speeds=[];receipts=[]
    for j in range(6):
        lo,hi=map(float,limits[j]);r,v,x,w,K,D,F,E=map(float,(reference[j],velocity[j],q[j],dq[j],kp[j],kd[j],ff[j],effort[j]))
        delta=float(desired[j])-r
        wanted=math.copysign(min(abs(delta)/dt,vmax,math.sqrt(2.*amax*abs(delta))),delta)
        vn=max(-vmax,min(vmax,max(v-amax*dt,min(v+amax*dt,wanted))));nominal=r+dt*vn
        rate=[r+dt*max(-vmax,v-amax*dt),r+dt*min(vmax,v+amax*dt)]
        Kc=K+D/dt;centers=[(K*(x+h*w)+D*w+D*r/dt-F)/Kc for h in (0.,.06)]
        radius=.90*E/Kc;lower=max(rate[0],lo+.01,max(centers)-radius);upper=min(rate[1],hi-.01,min(centers)+radius)
        if lower>upper:raise RuntimeError('empty_coupled_reference_interval:'+str(j))
        selected=max(lower,min(upper,nominal));vs=(selected-r)/dt
        check=motor_aware_axis_interval(feedforward=F,target_velocity=vs,delay_s=.02,
            reference=r,reference_velocity=v,measured_q=x,measured_dq=w,kp=K,kd=D,effort_limit=E,soft_lower=lo,soft_upper=hi,dt=dt)
        if not check['feasible'] or not check['lower']-1e-10<=selected<=check['upper']+1e-10:
            raise RuntimeError('native_motor_reference_screen_failed:'+str(j))
        candidates.append(selected);speeds.append(vs);receipts.append(dict(joint=j,lower=lower,upper=upper,selected=selected,velocity=vs))
    return np.array(candidates),np.array(speeds),receipts


def unload_reference(goal,start,reference,velocity,q,dq,kp,kd,gravity,effort,limits,age,dt=.005,start_ff=None):
    """Bumpless reconciliation of REAL issued PD gravity deflection.
    Keep original gains; replace the spring's gravity-support torque with the
    native gravity FF in proportion to actual issued reference progress. PD
    velocity is ZERO during unloading, independently of position-field rate.
    Piecewise-affine full rate/accel/PD/FF intersection, not a nominal veto.
    """
    def refuse(reason,j,**details):
        error=RuntimeError(reason+':'+str(j))
        error.wm_reference_inputs=dict(failing_joint_zero_based=j,goal=np.array(goal,copy=True),start=np.array(start,copy=True),
            reference=np.array(reference,copy=True),velocity=np.array(velocity,copy=True),q=np.array(q,copy=True),dq=np.array(dq,copy=True),
            kp=np.array(kp,copy=True),kd=np.array(kd,copy=True),gravity=np.array(gravity,copy=True),effort=np.array(effort,copy=True),
            limits=np.array(limits,copy=True),age=age,dt=dt,PD_velocity=0.,details=details,start_ff=None if start_ff is None else np.array(start_ff,copy=True))
        raise error
    initial_ff=np.zeros(6) if start_ff is None else np.asarray(start_ff,dtype=float)
    if initial_ff.shape!=(6,) or not np.isfinite(initial_ff).all():raise ValueError("Actual six-axis initial FF required")
    output=[];speeds=[];ffs=[];receipts=[]
    for j in range(6):
        r,v,x,w,K,D,G,E,origin,target=map(float,(reference[j],velocity[j],q[j],dq[j],kp[j],kd[j],gravity[j],effort[j],start[j],goal[j]))
        if abs(v)>.45:raise ValueError('Actual unload reference derivative outside fold domain')
        delta=target-r;wanted=math.copysign(min(abs(delta)/dt,.4499,math.sqrt(2*.999*abs(delta))),delta)
        vn=max(-.4499,min(.4499,max(v-.999*dt,min(v+.999*dt,wanted))));nominal=r+dt*vn
        lower=max(r+dt*max(-.4499,v-.999*dt),float(limits[j,0])+.01)
        upper=min(r+dt*min(.4499,v+.999*dt),float(limits[j,1])-.01)
        span=target-origin
        def coefficients(mid):
            if start_ff is not None:
                previous=float(initial_ff[j]);difference=G-previous
                if abs(span)<.001:
                    u=min(1.,max(0.,age/.5));return 0.,previous+difference*u*u*(3-2*u)
                alpha=(mid-origin)/span
                if alpha<=0:return 0.,previous
                if alpha>=1:return 0.,G
                return difference/span,previous-difference*origin/span
            if abs(span)<.001:
                u=min(1.,max(0.,age/.5));return 0.,G*u*u*(3-2*u)
            alpha=(mid-origin)/span
            if alpha<=0:return 0.,0.
            if alpha>=1:return 0.,G
            return G/span,-G*origin/span
        cuts=sorted(set([lower,upper]+[p for p in (origin,target) if lower<p<upper]));feasible=[]
        for lo,hi in zip(cuts[:-1],cuts[1:]):
            a,b=coefficients((lo+hi)/2);A=K+a
            for h in (0.,.06):
                B=-K*(x+h*w)-D*w+b
                if abs(A)<1e-9:
                    if abs(B)>.90*E:lo,hi=1.,0.
                else:
                    roots=sorted(((-.90*E-B)/A,(.90*E-B)/A));lo=max(lo,roots[0]);hi=min(hi,roots[1])
            if lo<=hi:feasible.append((max(lo,min(hi,nominal)),lo,hi,a,b))
        if not feasible:refuse('unload_coupled_reference_intersection_empty',j,lower=lower,upper=upper,cuts=cuts,nominal=nominal)
        selected,lo,hi,a,b=min(feasible,key=lambda z:abs(z[0]-nominal));ff=a*selected+b;vs=(selected-r)/dt
        check=motor_aware_axis_interval(feedforward=ff,target_velocity=0.,delay_s=.02,reference=r,reference_velocity=v,
            measured_q=x,measured_dq=w,kp=K,kd=D,effort_limit=E,soft_lower=float(limits[j,0]),soft_upper=float(limits[j,1]),dt=dt)
        if not check['feasible'] or not check['lower']-1e-10<=selected<=check['upper']+1e-10:refuse('unload_selected_motor_screen_refused',j,selected=selected,selected_ff=ff,motor_screen=check)
        output.append(selected);speeds.append(vs);ffs.append(ff);receipts.append(dict(joint=j,lower=lo,upper=hi,selected=selected,velocity=vs,feedforward=ff,PD_velocity=0.))
    return np.array(output),np.array(speeds),np.array(ffs),receipts


def base_tracking_com_goal(actual_com_x, base_velocity_x, com_velocity_x, standoff, position_gain, velocity_gain):
    """Map signed box-gap/base-velocity servo into the UNCHANGED native COM task.

    COM motion includes leg shape and floating-base rotation, not only arm
    motion. Removing only arm velocity permits leg reconfiguration to hide
    base drift. Subtract full measured shape velocity, and allow a bounded
    return command after overshoot instead of a one-sided dead zone.
    """
    values=(actual_com_x,base_velocity_x,com_velocity_x,standoff,position_gain,velocity_gain)
    if not np.isfinite(values).all() or min(position_gain,velocity_gain)<=0:
        raise ValueError('Finite kinematics and positive original gains required')
    desired_base_velocity=float(np.clip(2.*(standoff-.645),-.05,.05))
    internal_velocity=com_velocity_x-base_velocity_x
    goal=actual_com_x+velocity_gain/position_gain*(desired_base_velocity+internal_velocity)
    return goal,desired_base_velocity


class SoftStall(Exception):pass


def measured_face_standoff(box_center, base_position, box_rotation, box_length_m):
    if (not math.isfinite(box_length_m) or box_length_m<=0 or
            np.shape(box_center)!=(3,) or np.shape(base_position)!=(3,) or np.shape(box_rotation)!=(3,3)
            or not all(np.isfinite(v).all() for v in (box_center,base_position,box_rotation))):
        raise ValueError('Actual selected-box geometry required for front-face gap')
    return float(np.dot(np.asarray(box_center)-base_position,np.asarray(box_rotation)[:,0])-box_length_m/2)


class ProtectedStow:
    def __init__(self,r,last_two,compact_goal=None,unload_initial_ff=None,native_arrival=None):
        self.compact_goal=STOW_ARM.copy() if compact_goal is None else np.array(compact_goal,dtype=float,copy=True)
        if self.compact_goal.shape!=(6,) or not np.isfinite(self.compact_goal).all():raise ValueError('Explicit finite compact goal required')
        self.native_arrival=native_arrival
        if native_arrival is not None:
            from .native_nav_arrival_witness import NativeNAVArrivalWitness
            if not isinstance(native_arrival,NativeNAVArrivalWitness):raise ValueError('Actual native NAV witness required')
            native_arrival.validate(r)
            if not np.array_equal(native_arrival.compact_goal,self.compact_goal):raise ValueError('Witness and capture compact targets differ')
        self.arrival_balance=native_arrival is not None
        self.r,self.s=r,r.sim;s=self.s;finish=r.push['finish'];self.pm=r.push['model']
        self.old=r.last
        self.unload_initial_ff=None if unload_initial_ff is None else np.array(unload_initial_ff,dtype=float,copy=True)
        if self.unload_initial_ff is not None and (self.unload_initial_ff.shape!=(6,) or not np.array_equal(self.unload_initial_ff,self.old.feedforward[12:])):
            raise ValueError('Unload initial FF must equal actual last-issued arm FF, not a synthetic gravity guess')
        seed=committed_queue_screen(queue=[a.tolist() for a in s.queue],delay_steps=[int(v) for v in s.delays],
            q=s.data.qpos[s.qids].tolist(),dq=s.data.qvel[s.dids].tolist(),effort=self.pm.EFFORT.tolist())
        if not seed['screen_pass']:raise RuntimeError('immutable_pending_queue_refused:'+str(seed['failures']))
        self.unload_target=s.data.qpos[s.qids[12:]].copy()
        self.reference=self.old.position[12:].copy();self.velocity=(last_two[-1][12:]-last_two[-2][12:])/.005
        if np.max(abs(self.velocity))>.45:raise RuntimeError('actual_issued_reference_seed_too_fast')
        self.native=finish.FinishController(s,replace(finish.FinishConfig(),arm_pose=tuple(self.compact_goal),arm_speed=.45,deadline=60.,stance_posture_weight=0.))
        self.native.entry_position=self.old.position[:12].copy()  # NOT unissued p.targets
        import mujoco
        self.balance_reference=mujoco.MjData(s.model)
        if self.balance_reference is s.data:raise RuntimeError('Display/reference data alias live task')
        self.last_com_update=-math.inf;self.com_target=None
        self.started=float(s.data.time);self.phase='UNLOAD_CAPTURE' if native_arrival is None else 'ARRIVAL_CAPTURE';self.complete=False
        self.events=[dict(time=self.started,event='failed_PUSH_authority_retired_actual_queue_preserved' if native_arrival is None else 'actual_native_NAV_arrival_capture_actual_queue_preserved',pending_queue=seed)]
        self.segment_start=None;self.segment_origin=None;self.segment_duration=None
        self.index=0;self.last_update=-math.inf;self.support_anchor_since=None;self.support_anchors_latched=False
        self.captured_since=None;self.unloaded_time=None;self.stable_since=None
        self.waypoints=[np.array(q) for q in self.native.waypoints[:-1]]  # native reverse safe path; final compact interior of soft limits, not boundary zero
        self.waypoints[-1]=self.compact_goal.copy()
        self.limits=np.maximum(s.model.jnt_range[s.jids[12:],0],s.soft_limits[12:,0]),np.minimum(s.model.jnt_range[s.jids[12:],1],s.soft_limits[12:,1])
        self.limits=np.column_stack(self.limits);self.reference_receipts=[];self.metrics={}
        self.original_goal=s.box_push_target.numpy().copy();self.retired_history_sha=history_sha(s)
        if native_arrival is None:
            initial_gap=self.measure()['standoff_m']
            self.retreat_distance=max(.08,.645-initial_gap)
            if self.retreat_distance>.18:raise RuntimeError('required_measured_face_retreat_outside_registered_envelope')
        else:
            # A verified compact NAV arrival is NOT a new failed PUSH. Capture
            # its actual loaded stance; never servo toward an unrelated retired
            # box's forward face or silently modify the original NAV/PUSH goals.
            self.retreat_distance=0.

        self.retreat_duration=max(1.5,1.875*self.retreat_distance/.10)
        self.reference_start=self.reference.copy()
        self.seed=dict(position=self.reference.tolist(),reference_velocity=self.velocity.tolist(),actual_last_two_positions=[v[12:].tolist() for v in last_two],actual_PD_velocity=self.old.velocity[12:].tolist())

    def begin_segment(self,now):
        self.segment_start=now;self.segment_origin=self.reference.copy()
        delta=float(np.max(abs(self.waypoints[self.index]-self.segment_origin)))
        self.segment_duration=max(.6,1.875*delta/.40,math.sqrt(5.78*delta/.80))

    def event(self,name):self.events.append(dict(time=float(self.s.data.time),event=name))

    def measure(self):
        s=self.s;data=s.data;R=data.xmat[s.base_id].reshape(3,3)
        force=s.scene.sensors['box_contact_hand'].data.force_matrix_w.numpy().sum(axis=(1,2))[0]
        legal=bool(self.r.push['bridge'].box_push.hand_contact(s,s.hand_cfg)[0])
        feet=s.forces[s.feet_ids,2];foot_speeds=[]
        import mujoco
        for bid in s.feet_ids:
            J=np.zeros((3,s.model.nv));mujoco.mj_jacBody(s.model,data,J,None,int(bid));foot_speeds.append(float(np.linalg.norm((J@data.qvel)[:2])))
        boxv=data.qvel[s.box_did:s.box_did+6]
        return dict(hand_force_N=float(np.linalg.norm(force)),legal_hand_contact=legal,foot_normal_N=feet.tolist(),
            base_linear_speed=float(np.linalg.norm(data.qvel[:3])),base_angular_speed=float(np.linalg.norm(data.qvel[3:6])),
            tilt_rad=float(np.arccos(np.clip(R[2,2],-1,1))),max_foot_speed=max(foot_speeds),
            box_linear_speed=float(np.linalg.norm(boxv[:3])),box_angular_speed=float(np.linalg.norm(boxv[3:])),
            standoff_m=measured_face_standoff(data.xpos[s.box_id],data.qpos[:3],data.xmat[s.box_id].reshape(3,3),float(s.cfg.box_size[0])),
            arm_error=float(np.max(abs(data.qpos[s.qids[12:]]-self.compact_goal))),arm_speed=float(np.max(abs(data.qvel[s.dids[12:]]))),
            base_retreat_m=float(self.native.initial_base[0]-data.qpos[0]),base_horizontal_displacement_m=float(np.linalg.norm(data.qpos[:2]-self.native.initial_base[:2])))

    def clearance_gate(self,metrics):
        if self.native_arrival is None:return metrics['standoff_m']>=.63
        self.native_arrival.retain_goal(self.r)
        reason=self.native.guard.check(self.s.data.qpos[self.s.qids[12:]],record=True)
        if reason:raise RuntimeError('actual_NAV_arrival_original_geometry:'+reason)
        return True  # real original whole-scene clearance, not a fabricated gap

    def update(self):
        s=self.s;now=float(s.data.time);self.metrics=self.measure();m=self.metrics
        if history_sha(s)!=self.retired_history_sha or not np.array_equal(s.box_push_target.numpy(),self.original_goal):raise RuntimeError('retired_PUSH_history_or_original_goal_changed')
        if now-self.started>60:raise RuntimeError('protected_stow_timeout')
        if m['base_horizontal_displacement_m']>.18 or m['base_linear_speed']>.15:
            error=RuntimeError('measured_unload_retreat_outside_original_envelope')
            emit_capsule(self.r,'unload_envelope_refusal',view=s,extra=dict(error=repr(error),actual_metrics=m),preserve_primary_failure=True)
            raise error
        planted=min(m['foot_normal_N'])>=12 and m['max_foot_speed']<.03
        self.support_anchor_since=(self.support_anchor_since if self.support_anchor_since is not None else now) if planted else None
        if not self.support_anchors_latched and self.support_anchor_since is not None and now-self.support_anchor_since>=.1-1e-8:
            # NEW CONTROL-REFERENCE epoch from real loaded stationary feet, NOT
            # a foot/object/robot state write; preserve queue and solver history.
            self.native.anchors=s.data.xpos[s.feet_ids].copy()
            self.support_anchors_latched=True;self.last_com_update=-math.inf
            self.event('actual_loaded_stationary_feet_reference_captured')
        arrival_capture=self.phase=='ARRIVAL_CAPTURE'
        clearance=self.clearance_gate(m)
        capture_target=self.compact_goal if arrival_capture else self.unload_target
        capture=(self.support_anchors_latched and now-self.started>=(.5 if arrival_capture else 2.5) and m['hand_force_N']<3 and not m['legal_hand_contact'] and min(m['foot_normal_N'])>=12 and
            m['base_linear_speed']<.02 and m['base_angular_speed']<.1 and m['tilt_rad']<.1 and m['max_foot_speed']<.03 and
            m['box_linear_speed']<.02 and m['box_angular_speed']<.1 and clearance and
            np.max(abs(self.reference-capture_target))<.002 and np.max(abs(self.velocity))<.02 and m['arm_speed']<.12)
        if self.phase in ('UNLOAD_CAPTURE','ARRIVAL_CAPTURE'):
            self.captured_since=(self.captured_since if self.captured_since is not None else now) if capture else None
            if self.captured_since is not None and now-self.captured_since>=.2-1e-8:
                queued=committed_queue_screen(queue=[a.tolist() for a in s.queue],delay_steps=[int(v) for v in s.delays],q=s.data.qpos[s.qids].tolist(),dq=s.data.qvel[s.dids].tolist(),effort=self.pm.EFFORT.tolist())
                if not queued['screen_pass']:raise RuntimeError('fold_handoff_pending_queue_refused')
                start=s.data.qpos[s.qids[12:]].copy()
                if not arrival_capture:
                    _reach_choice_callback = globals().get('_reach_stow_path_choice_at_capture')
                    if _reach_choice_callback is not None:
                        _reach_choice_callback(self, start, capture=capture, queued=queued, now=now)
                for goal in ([self.compact_goal] if arrival_capture else self.waypoints):
                    reason=self.native.guard.segment(start,goal)
                    if reason:raise RuntimeError('failure_stow_path_blocked:'+reason)
                    start=goal
                self.phase='STOW_VERIFY' if arrival_capture else 'PROTECTED_STOW';self.unloaded_time=now
                if not arrival_capture:self.begin_segment(now)
                self.event('actual_arrival_brake_loaded_support_captured' if arrival_capture else 'actual_unloaded_supported_retreat_and_full_path_checked')
            elif now-self.started>5.:raise RuntimeError('actual_unload_capture_5s_timeout')
        if self.phase=='PROTECTED_STOW':
            goal=self.waypoints[self.index]
            if now-self.segment_start>=self.segment_duration and np.max(abs(s.data.qpos[s.qids[12:]]-goal))<.04 and np.max(abs(s.data.qvel[s.dids[12:]]))<.12 and np.max(abs(self.reference-goal))<.002 and np.max(abs(self.velocity))<.02:
                self.event('actual_safe_arm_waypoint_'+str(self.index));self.index+=1
                if self.index==len(self.waypoints):self.phase='STOW_VERIFY';self.event('actual_arm_compact_safe_pose_reached')
                else:self.begin_segment(now)
        final_capture=(m['hand_force_N']<3 and not m['legal_hand_contact'] and min(m['foot_normal_N'])>=12 and m['base_linear_speed']<.02 and m['base_angular_speed']<.1 and m['tilt_rad']<.1 and m['max_foot_speed']<.03 and m['box_linear_speed']<.02 and m['box_angular_speed']<.1 and clearance)
        final=(final_capture and m['arm_error']<.04 and m['arm_speed']<.12 and np.max(abs(self.reference-self.compact_goal))<.002 and np.max(abs(self.velocity))<.02)
        if self.phase in ('STOW_VERIFY','STOW_VERIFIED'):
            if final:
                if self.stable_since is None:self.stable_since=now
                if now-self.stable_since>=4.-1e-8 and not self.complete:
                    self.complete=True;self.phase='STOW_VERIFIED';self.event('failed_PUSH_stow_1s_plus3s_verified_NO_NAV' if self.native_arrival is None else 'actual_native_NAV_arrival_compact_hold_verified')
            else:
                if self.complete:raise RuntimeError('stow_verified_hold_lost')
                self.stable_since=None

    def command(self):
        s=self.s;c=self.native;now=float(s.data.time);age=now-self.started
        gravity=s.robot.get_gravity_compensation_forces().numpy()[0]
        cols=[s.robot.joint_names.index('joint'+str(i)) for i in range(1,7)]
        gravity=gravity[cols]
        if now-self.last_update>=.005-1e-8:
            self.last_update=now
            if self.phase=='UNLOAD_CAPTURE':
                try:
                    self.reference,self.velocity,self.command_ff,self.reference_receipts=unload_reference(self.unload_target,self.reference_start,self.reference,self.velocity,
                        s.data.qpos[s.qids[12:]],s.data.qvel[s.dids[12:]],self.pm.KP[12:],self.pm.KD[12:],gravity,self.pm.EFFORT[12:],self.limits,age,start_ff=getattr(self,'unload_initial_ff',None))
                except RuntimeError as error:
                    emit_capsule(self.r,'unload_reference_refusal',view=s,extra=dict(error=repr(error),reference_inputs=getattr(error,'wm_reference_inputs',None)),preserve_primary_failure=True)
                    raise
            else:
                if self.phase=='PROTECTED_STOW':
                    u=np.clip((now-self.segment_start)/self.segment_duration,0.,1.);blend=u**3*(10-15*u+6*u*u)
                    desired=self.segment_origin+blend*(self.waypoints[self.index]-self.segment_origin)
                else:desired=self.compact_goal
                self.command_ff=gravity.copy()
                self.reference,self.velocity,self.reference_receipts=select_reference(desired,self.reference,self.velocity,
                    s.data.qpos[s.qids[12:]],s.data.qvel[s.dids[12:]],self.pm.KP[12:],self.pm.KD[12:],self.command_ff,self.pm.EFFORT[12:],self.limits,dt=.005)
            reason=c.guard.segment(s.data.qpos[s.qids[12:]],self.reference) if self.phase!='UNLOAD_CAPTURE' else c.guard.check(self.reference,allow_hand_contact=True)
            if reason:raise RuntimeError('protected_reference_geometry:'+reason)
            predicted=s.data.qpos[s.qids[12:]]+.1*s.data.qvel[s.dids[12:]]
            warning=c.guard.check(predicted,allow_hand_contact=self.phase=='UNLOAD_CAPTURE',joint_limits=False)
            if warning:raise RuntimeError('actual_velocity_geometry_forecast:'+warning)
        ff=self.command_ff
        posture=c.entry_posture.copy()  # retain real supported PUSH stance by default
        if self.arrival_balance:
            if (age>=c.config.stance_delay+c.config.stance_seconds and self.support_anchors_latched
                    and c.config.stance_posture_weight!=0.):
                # Once real feet are loaded and native stance normalization is
                # complete, retire the competing posture cost for gap relocation.
                # Same native QP/constraints; no contact forces are overwritten.
                c.config=replace(c.config,stance_posture_weight=0.);c.qp.config=c.config
                self.event('actual_loaded_normalized_stance_then_gap_relocation')
            # Native Finish's actual post-gait stance normalization. Only
            # software references interpolate; robot state/forces stay measured.
            u=np.clip((age-c.config.stance_delay)/c.config.stance_seconds,0.,1.)
            w=u*u*(3.-2.*u);posture=(1-w)*c.entry_posture+w*c.stand_posture
        if now-self.last_com_update>=.02-1e-8:
            import mujoco
            self.last_com_update=now;before=s.data.qpos.copy();ref=self.balance_reference
            ref.qpos[:]=s.data.qpos;ref.qvel[:]=0.
            ref.qpos[s.qids[:12]]=posture
            ref.qpos[3:7]=[np.cos(c.yaw/2),0.,0.,np.sin(c.yaw/2)]
            mujoco.mj_forward(s.model,ref)
            self.com_target=c.anchors.mean(axis=0)+ref.subtree_com[s.base_id]-ref.xpos[s.feet_ids].mean(axis=0)
            if not np.array_equal(before,s.data.qpos):raise RuntimeError('Reference FK changed live task')
        com=self.com_target.copy()
        # Original PushEntry disables posture regularization for COM relocation.
        # Track the REAL box-face gap, not an assumed COM/base displacement ratio.
        import mujoco
        Jcom=np.zeros((3,s.model.nv));mujoco.mj_jacSubtreeCom(s.model,s.data,Jcom,s.base_id)
        if self.native_arrival is None:
            com[0],_=base_tracking_com_goal(float(s.data.subtree_com[s.base_id,0]),float(s.data.qvel[0]),
                float(Jcom[0]@s.data.qvel),self.measure()['standoff_m'],c.config.position_gain,c.config.velocity_gain)

        PD_velocity=np.zeros(6) if self.phase=='UNLOAD_CAPTURE' else self.velocity
        command=self.r.Command(np.r_[posture,self.reference],np.r_[np.zeros(12),PD_velocity],self.pm.KP.copy(),self.pm.KD.copy(),np.r_[np.zeros(12),ff])
        contacts=np.ones(4,dtype=bool) if self.arrival_balance else s.forces[s.feet_ids,2]>4.
        torque,*_=c.qp.solve(contacts,c.anchors,np.zeros((4,3)),np.zeros((4,3)),com,c.yaw,posture,command)
        takeover=np.clip(age/.1,0,1);takeover=takeover*takeover*(3-2*takeover)
        q=s.data.qpos[s.qids[:12]];dq=s.data.qvel[s.dids[:12]]
        command.position[:12]=q;command.kp[:12]=(1-takeover)*self.old.kp[:12]+takeover*5.
        command.kd[:12]=(1-takeover)*self.old.kd[:12]+takeover
        command.feedforward[:12]=(1-takeover)*(self.old.kp[:12]*(self.old.position[:12]-q)+self.old.kd[:12]*self.old.velocity[:12]+self.old.feedforward[:12])+takeover*(torque+dq)
        return command

    def after_step(self):
        s=self.s;reason=self.native.guard.check(s.data.qpos[s.qids[12:]],allow_hand_contact=self.phase=='UNLOAD_CAPTURE',record=True)
        if reason:raise RuntimeError('actual_stow_geometry:'+reason)
        if self.phase not in ('UNLOAD_CAPTURE','ARRIVAL_CAPTURE') and (min(s.forces[s.feet_ids,2])<12 or self.measure()['hand_force_N']>=3):raise RuntimeError('supported_unloaded_stow_gate_lost')
        if np.max(abs(s.torque[12:])/self.pm.EFFORT[12:])>=.98:raise RuntimeError('native_arm_effort_safety_during_recovery')
        box=self.r.push['bridge'].box_push
        for name,call in [('box_contact',lambda:box.forbidden_box_contact(s)),('invalid_hand_contact',lambda:box.invalid_hand_contact(s,s.hand_cfg)),('box_tipped',lambda:box.box_tipped(s))]:
            if bool(call()[0]):raise RuntimeError('native_'+name+'_during_recovery')
        self.update()  # ALL capture/stow/hold gates evaluated at actual200Hz, not just video/control frames

    def report(self):
        return dict(phase=self.phase,stow_verified=self.complete,native_PUSH_attempt_failed=self.native_arrival is None,NO_NAV_or_B_admission=self.native_arrival is None,
            native_NAV_arrival_capture=self.native_arrival.report() if self.native_arrival is not None else None,automatic_successor_admission=False,
            original_goal_preserved=np.array_equal(self.s.box_push_target.numpy(),self.original_goal),retired_PUSH_history_preserved=history_sha(self.s)==self.retired_history_sha,
            actual_motor_reference_seed=self.seed,events=self.events,metrics=self.metrics,stow_arm_reference=self.compact_goal.tolist(),
            minimum_body_clearance_m=self.native.guard.minimum_surface,minimum_other_clearance_m=self.native.guard.minimum,
            reference_speed_limit=.45,reference_acceleration_limit=1.,
            initial_required_face_retreat_m=self.retreat_distance,measured_face_target_m=.645 if self.native_arrival is None else None,retreat_velocity_limit_m_s=.05,
            leg_posture_regularization=0.,actual_stationary_support_reference_captured=self.support_anchors_latched,full_internal_COM_velocity_compensated=True,signed_base_gap_servo=self.native_arrival is None,synchronized_nominal_waypoints=True,nominal_speed=.40,nominal_acceleration=.80,
            native_arm_gains_unchanged=True,unload_PD_velocity_zero=True,actual_initial_FF_preserved=self.unload_initial_ff.tolist() if self.unload_initial_ff is not None else None,
            gravity_support_bumpless_reconciliation=True,leg_posture_reference='actual entry support stance retained',native_QP_max_residual=self.native.qp.maximum_residual)


class StallStowRouter:
    def __init__(self,r,native,root):
        self.r,self.native=r,native;self.recovery=None;self.monitor=InitialContactProgressMonitor(ContactProgressConfig(window_s=.06))
        self.last_two=deque([r.last.position.copy(),r.last.position.copy()],maxlen=2)
        self.original_termination=r.sim.termination;self.control_tick=0;self.abort=None;self.entry_patched=False
        self.log=(Path(root)/'stall-monitor-50hz.jsonl').open('x');self.recovery_log=(Path(root)/'stow-actual-200hz.jsonl').open('x')
        r.sim.termination=self.termination
    @property
    def complete(self):return self.recovery is not None and self.recovery.complete
    @property
    def phase(self):return self.recovery.phase if self.recovery else self.native.phase
    @property
    def kind(self):return 'push' if self.recovery else getattr(self.native,'kind','startup')
    @property
    def index(self):return self.native.index
    @property
    def events(self):return self.native.events+(self.recovery.events if self.recovery else [])
    @property
    def results(self):return self.native.results
    @property
    def switch_metrics(self):return self.native.switch_metrics
    @property
    def finish(self):return self.native.finish
    def termination(self):
        flags=self.original_termination();s=self.r.sim
        if self.recovery is not None or self.kind!='push' or self.native.phase=='prepare':return flags
        bad=[k for k,v in flags.items() if k!='box_settled' and v]
        legal=bool(self.r.push['bridge'].box_push.hand_contact(s,s.hand_cfg)[0]);near=bool(np.linalg.norm(s.data.xpos[s.box_id,:2]-s.box_push_target[0,:2].numpy())<.12)
        decision=self.monitor.observe(ContactProgressSample(self.control_tick,float(s.data.time),True,bool(s.controller.motion_ready[0]),legal,True,float(s.data.xpos[s.box_id,0]),near,bool(flags['box_settled']),bool(bad)))
        force=s.scene.sensors['box_contact_hand'].data.force_matrix_w.numpy().sum(axis=(1,2))[0]
        self.log.write(json.dumps(dict(tick=self.control_tick,time_s=float(s.data.time),motion_ready=bool(s.controller.motion_ready[0]),legal_hand_contact=legal,hand_force_N=force.tolist(),box_x=float(s.data.xpos[s.box_id,0]),box_position_world_xyz=s.data.xpos[s.box_id].tolist(),near_original_goal=near,native_settled=bool(flags['box_settled']),native_flags=flags,status=decision.status,elapsed_contact_s=decision.elapsed_contact_s,dx_m=decision.observed_forward_dx_m,native_hard_flags=bad,new_soft_abort=decision.new_soft_abort_request))+'\n');self.log.flush()
        if decision.new_soft_abort_request:
            self.abort=dict(time_s=float(s.data.time),box_dx_contact_window_m=decision.observed_forward_dx_m,contact_window_s=decision.elapsed_contact_s,original_goal=s.box_push_target.numpy().tolist(),native_goal_success=False,unissued_current_policy_proposal_retained=True,unissued_policy_target=s.targets.tolist(),last_actually_issued_target=self.r.last.position.tolist())
            emit_capsule(self.r,'soft_progress_abort',view=s,extra=dict(abort=self.abort,native_flags=flags))
            raise SoftStall('current_PUSH_attempt_insufficient_initial_progress')
        return flags
    def make_recovery(self):return ProtectedStow(self.r,list(self.last_two))

    def update(self):
        if self.recovery:
            flags=self.original_termination();bad=[k for k,v in flags.items() if k!='box_settled' and v]
            if bad:raise RuntimeError('native_recovery_hard_flags:'+','.join(bad))
            self.recovery.update()
        else:
            try:self.native.update()
            except SoftStall:self.recovery=self.make_recovery()
            if self.native.phase=='prepare' and not self.entry_patched:
                qp=self.native.preparation.qp;original=qp.solve
                def solve(contacts,anchors,fv,fa,com,yaw,posture,arm):
                    arm.position[12:]=getattr(self,'entry_arm',INITIAL_ARM)
                    return original(contacts,anchors,fv,fa,com,yaw,posture,arm)
                qp.solve=solve;self.entry_patched=True
            if self.native.finish is not None and self.recovery is None:raise RuntimeError('native_success_before_stall_not_a_failure_recovery')
        self.control_tick+=1
    def next_command(self):return self.recovery.command() if self.recovery else self.native.next_command()
    def after_step(self):
        s=self.r.sim;self.last_two.append(self.r.last.position.copy());limits=s.model.jnt_range[s.jids]
        if not np.isfinite(np.r_[s.data.qpos,s.data.qvel,s.torque]).all():raise RuntimeError('nonfinite_actual_state')
        if np.any(s.data.qpos[s.qids]<limits[:,0]) or np.any(s.data.qpos[s.qids]>limits[:,1]):raise RuntimeError('actual_strict_joint_range_violation')
        if np.any(abs(s.data.qvel[s.dids])>self.r.push['model'].SPEED):raise RuntimeError('actual_strict_joint_speed_violation')
        if self.recovery:
            self.recovery.after_step();m=self.recovery.metrics
            if self.log.tell()+self.recovery_log.tell()>32*1024*1024:raise RuntimeError('registered_private_recovery_log_quota_censor')
            self.recovery_log.write(json.dumps(dict(time_s=float(s.data.time),phase=self.phase,q=s.data.qpos[s.qids].tolist(),dq=s.data.qvel[s.dids].tolist(),arm_reference=self.recovery.reference.tolist(),arm_reference_velocity=self.recovery.velocity.tolist(),metrics=m))+'\n')
        else:
            self.native.after_step()
            if self.native.phase in ('startup','prepare'):
                reason=self.native.guard.check(s.data.qpos[s.qids[12:]],record=True)
                if reason:raise RuntimeError('initial_prefix_geometry:'+reason)
    def diagnostics(self):return dict(phase=self.phase,abort=self.abort,reference_intervals=self.recovery.reference_receipts if self.recovery else [])
    def report(self):return dict(abort=self.abort,recovery=self.recovery.report() if self.recovery else None,scope='failed PUSH unload/compact safe stow only, NO NAV/B/full route',reset_after_initial=0)
    def close(self):self.log.close();self.recovery_log.close()
