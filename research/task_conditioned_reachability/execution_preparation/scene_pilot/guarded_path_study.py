"""One private-model experiment: native path guard + source-timed repair modes.

Reference paths are NEW RESEARCH candidates, not online-authorized controls.
Nominal base face pose is a declared hypothesis, never actual PUSH termination.
No actors, controllers, renderer, mj_step or live task state are constructed.
"""
import argparse,ast,json,math,time
from pathlib import Path
from types import SimpleNamespace
from model_probe import reference_from_source,sha,save
from analyze_native_finish import finish_constants,segment_times


def main():
    import numpy as np,mujoco
    from scipy.optimize import linprog
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args();r=a.root.resolve();p=json.loads((r/'protocol.json').read_text());assert str(r)==p['own_root']
    with (r/'CPU-attempt.claim').open('x') as f:f.write('one native-guard model experiment, not physical task\n')
    start=time.monotonic()
    for name,h in p['inputs'].items():
        if sha(name)!=h:raise ValueError('Frozen input drift '+name)
    m=mujoco.MjModel.from_binary_path(p['model_path']);d=mujoco.MjData(m);base=m.body('base_link').id
    names=[f'{leg}_{joint}_joint' for leg in ('FR','FL','RR','RL') for joint in ('hip','thigh','calf')]+[f'joint{i}' for i in range(1,7)]
    qids=np.array([int(m.joint(n).qposadr[0]) for n in names]);jids=np.array([m.joint(n).id for n in names])
    scene=json.loads(Path(p['scene_path']).read_text());obj=next(o for o in scene['objects'] if o['id']==p['object_id']);proto=scene['box_prototypes']['prototypes'][obj['prototype']]
    binding=json.loads(Path(p['bindings_path']).read_text())[p['object_id']];bid=m.body(binding['body']).id
    reference=np.asarray(reference_from_source(p['model_source']));d.qpos[:]=m.qpos0;d.qpos[qids]=reference
    base_xyz=np.array([obj['center_xy_m'][0]-proto['size_m'][0]/2-p['nominal_face_gap_m'],obj['center_xy_m'][1],p['nominal_base_height_m']])
    d.qpos[:3]=base_xyz;d.qpos[3:7]=[1.,0.,0.,0.]
    original=Path(p['finish_source']).read_text();cfg=finish_constants(original)
    tree=ast.parse(original);node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='CollisionGuard')
    counts=dict(FK=0,geometry_distance=0,static_force_LP=0)
    class MJ:
        MjData=mujoco.MjData
        @staticmethod
        def mj_kinematics(model,data):
            counts['FK']+=1
            if counts['FK']>p['max_FK_calls']:raise RuntimeError('FK budget exceeded')
            mujoco.mj_kinematics(model,data);mujoco.mj_comPos(model,data)
        @staticmethod
        def mj_geomDistance(*args):
            counts['geometry_distance']+=1
            if counts['geometry_distance']>p['max_geometry_distance_calls']:raise RuntimeError('geometry budget exceeded')
            return mujoco.mj_geomDistance(*args)
    ns=dict(np=np,mujoco=MJ)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(p['finish_source']),'exec'),ns)
    feet=np.array([m.body(leg+'_foot').id for leg in ('FR','FL','RR','RL')]);mass=float(m.body_subtreemass[base]);g=-m.opt.gravity[2]
    friction=[]
    for i in range(4):
        for axis in (0,1):
            for sign in (-1.,1.):
                row=np.zeros(12);row[3*i+axis]=sign;row[3*i+2]=-p['assumed_static_friction']/np.sqrt(2.);friction.append(row)
    class Guard(ns['CollisionGuard']):
        def check(self,*args,**kwargs):
            reason=super().check(*args,**kwargs)
            if reason:return reason
            counts['static_force_LP']+=1
            if counts['static_force_LP']>p['max_static_LP_solves']:raise RuntimeError('static LP budget exceeded')
            c=self.data.subtree_com[base];foot=self.data.xpos[feet]
            def skew(v):
                x,y,z=v;return np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])
            E=np.vstack((np.tile(np.eye(3),(1,4)),np.column_stack([skew(x-c) for x in foot])))
            sol=linprog(np.zeros(12),A_ub=friction,b_ub=np.zeros(16),A_eq=E,b_eq=[0.,0.,mass*g,0.,0.,0.],
                        bounds=[(None,None) if i%3!=2 else (p['minimum_normal_N'],None) for i in range(12)],method='highs')
            return '' if sol.success else 'nominal_static_support_no_witness'
    sim=SimpleNamespace(model=m,data=d,qids=qids,jids=jids,box_id=bid,base_id=base)
    guard=Guard(sim,SimpleNamespace(surface_clearance=cfg.get('surface_clearance',.035),collision_margin=.002))
    # Thresholds are additionally pinned from exact native dataclass source.
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FinishConfig')
    native_limits={n.target.id:ast.literal_eval(n.value) for n in cls.body if isinstance(n,ast.AnnAssign) and n.target.id in ('surface_clearance','collision_margin')}
    assert native_limits==dict(surface_clearance=.035,collision_margin=.002)
    path=json.loads(Path(p['approach_source']).read_text())['waypoints'];q0=np.asarray(path[0]);q1=np.asarray(path[-1]);zero=np.array(cfg['arm_pose'])
    rows=[]
    for pose,q in [('native_stow_waypoint',q0),('native_waypoint_midpoint',.5*(q0+q1)),('native_approach_last',q1)]:
        d.qpos[qids[-6:]]=q;MJ.mj_kinematics(m,d)
        modes=[('original_full_reverse',[q1,q0,zero]),('research_reverse_suffix',[q0,zero]),('research_direct_stow',[zero])]
        pose_rows=[]
        for mode,targets in modes:
            before=dict(counts);begin=q.copy();reason=''
            for target in targets:
                reason=guard.segment(begin,np.asarray(target))
                if reason:break
                begin=np.asarray(target)
            durations=segment_times(q,[list(x) for x in targets],cfg)
            pose_rows.append(dict(mode=mode,nominal_segment_s=durations,nominal_reference_s=sum(durations),
                                  private_native_geometry_and_static_support_pass=not bool(reason),
                                  reason=reason or None,counts={k:counts[k]-before[k] for k in counts},
                                  online_mode_registered=False,
                                  continuous_path_tracking_or_actual_ground_contact_proven=False))
        eligible=[x for x in pose_rows if x['private_native_geometry_and_static_support_pass']]
        best=min(eligible,key=lambda x:(x['nominal_reference_s'],x['mode'])) if eligible else None
        rows.append(dict(nominal_pose=pose,q_rad=q,candidates=pose_rows,model_only_selected_mode=None if best is None else best['mode'],
                         model_only_selected_reference_s=None if best is None else best['nominal_reference_s']))
    for name,h in p['inputs'].items():
        if sha(name)!=h:raise ValueError('Input changed during experiment')
    result=dict(schema='phe-a03-native-guarded-modes-CPU-v1',status='COMPLETED_MODEL_ONLY',
                role='known-dev hypothetical near-face nominal posture; no actual PUSH terminal or task trials',
                nominal_base_xyz=base_xyz,object_id=p['object_id'],geometry_pairs=len(guard.pairs),
                model_only_new_reference_library_NOT_online_registered=True,
                native_guard_thresholds=native_limits,counts=counts,rows=rows,
                physical_steps=0,actor_or_WM_forwards=0,renderer_starts=0,
                goal_success_or_dynamic_handover_gain_proven=False,
                future_main_operation_cost='UNKNOWN',wall_s=time.monotonic()-start)
    save(r/'report.json',result)
    print(json.dumps(dict(status=result['status'],counts=counts,wall_s=result['wall_s'],
                         rows=[dict(pose=x['nominal_pose'],mode=x['model_only_selected_mode'],reference_s=x['model_only_selected_reference_s'],
                                    reasons=[a['reason'] for a in x['candidates']]) for x in rows]),indent=2))


if __name__=='__main__':main()
