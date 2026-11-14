#!/usr/bin/env python3
"""Explicit external requests exercise the REAL entry judge; NOT a model test.

Runs the same frozen physical harness. No API/backend/fixture motor control;
requests are only task intents. Native child actions and failures stay real.
"""
import argparse,hashlib,json,os,sys
from pathlib import Path


class RequestedIntentPlanner:
    decision_source='engineering_requests_NOT_model'
    def __init__(self,requests,journal,*,max_requests=2):
        self.requests=tuple(requests);self.journal=journal;self.index=0;self.pending=None
        if type(max_requests) is not int or max_requests not in (2,3):raise ValueError('Explicit bounded request capacity 2 or 3 required')
        if not 1<=len(self.requests)<=max_requests:raise ValueError('One/two explicit bounded engineering requests required' if max_requests==2 else 'One/two/three explicit bounded engineering requests required')
        from ainav.contracts import Primitive
        for request in self.requests:
            if set(request)!={'skill','target_ref','parameters'}:raise ValueError('Explicit task intent fields only')
            Primitive(request['skill'],request['target_ref'],tuple(sorted(request['parameters'].items())))
    @property
    def complete(self):return self.index==len(self.requests)
    def select(self,batch):
        from ainav.intents import IntentBatch
        from ainav.contracts import Primitive
        from ainav.planner import Selection
        if not isinstance(batch,IntentBatch) or self.pending is not None or self.complete:raise ValueError('Fresh engineering intent batch required')
        req=self.requests[self.index]
        matches=[i for i in batch.options if i.skill==req['skill'] and i.target_ref==req['target_ref'] and dict(i.parameters)==req['parameters']]
        if len(matches)!=1:raise ValueError('Requested engineering intent is not currently in semantic catalogue')
        i=matches[0];self.pending=i.sha256
        ref=self.journal(dict(event='explicit_engineering_intent_requested',request_index=self.index,request=req,
            intent_sha256=i.sha256,counts_as_model_decision=False,VLM_calls=0,physical_action_issued=False))
        return Selection(batch.sha256,i.token,i.sha256,Primitive.from_option(i).key,0,ref)
    def reject_intent(self,intent,reason,evidence_ref):
        self.journal(dict(event='engineering_intent_rejected',intent_sha256=intent.sha256,reason=reason,evidence_ref=evidence_ref,counts_as_model_decision=False))
        raise RuntimeError('Engineering entry request rejected; no fallback: '+reason)
    def observe_intent(self,intent,actual,receipt,binding_ref):
        if self.pending!=intent.sha256 or actual.skill!=intent.skill or actual.parameters!=intent.parameters or receipt.option_sha256!=actual.sha256:
            raise ValueError('Actual matching native interaction required')
        self.journal(dict(event='engineering_intent_actual_result',intent_sha256=intent.sha256,native_option_sha256=actual.sha256,
            actual_status=receipt.status,receipt_ref=receipt.evidence_ref,binding_ref=binding_ref,counts_as_model_decision=False))
        if receipt.status!='succeeded':raise RuntimeError('Engineering interaction actually '+receipt.status)
        self.index+=1;self.pending=None


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',required=True);ap.add_argument('--requests',required=True)
    ap.add_argument('--profile',default='yuanyue-5090');ap.add_argument('arguments',nargs=argparse.REMAINDER);a=ap.parse_args()
    source=Path(a.source).resolve();requests_path=Path(a.requests).resolve();requests=json.loads(requests_path.read_text())
    sys.path.insert(0,str(source))
    from ainav.deployment import profile
    from ainav.host_runner import compile_runner
    host=profile(a.profile);args=a.arguments[1:] if a.arguments[:1]==['--'] else a.arguments
    if '--root' not in args or '--gpu-lock' not in args or '--source' not in args:raise ValueError('Explicit fresh root/lock/source required')
    get=lambda k:args[args.index(k)+1]
    root=Path(get('--root')).resolve()
    if root.exists() or not root.is_relative_to(Path(host.root)/'experiments'):raise ValueError('Fresh engineering experiment root required')
    if Path(get('--source')).resolve()!=source or Path(get('--gpu-lock')).resolve()!=Path(host.lock_path).resolve():raise ValueError('Same frozen source and actual own lock required')
    for n,h in json.loads((source/'ainav-source.json').read_text())['files'].items():
        if hashlib.sha256((source/n).read_bytes()).hexdigest()!=h:raise ValueError('Frozen source changed:'+n)
    script=source/'run_full_course.py';code,receipt=compile_runner(script.read_text(),filename=str(script),host=host)
    request_sha=hashlib.sha256(requests_path.read_bytes()).hexdigest()
    receipt.update(engineering_only=True,API_calls=0,new_experiment_root=str(root),requests_sha256=request_sha,
        full_task_success_or_paper_efficacy_claimed=False,source_manifest_sha256=hashlib.sha256((source/'ainav-source.json').read_bytes()).hexdigest())
    dest=Path(host.root)/'deployment'/(root.name+'-engineering-host-launch.json')
    with dest.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    os.environ.pop('AINAV_VLM_API_KEY',None);os.environ.pop('DEEPSEEK_API_KEY',None)
    sys.argv=[str(script),*args]
    namespace=dict(__name__='explicit_engineering_entry_probe',__file__=str(script),__package__=None,_AINAV_HOST=host)
    exec(code,namespace)
    return namespace['main'](engineering_planner_factory=lambda journal:RequestedIntentPlanner(requests,journal),engineering_requests_sha256=request_sha)


if __name__=='__main__':raise SystemExit(main())
