"""One bounded read-only A03 real-model CPU experiment; NEVER a physics rollout.

Loads one frozen MJB plus pinned native nominal references. Writes only own root.
No old states/results, WM, actor, calibration world, renderer or mj_step is read/run.
Static foot anchors are NOMINAL model assumptions, not actual contact-force data.
"""
import argparse,ast,hashlib,json,os,resource,signal,time,traceback
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def save(path,value):
    def default(v):
        if hasattr(v,'tolist'):return v.tolist()
        raise TypeError(type(v).__name__)
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False,default=default)+'\n')


def reference_from_source(path):
    tree=ast.parse(Path(path).read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(n,ast.Name) and n.id=='REFERENCE' for n in node.targets):
            value=node.value
            # Frozen source is np.array([...]); evaluate only the literal payload.
            def literal(n):
                if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Mult)):
                    left,right=literal(n.left),literal(n.right)
                    if isinstance(n.op,ast.Add) and isinstance(left,list) and isinstance(right,list):return left+right
                    if isinstance(n.op,ast.Mult) and isinstance(left,list) and type(right) is int:return left*right
                    raise ValueError('Unsupported reference literal operation')
                return ast.literal_eval(n)
            if isinstance(value,ast.Call) and value.args:
                return literal(value.args[0])
            return literal(value)
    raise ValueError('Native REFERENCE literal not found; never execute/import native policy code')


