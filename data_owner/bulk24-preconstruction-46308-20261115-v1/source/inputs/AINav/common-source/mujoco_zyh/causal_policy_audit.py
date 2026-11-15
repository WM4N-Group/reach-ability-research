from pathlib import Path
import hashlib,json

def audit(root,report):
    root=Path(root);p=json.loads((root/'protocol.json').read_text());q=root/'causal-model-rpc';errors=[]
    def check(v,s):
        if not v:errors.append(s)
    def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    if not all(x.exists() for x in [root/'causal-model-decisions.jsonl',q/'request.json',q/'response.json']):
        return {'passed':False,'errors':['model/native decision incomplete; no success inferred'],'nontrivial_model_parameter_choices':0}
    rows=[json.loads(x) for x in (root/'causal-model-decisions.jsonl').read_text().splitlines()]
    accepted=[x for x in rows if x['event']=='model_selected_NAV_STEP_native_accepted']
    check(len(accepted)==1,'exactly one real model/native parameter choice required')
    request=json.loads((q/'request.json').read_text());response=json.loads((q/'response.json').read_text())
    check(response['request_sha256']==sha(q/'request.json') and response['context_sha256']==sha(q/'observed-context.npz'),'actual request/observation SHA differs')
    check(response['source_id']==p['source_id'] and response['episode_id']==p['episode_id'],'response episode binding differs')
    for row in accepted:
        check(row['actual_tasks'][1:]==row['nominal_tasks'][1:],'nonfirst tasks changed')
        check(abs(row['actual_tasks'][0]['goal'][0]-(row['nominal_tasks'][0]['goal'][0]+response['selected_dx_m']))<1e-12,'native goal not selected model payload')
    native=[json.loads(x) for x in (root/'integrated-stage-events.jsonl').read_text().splitlines()]
    starts=[x for x in native if x['event']=='integrated_owner_changed'];check(len(starts)==2,'original two task chunks required')
    if starts and accepted:check(starts[0]['tasks']==accepted[0]['actual_tasks'],'selected task not consumed by native constructor')
    check(report['WM_control']==1 and report['WM_forwards']==response['model_forecasts'],'true inference accounting differs')
    return {'passed':not errors,'errors':errors,'nontrivial_model_parameter_choices':len(accepted),'model_forecasts':response['model_forecasts'],
            'autonomous_object_or_task_graph_selection':False,'full_task_success_not_inferred_here':True}
