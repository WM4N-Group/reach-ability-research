"""Causal public-only fixed-PUSH features; private truth used ONLY for labels/masks."""
import json,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from .streams import sha,write_json
from .push_forecast_protocol import load_plan,plan_sha

HISTORY=8;HORIZONS=(.4,.8);NATIVE_STEPS=140
FEATURE_VERSION='public-rgbd-proprio-full-past-command-projection-v1'
_PROJECTION=None

def projection():
    global _PROJECTION
    if _PROJECTION is None:
        _PROJECTION=np.random.default_rng(12071).choice(np.array([-1.,1.],dtype=np.float32),(NATIVE_STEPS*180,48))/np.sqrt(NATIVE_STEPS*180)
    return _PROJECTION


def appearance(rgb,depth,K,mount):
    """Visible warm-surface proxy in this SINGLE same-appearance-object protocol.
    Not a general box detector/ID/mass estimator; fragments have no semantic IDs.
    All baselines receive the same descriptor and validity mask.
    """
    mask=(rgb[...,0]>1.3*rgb[...,1])&(rgb[...,1]>1.3*rgb[...,2])&(rgb[...,0]>40)
    valid=mask&np.isfinite(depth)&(depth>.05)&(depth<=15)
    if valid.sum()<32:return np.zeros(3),False
    v,u=np.nonzero(valid);z=depth[v,u]
    optical=np.stack(((u-K[0,2])*z/K[0,0],(v-K[1,2])*z/K[1,1],z),axis=1)
    return np.median(optical@mount[:3,:3].T+mount[:3,3],axis=0),True


def public_features(rgb,depth,proprio,actions,times,K,mount,past_commands,elapsed_push_s):
    # STRICT schema accepts no future frame/motor/state/private case metadata.
    if rgb.shape!=(8,128,192,3) or depth.shape!=(8,128,192) or proprio.shape!=(8,45) or actions.shape!=(8,18):
        raise ValueError('Exactly8 real calibrated public history frames required')
    if past_commands.shape!=(140,2,5,18) or not np.allclose(np.diff(times),.1,atol=1e-6):
        raise ValueError('Complete ordered140 native past steps and actual10Hz clock required')
    valid=np.isfinite(depth)&(depth>0)&(depth<=15)
    channels=np.concatenate((rgb.astype(np.float32)/255.,np.where(valid,depth,0)[...,None]/15.,valid[...,None]),axis=-1)
    pooled=channels.reshape(8,4,32,6,32,5).mean(axis=(2,4)).reshape(-1)
    points=[];visible=[]
    for i in range(8):
        p,ok=appearance(rgb[i],depth[i],K,mount);points.append(p);visible.append(ok)
    points=np.array(points);visible=np.array(visible);vel=[]
    for i in range(1,8):
        if visible[i] and visible[i-1]:
            # Body-frame visible-surface derivative plus public ego twist.
            vel.append((points[i]-points[i-1])/.1+proprio[i,42:45]+np.cross(proprio[i,39:42],points[i]))
    cv=np.median(vel[-4:],axis=0)[:2] if vel else np.zeros(2)
    kinematics=np.r_[points.reshape(-1),visible.astype(float),proprio.reshape(-1),actions.reshape(-1),elapsed_push_s,cv]
    scale=np.array([3.,3.,100.,10.,50.])[None,None,:,None]
    command_feature=(past_commands/scale).astype(np.float32).reshape(-1)@projection()
    full=np.r_[kinematics,pooled,command_feature]
    if not np.isfinite(full).all():raise ValueError('Nonfinite public features')
    return full.astype(np.float32),kinematics.astype(np.float32),np.tile(cv,2)*np.repeat(HORIZONS,2),bool(visible[-1])


def read_episode(root):
    root=Path(root);meta=json.loads((root/'episode/episode.json').read_text());idx=json.loads((root/'episode/index.json').read_text());report=json.loads((root/'report.json').read_text())
    visuals={};commands={}
    for row in idx['visual']:
        p=root/'episode'/row['path']
        if sha(p)!=row['sha256']:raise ValueError('Visual source changed')
        with np.load(p,allow_pickle=False) as z:
            for k in z.files:
                value=z[k]
                if k in ('camera_K','T_base_optical'):visuals[k]=value[0].copy()
                else:visuals.setdefault(k,[]).append(value[0].copy() if k!='control_ticks' else value.copy())
    for k,v in list(visuals.items()):
        if isinstance(v,list):visuals[k]=np.concatenate(v)
    for row in idx['commands']:
        p=root/'episode'/row['path']
        if sha(p)!=row['sha256']:raise ValueError('Motor source changed')
        with np.load(p,allow_pickle=False) as z:
            for k in z.files:commands.setdefault(k,[]).append(z[k].copy())
    commands={k:np.concatenate(v) for k,v in commands.items()}
    cat=[json.loads(x) for x in (root/'episode/private-catalog.jsonl').read_text().splitlines()]
    return meta,report,visuals,commands,cat


