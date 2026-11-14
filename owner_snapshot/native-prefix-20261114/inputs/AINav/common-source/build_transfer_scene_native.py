#!/usr/bin/env python3
"""Construct/render a fresh transfer world on A800, with ZERO motor steps/API calls.

This is geometry/deployment preflight, never a navigation trial. Refuse to call
an incompatible legacy FullCourse host; retain its actual protocol rejection.
"""
import argparse
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys
import time


def file_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def robot_signature(m,return_components=False):
    rows={'bodies':[],'joints':[],'geoms':[],'actuators':[]}
    base=m.body('base_link').id;ids=set()
    for i in range(m.nbody):
        parent=i
        while parent and parent!=base:parent=int(m.body_parentid[parent])
        if parent==base:ids.add(i)
    def values(view,names):
        return {n:getattr(view,n).tolist() for n in names}
    for i in sorted(ids):
        b=m.body(i);rows['bodies'].append(dict(name=b.name,**values(b,('mass','inertia','ipos','iquat','pos','quat'))))
    for i in range(m.njnt):
        j=m.joint(i)
        if int(j.bodyid[0]) in ids:rows['joints'].append(dict(name=j.name,**values(j,('type','axis','pos','range','limited','stiffness'))))
    for i in range(m.ngeom):
        g=m.geom(i)
        if int(g.bodyid[0]) in ids:rows['geoms'].append(dict(name=g.name,**values(g,('type','size','pos','quat','friction','condim','contype','conaffinity','solref','solimp'))))
    for i in range(m.nu):
        a=m.actuator(i);rows['actuators'].append(dict(name=a.name,**values(a,('trnid','gear','gainprm','biasprm','ctrlrange','forcerange'))))
    rows['engine']=dict(timestep=m.opt.timestep,gravity=m.opt.gravity.tolist(),integrator=int(m.opt.integrator),solver=int(m.opt.solver),iterations=m.opt.iterations)
    if return_components:return rows
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def cache_native_elements(spec):
    # In the pinned MuJoCo build, named lookup after appending world geoms can
    # still refer to old compiled indices. Cache actual original handles first.
    result=dict(box_body=spec.body('push_box'),box_geom=spec.geom('push_box_geom'),
                robot_body=spec.body('base_link'),ground=spec.geom('ground'))
    expected=dict(box_body='push_box',box_geom='push_box_geom',robot_body='base_link',ground='ground')
    if any(result[k].name!=v for k,v in expected.items()):raise ValueError('Native spec lookup identity mismatch')
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('source','bundle','scene','root','gpu-lock'):ap.add_argument('--'+name,required=True)
    a=ap.parse_args();source,bundle,scene_path,root=[Path(x).resolve() for x in (a.source,a.bundle,a.scene,a.root)]
    if root.exists():raise FileExistsError('Fresh zero-step root required; no retry of consumed ID')
    root.mkdir(parents=True,exist_ok=False);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    os.environ.update(MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='1',PYTHONDONTWRITEBYTECODE='1')
    sys.path.insert(0,str(source))
    from ainav.native.resources import ResourceLease
    from ainav.transfer_scene import validate_scene,public_scene,object_geometry
    scene=json.loads(scene_path.read_text());validate_scene(scene);save(root/'scene.json',scene);save(root/'public-scene.json',public_scene(scene))
    start=time.monotonic();report=dict(schema='ainav-transfer-scene-zero-step-v1',started_at=datetime.now().astimezone().isoformat(),
        scene_sha256=file_sha(scene_path),source_manifest_sha256=file_sha(source/'ainav-source.json'),
        main_world_motor_steps=0,actor_forwards=0,API_calls=0,task_success=False,
        navigation_trial_started=False,physical_task_feasibility_verified=False,automatic_retry=False,reset_after_initial=False)
    try:
        with ResourceLease([a.gpu_lock]) as lease:
            save(root/'resource-admission.json',lease.evidence)
            save(root/'attempt.claim',dict(pid=os.getpid(),max_launches=1,purpose='zero-step geometry only'))
            import numpy as np
            import torch
            import mujoco
            from PIL import Image,ImageDraw
            from scipy.spatial.transform import Rotation
            from mujoco_zyh.source_bundle import verify_bundle
            from mujoco_zyh.scene import calibration,CAMERA_NAME
            from mujoco_zyh import integrated_course,stall_stow
            torch.set_num_threads(2)
            report['asset_verification_before']=verify_bundle(bundle)
            report['actor_sha256']=json.loads((bundle/'MANIFEST.json').read_text())['actor_sha256']
            # Use unchanged SDK model construction, but do not load/forward actors.
            sys.path.insert(0,str(bundle/'switch'))
            from plugins import Plugin
            native=Plugin('push',['bridge','model'])
            with native.active():sim=native['bridge'].PushBridge(seed=3701,delay_ms=20,push_distance=.6)
            if float(sim.data.time)!=0. or len(sim.queue):raise RuntimeError('Native constructor unexpectedly advanced physics/FIFO')
            original_model=sim.model;original_signature=robot_signature(original_model);spec=sim.spec
            elements=cache_native_elements(spec)
            elements['ground'].pos=[0.,0.,scene['physical_environment']['floor_top_z_m']]
            elements['ground'].size=[25.,12.,.1]
            for g in spec.geoms:g.group=2
            elements['ground'].group=1
            surface_names={}
            for s in scene['surfaces']:
                x0,x1,y0,y1=s['bounds_xy_m'];lo,hi=s['bottom_z_m'],s['top_z_m'];name='transfer_'+s['id'];surface_names[s['id']]=name
                color=([.22,.38,.55,1.] if hi==0 else [.3,.5,.6,1.] if hi<.4 else [.2,.35,.6,1.])
                spec.worldbody.add_geom(name=name,type=mujoco.mjtGeom.mjGEOM_BOX,
                    pos=[(x0+x1)/2,(y0+y1)/2,(lo+hi)/2],size=[(x1-x0)/2,(y1-y0)/2,(hi-lo)/2],
                    contype=2,conaffinity=3,friction=[scene['physical_environment']['static_friction'],0.,0.],group=1,rgba=color)
            objects={};by_geom={}
            for item in scene['objects']:
                p=scene['box_prototypes']['prototypes'][item['prototype']];g=object_geometry(scene,item)
                name='push_box' if item['prototype']=='p0' else 'transfer_box_'+item['id'];gn=name+'_geom'
                if name=='push_box':body=elements['box_body'];geom=elements['box_geom']
                else:
                    body=spec.worldbody.add_body(name=name);body.add_freejoint(name=name+'_free')
                    geom=body.add_geom(name=gn,type=mujoco.mjtGeom.mjGEOM_BOX)
                body.pos=g['initial_center_xyz_m']
                for attr,value in dict(size=np.asarray(p['size_m'])/2,mass=p['mass_kg'],friction=p['geom_friction'],rgba=p['rgba'],
                    condim=p['condim'],contype=p['contype'],conaffinity=p['conaffinity'],priority=p['priority'],solref=p['solref'],
                    solimp=p['solimp'],margin=p['margin'],gap=p['gap'],group=1).items():setattr(geom,attr,value)
                objects[item['id']]=dict(body=name,geom=gn,prototype=item['prototype'],declared=g);by_geom[gn]=p
            foot_ids={original_model.body(n+'_foot').id for n in ('FR','FL','RR','RL')}
            foot_geoms={original_model.geom(i).name for i in range(original_model.ngeom) if int(original_model.geom_bodyid[i]) in foot_ids}
            pairs={frozenset((p.geomname1,p.geomname2)):p for p in spec.pairs}
            for gn,p in by_geom.items():
                for other in list(spec.geoms):
                    if other.name==gn or not(other.contype or other.conaffinity):continue
                    key=frozenset((gn,other.name))
                    mu=p['foot_pair_friction'] if other.name in foot_geoms else max(p['bottom_pair_friction'],by_geom.get(other.name,{}).get('bottom_pair_friction',0.))
                    pair=pairs.get(key)
                    if pair is None:pair=spec.add_pair(geomname1=gn,geomname2=other.name,condim=3);pairs[key]=pair
                    pair.friction=[mu,mu,0.,0.,0.]
            K,mount=calibration(192,128);q=Rotation.from_matrix(mount[:3,:3]@np.diag([1.,-1.,-1.])).as_quat()
            elements['robot_body'].add_camera(name=CAMERA_NAME,pos=mount[:3,3],quat=q[[3,0,1,2]],fovy=math.degrees(2*math.atan(128/(2*K[1,1]))))
            model=spec.compile();data=mujoco.MjData(model)
            report['compiled_dof_check']=dict(original_nv=original_model.nv,expected_nv=original_model.nv+6*(len(objects)-1),actual_nv=model.nv)
            if model.nv!=original_model.nv+6*(len(objects)-1) or robot_signature(model)!=original_signature:
                before=robot_signature(original_model,True);after=robot_signature(model,True);differences=[]
                for section in before:
                    if before[section]==after[section]:continue
                    if isinstance(before[section],list):
                        for old,new in zip(before[section],after[section]):
                            if old!=new:differences.append(dict(section=section,name=old.get('name'),changes={k:[v,new[k]] for k,v in old.items() if v!=new[k]}))
                    else:differences.append(dict(section=section,before=before[section],after=after[section]))
                save(root/'robot-identity-differences.json',differences)
                raise RuntimeError('Original robot/actuators/engine modified')
            if any(model.joint(n).id!=original_model.joint(n).id for n in native['model'].JOINTS):raise RuntimeError('Original robot joint IDs changed')
            # Registered before-first-step initialization only. No prior task state is loaded.
            qids=np.asarray([model.joint(n).qposadr[0] for n in native['model'].JOINTS]);data.qpos[qids]=stall_stow.initial_posture(native['model'].REFERENCE)
            data.qpos[:3]=[*scene['initial_robot']['xy_m'],.33];yaw=scene['initial_robot']['yaw_rad'];data.qpos[3:7]=[math.cos(yaw/2),0.,0.,math.sin(yaw/2)]
            mujoco.mj_forward(model,data);feet=np.asarray([model.body(n+'_foot').id for n in ('FR','FL','RR','RL')])
            support=next(s for s in scene['surfaces'] if s['id']==scene['initial_robot']['support'])
            data.qpos[2]+=support['top_z_m']+.022-float(data.xpos[feet,2].min());mujoco.mj_forward(model,data)
            checks=[]
            for ident,row in objects.items():
                p=scene['box_prototypes']['prototypes'][row['prototype']];g=model.geom(row['geom']);b=model.body(row['body'])
                good=(np.allclose(2*g.size,p['size_m'],rtol=0,atol=1e-12) and abs(float(b.mass[0])-p['mass_kg'])<1e-12
                    and np.allclose(b.inertia,p['inertia_kg_m2'],rtol=0,atol=1e-12) and np.array_equal(g.friction,p['geom_friction'])
                    and np.allclose(g.solref,p['solref'],rtol=0,atol=1e-12) and np.allclose(g.solimp,p['solimp'],rtol=0,atol=1e-12)
                    and np.allclose(data.xpos[b.id],row['declared']['initial_center_xyz_m'],rtol=0,atol=1e-12))
                required={row['geom'],surface_names[next(o['support'] for o in scene['objects'] if o['id']==ident)]}
                actual_mu=[model.pair_friction[i].tolist() for i in range(model.npair) if {model.geom(int(model.pair_geom1[i])).name,model.geom(int(model.pair_geom2[i])).name}==required]
                good=good and len(actual_mu)==1 and actual_mu[0]==[p['bottom_pair_friction'],p['bottom_pair_friction'],0.,0.,0.]
                if not good:raise RuntimeError('Compiled object differs from frozen original prototype: '+ident)
                checks.append(dict(id=ident,prototype=row['prototype'],mass_kg=float(b.mass[0]),size_m=(2*g.size).tolist(),support_pair_friction=actual_mu[0],verified=True))
            # Test the existing loader, without rewriting its predicates or ever issuing a motor command.
            try:integrated_course.validate_protocol(scene)
            except ValueError as error:
                report['unchanged_baseline_preflight']=dict(accepted=False,error=str(error),classification='scene_interface_incompatible_not_VLM_failure',
                    protocol_validator_sha256=file_sha(Path(integrated_course.__file__)),motor_commands_issued=0,
                    extra_blockers=['FullCourse registers only two movable object bodies','CourseBindingResolver pins three body identities',
                        'Terrain assigns fixed object support layers B=0.0/C=0.4','Old host forces an initial failed-A prefix','Original endpoint describes far bank, not new upper goal'])
            else:raise RuntimeError('Unexpected legacy acceptance; review before any motor trial')
            model_path=root/'scene.mjb';mujoco.mj_saveModel(model,str(model_path))
            np.savez_compressed(root/'initial-state.npz',qpos=data.qpos,qvel=data.qvel,time_s=data.time)
            save(root/'private-object-bindings.json',objects)
            save(root/'camera-calibration.json',dict(K=K.tolist(),T_base_optical=mount.tolist(),width=192,height=128))
            renderer=mujoco.Renderer(model,height=512,width=960)
            images=[]
            try:
                for name,lookat,distance,azimuth,elevation in [('overview',[8.,-1.1,0.],22.,100.,-45.),('bridge-side',[6.2,-1.1,0.],10.,110.,-42.),('upper-side',[12.8,-1.1,.3],10.,110.,-42.)]:
                    camera=mujoco.MjvCamera();camera.lookat[:]=lookat;camera.distance=distance;camera.azimuth=azimuth;camera.elevation=elevation
                    renderer.update_scene(data,camera=camera);image=Image.fromarray(renderer.render().copy());draw=ImageDraw.Draw(image)
                    draw.rectangle((0,0,960,30),fill=(18,25,34));draw.text((12,9),'TRANSFER SCENE | 5 unchanged-type boxes | ZERO motor steps / NOT task success',fill=(240,244,249))
                    path=root/(name+'.png');image.save(path);images.append(dict(path=str(path),sha256=file_sha(path)))
            finally:renderer.close()
            camera_renderer=mujoco.Renderer(model,height=128,width=192)
            try:
                camera_renderer.update_scene(data,camera=CAMERA_NAME);rgb=camera_renderer.render().copy();Image.fromarray(rgb).save(root/'initial-onboard-rgb.png')
                camera_renderer.enable_depth_rendering();camera_renderer.update_scene(data,camera=CAMERA_NAME);depth=camera_renderer.render().copy();np.save(root/'initial-depth-m.npy',depth,allow_pickle=False)
                if rgb.std()<1. or not np.isfinite(depth).all():raise RuntimeError('Real RGBD rendering failed')
            finally:camera_renderer.close()
            if data.time!=0. or sim.data.time!=0. or len(sim.queue):raise RuntimeError('Zero-step world unexpectedly advanced')
            report.update(outcome='new_scene_constructed_and_rendered_baseline_incompatible',new_scene_created=True,actual_box_count=len(objects),actual_nv=model.nv,
                robot_signature_sha256=original_signature,robot_unchanged=True,box_checks=checks,geometry_preflight=validate_scene(scene),
                rendered_images=images,main_world_time_s=float(data.time),real_RGBD_rendered=True,
                initial_stance_dynamics_verified=False,auxiliary_calibration_steps=0,scene_model_sha256=file_sha(model_path),
                source_bundle_verification_after=verify_bundle(bundle))
    except Exception as error:report.update(outcome='zero_step_build_failed',error=type(error).__name__+': '+str(error))
    report['wall_seconds']=time.monotonic()-start;save(root/'report.json',report);print(json.dumps(report,ensure_ascii=False))
    return 0 if report.get('new_scene_created') else 2

if __name__=='__main__':raise SystemExit(main())
