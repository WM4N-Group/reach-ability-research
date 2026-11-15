"""Public-blueprint candidates only; no material/role truth or successor table.

Reuses the original full-course front-.58m, center/±.15m NAV declarations.
Only same-support candidates are executable here. PUSH/CLIMB are NOT advertised
as connected by this first-action trial. A model-selected viewpoint is not a
bridge, climb or complete-task result.
"""
from copy import deepcopy
import math


def public_layout(scene):
    from .transfer_scene import public_scene
    return public_scene(scene)


def compile_layout_nav(public, *, support_ref):
    if public.get('schema')!='ainav-public-declared-geometry-v1':
        raise ValueError('Public initial blueprint required')
    surfaces={s['id']:s for s in public['surfaces']}
    if support_ref not in surfaces:raise ValueError('Actual source support absent from declared map')
    anchors=[];candidates=[];current=surfaces[support_ref];height=current['top_z_m']
    for surface in public['surfaces']:
        x0,x1,y0,y1=surface['bounds_xy_m']
        anchors.append(dict(target_ref=surface['id'],description=f'Declared static surface bounds_xy_m={[x0,x1,y0,y1]}, top_z_m={surface["top_z_m"]}. No task role.',
            position_xyz_m=[(x0+x1)/2,(y0+y1)/2,surface['top_z_m']],uncertainty_xyz_m=[0.,0.,0.]))
    for obj in public['objects']:
        allowed={'id','size_m','initial_center_xyz_m','initial_support_height_m'}
        if set(obj)!=allowed:raise ValueError('Only public blueprint object fields allowed; no dynamics/role truth')
        center=obj['initial_center_xyz_m'];size=obj['size_m']
        if not all(math.isfinite(v) for v in (*center,*size)) or min(size)<=0:raise ValueError('Finite declared cuboid required')
        anchors.append(dict(target_ref=obj['id'],description=f'Initial declared cuboid size_m={size}, support_height_m={obj["initial_support_height_m"]}; initial geometry only, mobility unknown.',
            position_xyz_m=list(center),uncertainty_xyz_m=[0.,0.,0.]))
        if abs(obj['initial_support_height_m']-height)>1e-8:continue
        x0,x1,y0,y1=current['bounds_xy_m'];front=center[0]-size[0]/2
        if not (x0<=front and center[0]+size[0]/2<=x1 and y0<=center[1]-size[1]/2 and center[1]+size[1]/2<=y1):continue
        for name,dy in (('center',0.),('left',.15),('right',-.15)):
            x,y=front-.58,center[1]+dy
            if not x0+.5<x<x1-.5 or not y0+.4<y<y1-.4:continue
            # Pure blueprint exclusion, NOT live native collision admission.
            if any(abs(x-o['initial_center_xyz_m'][0])<o['size_m'][0]/2+.3 and
                   abs(y-o['initial_center_xyz_m'][1])<o['size_m'][1]/2+.3 and
                   abs(o['initial_support_height_m']-height)<1e-8 for o in public['objects']):continue
            ref=obj['id']+':approach:'+name
            anchors.append(dict(target_ref=ref,description='Public front-side NAV viewpoint for '+obj['id']+'; not an object role or PUSH/CLIMB admission.',
                position_xyz_m=[x,y,height],uncertainty_xyz_m=[0.,0.,0.]))
            candidates.append(dict(target_ref=ref,object_ref=obj['id'],goal_xy=[x,y],surface_height_m=height))
    goal=public['goal'];surface=surfaces[goal['surface']];x0,x1,y0,y1=goal['bounds_xy_m']
    anchors.append(dict(target_ref='declared_final_goal',description='Final task goal region '+str(goal['bounds_xy_m'])+' on '+goal['surface']+'. Reaching a viewpoint is not task completion.',
        position_xyz_m=[(x0+x1)/2,(y0+y1)/2,surface['top_z_m']],uncertainty_xyz_m=[0.,0.,0.]))
    if len(anchors)>64 or not 2<=len(candidates)<=128:raise ValueError('Bounded multiple native-compatible viewpoint candidates required')
    if len({c['object_ref'] for c in candidates})<2:raise ValueError('At least two distinct objects required for meaningful object selection')
    return deepcopy(dict(declared_map=dict(source_ref='public initial scene blueprint; no private pose/material/role/route',anchors=anchors),candidates=candidates,
        goal=goal['instruction']+' Choose an information-gathering NAV viewpoint toward this final goal. This first-action test does not execute interactions or certify the full route.'))