def samples(root):
    meta,report,v,c,cat=read_episode(root);censors=Counter();full=[];kin=[];labels=[];cv=[];qt=[];visibility=[]
    entries=[e['time'] for e in report['native_events'] if e['event']=='enter' and e.get('skill')=='push']
    if not entries:return dict(eligible=0,censor={'no_native_PUSH_entry':1}),None
    start=entries[0];stop=report['sim_seconds']
    for e in report['native_events']:
        if e['event'] in ('push_exit_retract','push_safety_failure'):stop=min(stop,e['time'])
    times=v['timestamps_s'];limits=np.array(report['joint_position_limits_rad']);q=c['q_before'];dq=c['dq_before']
    strict=(q>=limits[:,0]-1e-10).all(1)&(q<=limits[:,1]+1e-10).all(1)&(abs(dq)<=np.array([30.1,30.1,15.7]*4+[3.]*6)).all(1)
    bad_prefix=np.r_[0,np.cumsum(~strict)]
    for i in range(7,len(times),2):
        t=float(times[i])
        if t<start+.8:continue
        if t+.8>=stop-1e-7:censors['future_native_boundary_or_registered_censor']+=1;continue
        j=int(round(t*200));end=int(round((t+.8)*200));begin=int(round((t-.7)*200))
        if end>=len(q) or begin<0:censors['incomplete_actual_motor_history_or_future']+=1;continue
        if bad_prefix[end+1]-bad_prefix[j]>0:censors['strict_joint_range_or_speed_in_future_window']+=1;continue
        if abs(float(c['time_s'][j-1])-t)>1e-7:censors['motor_clock_mismatch']+=1;continue
        future_indices=[i+4,i+8]
        if any(k>=len(times) or abs(float(times[k])-t-h)>1e-6 for k,h in zip(future_indices,HORIZONS)):
            censors['missing_actual_future_frame']+=1;continue
        history=slice(i-7,i+1);past=np.stack((c['issued'][begin:j],c['delayed'][begin:j]),axis=1)
        f,k,baseline,vis=public_features(v['rgb'][history],v['depth_m'][history,...,0],v['proprio'][history],v['actions_previous'][history],times[history],v['camera_K'],v['T_base_optical'],past,t-start)
        # Private state is accessed ONLY AFTER public features are materialized.
        if cat[i]['objects'][0]['opaque_object_id']!='probe_object':raise ValueError('Wrong physical object label binding')
        R=np.array(cat[i]['R_world_from_body']);anchor=np.array(cat[i]['objects'][0]['position_world_m']);target=[]
        for idx in future_indices:target.extend(((np.array(cat[idx]['objects'][0]['position_world_m'])-anchor)@R)[:2])
        full.append(f);kin.append(k);labels.append(target);cv.append(baseline);qt.append(t);visibility.append(vis)
    audit=dict(eligible=len(labels),censor=dict(censors),source_id=meta['source_id'],role=meta['role'],
        training_allowed=meta['training_allowed'],native_PUSH_entry_s=start,native_PUSH_end_s=stop,
        strict_unsafe_physics_steps_total=int((~strict).sum()),strict_sample_window_unsafe_steps=0,
        source_sim_s=report['sim_seconds'],native_outcome=report['caller_outcome'],error=report['error'],
        visible_proxy_fraction=float(np.mean(visibility)) if visibility else 0.,
        label_fields=['box_dx_at0p4_query_body_m','box_dy_at0p4_query_body_m','box_dx_at0p8_query_body_m','box_dy_at0p8_query_body_m'])
    arrays=dict(full=np.array(full,dtype=np.float32),kin=np.array(kin,dtype=np.float32),y=np.array(labels,dtype=np.float32),cv=np.array(cv,dtype=np.float32),query_times=np.array(qt)) if labels else None
    return audit,arrays


def build_dataset(root,output):
    root=Path(root);output=Path(output);output.mkdir(exist_ok=False);rows=[]
    for case in load_plan()['cases']:
        ep=root/'episodes'/case['id'];audit,arrays=samples(ep);name=case['id']+'.npz'
        if arrays is not None:np.savez_compressed(output/name,**arrays)
        rows.append(dict(id=case['id'],split=case['split'],audit=audit,path=name if arrays is not None else None,
            sha256=sha(output/name) if arrays is not None else None,source_freeze_sha256=sha(ep/'freeze.json'),
            source_closure_sha256=sha(ep/'episode/closure.json')))
    counts={s:sum(r['audit']['eligible'] for r in rows if r['split']==s) for s in ('train','validation','test')}
    groups={s:sum(r['audit']['eligible']>0 for r in rows if r['split']==s) for s in counts};plan=load_plan()
    passed=all(counts[s]>=plan['minimum_eligible_queries'][s] and groups[s]>=plan['minimum_eligible_episodes'][s] for s in counts)
    result=dict(schema='narrow-push-dataset-v1',feature_version=FEATURE_VERSION,plan_sha256=plan_sha(),rows=rows,
        eligible_queries=counts,eligible_episodes=groups,coverage_pass=passed,
        no_future_command_or_private_input=True,full_past_command_steps_per_query=140,
        heldout_physics_conditions=True,strict_zero_violation_query_to_label_windows=True,
        entire_physics_episode_safe_certified=False,unexecuted_branches_labeled=False)
    write_json(output/'manifest.json',result);print(json.dumps(result));return result
