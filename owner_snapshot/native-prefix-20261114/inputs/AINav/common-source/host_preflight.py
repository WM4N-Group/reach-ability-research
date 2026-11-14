#!/usr/bin/env python3
"""Finite 5090 deployment smoke: pinned imports, original actors and EGL.

Synthetic actor inputs + independent display-only MjData. No task Runtime,
no task/world restoration, no motor commands or physics integration. Does NOT
certify complete navigation, skill transitions or paper effectiveness.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('source','bundle','scene-root','root','profile'):ap.add_argument('--'+k,required=True)
    a=ap.parse_args();source,bundle,case,root=(Path(v).resolve() for v in (a.source,a.bundle,a.scene_root,a.root))
    if root.exists():raise FileExistsError('Fresh deployment-smoke root required')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));root.mkdir(parents=True,exist_ok=False);sys.path.insert(0,str(source))
    from ainav.deployment import profile
    from ainav.native.resources import ResourceLease
    host=profile(a.profile)
    os.environ.update(MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID=str(host.egl_device_id),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2')
    report=dict(schema='ainav-pinned-deployment-smoke-v1',started_at=datetime.now().astimezone().isoformat(),host=host.report(),pid=os.getpid(),uid=os.getuid(),
        frozen_source_manifest_sha256=sha(source/'ainav-source.json'),main_task_Runtime_instances=0,task_motor_steps=0,physics_steps=0,
        actor_forwards=0,actor_input_scope='synthetic zeros for CUDA/serialization compatibility only',display_MjData_instances=0,actual_task_success=False,
        max_wall_s=150,resource_lease_scope='AINav-only mutual exclusion; other users do not share this lock, not exclusive GPU reservation',
        other_user_containers_or_processes_stopped=False,weights_or_task_or_safety_modified=False,automatic_retry=False)
    start=time.monotonic()
    def timeout(*_):raise TimeoutError('Bounded deployment smoke wall timeout')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(150)
    renderer=None
    try:
        with ResourceLease([host.lock_path]) as lease:
            save(root/'resource-admission.json',lease.evidence)
            from mujoco_zyh.source_bundle import verify_bundle
            import importlib.metadata as metadata
            expected={'torch':'2.7.0+cu128','numpy':'1.26.4','scipy':'1.13.1','osqp':'1.1.3','mujoco':'3.3.2'}
            versions={k:metadata.version(k) for k in expected};report['versions']=versions
            if versions!=expected:raise ValueError('Pinned native dependency versions differ')
            report['Python_version']=sys.version;report['asset_verification']=verify_bundle(bundle)
            model_file=case/'scene.mjb';scene_report=json.loads((case/'report.json').read_text())
            if sha(model_file)!=scene_report['scene_model_sha256']:raise ValueError('Original static five-box MJB differs')
            report['static_scene_sha256']=sha(model_file)
            import numpy as np
            import torch
            torch.set_num_threads(2)
            if not torch.cuda.is_available():raise RuntimeError('Declared host CUDA unavailable; no CPU fallback')
            index=int(host.actor_device.split(':')[1]);torch.cuda.set_per_process_memory_fraction(.06,index)
            free,total=torch.cuda.mem_get_info(index);report['GPU_available_after_context_init_MiB']=free/2**20
            report['GPU_name']=torch.cuda.get_device_name(index);report['CUDA_build']=torch.version.cuda
            if free<2*2**30:raise RuntimeError('Insufficient current shared-GPU headroom; stop without interfering with other task')
            report['GPU_compute_capability']=list(torch.cuda.get_device_capability(index))
            synthetic=[('nav/policy/actor.pt',210,18),('climb/policy/actor.pt',923,18),('push/policy/leg_actor.pt',226,12),('push/policy/arm_actor.pt',226,19)]
            results=[]
            for name,dim,outdim in synthetic:
                path=bundle/name;cpu=torch.jit.load(str(path),map_location='cpu').eval();gpu=torch.jit.load(str(path),map_location=host.actor_device).eval()
                with torch.inference_mode():
                    original=cpu(torch.zeros((1,dim)));actual=gpu(torch.zeros((1,dim),device=host.actor_device));torch.cuda.synchronize(index)
                report['actor_forwards']+=2
                if not isinstance(actual,torch.Tensor) or list(actual.shape)!=[1,outdim] or not torch.isfinite(actual).all():raise ValueError('Original actor shape/finite CUDA check failed:'+name)
                difference=float(torch.max(abs(actual.cpu()-original)))
                results.append(dict(actor=name,actor_sha256=sha(path),input_dimensions=dim,output_dimensions=outdim,cpu_cuda_max_absolute_difference=difference,
                    finite=True,original_CPU_and_CUDA_actor_weights_same=True,physical_success_not_inferred=True))
                del cpu,gpu,original,actual
            report['original_actor_checks']=results;report['GPU_peak_Torch_allocated_MiB']=torch.cuda.max_memory_allocated(index)/2**20
            import mujoco
            from PIL import Image
            model=mujoco.MjModel.from_binary_path(str(model_file));data=mujoco.MjData(model);report['display_MjData_instances']=1
            mujoco.mj_forward(model,data)  # Independent display data only, no mj_step.
            camera=mujoco.MjvCamera();camera.lookat[:]=[7.,-.9,.3];camera.distance=15.;camera.azimuth=100.;camera.elevation=-35.
            renderer=mujoco.Renderer(model,height=128,width=192);renderer.update_scene(data,camera=camera);rgb=renderer.render().copy()
            from OpenGL.GL import glGetString,GL_VENDOR,GL_RENDERER,GL_VERSION
            strings={name:(glGetString(key) or b'').decode(errors='replace') for name,key in (('vendor',GL_VENDOR),('renderer',GL_RENDERER),('version',GL_VERSION))}
            report['actual_OpenGL_implementation']=strings
            if 'NVIDIA' not in strings['vendor']:raise RuntimeError('Declared GPU EGL renderer unavailable; no silent software-render fallback')
            if rgb.shape!=(128,192,3) or len(np.unique(rgb.reshape(-1,3),axis=0))<8:raise ValueError('EGL image is blank/invalid')
            image=root/'display-only-EGL-smoke.png';Image.fromarray(rgb).save(image)
            report['EGL_render']=dict(width=192,height=128,sha256=sha(image),path=str(image),display_only_not_task_observation=True,unique_RGB_colors=len(np.unique(rgb.reshape(-1,3),axis=0)))
            # Connectivity test is explicitly unauthenticated: no inference cost/key.
            import urllib.request,urllib.error
            try:
                with urllib.request.urlopen('https://api.deepseek.com/models',timeout=12) as response:status=response.status
            except urllib.error.HTTPError as e:status=e.code
            report['DeepSeek_connectivity']=dict(HTTP_status=status,HTTPS_reachable=True,API_key_used=False,inference_calls=0)
            report.update(outcome='deployment_smoke_passed_NOT_task_success',deployment_smoke_passed=True)
    except Exception as e:report.update(outcome='failed_no_retry',error=type(e).__name__+': '+str(e),deployment_smoke_passed=False)
    finally:
        if renderer is not None:
            try:renderer.close()
            except Exception as e:report['renderer_close_error']=type(e).__name__
        signal.alarm(0);report['wall_seconds']=time.monotonic()-start;save(root/'report.json',report)
    print(json.dumps(report));return 0 if report.get('deployment_smoke_passed') else 2


if __name__=='__main__':raise SystemExit(main())
