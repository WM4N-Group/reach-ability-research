#!/usr/bin/env python3
"""CPU SOFTWARE FIXTURE of exact original query functions; NO real WM weights.

No recorded OBS/DEV data, Runtime, actor, API, optimizer, training or live context.
This catches source function dependencies/shape/clock wiring, not task accuracy.
"""
from dataclasses import replace
import argparse,datetime,hashlib,json,os,sys,tempfile,time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.task_conditioned_reachability.execution_preparation.v4_causal_wm_query import build_original_buffer,CausalWMQueryPort


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('model-source','query-source','output'):p.add_argument('--'+n,required=True)
    a=p.parse_args();assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
    blocked=[]
    def fence(event,args):
        if event=='import'and str(args[0]).split('.')[0]in('mujoco','onnxruntime','gym','isaaclab'):
            blocked.append(str(args[0]));raise RuntimeError('No native/Actor')
        if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
            blocked.append(event);raise RuntimeError('No API/network/child')
    sys.addaudithook(fence)
    sys.path.insert(0,str(Path(a.model_source).resolve()))
    import numpy as np
    import torch
    from visual_latent_world_model import Belief
    torch.set_num_threads(2)
    class FixtureModel:
        training=False;device='cpu'
        def __init__(self):self.encoder_calls=0;self.latent_updates=0
        def encoder(self,history):self.encoder_calls+=1;return torch.zeros((1,3,2))
        def initial_state(self,now):
            return Belief(h=torch.zeros((1,4)),z=torch.zeros((1,2)),mean=torch.zeros((1,2)),std=torch.ones((1,2)),
                time_s=now.double(),anchor_time_s=now.double(),has_observation=torch.zeros(1,dtype=torch.bool),is_posterior=torch.zeros(1,dtype=torch.bool))
        def native_action(self,value):return value
        def _advance(self,state,action,dt,mask,flag):self.latent_updates+=1;return replace(state,time_s=state.time_s+dt)
        def posterior(self,value):return torch.zeros((1,4))
        def _normal(self,value):return torch.zeros((1,2)),torch.ones((1,2))
    model=FixtureModel();started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='explicit-WM-query-fixture-')as temp:
        out=Path(temp)/'query'
        buffer=build_original_buffer(model,dict(mean=[0.]*45,std=[1.]*45),out,
            query_source_root=a.query_source,software_fixture=True)
        try:CausalWMQueryPort(buffer,role='CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY')
        except ValueError:production_relabel_refused=True
        else:raise AssertionError('Fixture buffer gained live identity')
        port=CausalWMQueryPort(buffer,role='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT')
        def packet(tick):
            return dict(rgb=torch.zeros((1,1,2,2,3),dtype=torch.uint8),depth_m=torch.ones((1,1,2,2,1)),
                camera_K=torch.eye(3)[None],T_base_optical=torch.eye(4)[None],proprio=torch.zeros((1,1,45)),
                timestamps_s=torch.tensor([[tick*.005]],dtype=torch.float64),
                actions_previous=torch.full((1,1,18),tick*.001),action_valid=torch.tensor([[tick>0]]))
        port.on_visual(packet(0))
        for tick in range(1,44):
            port.on_issued(np.full(18,tick*.001),tick,tick*.005,
                actual_issued_skill='NAV',native_owner_id='EXPLICIT_FIXTURE_OWNER_NOT_NATIVE')
            if tick in (20,40):port.on_visual(packet(tick))
        public=SimpleNamespace(time_s=.215,sha256='a'*64,value=dict(public_state=dict(
            q=[0.]*18,dq=[0.]*18,gravity=[0.]*3,angular_velocity=[0.]*3,linear_velocity=[0.]*3)))
        batch=SimpleNamespace(observation=public)
        context=port(batch,(SimpleNamespace(sha256='b'*64),))
        assert context['source_role']=='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT' and not context['live_policy_context_allowed']
        assert context['target8_by_option_sha256']=={'b'*64:None}
        assert model.encoder_calls==1 and model.latent_updates==43
        assert abs(float(context['belief'].time_s[0])-.215)<1e-7 and abs(float(context['belief'].anchor_time_s[0])-.2)<1e-7
        assert context['public60'][45]==1 and context['public60'][46:51].sum()==0
        with np.load(context['input_file'],allow_pickle=False)as data:
            assert data['native18_through_query'].shape==(43,18)
            assert np.array_equal(data['native_physical_ticks'],np.arange(1,44))
            assert np.allclose(data['RGB_times_s'],[0.,.1,.2])
        # Wrong WM anchor time cannot be accepted as descriptor provenance.
        bad=CausalWMQueryPort(buffer,role='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT',
            target_provider=lambda obs,opts,anchor:dict(WM_anchor_RGB_bytes_sha256=hashlib.sha256(anchor['rgb'].tobytes()).hexdigest(),WM_anchor_time_s=.215,target8_by_option_sha256={'b'*64:None}))
        try:bad(batch,(SimpleNamespace(sha256='b'*64),))
        except ValueError:wrong_anchor_refused=True
        else:raise AssertionError('Another off-grid frame accepted as WM anchor')
    report=dict(at=datetime.datetime.now().astimezone().isoformat(),role='EXPLICIT_SOFTWARE_ORIGINAL_QUERY_FUNCTION_SMOKE_NOT_REAL_MODEL_OR_NATIVE',
        exact_original_functions_called=['resize_packet','BehaviorQueryBuffer','filter_full_native'],
        fixture_model_encoder_calls=1,fixture_model_latent_updates=43,fixture_reference_commands=43,
        original_query_grid_and_tail_passed=True,production_fixture_relabel_refused=production_relabel_refused,
        wrong_anchor_refused=wrong_anchor_refused,fixture_arrays_removed=True,real_checkpoint_loads=0,
        actual_model_WM_prediction_or_current_V4_queries=0,recorded_OBS_or_DEV_model_inputs=0,
        real_native_world_Actor_API_or_fit=0,forbidden_attempts=blocked,wall_s=time.monotonic()-started)
    assert not blocked
    with Path(a.output).open('x')as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
