"""Read-only TRAIN-source audit for declared-skill model adaptations.

Code hashes are provenance, not proofs of equivalent behavior. Future phase
transitions are diagnostic labels only. No new collection or model test reads.
"""
import argparse,ast,hashlib,importlib.util,json
from collections import Counter,defaultdict
from pathlib import Path


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def code_fingerprints(text):
    tree=ast.parse(text);out={}
    def walk(body,parent=''):
        for node in body:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                name=(parent+'.' if parent else '')+node.name
                out[name]=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()
                walk(node.body,name)
    walk(tree.body)
    return out


def horizon_changes(times,labels,index,horizon):
    end=times[index]+horizon
    if end>times[-1]+1e-7:return None
    j=index+1
    while j<len(times) and times[j]<=end+1e-7:
        if labels[j]!=labels[index]:return float(times[j]-times[index])
        j+=1
    return False


def audit(manifest,decoder,output):
    manifest=Path(manifest);decoder=Path(decoder);output=Path(output);output.mkdir(exist_ok=False)
    m=json.loads(manifest.read_text())
    if not m['episodes'] or any(e['role']!='train' for e in m['episodes']):raise ValueError('TRAIN-only frozen source manifest required')
    spec=importlib.util.spec_from_file_location('_wm_pinned_main_intent_decoder',decoder);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if tuple(module.VOCAB)!=('WAIT','PUSH_A','RECOVER_A','NAV_B','PUSH_B','NAV_STEP','CLIMB_STEP','NAV_HIGH','CLIMB_HIGH','NAV_C','PUSH_C','NAV_BRIDGE','CLIMB_BRIDGE','NAV_FAR','BRAKE_FAR'):raise ValueError('Pinned task-vocabulary contract differs')
    from .integrated_course import layout
    boundaries=['NAV_STEP','NAV_BRIDGE'];totals=defaultdict(Counter);examples=defaultdict(list);contracts={};rows=[]
    control_names=('layout','configure_scene','Terrain','frame_classes','weak_flags','install','translated_finish_type','elevated_push_machine','compact_hold_command','Prefix','prepared_machine','FarBankStop','IntegratedRouter')
    for e in m['episodes']:
        root=Path(e['root']);p=json.loads((root/'protocol.json').read_text());freeze=json.loads((root/'freeze.json').read_text())
        if sha(root/'report.json')!=e['report_sha256']:raise ValueError('Frozen training report changed')
        for path,digest in e['files_sha256'].items():
            if sha(root/path)!=digest:raise ValueError('Frozen training index/closure/protocol changed')
        relative='source/mujoco_zyh/integrated_course.py';text=(root/relative).read_text()
        if sha(root/relative)!=freeze['inputs'][relative]:raise ValueError('Frozen controller source changed')
        nodes=code_fingerprints(text);selected={k:v for k,v in nodes.items() if k.split('.')[0] in control_names}
        runtime_parameters={k:p.get(k) for k in ('NAV_actor_command_frame','compact_NAV_arm_hold','CLIMB_takeover_measured_contacts','C_stop_reference','NAV_arm_stopped_speed','NAV_arrival_hold_s','NAV_arrival_speed_m_s','NAV_arrival_yaw_rate_rad_s','far_bank_stop','soft_arm_effort_margin_warning_only')}
        control_id=canonical(dict(nodes=selected,runtime_parameters=runtime_parameters));contracts[e['source_group']]=dict(revision=p['execution_revision'],code_sha256=sha(root/relative),control_AST_and_parameters_sha256=control_id,nodes=selected,runtime_parameters=runtime_parameters)
        decoder_state=module.CausalPhaseDecoder();times=[];labels=[];phases=[];case=p['integrated_case']
        for line in (root/'episode/control-boundaries.jsonl').open():
            r=json.loads(line);times.append(float(r['time_s']));labels.append(decoder_state.push(r));phases.append(r['phase'])
        source_macros={};first={}
        for i,label in enumerate(labels):
            if label not in first:first[label]=i
            totals[label]['control_ticks']+=1;totals[label]['duration_milliseconds']+=20
            key=phases[i].partition('/')[2];totals[label]['phase:'+key]+=1
        for label in sorted(set(labels)):
            goal=list(module.declared_goal(label,case,layout));phase_counts=Counter(phases[i].partition('/')[2] for i,x in enumerate(labels) if x==label)
            per_horizon={}
            for h in (.5,1.,2.):
                eligible=changed=0
                for i in range(0,len(labels),25):
                    if labels[i]!=label:continue
                    change=horizon_changes(times,labels,i,h)
                    if change is not None:eligible+=1;changed+=change is not False
                per_horizon[str(h)]=dict(query_samples=eligible,macro_changes_within_horizon=changed)
            source_macros[label]=dict(declared_goal_world_xyz=goal,coarse_public_control_phases=dict(phase_counts),future_transition_labels_only=per_horizon)
            if label in boundaries:
                i=first[label];examples[label].append(dict(source_group=e['source_group'],control_contract_id=control_id,declared_goal_world_xyz=goal,first_macro_time_s=times[i],macro_change_within_2s=horizon_changes(times,labels,i,2.)))
        rows.append(dict(source_group=e['source_group'],root=str(root),role='train',control_boundaries_sha256=sha(root/'episode/control-boundaries.jsonl'),
            controller_freeze_sha256=sha(root/'freeze.json'),execution_revision=p['execution_revision'],source_control_contract_id=control_id,macros=source_macros))
    comparisons=[]
    ids=list(contracts)
    for a,b in zip(ids,ids[1:]):
        x,y=contracts[a],contracts[b];keys=set(x['nodes'])|set(y['nodes'])
        changed=[k for k in sorted(keys) if x['nodes'].get(k)!=y['nodes'].get(k)]
        # Parent hash changes include their nested definitions: names are evidence,
        # not an additive count of distinct control changes.
        comparisons.append(dict(from_source=a,to_source=b,changed_AST_scopes=changed,changed_runtime_parameters=[k for k in x['runtime_parameters'] if x['runtime_parameters'][k]!=y['runtime_parameters'][k]],
            raw_file_equal=x['code_sha256']==y['code_sha256'],selected_control_AST_and_parameters_equal=x['control_AST_and_parameters_sha256']==y['control_AST_and_parameters_sha256']))
    coverage={}
    for label,items in examples.items():
        points=sorted({tuple(x['declared_goal_world_xyz']) for x in items})
        coverage[label]=dict(unique_recorded_declared_goals=[list(x) for x in points],number_of_episodes=len(items),
            first_boundary_macro_changes_within_2s=sum(x['macro_change_within_2s'] is not False and x['macro_change_within_2s'] is not None for x in items),examples=items)
    result=dict(schema='integrated-train-macro-source-contract-audit-v1',manifest_sha256=sha(manifest),decoder_path=str(decoder),decoder_sha256=sha(decoder),decoder_action_schema_sha256=module.SCHEMA_SHA256,
        source_count=len(rows),raw_code_contracts=len({c['code_sha256'] for c in contracts.values()}),selected_control_AST_contracts=len({c['control_AST_and_parameters_sha256'] for c in contracts.values()}),
        controller_contracts=contracts,adjacent_source_comparisons=comparisons,action_support=coverage,sources=rows,
        test_or_validation_sources_read=False,physics_steps_started=0,model_updates=0,old_roles_or_files_modified=False,
        limitations=['Static source hashes do not prove physical equivalence.','Coarse phase logs do not expose all native PUSH Finish or CLIMB stop-controller latent state.',
        'A parameter absent from recorded goals has no direct same-parameter outcome support; this does not prove it is physically unsafe.',
        'Future phase transitions are retrospective labels, never online inputs.','Source contract fingerprint must not encode private materials as online observations.'])
    with (output/'macro-source-audit.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(dict(source_count=len(rows),raw_code_contracts=result['raw_code_contracts'],selected_control_AST_contracts=result['selected_control_AST_contracts'],
        action_support={k:{key:v[key] for key in ('unique_recorded_declared_goals','first_boundary_macro_changes_within_2s')} for k,v in coverage.items()},output=str(output/'macro-source-audit.json'),sha256=sha(output/'macro-source-audit.json'))),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('manifest','decoder','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();audit(a.manifest,a.decoder,a.output)
