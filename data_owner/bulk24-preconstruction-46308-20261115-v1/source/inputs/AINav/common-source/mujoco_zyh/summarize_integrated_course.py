"""Summarize five independently accepted continuous scenarios, never partial tasks."""
import argparse,hashlib,json
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def summarize(base,roots,audits,output):
    if len(roots)!=5 or len(audits)!=5:raise ValueError('Exactly five explicit accepted roots/audits required')
    rows=[];geometries=set();cases=set()
    for root,apath in zip(map(Path,roots),map(Path,audits)):
        p=json.loads((root/'protocol.json').read_text());r=json.loads((root/'report.json').read_text());a=json.loads(apath.read_text())
        if not r['task_success'] or r['error'] or not a['passed'] or a['errors']:raise ValueError('Incomplete/failed integrated version: '+str(root))
        if a['report_sha256']!=sha(root/'report.json') or a['freeze_sha256']!=sha(root/'freeze.json'):raise ValueError('Accepted evidence changed')
        c=p['integrated_case'];key=c['case_id'];geometry={k:v for k,v in c.items() if k!='case_id'}
        if key in cases or json.dumps(geometry,sort_keys=True) in geometries:raise ValueError('Duplicate ID/geometry cannot count as another version')
        cases.add(key);geometries.add(json.dumps(geometry,sort_keys=True))
        if not a['actual_gap_crossing_samples'] or not a['full_endpoint']['passed']:raise ValueError('Actual robot crossing/loaded far-bank end required')
        rows.append(dict(case_id=key,root=str(root),protocol_sha256=sha(root/'protocol.json'),report_sha256=sha(root/'report.json'),
            independent_audit=str(apath),audit_sha256=sha(apath),geometry=c,materials=p['registered_materials'],
            execution_revision=p['execution_revision'],sim_seconds=r['sim_seconds'],frames=r['frames'],physical_steps=r['physical_steps'],
            completed_native_skills=a['native_completed_skills'],crossing_samples=len(a['actual_gap_crossing_samples']),endpoint=a['full_endpoint']))
    if cases!={f'full-{i}' for i in range(1,6)}:raise ValueError('The five registered full scenario IDs are required')
    failed=[];unlaunched=[]
    for root in sorted(Path(base).glob('integrated-course-full-*-20261026-v*')):
        if (root/'report.json').exists():
            r=json.loads((root/'report.json').read_text())
            if not r['task_success']:failed.append(dict(root=str(root),sim_seconds=r['sim_seconds'],error=r['error'],report_sha256=sha(root/'report.json')))
        elif not (root/'attempt.claim').exists():unlaunched.append(str(root))
    d=dict(schema='five-full-continuous-integrated-scenarios-v1',all_five_complete=True,count=5,
        success_contract='In EACH single continuous world: A real push-stall/recover, B selected/pushed/stowed/stepped,40cm platform, C real bridge deployment/stow, robot crosses true gap and ends loaded on far bank.',
        rows=rows,total_frames=sum(x['frames'] for x in rows),total_main_physics_steps=sum(x['physical_steps'] for x in rows),
        retained_development_failures=failed,prepared_but_unlaunched_roots=unlaunched,
        old_partial_scenarios_counted=False,actor_weights_retrained=False,WM_control=False,
        physical_steps_started_by_summary=0,independent_generalization_or_hardware_certificate_claimed=False)
    with Path(output).open('x') as f:json.dump(d,f,indent=2)
    print(json.dumps(dict(all_five_complete=True,frames=d['total_frames'],main_steps=d['total_main_physics_steps'],retained_failures=len(failed),output=str(output),sha256=sha(output))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--roots',nargs=5,required=True);p.add_argument('--audits',nargs=5,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();summarize(a.base,a.roots,a.audits,a.output)