class ModelLayoutNav:
    """One actual VLM/tree-selected NAV; unchanged verified native session."""
    def __init__(self,runtime,registry,*,capture_witness,observer,root,journal,scene):
        from pathlib import Path
        from .native.registered_nav_factory import RegisteredNavSessionFactory
        from .native.observation import AcquisitionPublisher
        from mujoco_zyh import native_behavior_executor as api
        self.r,self.observer,self.journal=runtime,observer,journal
        self.registry=registry;self.layout=compile_layout_nav(public_layout(scene),support_ref=capture_witness.support_ref)
        self.factory=RegisteredNavSessionFactory(runtime,registry,initial_witness=capture_witness,journal=journal,native_api=api)
        self.executor=api.NativeOptionExecutor(runtime,self.factory,journal);self.factory.attach_executor(self.executor)
        self.publisher=AcquisitionPublisher(Path(root)/'model-observations')
        self.backend=self.planner=None;self.selection=None;self.chosen=None;self.receipts=[];self.batch=None
        self.scene=public_layout(scene)
    def start(self):
        from dataclasses import asdict
        from .contracts import DecisionBatch,canonical
        from .native.behavior_authority import BehaviorOption
        from .backend import create_vision_backend
        from .vlm import RoleRunner
        from .planner import AinavPlanner
        r=self.r;now=float(r.sim.data.time)
        witness=self.factory._current_completed_witness()
        packet,_=self.observer.capture(r.step_count//4,r.last.position)
        obs=self.publisher.publish(packet,now=now,descriptors=[],declared_map=self.layout['declared_map'],goal=self.layout['goal'],events=[],
            public_status=dict(support_surface=witness.support_ref))
        proof=self.journal(dict(event='model_nav_actual_support',time_s=now,witness=witness.report(),model_input=False))
        options=tuple(BehaviorOption('model-nav-'+str(i),'NAV',c['target_ref'],tuple(sorted(dict(goal_world_x_m=c['goal_xy'][0],goal_world_y_m=c['goal_xy'][1],surface_height_m=c['surface_height_m']).items())),60.,proof) for i,c in enumerate(self.layout['candidates']))
        batch=DecisionBatch('first-actual-model-layout-query',obs,options,canonical(dict(source_ref='frozen verified RegisteredNavSessionFactory/RegisteredCompactNav; unchanged control',skills=['NAV'],constraints=[
            'Only NAV is executable in this bounded first-action trial. No PUSH/CLIMB or full-task success is claimed.',
            'All cuboid geometry is initial PUBLIC blueprint, not current private pose; mass/friction/mobility unknown.',
            'Every admitted first action is a same-support public viewpoint. Native guards decide motion safety and completion.',
            'Select among multiple objects using final goal and image/map. No designated box roles or successor sequence.',
            'Do not put NAV on a different support in a future plan: no support-changing skill is connected in this first-action test. Partial plans are appropriate.'
        ])))
        self.factory.bind_batch(batch);self.batch=batch
        self.backend=create_vision_backend(max_calls=8,max_tokens=4096,max_total_tokens=100000)
        self.journal(dict(event='model_nav_backend_verified',identity=self.backend.identity))
        self.planner=AinavPlanner(RoleRunner(self.backend,self.journal,timeout_s=90.),self.journal,plan_count=3,terminal_bonus=10.,max_role_calls=8)
        self.selection=self.planner.select(batch)
        self.chosen=next(o for o in options if o.sha256==self.selection.option_sha256 and o.token==self.selection.token)
        # No default index, heuristic choice, exception fallback or replacement.
        receipt=self.executor.start(self.chosen,batch.decision_id,now)
        self.journal(dict(event='model_nav_exact_selection_dispatched',selection=asdict(self.selection),option=asdict(self.chosen),
            query_sha256=batch.sha256,candidate_count=len(options),object_count=len({c['object_ref'] for c in self.layout['candidates']}),model_decision=True,full_task_success=False))
        self.receipts.append(asdict(receipt));self.journal(dict(event='model_nav_receipt',receipt=asdict(receipt)))
        return self.executor.session.machine.native_nav
    def drain(self):
        from dataclasses import asdict
        for receipt in self.executor.receipts():
            self.receipts.append(asdict(receipt));self.journal(dict(event='model_nav_receipt',receipt=asdict(receipt)))
            if receipt.status in ('succeeded','hard_stop','failed','budget_expired'):
                self.planner.observe(self.chosen,receipt)
            if receipt.status in ('hard_stop','failed','budget_expired'):raise RuntimeError('Native selected action stopped; no retry/fallback:'+receipt.status)
    def update(self):self.executor.update();self.drain()
    def command(self):return self.executor.next_command()
    def after_actual_issue(self,issued,tick,now):
        self.executor.record_issued(issued,tick,now,'actual-commands:physical_tick='+str(tick));self.drain()
    def report(self):
        from dataclasses import asdict
        return dict(kind='real_VLM_tree_selected_first_NAV_only',model_calls=self.backend.calls if self.backend else 0,
            model_total_tokens=self.backend.total_tokens if self.backend else 0,model_selection=asdict(self.selection) if self.selection else None,
            selected_option=asdict(self.chosen) if self.chosen else None,receipts=self.receipts,
            candidate_count=len(self.layout['candidates']),distinct_object_count=len({c['object_ref'] for c in self.layout['candidates']}),
            whole_task_or_interaction_chain_verified=False,unconnected_skills=['PUSH','CLIMB','HOLD'],automatic_retry=False,controller_tuned=False)
