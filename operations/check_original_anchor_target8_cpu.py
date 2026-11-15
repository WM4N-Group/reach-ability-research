#!/usr/bin/env python3
"""One explicit synthetic RGBD smoke of ORIGINAL plane functions; no model/task.

Requires existing NumPy on compute host; no dependency installation. Arrays stay
in RAM and do not become live WM inputs, samples, fit data or native permissions.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.task_conditioned_reachability.execution_preparation.v4_anchor_target8 import (
    AnchorTarget8Provider,load_original_geometry,PINS)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args=parser.parse_args(); started=time.monotonic()
    import numpy as np
    root=Path(__file__).resolve().parents[1]/'inference_source/original_behavior7a6_geometry'
    ambient=sys.modules.get('visual_box_proposals')
    api=load_original_geometry(root)
    assert load_original_geometry(root) is api  # Separate A/B consumers reuse code, not source history.
    assert sys.modules.get('visual_box_proposals') is ambient
    rgb=np.zeros((64,96,3),dtype=np.uint8);depth=np.zeros((64,96),dtype=np.float32)
    rgb[20:44,32:64]=[0,200,0];depth[20:44,32:64]=2.
    K=np.array([[96.,0,48.],[0,96.,32.],[0,0,1.]])
    T=np.array([[0.,0.,1.,0.],[-1.,0.,0.,0.],[0.,-1.,0.,0.],[0.,0.,0.,1.]])
    anchor=dict(rgb=rgb,depth_m=depth,camera_K=K,T_base_optical=T,time_s=1.)
    obs=SimpleNamespace(time_s=1.015);options=(SimpleNamespace(sha256='a'*64),)
    def associate(observation,options,frame):
        proposals=api.propose_visual_candidates(frame['rgb'],frame['depth_m'],frame['camera_K'],frame['T_base_optical'])
        return dict(WM_anchor_RGB_bytes_sha256=proposals['RGB_sha256'],WM_anchor_time_s=frame['time_s'],
            WM_anchor_calibration_sha256=proposals['calibration_sha256'],
            frame_local_ref_by_option_sha256={'a'*64:dict(frame_local_ref='visual-proposal-0',declared_standoff_m=1.05)})
    producer=AnchorTarget8Provider(geometry_source_root=root,association_provider=associate,software_fixture=True)
    before=[hashlib.sha256(anchor[k].tobytes()).hexdigest() for k in ('rgb','depth_m','camera_K','T_base_optical')]
    result=producer(obs,options,anchor);target=result['target8_by_option_sha256']['a'*64]
    assert target is not None and np.allclose(target[:5],[1,0,0,2,2],atol=1e-6,rtol=0)and target[7]==1.
    assert result['source_role']=='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT'
    assert before==[hashlib.sha256(anchor[k].tobytes()).hexdigest()for k in ('rgb','depth_m','camera_K','T_base_optical')]
    unknown=AnchorTarget8Provider(geometry_source_root=root,software_fixture=True)(obs,options,anchor)
    assert unknown['target8_by_option_sha256']['a'*64]is None
    missing=dict(anchor,depth_m=np.zeros_like(depth))
    no_depth=producer(obs,options,missing);assert no_depth['target8_by_option_sha256']['a'*64]is None
    ambiguous_rgb=np.zeros_like(rgb);ambiguous_depth=np.zeros_like(depth)
    for x0,x1 in ((12,30),(60,78)):
        ambiguous_rgb[20:44,x0:x1]=[0,200,0];ambiguous_depth[20:44,x0:x1]=2.
    ambiguous=producer(obs,options,dict(anchor,rgb=ambiguous_rgb,depth_m=ambiguous_depth))
    assert ambiguous['target8_by_option_sha256']['a'*64]is None
    def old_anchor(observation,options,frame):
        answer=associate(observation,options,frame);answer['WM_anchor_RGB_bytes_sha256']='b'*64;return answer
    stale=AnchorTarget8Provider(geometry_source_root=root,association_provider=old_anchor,software_fixture=True)
    try:stale(obs,options,anchor)
    except ValueError:pass
    else:raise AssertionError('Wrong WM anchor not refused')
    forbidden=sorted(name for name in sys.modules if name.split('.')[0]in('torch','mujoco','onnxruntime'))
    assert not forbidden
    report=dict(at=dt.datetime.now().astimezone().isoformat(),
        role='EXPLICIT_SYNTHETIC_ORIGINAL_GEOMETRY_CPU_SMOKE_NOT_SENSOR_WM_FORWARD_OR_NATIVE_QUALIFICATION',
        reader_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_pins=dict(PINS),
        original_functions_executed=['propose_visual_candidates','describe_visible_goal','front_plane','geometry_vector'],
        anchor_resolution_px=[96,64],synthetic_valid_plane_target8=list(target),
        no_source_array_mutation=True,private_modules_do_not_replace_ambient_visual_module=True,
        immutable_geometry_functions_reused_for_second_producer=True,
        no_association_is_None=True,no_depth_is_None=True,ambiguous_same_color_is_None=True,stale_anchor_refused=True,
        original_refusal_reasons=dict(no_depth=no_depth['target8_evidence_by_option_sha256']['a'*64],
            ambiguous=ambiguous['target8_evidence_by_option_sha256']['a'*64]),
        target_mask0_abstention_policy_unchanged=True,actual_sensor_frames_used=0,
        real_checkpoint_restores=0,real_WM_forward_calls=0,physics_Runtime_Actor_API_or_training_calls=0,
        synthetic_arrays_persisted=False,forbidden_modules=forbidden,wall_s=time.monotonic()-started)
    with Path(args.output).open('x')as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    def fence(event,args):
        if event=='import'and str(args[0]).split('.')[0]in('torch','mujoco','onnxruntime'):
            raise RuntimeError('No model or native import')
        if event in('subprocess.Popen','socket.connect','socket.bind','socket.getaddrinfo'):
            raise RuntimeError('No child process or network')
    sys.addaudithook(fence)
    main()
