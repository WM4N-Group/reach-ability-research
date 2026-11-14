"""One source-level handover-cost experiment using OWN model-probe output only.

No model reload/FK/physics. Evaluates the EXACT frozen FinishController waypoint
order and time formula on three nominal source configurations, NOT task end
observations. Contrasts with a speed-only arm-entry lower bound, not a policy.
"""
import argparse,ast,hashlib,json,math,time
from pathlib import Path
from model_probe import reference_from_source,save


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def finish_constants(source):
    tree=ast.parse(source)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FinishConfig')
    result={n.target.id:ast.literal_eval(n.value) for n in cls.body if isinstance(n,ast.AnnAssign)
            and isinstance(n.target,ast.Name) and n.target.id in
            ('arm_pose','arm_speed','minimum_segment_seconds','final_segment_seconds','stance_delay','stance_seconds','stable_seconds','verify_seconds')}
    if len(result)!=8:raise ValueError('Exact FinishConfig constant set required')
    required=["self.waypoints = list(reversed(json.loads(","self.waypoints.append(list(cfg.arm_pose))",
              'minimum = cfg.final_segment_seconds if self.waypoint==len(self.waypoints)-1 else cfg.minimum_segment_seconds',
              'self.segment_duration = max(minimum,1.875*np.max(abs(goal-self.arm_start))/cfg.arm_speed)']
    if not all(part in source for part in required):raise ValueError('Native waypoint/timing semantics changed')
    return result


def segment_times(start,path,config):
    if len(start)!=6 or any(len(q)!=6 for q in path):raise ValueError('Six-joint nominal configurations required')
    q=list(start);times=[]
    for k,target in enumerate(path):
        tmin=config['final_segment_seconds'] if k==len(path)-1 else config['minimum_segment_seconds']
        times.append(max(tmin,1.875*max(abs(b-a) for a,b in zip(q,target))/config['arm_speed']))
        q=list(target)
    return times


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);args=ap.parse_args();root=args.root.resolve()
    p=json.loads((root/'protocol.json').read_text());assert str(root)==p['own_root']
    with (root/'source-analysis.claim').open('x') as f:f.write('one source-cost analysis; no model/physics run\n')
    start=time.monotonic()
    for name,digest in p['inputs'].items():
        if sha(name)!=digest:raise ValueError('Input changed '+name)
    raw=json.loads(Path(p['probe_report']).read_text());assert raw['status']=='COMPLETED_MODEL_ONLY'
    cfg=finish_constants(Path(p['finish_source']).read_text());path=list(reversed(json.loads(Path(p['approach_source']).read_text())['waypoints']))+[list(cfg['arm_pose'])]
    machine=Path(p['machine_source']).read_text()
    if "np.max(abs(p.data.qpos[p.qids[12:]]))>.12" not in machine:raise ValueError('Native arm-entry gate changed')
    rows=[]
    for item in raw['rows']:
        q=item['q_rad'];durations=segment_times(q,path,cfg)
        rows.append(dict(pose_id=item['pose_id'],native_reference_segment_s=durations,
                         nominal_native_reference_path_s=sum(durations),
                         speed_only_entry_lower_bound_s=max(max(abs(v)-.12,0.)/3. for v in q),
                         original_native_waypoint_order_preserved=True,
                         timings_exclude_real_tracking_wait_support_capture_and_main_operation=True,
                         original_static_force_witness_exists=item['nominal_force_witness_N'] is not None))
    native_order=[r['pose_id'] for r in sorted(rows,key=lambda r:r['nominal_native_reference_path_s'])]
    heuristic_order=[r['pose_id'] for r in sorted(rows,key=lambda r:r['speed_only_entry_lower_bound_s'])]
    result=dict(schema='phe-actual-source-handover-reference-cost-v1',status='COMPLETED_SOURCE_COST_ONLY',
                role='known-dev source/model nominal states; not actual PUSH terminations or independent task trials',
                constants=cfg,ordered_native_waypoints=path,rows=rows,
                native_reference_cost_order=native_order,speed_only_margin_order=heuristic_order,
                orders_differ=native_order!=heuristic_order,
                zero_assumed_repair_distance_does_not_skip_registered_native_waypoints=True,
                future_operation_cost='UNKNOWN',whole_task_gain='NOT_MEASURED',
                true_handover_envelope='UNKNOWN_missing_path_clearance_actual_tracking_and_terminal_operation_state',
                new_FK_calls=0,new_model_reads=0,new_physics_steps=0,new_actors_or_WM=0,
                online_optimizer_or_original_native_source_changed=False,wall_s=time.monotonic()-start)
    for name,digest in p['inputs'].items():
        if sha(name)!=digest:raise ValueError('Input modified '+name)
    save(root/'report.json',result);print(json.dumps(dict(status=result['status'],rows=rows,orders_differ=result['orders_differ']),indent=2))


if __name__=='__main__':main()
