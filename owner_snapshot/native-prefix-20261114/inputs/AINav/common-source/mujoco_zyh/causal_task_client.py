"""One causal, actual model-ranked first NAV_STEP choice in the native task.
All remaining task stages/targets are the unmodified native program. Uses only
acquired public RGBD/proprio and declared task cues. Never steps/resets a world.
"""
from pathlib import Path
from collections import deque
from copy import deepcopy
from types import MethodType
import json,hashlib,time,math
import numpy as np
from skill_intents import CausalPhaseDecoder
from task_inputs import state_input,action
from .task_boundary_request import FirstNAVBoundaryRequest
from .visible_surface_goal import describe_visible_goal
from visual_box_proposals import propose_visual_candidates


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def choose_tasks(tasks,stage,dx):
    if stage!='B_STEP_HIGH_PLATFORM' or len(tasks)!=5 or tasks[0].get('skill')!='nav' or tasks[1].get('skill')!='climb':raise ValueError('Pinned first NAV stage required')
    if type(dx) not in (int,float) or not math.isfinite(dx) or dx not in [-.02,0.,.02]:raise ValueError('Only three registered model offsets allowed')
    if abs(tasks[0]['goal'][0]-.05)>1e-7:raise ValueError('Common nominal .05m NAV_STEP target changed')
    out=deepcopy(tasks);out[0]['goal'][0]+=dx
    return out


class Client:
    def __init__(self,router,observer,p,root):
        self.router=router;self.r=router.r;self.observer=observer;self.p=p;self.root=Path(root);self.cfg=p['causal_model_policy']
        n=self.cfg['normalizer'];self.mean=np.asarray(n['mean'],np.float32);self.scale=np.asarray(n['scale'],np.float32)
        self.decoder=CausalPhaseDecoder();self.current=None;self.began=None;self.builder=FirstNAVBoundaryRequest(n,state_input,action)
        self.attempts=0;self.accepted=0;self.forwards=0;self.selected=None
        self.events=(self.root/'causal-model-decisions.jsonl').open('x')
        original=router.start_chunk;owner=self
        def start_chunk(instance,tasks,stage):
            if stage!='B_STEP_HIGH_PLATFORM':return original(tasks,stage)
            if owner.attempts:raise ValueError('Only one actual first-NAV model query allowed')
            owner.attempts+=1;before=owner.observer.snapshot();dx,response=owner.request(tasks,stage)
            if not owner.observer.unchanged(before,owner.observer.snapshot()):raise ValueError('Model wait changed physical state/FIFO')
            chosen=choose_tasks(tasks,stage,dx);original(chosen,stage)
            if instance.active.tasks!=chosen:raise ValueError('Selected model parameters not accepted by original native constructor')
            owner.accepted=1;owner.selected=dx
            event={'event':'model_selected_NAV_STEP_native_accepted','time_s':float(owner.r.sim.data.time),'selected_dx_m':dx,
                   'nominal_tasks':deepcopy(tasks),'actual_tasks':deepcopy(chosen),'model_forecasts':response['model_forecasts'],
                   'request_sha256':response['request_sha256'],'checkpoint_sha256':response['checkpoint_sha256'],
                   'task_graph_and_B_C_identities_learned':False,'not_full_task_success':True}
            owner.events.write(json.dumps(event)+'\n');owner.events.flush()
            instance.event('model_NAV_STEP_parameter_accepted',selected_dx_m=dx,actual_tasks=chosen,model_forecasts=response['model_forecasts'])
        router.start_chunk=MethodType(start_chunk,router)
        close=router.close
        def wrapped_close():
            try:close()
            finally:owner.events.close()
        router.close=wrapped_close

    def control(self,time_s,skill,phase):
        if self.attempts:return
        macro=self.decoder.push({'time_s':time_s,'skill':skill,'phase':phase})
        if macro!=self.current:self.current=macro;self.began=time_s

    def capture(self,packet):
        if self.attempts:return
        arrays={key:value.numpy().copy() for key,value in packet.items()}
        self.builder.append_acquired(arrays,declared_macro=self.current,macro_declared_at_s=self.began)

    def public_body(self):
        s=self.r.sim
        return np.r_[s.data.qpos[s.qids],s.data.qvel[s.dids],self.observer.public_body_proprio()].astype(np.float32)

    def request(self,tasks,stage):
        t=float(self.r.sim.data.time)
        completed=next((x for x in reversed(self.router.extra_events) if x['event']=='B_native_goal_and_original_finish_complete'),None)
        if completed is None:raise ValueError('Actual public B-completion event absent before model query')
        known={key:completed[key] for key in ('time','event','stage')}
        built=self.builder.build(decision_time_s=t,actual_public_body=self.public_body(),body_observed_at_s=t,known_B_completion=known)
        arrays=built['context_arrays'];times=built['provenance']['rgb_times_s']
        q=self.root/'causal-model-rpc';q.mkdir(exist_ok=False)
        with (q/'observed-context.npz').open('xb') as f:
            np.savez_compressed(f,**arrays)
        request=dict(schema='causal-first-NAV-parameter-query-v2',method=self.cfg['method'],checkpoint_sha256=self.cfg['checkpoint_sha256'],
             context_sha256=sha(q/'observed-context.npz'),anchor_time_s=t,rgb_times_s=times,body_time_s=t,candidate_dx_m=[-.02,0.,.02],
             source_id=self.p['source_id'],episode_id=self.p['episode_id'],decision_id='first-NAV_STEP',observation_epoch=int(round(t/.005)))
        (q/'request.json').write_text(json.dumps(request,indent=2)+'\n');(q/'candidate-current-geometry.json').write_text(json.dumps(built['provenance'],indent=2)+'\n')
        (q/'READY').write_text('ready\n');print('CAUSAL_MODEL_REQUEST_READY',self.p['source_id'],flush=True)
        began=time.monotonic()
        while not (q/'response.json').exists():
            if time.monotonic()-began>=60.:raise ValueError('Bounded model response deadline; no fixed fallback')
            time.sleep(.1)
        response=json.loads((q/'response.json').read_text())
        for key in ['source_id','episode_id','decision_id','observation_epoch','checkpoint_sha256']:
            if response.get(key)!=request[key]:raise ValueError('Fresh model response binding differs: '+key)
        if response.get('request_sha256')!=sha(q/'request.json') or response.get('context_sha256')!=sha(q/'observed-context.npz') or response.get('future_recorded_commands_or_outcomes_read') is not False:raise ValueError('Response causal context/SHA differs')
        costs=response['costs'];dxs=[-.02,0.,.02]
        if response.get('candidate_dx_m')!=dxs or len(costs)!=3 or not all(type(v) in (int,float) and math.isfinite(v) for v in costs) or max(costs)-min(costs)<=1e-10 or costs.count(min(costs))!=1:raise ValueError('Unique finite distinguishing model score required')
        chosen=dxs[costs.index(min(costs))]
        if response['selected_dx_m']!=chosen or response['model_forecasts']!=(3 if self.cfg['method']=='dino' else 12):raise ValueError('Choice/actual inference accounting differs')
        self.forwards=response['model_forecasts'];return chosen,response

    def summary(self):
        return dict(method=self.cfg['method'],checkpoint_sha256=self.cfg['checkpoint_sha256'],requests=self.attempts,
                    native_accepted_choices=self.accepted,model_forecasts=self.forwards,selected_dx_m=self.selected,
                    task_graph_and_B_C_identities_learned=False,scope='one model-ranked first NAV_STEP parameter; rest native nominal')


def attach(router,observer,p,root):
    router.causal_policy=Client(router,observer,p,root);return router.causal_policy
