"""Exact semantic completion check over the EXISTING native journal.
No receipt generation, no skill/guard override, no extra logger or world read.
Source planner itself already enforces matching typed NativeReceipt on observe.
"""
def need(ok,msg):
    if not ok:raise ValueError(msg)

def verify_completed_requests(planner,expected,events):
    need(len(expected)==3 and [r['skill'] for r in expected]==['NAV','PUSH','CLIMB'],'Exact three semantic requests, not preparations')
    need(list(planner.requests)==expected and planner.complete and planner.index==3 and planner.pending is None,'Exact declared requests and completed index3/no pending')
    requests=[(i,e) for i,e in enumerate(events) if e.get('event')=='explicit_engineering_intent_requested']
    results=[(i,e) for i,e in enumerate(events) if e.get('event')=='engineering_intent_actual_result']
    outcomes=[(i,e) for i,e in enumerate(events) if e.get('event')=='intent_actual_native_outcome' and e.get('execution_role')=='interaction']
    need(len(requests)==len(results)==len(outcomes)==3,'Exactly three real semantic native outcomes, no omitted NAV or extra interaction')
    need(not any(e.get('event')=='engineering_intent_rejected' for e in events),'Rejected semantic request cannot be successful task')
    rows=[];last_result=-1
    for index,((ri,request),(oi,outcome),(ei,result),declared) in enumerate(zip(requests,outcomes,results,expected)):
        need(last_result<ri<oi<ei,'Strict original intent/outcome/observation order')
        need(request['request_index']==index and request['request']==declared,'Exact request order/parameters')
        intent=request['intent_sha256'];option=result['native_option_sha256'];receipt=outcome['receipt']
        need(intent==outcome['intent_sha256']==result['intent_sha256'],'Same semantic intent across native result')
        need(option==outcome['native_option_sha256']==receipt['option_sha256'],'Same issued option and actual native receipt')
        need(receipt['status']==result['actual_status']=='succeeded' and outcome['intent_succeeded'] is True,'All three actual native interactions must succeed')
        need(bool(receipt['evidence_ref']) and receipt['evidence_ref']==result['receipt_ref'] and bool(result['binding_ref']),'Original receipt/binding evidence references')
        rows.append(dict(request_index=index,request=declared,intent_sha256=intent,native_option_sha256=option,receipt_ref=result['receipt_ref'],binding_ref=result['binding_ref'],status='succeeded'))
        last_result=ei
    need(len({r['intent_sha256'] for r in rows})==3 and len({r['native_option_sha256'] for r in rows})==3,'No duplicate intent/option reuse')
    return dict(exact_requested_semantic_success_count=3,preparation_receipts_not_counted=True,requests=rows)
