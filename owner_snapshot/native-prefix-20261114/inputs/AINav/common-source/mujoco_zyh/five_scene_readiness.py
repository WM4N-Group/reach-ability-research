"""Read-only five-geometry engineering readiness, never a hardware certificate."""
import argparse
import hashlib
import json
from pathlib import Path

ACCEPTED=(('platform20-wide',1),('platform12-shortlane',2),('platform16-detour',5),('bridge15-wide',6),('bridge25-long',6))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def build(base,review,output):
    base=Path(base);review=Path(review);rows=[]
    for name,revision in ACCEPTED:
        root=base/f'five-easy-{name}-20261026-v{revision}'
        p=json.loads((root/'protocol.json').read_text());r=json.loads((root/'report.json').read_text())
        a=json.loads((review/(name+'-data-audit.json')).read_text())
        freeze=json.loads((root/'freeze.json').read_text())
        if any(sha(root/f)!=h for f,h in freeze['inputs'].items()):raise ValueError('Frozen source mismatch: '+name)
        if not r['task_success'] or r['error'] or not r['engineering_scene_endpoint']['passed']:raise ValueError('Scene did not pass: '+name)
        if not a['data_integrity_pass'] or a['errors']:raise ValueError('Data audit failed: '+name)
        if a['actual_physical_command_steps']!=r['physical_steps'] or a['actual_visual_frames']!=r['frames']:raise ValueError('Count mismatch')
        result_skills=[x['skill'] for x in r['native_results'] if x.get('successful')]
        if result_skills.count('push')!=1:raise ValueError('Actual native PUSH completion missing')
        if p['suite_case']['family']=='side_platform' and result_skills.count('climb')!=1:raise ValueError('Actual native CLIMB completion missing')
        if p['suite_case']['family']=='bridge':
            e=r['engineering_scene_endpoint']
            if not e['bridge_spans_both_banks'] or min(e['bridge_bank_normal_N'].values())<=.05 or e['robot_crossing_claimed']:raise ValueError('Actual bridge support absent or crossing misclaimed')
        state=root/'review-state';cl=json.loads((state/'closure.json').read_text())
        if cl['frames']!=r['frames'] or any(sha(state/c['path'])!=c['sha256'] for c in cl['chunks']):raise ValueError('Raw review-state integrity failed')
        rows.append(dict(case_id=name,root=str(root),protocol_sha256=sha(root/'protocol.json'),
            freeze_sha256=sha(root/'freeze.json'),report_sha256=sha(root/'report.json'),
            data_audit_sha256=sha(review/(name+'-data-audit.json')),case=p['suite_case'],
            sim_seconds=r['sim_seconds'],frames=r['frames'],physical_steps=r['physical_steps'],
            native_completed_skills=result_skills,endpoint=r['engineering_scene_endpoint'],
            original_angle_violation_rad=r['angle_violation_rad'],original_speed_exceeded_steps=r['speed_exceeded_physics_steps']))
    failures=[]
    for path in sorted(base.glob('five-easy-*-20261026-v*/report.json')):
        r=json.loads(path.read_text())
        if not r['task_success']:failures.append(dict(root=str(path.parent),error=r['error'],sim_seconds=r['sim_seconds'],report_sha256=sha(path)))
    d=dict(schema='five-distinct-easy-scenes-readiness-v1',all_five_passed=len(rows)==5,
        geometry_count=5,rows=rows,development_failures_retained=failures,
        scope='Three full NAV/PUSH/NAV/CLIMB fixed platforms and two actual bridge construction/stow tasks. No robot bridge crossing, A/B/C40cm completion or hardware certification claimed.',
        development_episodes_reclassified_as_training=False,new_physics_steps=0,
        total_frames=sum(r['frames'] for r in rows),total_physical_steps=sum(r['physical_steps'] for r in rows))
    with Path(output).open('x') as f:json.dump(d,f,indent=2)
    print(json.dumps(dict(all_five_passed=True,total_frames=d['total_frames'],total_physical_steps=d['total_physical_steps'],failures_retained=len(failures),output=str(output),sha256=sha(output))))
    return d

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--review',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.base,a.review,a.output)
