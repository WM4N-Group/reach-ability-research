"""Independent closed-source audit: sparse RGBD clock and all delayed motor steps.

Streaming one chunk at a time; no full-episode RGBD materialization/model forward.
This validates data integrity, not skill success or cross-engine equivalence.
"""
import argparse
from collections import deque
import json
from pathlib import Path
import numpy as np
import torch
from visual_shadow_model import INPUT_KEYS,validate_visual_input
from .streams import sha,write_json


def audit(root):
    root=Path(root);m=json.loads((root/'episode.json').read_text());c=json.loads((root/'closure.json').read_text())
    errors=[]
    def check(ok,reason):
        if not ok:errors.append(reason)
    check(m['schema']=='piper-mujoco-visual-action-stream-v2' and m['backend']=='mujoco','wrong backend/schema')
    check(m['requires_complete_intervening_action_stream_consumer'] is True and not m['v1_visual_history_loader_compatible'],'ambiguous sparse actions')
    check(c['storage_complete'],'incomplete chunk storage')
    for name,key in [('episode.json','episode_sha256'),('index.json','index_sha256'),('private-catalog.jsonl','private_catalog_sha256'),('control-boundaries.jsonl','control_boundaries_sha256')]:
        check(sha(root/name)==c[key],'changed '+name)
    index=json.loads((root/'index.json').read_text())
    control_count=0;frames=0;history=deque(maxlen=5);max_pd_error=0.;max_clip_error=0.
    visual_targets={0:np.zeros(18,dtype=np.float32)}
    run_report=root.parent/'report.json'
    report=json.loads(run_report.read_text()) if run_report.exists() else None
    delays=np.asarray(report['delay_steps'] if report else m['delay_steps'],dtype=int)
    effort=np.asarray(report['effort_limits_nm'] if report else m['effort_limits_nm'])
    for row in index['commands']:
        path=root/row['path'];check(path.resolve().is_relative_to(root/'commands'),'unsafe command path');check(sha(path)==row['sha256'],'command hash')
        with np.load(path,allow_pickle=False) as z:
            required={'issued','delayed','torque','raw_torque','q_before','dq_before','physical_tick','time_s'}
            check(set(z.files)==required,'command fields')
            for i,tick in enumerate(z['physical_tick']):
                control_count+=1;check(int(tick)==control_count,'physical command gap')
                check(abs(float(z['time_s'][i])-control_count*.005)<1e-7,'physics timestamp mismatch')
                issued=z['issued'][i];history.append(issued.copy())
                if control_count%(4*m['visual_stride_control_ticks'])==0:
                    visual_targets[control_count//4]=issued[0].astype(np.float32)
                expected=np.stack([history[max(0,len(history)-1-int(lag))][:,j] for j,lag in enumerate(delays)],axis=1)
                check(np.array_equal(z['delayed'][i],expected),'motor delay/queue continuity mismatch')
                d=z['delayed'][i]
                raw=d[2]*(d[0]-z['q_before'][i])+d[3]*(d[1]-z['dq_before'][i])+d[4]
                max_pd_error=max(max_pd_error,float(np.max(abs(raw-z['raw_torque'][i]))))
                max_clip_error=max(max_clip_error,float(np.max(abs(np.clip(raw,-effort,effort)-z['torque'][i]))))
    check(max_pd_error<1e-7,'raw motor PD mismatch');check(max_clip_error<1e-7,'torque limit mismatch')
    last_tick=-1
    for row in index['visual']:
        path=root/row['path'];check(path.resolve().is_relative_to(root/'visual'),'unsafe visual path');check(sha(path)==row['sha256'],'visual hash')
        with np.load(path,allow_pickle=False) as z:
            check(set(z.files)==set(INPUT_KEYS)|{'control_ticks'},'private truth leaked into public visual fields')
            packet={n:torch.from_numpy(z[n].copy()) for n in INPUT_KEYS};validate_visual_input(packet)
            ticks=z['control_ticks']
            check(len(ticks)==packet['rgb'].shape[1],'visual length mismatch')
            for i,tick in enumerate(ticks):
                check(int(tick)==frames*m['visual_stride_control_ticks'],'sparse visual gap/fabricated history')
                check(abs(float(packet['timestamps_s'][0,i])-int(tick)*.02)<1e-6,'visual timestamp mismatch')
                check(bool(packet['action_valid'][0,i])==(int(tick)>0),'action-valid mismatch')
                check(int(tick)*4<=control_count,'visual has no complete actual action prefix')
                check(int(tick) in visual_targets and np.array_equal(packet['actions_previous'][0,i].numpy(),visual_targets.get(int(tick))),
                    'visual last-issued target differs from actual motor stream')
                frames+=1;last_tick=int(tick)
    catalog=[json.loads(line) for line in (root/'private-catalog.jsonl').read_text().splitlines()]
    check(len(catalog)==frames,'catalog boundary count mismatch')
    check(all(row.get('model_input_allowed') is False and row.get('control_tick')==i*m['visual_stride_control_ticks'] for i,row in enumerate(catalog)), 'catalog public/stale identity')
    check(control_count==c['physical_command_steps'] and frames==c['observations'],'closure counts mismatch')
    check(c['compressed_payload_bytes']<=m['max_payload_bytes'],'byte budget exceeded')
    return dict(schema='piper-mujoco-closed-data-audit-v2',data_integrity_pass=not errors,errors=errors,
        actual_physical_command_steps=control_count,actual_visual_frames=frames,
        full_intervening_actions_checked=True,max_PD_recompute_error=max_pd_error,max_torque_clip_error=max_clip_error,
        last_visual_tick=last_tick,streaming_chunk_read=True,actor_or_WM_forwards=0,
        task_success_inferred=False,actual_task_outcome=report['caller_outcome'] if report else None)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--episode',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=audit(a.episode);write_json(a.output,r);print(json.dumps(r));raise SystemExit(0 if r['data_integrity_pass'] else 2)


if __name__=='__main__':main()
