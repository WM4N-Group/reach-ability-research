#!/usr/bin/env python3
"""Original full-task Runtime + new placement binding, ZERO main-world steps.

No fake successful prefix/owner; prospective binding is not execution admission.
"""
import argparse
from datetime import datetime
import hashlib,json,os,resource,sys,time
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2,default=lambda v:v.tolist(),allow_nan=False);f.write('\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('source','bundle','root','gpu-lock'):ap.add_argument('--'+k,required=True)
    ap.add_argument('--host-adapter',choices=('verified-placement','execution-judged'),default='verified-placement')
    a=ap.parse_args();source,bundle,root=(Path(x).resolve() for x in (a.source,a.bundle,a.root))
    if root.exists():raise FileExistsError('Fresh preflight root required')
    root.mkdir(parents=True);sys.path.insert(0,str(source));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    os.environ.update(MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='0',PYTHONDONTWRITEBYTECODE='1')
    from ainav.native.resources import ResourceLease
    from ainav.evidence import Journal
    journal=Journal(root/'events.jsonl');r=observer=None;start=time.monotonic()
    report=dict(schema='ainav-full-task-placement-integration-zero-v1',started_at=datetime.now().astimezone().isoformat(),source_manifest_sha256=sha(source/'ainav-source.json'),
        main_world_steps=0,API_calls=0,model_decisions=0,task_success=False,automatic_retry=False)
    try:
        with ResourceLease([a.gpu_lock]) as lease:
            save(root/'resource-admission.json',lease.evidence)
            import torch
            torch.set_num_threads(2)
            from mujoco_zyh import integrated_course as integrated,stall_stow as stall,native_behavior_executor as api
            from mujoco_zyh.runtime_adapter import construct_runtime
            from mujoco_zyh.observer import OnboardObserver
            from ainav.native.full_bindings import _SOURCES
            from ainav.native.full_verified_placement import PlacementCourseResolver,VerifiedPlacementFullCourse
            from ainav.contracts import file_sha
            from ainav.native.observation import AcquisitionPublisher
            from ainav.deployment import profile
            from mujoco_zyh.source_bundle import verify_bundle
            import importlib
            report['assets_before']=verify_bundle(bundle)
            native=integrated.protocol(next(c for c in integrated.plan()['cases'] if c['case_id']=='full-4'));integrated.validate_protocol(native)
            r,machine,receipt=construct_runtime(bundle,profile('yuanyue-5090').runtime_config(dict(native,bundle=str(bundle))))
            save(root/'construction.json',receipt);report['auxiliary_calibration']=r.wm_auxiliary_calibration
            r.wm_completion_clock_journal=journal;before=api.world_snapshot(r)
            observer=OnboardObserver(r,native);packet,_=observer.capture(0,r.last.position)
            modules={name:importlib.import_module(name) for name in _SOURCES}
            resolver=PlacementCourseResolver(r,proposals=modules['visual_box_proposals'],geometry=modules['native_visual_target_binding'],contexts=modules['mujoco_selected_target_context'],native_api=api,native_history_sha=stall.history_sha,source_sha256={n:file_sha(m.__file__) for n,m in modules.items()})
            descriptors=resolver.observe(packet,control_tick=0,physical_tick=0)
            AcquisitionPublisher(root/'actual-observation').publish(packet,now=0.,descriptors=[dict(target_ref=x['target_ref'],label='actual observed cuboid',bbox_xyxy=x['descriptor']['pixel_bbox_xyxy'],evidence_ref='zero-current-RGBD') for x in descriptors],declared_map=dict(source_ref='zero-step binding check only',anchors=[]),goal='Observe only; no task action admitted.',events=[])
            # At the original start, only the required failed-A object may be
            # visible. Never fabricate visibility to bind a future target.
            # Exercise private prospective target construction separately; it
            # is NOT a current RGBD query or native motion admission.
            from ainav.native.full_verified_placement import placement_declaration,SelectedPlacementContexts
            contexts=SelectedPlacementContexts(modules['mujoco_selected_target_context'])
            rows=[]
            for candidate in ('middle','heavy'):
                body=r.wm_candidate_contacts['scene_keys'][candidate]
                pos=r.sim.data.xpos[r.sim.model.body(body).id].copy();gid=r.sim.model.geom(body+'_geom').id
                size=tuple(float(v)*2 for v in r.sim.model.geom_size[gid]);source_h=0. if candidate=='middle' else .4
                public=(float(pos[0]+.2),float(pos[1]));contract=placement_declaration(body,size,public,source_h)
                contexts.pending=contract
                view,proof=contexts.make_target_context(r,r.wm_candidate_contacts,candidate,cfg_overrides={'box_size':size},
                    declared_push={'distance_m':.31,'declaration_id':'zero-prospective-'+candidate,'goal_xy_m':contract.drive_goal_xy_m})
                contexts.pending=None
                if not (view.box_push_target[0,:2].numpy()==__import__('numpy').asarray(contract.drive_goal_xy_m,dtype='float32')).all():raise ValueError('Actual prebound drive differs')
                if view.body_braking_reference.declaration.body_goal_xy_m!=public:raise ValueError('Body reference differs from public placement')
                if view.settled.report()['native_advances']!=0:raise ValueError('Unissued clock advanced')
                rows.append(dict(body=body,public_goal=list(public),drive_goal=list(contract.drive_goal_xy_m),actual_distance=.31,clock=view.settled.report(),
                    actual_current_image_association_claimed=False,native_session_not_constructed=True,private_prospective_only=True))
            from mujoco_zyh.streams import ChunkedEpisodeWriter
            writer=ChunkedEpisodeWriter(root/'unissued-composed-episode',dict(native,joint_names=r.push['model'].JOINTS,
                actor_sha256=json.loads((bundle/'MANIFEST.json').read_text())['actor_sha256']))
            class NoPlanningAtZero:
                def select(self,*args):raise RuntimeError('No model/dispatch authorized at zero-step')
            Host=VerifiedPlacementFullCourse
            if a.host_adapter=='execution-judged':
                from ainav.native.execution_judged_course import ExecutionJudgedFullCourse
                Host=ExecutionJudgedFullCourse
            host=Host(runtime=r,native_a=machine,observer=observer,writer=writer,root=root,config=dict(native,bundle=str(bundle)),
                api=api,integrated=integrated,stall=stall,planner=NoPlanningAtZero(),journal=journal)
            if a.host_adapter=='execution-judged':
                actual=host.observe_public(0.)
                intents=host.intent_catalogue(actual)
                report['semantic_intent_skills']=sorted({x.skill for x in intents})
                report['unready_interaction_intents_present']=any(x.skill in ('PUSH','CLIMB') for x in intents)
                report['entry_source_identity']=host.entry_source_identity
                report['intent_catalogue_scope']='original startup before required loaded-support prefix; an empty catalogue is correct if no measured support'
                report['execution_judge_coordinator_connected']=host.gateway is host.coordinator and host.planner is host.coordinator
                if not report['execution_judge_coordinator_connected']:raise ValueError('Execution judge not connected to native loop')
            host.private_samples.close();host.prefix.log.close();host.prefix.recovery_log.close()
            writer.close(outcome='zero_unissued_host_construction',terminal_time_s=0.,censored=True)
            report['actual_host_constructed']=type(host).__name__
            if before!=api.world_snapshot(r) or r.step_count or r.sim.data.time:raise RuntimeError('Zero binding changed original world/FIFO')
            report.update(outcome='actual_RGBD_placement_binding_zero_passed',prospective_targets=rows,actual_host_class_imported=Host.__name__,
                completed_prefix_or_owner_fabricated=False,native_motion_admission_claimed=False)
            report['assets_after']=verify_bundle(bundle)
    except Exception as e:report.update(outcome='failed_no_retry',error=type(e).__name__+': '+str(e))
    finally:
        if observer:observer.close()
        report['wall_seconds']=time.monotonic()-start;journal.close();save(root/'report.json',report)
    print(json.dumps(report,default=lambda v:v.tolist()));return 0 if report['outcome']=='actual_RGBD_placement_binding_zero_passed' else 2


if __name__=='__main__':raise SystemExit(main())
