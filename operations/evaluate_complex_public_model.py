#!/usr/bin/env python3
"""Run A/B on AINav's actual PUBLIC scene model, NEVER claim native success.

No importing scene constructor/private qualification or reading its witness.
This public-model diagnostic does not execute/record a robot or qualify a plan.
"""
import argparse,dataclasses,datetime as dt,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.task_conditioned_reachability.execution_preparation.complex_public_model import PublicSceneModel
from research.task_conditioned_reachability.execution_preparation.finite_multistep_planner import propose
p=argparse.ArgumentParser(description=__doc__)
for name in ('public-task','expected-task-sha','finite-placements','expected-placements-sha','output'):p.add_argument('--'+name,required=True)
p.add_argument('--source-role',choices=('AINAV_IMPLEMENTED_PUBLIC_ASSET','REACH_PROPOSED_NOT_NATIVE_ASSET'),default='AINAV_IMPLEMENTED_PUBLIC_ASSET')
a=p.parse_args();forbidden=[]
def fence(event,args):
    if event=='import' and str(args[0]).split('.')[0] in ('mujoco','torch','onnxruntime'):
        forbidden.append(str(args[0]));raise RuntimeError('No native/Actor')
    if event in ('socket.connect','subprocess.Popen','socket.getaddrinfo'):
        forbidden.append(event);raise RuntimeError('No network/child')
    if event=='open' and isinstance(args[0],str) and any(x in args[0] for x in
            ('static_qualification','PRIVATE_NOMINAL','scene.json','private_terminal','/query-private-')):
        forbidden.append(args[0]);raise RuntimeError('Public source only, no existence answer/actual private pose')
sys.addaudithook(fence)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(a.public_task)==a.expected_task_sha and sha(a.finite_placements)==a.expected_placements_sha
# Explicit SHARED public experimental prior from AINav README; NOT hidden current
# body position. Envelope .45m is a fixed nominal method assumption, NOT copied
# from source's private qualification and NOT a verified tracking/safety bound.
model=PublicSceneModel(json.loads(Path(a.public_task).read_bytes()),json.loads(Path(a.finite_placements).read_bytes()),
                       declared_initial_reference_xy_m=(-.08,0.),nominal_envelope_radius_m=.45)
results={}
for method in ('greedy','multistep'):
    state=model.initial;history=[];nonforced_reconstruction_choices=0
    for decision in range(12):
        out=propose(state,arcs=model.arcs,is_goal=model.is_goal,state_key=model.key,
                    method=method,cost_unit='m_nominal_NAV_route_plus_box_translation',
                    max_depth=4,max_transitions=256,max_wall_s=.25)
        available=tuple(model.arcs(state))
        if len(available)>1 and out['action'] is not None and out['action'].kind=='PUSH_WITH_NAV_ROUTE':
            nonforced_reconstruction_choices+=1
        action=out['action'];history.append(dict(decision_index=decision,public_nominal_state=dataclasses.asdict(state),
            proposed_action=None if action is None else dataclasses.asdict(action),
            status=out['status'],common_nominal_candidate_count=len(available),examined_transitions=out['examined_transitions'],planner_wall_s=out['planner_wall_s'],
            fallback_to_shared_greedy=out['fallback_to_shared_greedy'],native_execution_authorized=False))
        if action is None:break
        matches=[arc for arc in model.arcs(state) if arc.action==action];assert len(matches)==1
        state=matches[0].next_state  # COUNTERFACTUAL DIAGNOSTIC ONLY, never an actual observation update.
        if model.is_goal(state):break
    results[method]=dict(nominal_goal_reached=model.is_goal(state),decision_bundles=len(history),history=history,
        actual_task_success=None,physical_calls=0,not_live_method_execution=True,
        nonforced_nominal_reconstruction_choices=nonforced_reconstruction_choices)
assert sha(a.public_task)==a.expected_task_sha and sha(a.finite_placements)==a.expected_placements_sha and not forbidden
out=dict(at=dt.datetime.now().astimezone().isoformat(),role='PUBLIC_MODEL_DIAGNOSTIC_NOT_NATIVE_AB',source_role=a.source_role,
    source_pins={str(Path(a.public_task).resolve()):a.expected_task_sha,str(Path(a.finite_placements).resolve()):a.expected_placements_sha},
    common_model_nominal_radius_m=.45,common_initial_declared_reference_xy_m=[-.08,0.],model_inputs_exclude_private_existence_witness=True,
    nominal_states_not_actual_world_updates=True,actual_native_scene_qualification=False,actual_3_meaningful_decisions_NOT_proven=True,
    native_option_mapping_NOT_qualified=True,physical_dispatches=0,videos=0,results=results,forbidden_attempts=forbidden)
with Path(a.output).open('x') as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({method:{k:v for k,v in r.items() if k!='history'}for method,r in results.items()},ensure_ascii=False))
