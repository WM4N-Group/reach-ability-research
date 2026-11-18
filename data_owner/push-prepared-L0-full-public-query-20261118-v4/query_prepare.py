"""Exact shared query/watch/phase calls with CPU-only synthetic inputs."""
from pathlib import Path
import json
import hashlib
import tempfile
from types import SimpleNamespace


def need(value, message):
    if not value: raise ValueError(message)


def qualify_query_bindings(c, freeze):
    import numpy as np
    from ainav.native import observation as obs
    from ainav import contracts
    from public_descriptor_projection import publish_current
    from resource_watch import ResourceWatch
    from scoped_io import StopState, PolicyStop
    from query_bindings import construct_watch, check_phase_health
    for module in (obs, contracts):
        p=Path(module.__file__)
        need(freeze['files'].get(str(p))==hashlib.sha256(p.read_bytes()).hexdigest(),'Original public contract SHA')
    def never_probe(): raise AssertionError('CPU prepare must not start a probe')
    watch,cfg=construct_watch(ResourceWatch,never_probe,StopState(),lambda:True,c)
    need(watch.thread is None and watch.probe_calls==0,'No watch thread or probe during CPU check')
    health_calls=[]
    def health(): health_calls.append(True)
    def gate(phase,skill,config=c):
        return check_phase_health(health,StopState(),config,phase,SimpleNamespace(skill=skill))
    need(gate('main','PUSH'),'Authorized main/PUSH')
    for phase,skill,config in [('zero','PUSH',c),('main','NAV',c),('main','PUSH',dict(c,full_original_task_execution=False))]:
        try:gate(phase,skill,config)
        except PolicyStop:pass
        else:raise AssertionError('Phase/skill gate failed closed check')
    need(len(health_calls)==4,'Health must run on both allowed and rejected paths')
    failure=ValueError('synthetic original-health failure')
    def fail_health():raise failure
    try:check_phase_health(fail_health,StopState(),c,'main',SimpleNamespace(skill='PUSH'))
    except ValueError as exc:need(exc is failure,'Original health failure preserved')
    else:raise AssertionError('Swallowed original health failure')
    rgb=np.zeros((1,1,128,192,3),dtype=np.uint8);proprio=np.zeros((1,1,45));proprio[0,0,38]=-1.
    packet=dict(rgb=rgb,depth_m=np.ones((1,1,128,192,1),dtype=np.float32),camera_K=np.array([[[100.,0.,96.],[0.,100.,64.],[0.,0.,1.]]]),T_base_optical=np.eye(4)[None],proprio=proprio,actions_previous=np.zeros((1,1,18)),action_valid=np.zeros((1,1),dtype=bool),timestamps_s=np.array([[6.505]]))
    row=dict(target_ref='FAKE_CPU_OPAQUE_REF',RGB_sha256=hashlib.sha256(rgb[0,0].tobytes()).hexdigest(),descriptor=dict(appearance_family='FAKE_CURRENT_RGB_COLOR',pixel_bbox_xyxy=[1,2,10,12],pixel_centroid_uv=[5.,6.],median_observed_RGB=[0.,0.,0.],pixel_count=20,geometry_valid=True))
    kwargs=dict(now=6.505,declared_map=dict(source_ref='Original fixed L0 source, not live GT',anchors=[]),goal='Original independent PUSH L0 startup then one registered +X .6m PUSH/public[1.7,0]/full original exit',events=[])
    with tempfile.TemporaryDirectory(prefix='CPU_ONLY_ORIGINAL_PUBLISHER-') as tmp:
        try:obs.AcquisitionPublisher(Path(tmp)/'raw').publish(packet,descriptors=(row,),**kwargs)
        except ValueError as exc:need(str(exc)=='Detector-only measured descriptor fields required','Original raw schema predicate')
        else:raise AssertionError('Raw schema was accepted')
        pub=obs.AcquisitionPublisher(Path(tmp)/'projected')
        try:publish_current(pub,packet,(dict(row,RGB_sha256='f'*64),),**kwargs)
        except ValueError:need(pub.count==0,'Stale row must reject before publisher')
        else:raise AssertionError('Stale descriptor was accepted')
        result=publish_current(pub,packet,(row,),**kwargs)
        obj=json.loads(result.encoded)["objects"][0]
        need(obj['target_ref']==row['target_ref'] and obj['bbox_xyxy']==[1,2,10,12]
             and obj['geometry']==dict(status='unknown',source='unavailable',values={},uncertainty={})
             and obj['evidence_ref']=='current-public-RGB-bytes-sha256:'+row['RGB_sha256'],'Original Observation ABI/privacy')
    return dict(CPU_fixture_only=True,actual_watch_configuration=cfg,public_Observation_returned=True,
        raw_descriptor_rejected=True,stale_descriptor_rejected=True,main_PUSH_allowed=True,
        zero_PUSH_rejected=True,main_NAV_rejected=True,health_failure_propagated=True)
