#!/usr/bin/env python3
"""Independent data-layout adapter for fcf13 delivery. Does NOT execute producer code.
Uses reviewer checker primitives for original masks, typed inputs/return,9gate logic
and attribution; reads npz with allow_pickle=False. No Torch/FK/planner/SDK/GPU.
"""
import sys
sys.dont_write_bytecode=True
import argparse,ast,hashlib,json
from pathlib import Path
from datetime import datetime
try:
    import numpy as np
except ImportError as exc:
    raise SystemExit('Missing NumPy: use an existing isolated environment; no replay was started.') from exc
import replay_checker as c
from evidence_paths import MODULE_DIR, add_evidence_arguments

D = OUT = None
EXPECTED='fcf13d3081ed837de14cd778aa9b3ed092c4079f625f72ce419b24fffb2355a8'
PNAMES=('body_path_gap','support_path_margin','support_path_IK','leg_path_gap','full_swing_margin','full_swing_IK','full_swing_gap','four_load_min','four_load_residual')

def eq(a,b,message):c.need(np.array_equal(a,b),message)
def typed_np(a):
    c.need(a.dtype in (np.dtype('float32'),np.dtype('int64'),np.dtype('bool')),'Unexpected artifact array dtype')
    return c.typed(a.tolist(),str(a.dtype),list(a.shape))
def mask_np(a):
    c.need(a.dtype==np.bool_,'Boolean array dtype required')
    return c.bool_payload(a.reshape(-1).tolist(),list(a.shape))
def group(a,key):return np.concatenate([a[f'detail_{key.format(i=i)}'] for i in range(11)],axis=1)[0]