def run(root,protocol):
    import sys
    import numpy as np
    import mujoco
    from scipy.optimize import linprog
    from handover_envelope import relative_hand_linearization,support_moment_linearization
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='':raise ValueError('CPU-only device required')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(180,180))
    started=time.monotonic();p=protocol
    if p['physics_steps_allowed']!=0 or p['actor_or_WM_forwards_allowed']!=0:raise ValueError('Wrong probe authority')
    for name,digest in p['source_inputs'].items():
        if sha(name)!=digest:raise ValueError('Frozen input changed: '+name)
    model=mujoco.MjModel.from_binary_path(p['model_path']);data=mujoco.MjData(model)
    robot=model.body('base_link').id;hand=model.body('end_effector').id
    joint_names=[f'{leg}_{part}_joint' for leg in ('FR','FL','RR','RL') for part in ('hip','thigh','calf')]
    actual_names=[model.joint(j).name for j in range(model.njnt)]
    if not all(name in actual_names for name in joint_names):
        # Exact native JOINTS is also a source literal; it is not a guessed order.
        tree=ast.parse(Path(p['native_model_source']).read_text());joint_names=None
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(n,ast.Name) and n.id=='JOINTS' for n in node.targets):
                joint_names=ast.literal_eval(node.value);break
        if joint_names is None:raise ValueError('Native joint-order literal required')
    if len(joint_names)==12:joint_names+=['joint'+str(i) for i in range(1,7)]
    reference=np.asarray(reference_from_source(p['native_model_source']),float)
    if len(joint_names)!=18 or reference.shape!=(18,):raise ValueError('Native reference count mismatch')
    qids=np.array([int(model.joint(n).qposadr[0]) for n in joint_names]);dids=np.array([int(model.joint(n).dofadr[0]) for n in joint_names])
    armq=qids[-6:];armd=dids[-6:]
    bounds=model.jnt_range[[model.joint(n).id for n in joint_names[-6:]]]
    approach=json.loads(Path(p['native_approach']).read_text());q0=np.asarray(approach['waypoints'][0],float);q1=np.asarray(approach['waypoints'][-1],float)
    base0=model.qpos0.copy();base0[:3]=p['nominal_base_xyz'];base0[3:7]=[1.,0.,0.,0.];base0[qids]=reference
    feet=np.array([model.body(leg+'_foot').id for leg in ('FR','FL','RR','RL')])
    # Body map is only a static scene binding for this engineering model probe.
    bindings=json.loads(Path(p['body_bindings']).read_text());entry=bindings[p['object_id']]
    obj=model.body(entry['body']).id
    counter=0
    def fk(qpos):
        nonlocal counter
        counter+=1
        if counter>p['max_FK_calls']:raise RuntimeError('FK budget exceeded')
        data.qpos[:]=qpos
        mujoco.mj_kinematics(model,data);mujoco.mj_comPos(model,data)
    def matrices():
        J=np.zeros((3,model.nv));Jr=np.zeros_like(J);Jc=np.zeros_like(J)
        mujoco.mj_jacBody(model,data,J,Jr,hand);mujoco.mj_jacSubtreeCom(model,data,Jc,robot)
        return J[:,armd].copy(),Jc[:,armd].copy()
    poses=[('native_stow_waypoint',q0),('native_waypoint_midpoint',.5*(q0+q1)),('native_approach_last',q1)]
    rows=[];lp_count=0
    for name,q in poses:
        if np.any(q<bounds[:,0]) or np.any(q>bounds[:,1]):raise ValueError('Native nominal q outside compiled arm domain')
        state=base0.copy();state[armq]=q;fk(state)
        ph=data.xpos[hand].copy();com=data.subtree_com[robot].copy();rb=data.xmat[robot].reshape(3,3).copy();ro=data.xmat[obj].reshape(3,3).copy()
        local=rb.T@(ph-data.xpos[robot]);po=ro.T@(ph-data.xpos[obj]);J,Jc=matrices();foot=data.xpos[feet].copy()
        maps=relative_hand_linearization(ro,rb,local,rb.T@J,po)
        eps=p['finite_difference_step_rad'];Jh_fd=np.zeros_like(J);Jc_fd=np.zeros_like(Jc)
        for k in range(6):
            plus=state.copy();minus=state.copy();plus[armq[k]]+=eps;minus[armq[k]]-=eps
            fk(plus);hp=data.xpos[hand].copy();cp=data.subtree_com[robot].copy()
            fk(minus);hm=data.xpos[hand].copy();cm=data.subtree_com[robot].copy()
            Jh_fd[:,k]=(hp-hm)/(2*eps);Jc_fd[:,k]=(cp-cm)/(2*eps)
        fk(state)
        mass=float(model.body_subtreemass[robot]);g=float(-model.opt.gravity[2])
        identity=np.tile(np.eye(3),(1,4));moment=np.column_stack([np.array([[0.,-v[2],v[1]],[v[2],0.,-v[0]],[-v[1],v[0],0.]]) for v in foot-com])
        # Static gravity-only force witness under assumed anchors/friction.
        # No active PUSH wrench or real four-foot support is claimed.
        E=np.vstack((identity,moment));rhs=np.r_[0.,0.,mass*g,0.,0.,0.]
        fric=[];fricrhs=[];mu=p['assumed_static_friction']
        for i in range(4):
            for axis in (0,1):
                for sign in (-1.,1.):
                    row=np.zeros(12);row[3*i+axis]=sign;row[3*i+2]=-mu/np.sqrt(2.)
                    fric.append(row);fricrhs.append(0.)
        forces=linprog(np.zeros(12),A_ub=np.array(fric),b_ub=np.array(fricrhs),A_eq=E,b_eq=rhs,
                       bounds=[(None,None) if i%3!=2 else (p['minimum_nominal_normal_N'],None) for i in range(12)],method='highs');lp_count+=1
        f=forces.x.reshape(4,3) if forces.success else None
        supportmap=support_moment_linearization(foot,com,ph,f,[0.,0.,0.]) if f is not None else None
        row=dict(pose_id=name,q_rad=q,hand_position_world_m=ph,COM_world_m=com,foot_world_m=foot,
                 hand_joint_J_world_m_per_rad=J,COM_joint_J_world_m_per_rad=Jc,
                 relative_hand_repair_matrix=maps['repair_matrix'],object_error_matrix=maps['object_error_matrix'],
                 hand_J_max_abs_finite_difference_error=float(np.max(np.abs(J-Jh_fd))),
                 COM_J_max_abs_finite_difference_error=float(np.max(np.abs(Jc-Jc_fd))),
                 nominal_static_force_LP_status=int(forces.status),
                 nominal_force_witness_N=f,
                 nominal_force_moment_residual=None if f is None else E@f.ravel()-rhs,
                 nominal_support_moment_matrices=supportmap,
                 actual_ground_contact_verified=False,pose_was_actually_executed=False)
        rows.append(row)
    for source,digest in p['source_inputs'].items():
        if sha(source)!=digest:raise ValueError('Input modified during experiment: '+source)
    if lp_count>p['max_LP_solves']:raise ValueError('LP budget exceeded')
    return dict(schema='phe-a03-source-model-experiment-v1',status='COMPLETED_MODEL_ONLY',
                source_role='known development scene/model parameters, not TRAIN or independent TEST',
                actual_runtime_version=mujoco.__version__,model_sha256=sha(p['model_path']),
                scenario_object_id=p['object_id'],scenario_body_id=int(obj),
                model_read_count=1,private_MjData_created=1,FK_calls=counter,LP_solves=lp_count,
                rows=rows,max_hand_J_error=max(r['hand_J_max_abs_finite_difference_error'] for r in rows),
                max_COM_J_error=max(r['COM_J_max_abs_finite_difference_error'] for r in rows),
                physics_steps=0,SDK_or_Renderer_starts=0,WM_or_actor_forwards=0,
                nominal_zero_error_algebra_is_not_robust_certificate=True,
                future_PHE_cost='UNKNOWN_no_actual_operation_terminal_prediction_or_same_plan_handover_producer',
                actual_PHE_policy_or_task_benefit_verified=False,
                wall_s=time.monotonic()-started)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);args=ap.parse_args();root=args.root.resolve()
    p=json.loads((root/'protocol.json').read_text());assert str(root)==p['own_root']
    if (root/'report.json').exists():raise ValueError('Never overwrite completed experiment')
    with (root/'CPU-attempt.claim').open('x') as f:f.write('one CPU model experiment; no retries or physical authority\n')
    started=time.monotonic()
    try:
        result=run(root,p);save(root/'report.json',result)
        print(json.dumps({k:result[k] for k in ('status','FK_calls','LP_solves','max_hand_J_error','max_COM_J_error','wall_s')},indent=2))
    except Exception as exc:
        save(root/'report.json',dict(status='FAILED_NO_RETRY',error=repr(exc),traceback=traceback.format_exc(),wall_s=time.monotonic()-started,physics_steps=0))
        raise


if __name__=='__main__':main()
