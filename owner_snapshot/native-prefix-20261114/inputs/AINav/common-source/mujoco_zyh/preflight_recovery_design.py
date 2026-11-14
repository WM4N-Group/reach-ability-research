"""Read-only source-consumer inventory for proposed MuJoCo failed-PUSH recovery.

No MuJoCo/Runtime import or construction. Native sources and all published
payloads are hashed, selected definitions inspected, not executed or rewritten.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
from .source_bundle import verify_bundle
from .recovery_design import validate_design


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def definition(path,owner):
    text=Path(path).read_text();nodes=ast.parse(text).body
    for part in owner.split('.'):
        found=[n for n in nodes if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name==part]
        if len(found)!=1:raise ValueError('Exact native source definition missing: '+owner)
        node=found[0];nodes=node.body
    return dict(owner=owner,first_line=node.lineno,last_line=node.end_lineno,
        definition_sha256=hashlib.sha256(ast.get_source_segment(text,node).encode()).hexdigest())


def inspect(bundle,protocol):
    bundle=Path(bundle);source=verify_bundle(bundle);design=validate_design(protocol)
    consumers=[]
    spec=[
        ('switch/machine.py','Machine.update','Native hard flags raise, and only box_settled triggers Finish; early soft abort needs new explicit pre-command route and single stateful predicate sample'),
        ('push/bridge.py','PushBridge.termination','Original clipped-torque .98 arm guard plus geometry/contact/fall remain; add actual raw/queue prediction and strict200Hz speed/range gate, do not weaken native flags'),
        ('push/finish.py','FinishController.command','Native command rejects box>=.12m from original goal (finish_box_left_goal), samples termination, and plans all four contacts; cannot reuse by moving failed A goal'),
        ('push/finish.py','FinishController._arm_step','Native waits.5s and base speed<=.08 then sweeps reverse waypoints; no explicit hand-unload gate, and strict failure path needs measured capture first'),
        ('push/finish.py','FinishController.__init__','Seeds arm_reference from actual q and arm_velocity_reference=zeros; failure entry instead needs factual issued5-channel torque/reference epoch, no fake zero derivative'),
        ('push/finish.py','CollisionGuard.segment','Reuse native arm-vs-all-compiled-collision-geoms sweep including added boxes/platform; separately prove whole-body/leg retreat path and retain actual strict limits'),
        ('push/finish.py','FinishController.after_step','Actual support>4N and native1s+3s finish verification occur after retraction; failure route must capture actual>=12N before stow'),
        ('push/balance.py','WholeBodyQP.solve','Reuse native torque/support machinery with ACTUAL contact mask; QP clips its arm torque model, so separate unclipped raw-torque/FF admission remains mandatory'),
        ('switch/runtime.py','Runtime.step','One physics world/queue; retain native actual200Hz guards and record all issued/delayed commands'),
        ('switch/runtime.py','Runtime.reset_nav_history','Native local software NAV epoch is distinct from deleting physical delay/action/observer history'),
        ('switch/runtime.py','Runtime.push_enter','Never reenter/reset failed PUSH controller to hide its failed goal/history'),
        ('switch/machine.py','Machine.activate','Original stationary/arm-safe entry checks and same-boundary physical state/queue assertions remain'),
        ('nav/navigation.py','NavSkill.stability_checks','Fresh current-goal arrival gates plus real travel and added arrival stow/.5s READY, not zero-idle or old receipt'),
        ('push/motor.py','MotorCommand.array','All18 position/velocity/Kp/Kd/FF channels; last issued vs delayed values must remain distinct'),
    ]
    for path,owner,note in spec:
        consumers.append(dict(path=str((bundle/path).resolve()),file_sha256=sha(bundle/path),**definition(bundle/path,owner),required_treatment=note))
    profile=json.loads((bundle/'push/robot/piper_robot_profile.json').read_text());lookup={j['name']:j['range'] for j in profile['joints']}
    names=[f'joint{i}' for i in range(1,7)];limits=[lookup[n] for n in names];margin=.01
    candidate=[max(lo+margin,min(hi-margin,0.)) for lo,hi in limits]
    problems=[dict(joint=n,range=lim,zero_on_boundary=(lim[0]==0. or lim[1]==0.)) for n,lim in zip(names,limits) if lim[0]==0. or lim[1]==0.]
    parent=Path(__file__).parents[1]
    reused={n:sha(parent/n) for n in ('initial_contact_progress_monitor.py','recovery_reference_intersection.py','failure_exit_backoff_contract.py','contact_failure_exit_contract.py')}
    witnesses={}
    for key,relative,marker in [
        ('failed_goal_rejected','push/finish.py',"self.fail('finish_box_left_goal')"),
        ('native_brake_wait','push/finish.py','if now-self.started<.5:return'),
        ('native_brake_speed','push/finish.py','if np.linalg.norm(sim.data.qvel[:3])>.08:return'),
        ('native_zero_reference_velocity','push/finish.py','self.arm_velocity_reference = np.zeros(6)'),
        ('planned_four_contact_QP','push/finish.py','self.qp.solve(np.ones(4,dtype=bool)'),
        ('all_compiled_collision_geoms','push/finish.py','geoms = [i for i in range(model.ngeom)')]:
        lines=[i+1 for i,line in enumerate((bundle/relative).read_text().splitlines()) if marker in line]
        if len(lines)!=1:raise ValueError('Native source witness changed: '+key)
        witnesses[key]=dict(path=relative,line=lines[0],marker=marker)
    return dict(schema='mujoco-no-reset-recovery-source-design-preflight-v1',design=design,source=source,
        native_consumer_inventory=consumers,native_source_witnesses=witnesses,reused_CPU_contract_sha256=reused,
        native_zero_arm_reference_compatibility=dict(boundary_joints=problems,proposed_inward_reference_rad=candidate,
            pose_or_reference_written=False,FK_collision_NAV_policy_or_dynamics_validated=False,
            cannot_reuse_Finish_zero_target_or_native_NAV_zero_PD_unchanged=True),
        top_live_blockers=['strict startup/NAV velocity and actual angle-range admission unresolved from native1kg run',
            'early-abort command lease and single native termination query per tick not integrated',
            'feedforward/delay-aware unloaded supported controller and immutable queue-prefix feasibility not implemented live',
            'actual full-scene backoff/swept stow and fresh arrival reference epoch not implemented live',
            'NAV inward arm adapter/current-goal3-tick/.5s READY proof not implemented live',
            'private50Hz contact/progress/force/foot evidence and200Hz guard coverage logs not yet wired;10Hz catalog cannot replay60ms detector',
            'independent new protocol/freeze/preflight/one-shot claim not prepared; no design dispatcher'],
        new_physics_starts=0,actor_forwards=0,WM_forwards=0,training_runs=0,dispatchable=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();protocol=json.loads(Path(__file__).with_name('no_reset_recovery_protocol_v1.json').read_text())
    result=inspect(a.bundle,protocol)
    result['own_sources']={n:sha(Path(__file__).with_name(n)) for n in ('recovery_design.py','preflight_recovery_design.py','test_recovery_design.py','no_reset_recovery_protocol_v1.json')}
    with a.output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(dict(design_consistent=result['design']['design_consistent'],native_consumers=len(result['native_consumer_inventory']),dispatchable=False,new_physics_starts=0)))


if __name__=='__main__':main()
