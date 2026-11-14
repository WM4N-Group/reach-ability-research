"""Bounded real-course NAV control-chain pilot, NOT full A/B/C autonomy.

The original required A-failure/protected-stow test prefix remains native and is
explicitly not credited to the VLM. Thereafter DeepSeek/tree chooses among three
public ground viewpoints; no B/C object-role table or world-model prediction.
"""
from dataclasses import asdict
import json
from pathlib import Path
from .course_tools import (CourseGuardsAndWriter, CourseMonitor, CourseSessionFactory,
                           PublicReference, NotAdmitted, nav_backend, movement_entry)
from .gateway import NativeDecisionGateway
from .loop import AinavLoop
from .observation import AcquisitionPublisher
from ..contracts import canonical, sha
from ..native.behavior_authority import BehaviorOption


class StaticMapNavigationOnly:
    """Production fail-closed resolver: this pilot cannot bind dynamic PUSH."""
    def targets_for_query(self, runtime, query_sha256):
        return ()

    def resolve(self, *args):
        raise NotAdmitted('Dynamic-object binding is not enabled in this NAV pilot')


class NavPilot(CourseGuardsAndWriter):
    def __init__(self, *, runtime, native_a, observer, writer, root, config,
                 api, integrated, stall, planner, journal):
        import numpy as np
        from visual_box_proposals import propose_visual_candidates
        self.np,self.propose = np,propose_visual_candidates
        self.r,self.observer,self.writer,self.root = runtime,observer,writer,Path(root)
        self.config,self.api,self.integrated,self.stall = config,api,integrated,stall
        self.planner,self.primary_journal = planner,journal
        self.prefix=stall.StallStowRouter(runtime,native_a,root)
        self.monitor=CourseMonitor(runtime,config,integrated,stall,self.prefix,api)
        self.extra_guards=lambda: True  # Original native guards remain in every native session.
        self.loop=None;self.tick=0;self._before=None;self._last_issued=runtime.last.position.copy()
        self._world=(runtime.sim,runtime.sim.model,runtime.sim.data,runtime.sim.queue,
                     runtime.sim.controller,runtime.sim.box_push_target)
        self.completed=[];self.dispatched=[];self.visited=set();self.sequence=0
        self.private_initial_by_option={};self.last_capture_tick=None;self.prefix_proof=None
        lane=config['integrated_case']['lane_y_m']
        # Public static survey anchors at the original initial X, not object poses.
        # These do NOT identify B/C roles or encode the full task successor route.
        self.references=tuple(PublicReference('ground-view:'+name,(-.08,lane+dy),0.,
            'declared-static-survey-map-v1') for name,dy in (('left',.35),('center',0.),('right',-.35)))
        self.factory=CourseSessionFactory(runtime=runtime,bundle=config['bundle'],resolver=StaticMapNavigationOnly(),
            api=api,integrated=integrated,monitor=self.monitor,prefix=self.prefix,root=root,
            references=self.references,guards=self._native_guards)
        self.executor=api.NativeOptionExecutor(runtime,self.factory,self.journal)
        self.factory.executor=self.executor
        self.publisher=AcquisitionPublisher(self.root/'query-observations')
        self.capabilities=canonical(dict(source_ref='frozen original NAV actor + compact-NAV native entry contract',
            skills=['NAV'],constraints=[
                'This control-chain pilot admits only NAV. PUSH/CLIMB are not yet connected here.',
                'The original final goal remains far-bank loaded stop; partial information-gathering plans are allowed.',
                'Admitted first actions passed actual native support/entry checks. NAV performs native obstacle avoidance.',
                'Map anchors are declared public geometry, not hidden live positions. Unknown future geometry is not an achieved state.',
                'Use distinct navigation sequences if sharing a first action. Never claim full task completion from a viewpoint arrival.']))
        self.gateway=NativeDecisionGateway(runtime=runtime,observe_public=self.observe_public,
            admitted_options=self.catalogue,bind_native=self.bind,snapshot=self._snapshot,
            journal=self.journal,capability_contract=self.capabilities)

    def journal(self, row):
        # Primary actual receipt is persisted before private/public receipt hooks.
        ref=self.primary_journal(row)
        if row['event']=='ainav_native_admitted':
            option=self.executor.option
            if option is not None:
                self.private_initial_by_option[option.sha256]=self.r.sim.data.xpos[self.r.sim.base_id].copy()
                self.dispatched.append(dict(time_s=float(self.r.sim.data.time),option=asdict(option)))
        elif row['event']=='ainav_native_receipt' and row['receipt']['status']=='succeeded':
            option=self.executor.option
            before=self.private_initial_by_option[option.sha256]
            after=self.r.sim.data.xpos[self.r.sim.base_id].copy()
            self.visited.add(option.target_ref)
            record=dict(option_sha256=option.sha256,target_ref=option.target_ref,
                completion_time_s=row['receipt']['time_s'],native_receipt=row['receipt'],
                actual_base_displacement_world_m=(after-before).tolist(),model_input=False)
            self.completed.append(record)
            self.primary_journal(dict(event='private_actual_NAV_motion_witness',**record))
        return ref

    def capture_grid(self):
        if self.tick%20==0 and self.last_capture_tick!=self.tick:
            packet,private=self.observer.capture(self.tick//4,self._last_issued)
            self.writer.append_visual(packet,control_tick=self.tick//4,private_catalog=private)
            self.last_capture_tick=self.tick

    def observe_public(self, now):
        packet,private=self.observer.capture(self.tick//4,self._last_issued)
        def array(x):return x.detach().cpu().numpy()
        proposals=self.propose(array(packet['rgb'])[0,0],array(packet['depth_m'])[0,0],
                              array(packet['camera_K'])[0],array(packet['T_base_optical'])[0])
        self.sequence+=1
        directory=self.root/('query-private-%04d'%self.sequence);directory.mkdir()
        (directory/'catalog.json').write_text(json.dumps(private,indent=2)+'\n')
        (directory/'pixel-proposals.json').write_text(json.dumps(proposals,indent=2)+'\n')
        descriptors=[dict(target_ref='query%d-region%d'%(self.sequence,i),
            label='frame-local '+p['appearance_family']+' region, persistent object identity unknown',
            bbox_xyxy=p['pixel_bbox_xyxy'],evidence_ref='query%d:RGBD-pixel-proposal%d'%(self.sequence,i))
            for i,p in enumerate(proposals['candidates'])]
        anchors=[dict(target_ref=r.ref,description='declared ground survey viewpoint; not a prescribed task successor',
            position_xyz_m=[*r.xy,0.],uncertainty_xyz_m=[0.,0.,0.]) for r in self.references]
        goal=self.integrated.layout(self.config['integrated_case'])
        anchors.append(dict(target_ref='original-final-goal',description='declared far-bank finish; must actually be reached and loaded',
            position_xyz_m=[goal['finish_x'],self.config['integrated_case']['lane_y_m'],.6],uncertainty_xyz_m=[0.,0.,0.]))
        events=[dict(kind='completion' if self.completed else 'failure',
            description=('Actual NAV completed at '+self.completed[-1]['target_ref'] if self.completed else
                         'Original initial PUSH failed and mandatory native protected stow completed; cause is contextual, not global immovability'),
            evidence_ref=self.completed[-1]['native_receipt']['evidence_ref'] if self.completed else 'actual-native-prefix.json')]
        observation=self.publisher.publish(packet,now=now,descriptors=descriptors,
            declared_map=dict(source_ref='public static ground viewpoints and original final geometry; no dynamic object poses',anchors=anchors),
            goal='Reach the original far bank and stop with loaded support. Current bounded pilot can navigate to gain observations; do not claim full goal completion.',events=events)
        return observation

    def catalogue(self, observation):
        p=self.r.sim;np=self.np
        ids=[p.model.body(n+'_foot').id for n in ('FR','FL','RR','RL')]
        xyz=np.asarray(p.data.xpos[ids]);loads=np.asarray(p.forces[ids,2])
        if (not np.isfinite(xyz).all() or not np.isfinite(loads).all()
                or np.count_nonzero(loads>3.)<3 or not np.all(abs(xyz[:,2]-.022)<.08)):
            raise NotAdmitted('Original actual ground-support domain unavailable')
        if nav_backend(self.r,0.)=='compact_nav':self.factory._completed_compact_owner()
        else:movement_entry(self.r)
        receipt=self.journal(dict(event='actual_native_NAV_entry_admission',time_s=observation.time_s,
            source='unchanged native support and actual completed protected owner',model_input=False))
        return tuple(BehaviorOption('query%d-%s'%(self.sequence,r.ref),'NAV',r.ref,
            tuple(sorted(dict(goal_world_x_m=r.xy[0],goal_world_y_m=r.xy[1],surface_height_m=0.).items())),
            60.,receipt) for r in self.references if r.ref not in self.visited)

    def bind(self, batch):
        self.factory.bind_query(batch.sha256,batch.options)

    def step_one(self):
        p=self.r.sim
        if abs(float(p.data.time)-self.tick*.005)>1e-7:raise RuntimeError('Original physical clock differs')
        self.capture_grid()
        self._before=(float(p.data.time),p.data.qpos[p.qids].copy(),p.data.qvel[p.dids].copy())
        if self.loop is None:
            if self.tick%4==0:self.prefix.update()
            if self.prefix.complete:
                self.prefix_proof=self.monitor.prefix_evidence()
                (self.root/'actual-native-prefix.json').write_text(json.dumps(self.prefix_proof,indent=2)+'\n')
                self.journal(dict(event='original_required_prefix_complete',time_s=float(p.data.time),
                                  counts_as_model_decision=False,automatic_next_task_skill=False))
                self.loop=AinavLoop(runtime=self.r,executor=self.executor,planner=self.planner,
                    batch_provider=self.gateway,snapshot=self._snapshot,command_writer=self._write_command,
                    after_step_guard=self._after_guard,journal=self.journal,physical_tick=self.tick)
                return False
            command=self.prefix.next_command();issued=command.array().copy();before=float(p.data.time)
            try:self.r.step(command)
            finally:
                if float(p.data.time)>before:
                    if abs(float(p.data.time)-before-.005)>1e-7:raise RuntimeError('Original single tick exceeded')
                    self.tick+=1
                    try:self._write_command(issued,self.tick,float(p.data.time))
                    finally:
                        try:self.prefix.after_step()
                        finally:self._after_guard()
            return True
        try:return self.loop.step_one()
        finally:self.tick=self.loop.physical_tick