def audit(args):
    global D, OUT
    roots=c.configure(args)
    D=args.candidate.resolve()
    c.need(args.manifest_sha256==EXPECTED,'This adapter is pinned to the accepted fcf13 artifact layout')
    c.need(D.is_dir(),'Missing diagnostic candidate directory')
    OUT=roots.new_output(args.output_dir,D)
    OUT.mkdir(exist_ok=False)
    c.need(c.sha(D/'diagnostic-manifest.json')==EXPECTED,'Final diagnostic manifest mismatch')
    manifest=c.load_json(D/'diagnostic-manifest.json');verified={}
    for name,digest in manifest['files_sha256'].items():
        path=(D/name).resolve();c.need(path.is_relative_to(D),'Artifact path escapes candidate')
        c.need(path.stat().st_size<128*1024*1024,'Unbounded diagnostic artifact')
        c.need(c.sha(path)==digest,'Artifact hash mismatch '+name);verified[name]=digest
    oracle,contract=c.read_contract_and_oracle()
    c.need(c.ORACLE_HASH==contract['oracle_sha256'],'Reviewer original oracle changed')
    c.verify_original_bindings(oracle)
    native=c.load_json(D/'cpu_replay_01/native-call-input.json');returned=c.load_json(D/'cpu_replay_01/native-return.json')
    events=c.ROOTS.original_path('events')
    c.need(c.same(native,c.read_line(events,oracle['original_enter_ref'])),'Not exact original input event')
    c.need(c.same(returned,c.read_line(events,oracle['original_return_ref'])),'Not exact original return event')
    c.need(c.same(c.flatten_inputs(native['inputs']),oracle['original_input_schema']),'Original typed input reconstruction changed')
    for key,value in c.IDENTITY.items():c.need(native[key]==value and returned[key]==value,'Wrong call identity '+key)
    suff=c.load_json(D/'cpu_replay_01/input-sufficiency.json');deps=c.load_json(D/'cpu_replay_01/dependency-manifest.json')
    match=c.load_json(D/'cpu_replay_01/replay-match.json');dec=c.load_json(D/'cpu_replay_01/gate-decomposition.json')
    loc=c.load_json(D/'cpu_decomposition_02/localization-and-next-state.json')
    c.need(suff['device']=='cpu' and suff['runtime']['replay_device']=='cpu','Replay not CPU')
    c.need(suff['runtime']['torch']=='2.7.0+cpu' and suff['runtime']['torch_threads']==1 and suff['runtime']['default_dtype']=='torch.float32','Numeric execution context mismatch')
    for key in ('new_physical_sources','environment_starts','physics_steps','actor_forwards'):c.need(suff[key]==0,'Nonzero execution scope '+key)
    c.need(suff['missing_inputs']==[] and len(suff['unverified_metadata'])>0,'Missing dependency/undisclosed native dtype limitation')
    meta={m['path'].replace('.','/'):m for m in suff['input_tensor_metadata']}
    expected_tensors={k:v for k,v in oracle['original_input_schema'].items() if v['shape']}
    c.need(set(meta)==set(expected_tensors),'Tensor metadata coverage mismatch')
    for k,t in expected_tensors.items():
        m=meta[k];c.need(m['shape']==t['shape'] and m['dtype']=='torch.'+t['dtype'] and m['device']=='cpu' and m['json_roundtrip_exact'] is True,'dtype/device materialization mismatch '+k)
    c.need(c.same(c.load_json(D/'cpu_replay_01/native-frame.json'),oracle['frame']),'Wrong actual frame')
    frozen=c.load_json(c.CONTROL/'package-manifest.json')['files_sha256']
    bound={}
    for rel,expected in oracle['dependencies'].items():
        path=c.CONTROL/rel;c.need(c.sha(path)==expected['sha256']==frozen[rel],'Original dependency changed '+rel)
        if rel!='frozen-math-sha256.json':c.need(suff['source_dependencies'][rel]==expected['sha256'],'Dependency not in imported/AST-source inventory '+rel)
        bound[rel]=expected['sha256']
    for rel,digest in deps['source_sha256'].items():c.need(c.sha(c.CONTROL/rel)==digest==frozen[rel],'Bad actual module binding '+rel)
    for layer in suff['USD_layers']:
        path=(c.CONTROL/layer['relative_path']).resolve();c.need(path.is_relative_to(c.CONTROL),'Unbound external USD layer')
        c.need(c.sha(path)==layer['sha256']==frozen[layer['relative_path']],'Asset layer mismatch')
    geometry_path=c.CONTROL/'actual-usd-and-config-geometry.json'
    c.need(c.sha(geometry_path)==frozen['actual-usd-and-config-geometry.json'],'Geometry lineage receipt changed')
    geometry=c.load_json(geometry_path)
    c.need(c.same(suff['model_geometry'],geometry['kinematics_geometry']),'Different model geometry')
    c.need(c.same(native['inputs']['link_bounds'],geometry['leg_primitives']),'Logged primitive geometry mismatch')
    c.need(c.same(native['inputs']['body_bounds'],geometry['body_bounds']),'Body geometry mismatch')
    c.need(suff['USD_layers'][0].get('sha256') or len(suff['USD_layers'])>0,'No source layers')
    c.need(any(l['sha256']==geometry['USD_sha256'] for l in suff['USD_layers']),'Top model USD not tied to lineage')
    for item in suff['model_geometry'].values():c.tensor_check(c.typed(item,'float32'))
    c.need(deps['script_sha256']==c.sha(D/'replay_joint_gate.py'),'Replay code not bound')
    c.need(match['full_original_callee_invocations']==match['actual_return_hook_invocations']==1,'Replay called original more/less than once')
    c.need(match['profile_counts']==dict(support_load=1,support_path=11,leg_path=11,swing=11,four_load=11),'Missing actual five return observers')
    for t,o in zip(match['replay_return'],oracle['original_return']):c.tensor_check(c.typed(t),o)
    c.need(len(match['replay_return'])==4 and c.same(match['native_return'],returned['result']),'Return mismatch')
    with np.load(D/'cpu_replay_01/replay-arrays.npz',allow_pickle=False) as data,\
         np.load(D/'cpu_replay_01/gate-components.npz',allow_pickle=False) as comp,\
         np.load(D/'cpu_decomposition_02/independent-cumulative-and-localization.npz',allow_pickle=False) as post:
        # Validate all arrays' numerical dtypes; no opaque pickled objects or nonfinite masks/metrics.
        for archive in (data,comp,post):
            for key in archive.files:
                v=archive[key];c.need(v.dtype.kind in 'bifu' and np.isfinite(v).all(),'Nonfinite/object archive array '+key)
        c.need(data['initial_samples'].shape==(32768,5) and data['initial_samples'].dtype==np.float32,'Sampler dtype/count mismatch')
        c.need(data['initial_positions'].shape==(1,32768,3) and data['initial_rotations'].shape==(1,32768,4),'Candidate geometry shape mismatch')
        eq(data['initial_positions'],np.asarray(native['inputs']['origin'],dtype=np.float32)[:,None]+(data['initial_samples'][None,:,:3]-np.float32(.5))*np.float32(.16),'Sample->position arithmetic changed')
        original_masks=[oracle['initial']]+oracle['chunks'];mask_matches=[]
        for i,original in enumerate(original_masks):
            observed=data[f'mask_{i:02d}'];c.decode_mask(mask_np(observed),original['payload'])
            mask_matches.append(dict(index=i,shape=list(observed.shape),true_count=int(observed.sum()),sha256=hashlib.sha256(observed.tobytes()).hexdigest()))
        ids=np.flatnonzero(data['mask_00'][0]);eq(ids,np.array(oracle['ordered_initial_survivor_indices'],dtype=np.int64),'Original666 index order mismatch')
        eq(data['initial_ordered_indices'],ids,'Saved actual where() index order mismatch')
        eq(comp['original_candidate_indices'],ids,'Component candidate domain changed')
        eq(post['candidate_indices'],ids,'Postprocessing candidate domain changed')
        gate_arrays={g['id']:[] for g in c.GATES};collected_metrics={g['metric']:[] for g in c.GATES}
        for j,original in enumerate(oracle['chunks']):
            idx=data[f'chunk_{j:02d}_ids'];eq(idx,np.array(original['indices'],dtype=np.int64),'Chunk order/indices mismatch')
            eq(data[f'chunk_{j:02d}_p'],data['initial_positions'][:,idx],'Chunk candidate position substituted')
            eq(data[f'chunk_{j:02d}_rotation'],data['initial_rotations'][:,idx],'Chunk candidate orientation substituted')
            prefix=f'chunk_{j:02d}_';ready=data[prefix+'ready'];eq(ready,data[f'mask_{j+1:02d}'],'Joint local/hook mask differs')
            chunk=dict(ordinal=j+1,row=0,original_candidate_indices=idx.tolist(),ready=mask_np(ready),metrics={},gate_masks={},signed_slacks={})
            begin=sum(len(z['indices']) for z in oracle['chunks'][:j]);end=begin+len(idx)
            for name,g in zip(PNAMES,c.GATES):
                metric=data[prefix+g['metric']];expected=comp['value_'+g['metric']][begin:end].reshape(1,-1)
                eq(metric,expected,'Copied numeric component differs from actual-call local '+g['metric'])
                chunk['metrics'][g['metric']]=typed_np(metric)
                chunk['gate_masks'][g['id']]=mask_np(comp['pass_'+name][begin:end].reshape(1,-1))
                chunk['signed_slacks'][g['id']]=typed_np(comp['slack_'+name][begin:end].reshape(1,-1))
                collected_metrics[g['metric']].extend(metric.reshape(-1).tolist())
            checked=c.check_chunk(chunk,original)
            for k,values in checked.items():gate_arrays[k].extend(values)
            path_valid=np.logical_and.reduce([np.frombuffer(checked[g['id']],dtype=np.uint8).astype(bool) for g in c.GATES[:4]])
            eq(path_valid,data[prefix+'path_valid'].reshape(-1),'Path conjunction changed')
        attribution=c.statistic(gate_arrays)
        for row,pr,name in zip(attribution['rows'],dec['table'],PNAMES):
            c.need(pr['gate']==name and pr['independent_fail']==row['independent_rejected'] and pr['independent_pass']==666-row['independent_rejected'] and pr['only_this_gate_fails']==row['exclusive_rejected'] and pr['newly_excluded_in_display_order']==row['first_excluded_in_declared_order'] and pr['cumulative_pass']==row['cumulative_survivors'],'Wrong independent/exclusive/cumulative statistic')
        c.need(list(dec['ordered_gate_names'])==list(PNAMES),'Producer display order changed')
        cumulative=np.ones(666,dtype=bool)
        for g,name in zip(c.GATES,PNAMES):
            bits=np.array(gate_arrays[g['id']],dtype=bool);eq(bits,post['independent_'+name],'Post independent mask wrong');cumulative &= bits
            eq(cumulative,post['cumulative_'+name],'Post cumulative mask wrong')
        # Check exact logged initial6-way conjunction from saved original intermediates only.
        initial_metrics=['margin','error','angle','tripod'];c.need(all(data['initial_'+k].dtype==np.float32 for k in initial_metrics),'Initial precision changed')
        delta=data['initial_positions']-np.asarray(native['inputs']['origin'],dtype=np.float32)[:,None]
        first=[data['initial_margin']>=np.float32(.03),data['initial_error']<np.float32(.001),data['initial_angle']<=np.float32(.35),
            np.sqrt(np.sum(delta[...,:2]**2,axis=-1,dtype=np.float32))<=np.float32(.08),np.abs(delta[...,2])<=np.float32(.08),data['initial_tripod']>=np.float32(.025)]
        eq(np.logical_and.reduce(first),data['mask_00'],'Initial six saved terms do not recompose')
        initial_counts=[];current=np.ones_like(first[0])
        for b,row in zip(first,loc['initial_table']):
            previous=current.copy();current &= b
            c.need(int(b.sum())==row['independent_pass'] and int(current.sum())==row['cumulative_pass'] and int((previous & ~b).sum())==row['newly_excluded_display_order'],'Initial attribution wrong')
            initial_counts.append(dict(gate=row['gate'],independent_pass=int(b.sum()),cumulative_pass=int(current.sum())))
        # Validate read-only saved return profiling/localization, no new geometric computation.
        paths=group(data,'leg_path_{i:02d}_gap');c.need(paths.shape==(666,21,4,3),'Path detail axes changed')
        mins=paths.min(axis=(1,2,3));eq(mins,comp['value_legs_gap'],'Per-phase/link gaps do not reduce to original scalar')
        argmin=np.array([np.unravel_index(int(p.argmin()),p.shape) for p in paths],dtype=np.int64)
        eq(argmin,post['path_argmin_phase_leg_link'],'Localization not actual argmin')
        per_link=paths.min(axis=1);eq(per_link,post['path_per_leg_link_min'],'Per-link reduction wrong')
        start=paths[:,0].min(axis=(1,2));end=paths[:,-1].min(axis=(1,2))
        eq(start,post['path_initial_min'],'Start-gap reduction wrong');eq(end,post['path_endpoint_min'],'Endpoint-gap reduction wrong')
        selected=native['inputs']['swing_preview']['leg'][0];c.need(selected==3,'Not original RR swing')
        nominal=group(data,'swing_{i:02d}_nominal')[:,:,selected];loaded=group(data,'swing_{i:02d}_loaded')[:,:,selected]
        reload=group(data,'swing_{i:02d}_reload_margin');pre=np.minimum(nominal,loaded).min(axis=1)
        eq(np.minimum(pre,reload),comp['value_sm'],'Original swing margin components/reload do not recompose')
        eq(nominal,post['swing_selected_nominal_phase_margin'],'Selected nominal margin changed')
        eq(loaded,post['swing_selected_loaded_phase_margin'],'Selected loaded margin changed')
        eq(reload,post['swing_reload_margin'],'Reload margin changed')
        # Reported failure combinations must be actual simultaneous failures, not independent counts added.
        patterns={}
        for i,idx in enumerate(ids):
            failed=[name for name,g in zip(PNAMES,c.GATES) if not gate_arrays[g['id']][i]]
            key=' & '.join(failed) or 'ALL_PASS';patterns.setdefault(key,[]).append(int(idx))
        c.need(c.same(dec['failure_combinations'],{k:dict(count=len(v),candidate_indices=v) for k,v in patterns.items()}),'Failure overlap combinations wrong')
        gd={g['id']:np.array(gate_arrays[g['id']],dtype=bool) for g in c.GATES}
        swing=gd['swing_primitive_gap'];swingmargin=gd['swing_loaded_joint_margin']
        all_except_leg=np.logical_and.reduce([v for k,v in gd.items() if k!='leg_path_gap'])
        c.need(int(gd['leg_path_gap'].sum())==0 and int(swing.sum())==2 and int(swingmargin.sum())==603 and int((swing&swingmargin).sum())==0 and not all_except_leg.any(),'Claimed two independently empty groups not supported')
        c.need(int((per_link[:,0,2]<np.float32(.005)).sum())==666,'FL calf does not fail all666')
        examples=[]
        for candidate in [2870,6022,32486]:
            i=int(np.flatnonzero(ids==candidate)[0]);phase,leg,link=argmin[i]
            calculated=dict(candidate_index=candidate,order_in_666=i,path_gap_m=float(mins[i]),worst_phase_sample=int(phase),
                fraction=float(phase/20),worst_leg=int(leg),worst_link=int(link),initial_gap_m=float(start[i]),endpoint_gap_m=float(end[i]),
                swing_gap_m=float(comp['value_sg'][i]),swing_margin=float(comp['value_sm'][i]),
                swing_nominal_min=float(nominal[i].min()),swing_nominal_worst_sample=int(nominal[i].argmin()),
                swing_loaded_min=float(loaded[i].min()),swing_loaded_worst_sample=int(loaded[i].argmin()),reload_margin=float(reload[i]))
            producer=next(e for e in loc['candidate_examples'] if e['candidate_index']==candidate)
            c.need(producer['support_path_worst']['sample']==int(phase) and producer['support_path_worst']['gap_m']==calculated['path_gap_m'],'Example path localization wrong')
            for name,key in [('swing_nominal_min','swing_nominal_min'),('swing_nominal_worst_sample','swing_nominal_worst_sample'),('swing_gravity_loaded_min','swing_loaded_min'),('swing_gravity_loaded_worst_sample','swing_loaded_worst_sample'),('reload_margin','reload_margin')]:
                c.need(producer[name]==calculated[key],'Example swing component localization wrong '+name)
            examples.append(calculated)
        numeric=dict(independent_pass={g['id']:int(gd[g['id']].sum()) for g in c.GATES},
            cumulative=attribution,initial_six=initial_counts,
            full_swing_gap_pass_indices=ids[swing].tolist(),full_swing_gap_margin_intersection=int((swing&swingmargin).sum()),
            all_other_gates_pass_if_leg_removed=int(all_except_leg.sum()),FL_calf_path_fail_count=666,
            best_full_path_gap_m=float(mins.max()),start_min_range_m=[float(start.min()),float(start.max())],
            examples=examples,reported_failure_combinations_checked=True)
    # Explicit source instrumentation constraints, plus human review recorded separately in receipt.
    replay_source=(D/'replay_joint_gate.py').read_text();tree=ast.parse(replay_source)
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and ast.unparse(n.func)=='m.expanded_ground_support_pose']
    c.need(len(calls)==1,'More than one source-level original expanded invocation')
    for expected in ['sys.setprofile(profiler)','geometry_frame_context(math_frame)','value.detach().cpu().numpy().copy()',
                     'hook.expanded_enter=enter;hook.expanded_return=returned_hook;hook.mask_record=mask_hook',
                     'sys.setprofile(None);hook.expanded_enter,hook.expanded_return,hook.mask_record=original_hooks']:
        c.need(expected in replay_source,'Replay instrumentation structure changed')
    # Preserve failed postprocessing history; its changed calculation does not rerun replay.
    c.need((D/'analyze_gate_arrays_initial_failed.py').exists() and 'AssertionError' in (D/'cpu_decomposition_01.log').read_text(),'Original postprocess failure disappeared')
    c.need(c.sha(D/'diagnostic-manifest.json')==EXPECTED,'Manifest changed during independent review')
    for n,dig in verified.items():c.need(c.sha(D/n)==dig,'Diagnostic artifact changed during independent review '+n)
    c.verify_original_bindings(oracle)
    report=dict(schema='verification-capture32-delivered-NPZ-audit-v1',at=datetime.now().astimezone().isoformat(),
      status='EXACT_ARTIFACT_AND_SOURCE_DEPENDENCY_CHECKS_PASS',diagnostic_manifest_sha256=EXPECTED,
      checker_sha256=c.sha(MODULE_DIR/'replay_checker.py'),adapter_sha256=c.sha(__file__),
      schema_adaptation='Producer NPZ and5return-profile schema inspected directly; no invented33individual-call trace or generic checker PASS. Shared checker original-data/typed-input/mask/gate/slack/attribution primitives used.',
      original_identity=c.IDENTITY,original_inputs=41,original_input_tensor_metadata_count=len(meta),
      mask_matches=mask_matches,ordered_ids_exact=True,chunk_count=11,original_complete_return_exact=True,
      numeric_results=numeric,source_dependency_hashes=bound,asset_layer_hashes=suff['USD_layers'],
      model_geometry_lineage=dict(receipt=str(geometry_path),sha256=c.sha(geometry_path),geometry_equal=True,
        receipt_is_inherited_v010_asset_evidence_not_new_native_model_snapshot=True,
        producer_reextracted_current_same_hash_USD=True,USD_link_body_geometry_match_actual_original_inputs=True),
      actual_observed_return_profile_counts=match['profile_counts'],transitive_coverage='Bound unmodified original computation source + actual5return observers; lower function execution dependency inferred from that source, not independently profiled33counts.',
      producer_runtime=suff['runtime'],numeric_limit=suff['unverified_metadata'],
      original_callee_recorded_invocations=1,independent_new_replay_FK_IK_runs=0,
      independent_array_operations='Thresholds,AND,stats,existing-array norms/min/argmin only; no candidate generation/model/load/geometry evaluation',
      failed_postprocess_retained=True,developer_tests_executed=False,
      original_and_candidate_artifacts_unchanged=True,physical_steps=0,SDK_runs=0,GPU_calls=0,
      artifact_sha256=verified)
    c.write_new(OUT/'result.json',report)
    print(json.dumps({k:report[k] for k in ('status','diagnostic_manifest_sha256','schema_adaptation','original_inputs','original_input_tensor_metadata_count','ordered_ids_exact','chunk_count','original_complete_return_exact','actual_observed_return_profile_counts','independent_new_replay_FK_IK_runs')},ensure_ascii=False,indent=2))
    print(json.dumps(numeric,ensure_ascii=False,indent=2))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    add_evidence_arguments(parser)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    try:
        audit(args)
        return 0
    except (OSError,ValueError,KeyError,AssertionError) as exc:
        print(json.dumps(dict(status='NOT_ACCEPTED_OR_MISSING_DEPENDENCY',error=str(exc),replay_executed=False)))
        return 2

if __name__=='__main__':raise SystemExit(main())
