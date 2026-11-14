"""Engineering fixture: real RGBD query + exact factory + native executor.

The explicit first-of-two selection is NOT a VLM, policy baseline or task route.
Only used by the independent bounded control-interface development runner.
"""
from dataclasses import asdict
from pathlib import Path


class NativeNavOptionProbe:
    def __init__(self,runtime,registry,*,capture_witness,observer,root,journal,delta):
        from ainav.native.registered_nav_factory import RegisteredNavSessionFactory
        from ainav.native.observation import AcquisitionPublisher
        from mujoco_zyh import native_behavior_executor as api
        self.r,self.registry,self.observer,self.journal=runtime,registry,observer,journal
        self.delta=tuple(delta);self.sequence=0;self.records=[];self.receipts=[]
        self.publisher=AcquisitionPublisher(Path(root)/'option-probe-observations')
        self.factory=RegisteredNavSessionFactory(runtime,registry,initial_witness=capture_witness,journal=journal,native_api=api)
        self.executor=api.NativeOptionExecutor(runtime,self.factory,journal);self.factory.attach_executor(self.executor)

    def start_segment(self):
        import numpy as np
        from ainav.contracts import DecisionBatch,canonical
        from ainav.native.behavior_authority import BehaviorOption
        self.sequence+=1;r=self.r;p=r.sim;now=float(p.data.time)
        witness=self.factory._current_completed_witness();height=self.registry.surfaces[witness.support_ref].top_z_m
        xy=p.data.qpos[:2].copy();dx,dy=self.delta
        goals=(xy+np.asarray([dx,dy]),xy+np.asarray([-dy,dx]))
        anchors=[dict(target_ref='probe_'+str(self.sequence)+'_'+str(i),description='Explicit engineering probe target, not a task plan',
            position_xyz_m=[float(g[0]),float(g[1]),height],uncertainty_xyz_m=[0.,0.,0.]) for i,g in enumerate(goals)]
        packet,_=self.observer.capture(r.step_count//4,r.last.position)
        obs=self.publisher.publish(packet,now=now,descriptors=[],
            declared_map=dict(source_ref='engineering-option-probe-declarations',anchors=anchors),
            goal='Verify native option plumbing only; explicit engineering first target, no model task claim.',events=[])
        proof=self.journal(dict(event='engineering_NAV_entry_support_witness',time_s=now,witness=witness.report(),model_input=False))
        options=tuple(BehaviorOption('probe-option-'+str(self.sequence)+'-'+str(i),'NAV',a['target_ref'],
            tuple(sorted(dict(goal_world_x_m=a['position_xyz_m'][0],goal_world_y_m=a['position_xyz_m'][1],surface_height_m=height).items())),
            60.,proof) for i,a in enumerate(anchors))
        batch=DecisionBatch('engineering-option-probe-'+str(self.sequence),obs,options,canonical(dict(source_ref='native NAV only interface probe',
            skills=['NAV'],constraints=['Explicit engineering selector, not model inference','Original native guards own admission and motion'])))
        self.factory.bind_batch(batch)
        chosen=options[0]  # Fixture ONLY. Never used by the production VLM planner.
        receipt=self.executor.start(chosen,batch.decision_id,now)
        self.journal(dict(event='engineering_explicit_option_selection',query_sha256=batch.sha256,selected_option_sha256=chosen.sha256,
            option=asdict(chosen),candidate_count=len(options),model_decision=False,physical_command_issued=False))
        self.receipts.append(asdict(receipt));self.journal(dict(event='engineering_native_option_receipt',receipt=asdict(receipt),model_decision=False))
        self.records.append(dict(query_sha256=batch.sha256,selected_option_sha256=chosen.sha256,candidate_count=len(options),
            observation_sha256=obs.sha256,start_time_s=now,model_decision=False))
        return self.executor.session.machine.native_nav

    def _drain(self):
        for receipt in self.executor.receipts():
            self.receipts.append(asdict(receipt));self.journal(dict(event='engineering_native_option_receipt',receipt=asdict(receipt),model_decision=False))
            if receipt.status in ('hard_stop','failed','budget_expired'):raise RuntimeError('Native option boundary requires protection, not scripted replacement: '+receipt.status)

    def update(self):self.executor.update();self._drain()
    def command(self):return self.executor.next_command()
    def after_actual_issue(self,issued,tick,now):
        self.executor.record_issued(issued,tick,now,'actual-commands:physical_tick='+str(tick));self._drain()
    def report(self):return dict(kind='native_factory_executor_engineering_probe',queries=self.records,receipts=self.receipts,
        real_native_sessions=len(self.executor.sessions),API_calls=0,model_decisions=0,
        production_task_success_not_inferred=True,selector='explicit_first_probe_option_NOT_VLM')
