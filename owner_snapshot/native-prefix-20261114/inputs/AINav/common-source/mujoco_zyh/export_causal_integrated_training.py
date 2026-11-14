"""Export train-only public state/causal skill arrays for task-model adaptation.

No model fit, test access, private catalog, true base/box pose, or future motor
stream. Nominal world goals are declared known task-map instructions, not actual
moving-box locations. Derived odometry is explicitly approximate and causal.
"""
import argparse,importlib.util,json
from pathlib import Path
import numpy as np
from .streams import sha,write_json
from .public_navigation_state import PublicNavigationState
from .integrated_course import layout


def export(manifest,decoder,audit_path,output):
    manifest=Path(manifest);decoder=Path(decoder);audit_path=Path(audit_path);output=Path(output);output.mkdir(exist_ok=False)
    m=json.loads(manifest.read_text());audit=json.loads(audit_path.read_text())
    if any(r['role']!='train' for r in m['episodes']) or len(m['episodes'])!=9:raise ValueError('Frozen original9 TRAIN-only source pack required')
    spec=importlib.util.spec_from_file_location('_wm_causal_intents_export',decoder);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if sha(decoder)!=audit['decoder_sha256']:raise ValueError('Decoder differs from audited causal declaration schema')
    audited={r['source_group']:r for r in audit['sources']};rows=[]
    for e in m['episodes']:
        group=e['source_group'];root=Path(e['root']);p=json.loads((root/'protocol.json').read_text())
        control_path=root/'episode/control-boundaries.jsonl';record=audited[group]
        if sha(control_path)!=record['control_boundaries_sha256'] or sha(root/'report.json')!=e['report_sha256']:raise ValueError('Frozen source controls/report changed')
        if sha(e['packed'])!=e['packed_sha256']:raise ValueError('Frozen public source pack changed')
        # Explicitly avoid loading the 'actions' member, which contains recorded
        # future motor intervals and is not this online macro-action interface.
        keys=('rgb','depth_m','depth_valid','proprio','timestamps_s','camera_K','T_base_optical')
        with np.load(e['packed'],allow_pickle=False) as z:arrays={k:z[k].copy() for k in keys}
        decoder_state=module.CausalPhaseDecoder();labels={};phases={}
        for line in control_path.open():
            r=json.loads(line);tick=int(r['control_tick']);labels[tick]=decoder_state.push(r);phases[tick]=r['phase']
        state=PublicNavigationState();odometry=[];relative=[];actions=[];ids=[];public_phases=[]
        for timestamp,proprio in zip(arrays['timestamps_s'],arrays['proprio']):
            tick=int(round(float(timestamp)/.02))
            if abs(tick*.02-timestamp)>1e-6 or tick not in labels:raise ValueError('Actual visual/current-control timestamp alignment differs')
            name=labels[tick];goal=module.declared_goal(name,p['integrated_case'],layout)
            odometry.append(state.update(timestamp,proprio));relative.append(state.goal_body_xy(goal[:2]))
            actions.append(module.encode_intent(name,goal,.6 if name.startswith('PUSH') else 0.,.1));ids.append(module.VOCAB.index(name));public_phases.append(phases[tick])
        arrays.update(observed_odometry_xy_yaw=np.asarray(odometry),declared_goal_body_xy_estimate=np.asarray(relative),
            declared_skill_parameters=np.asarray(actions,dtype=np.float32),declared_skill_id=np.asarray(ids,dtype=np.int64))
        filename=output/(group+'.npz')
        with filename.open('xb') as f:np.savez_compressed(f,**arrays)
        # Task-progress/phase strings and contract IDs are source metadata. They
        # are not silently appended to a model's image/state tensors.
        phase_file=output/(group+'-declared-phases.json');write_json(phase_file,dict(actual_public_phase_history=public_phases,source_control_contract_id=record['source_control_contract_id']))
        rows.append(dict(source_group=group,role='train',original_role=e['role'],original_pack_sha256=e['packed_sha256'],
            original_root=str(root),source_control_contract_id=record['source_control_contract_id'],path=str(filename),sha256=sha(filename),
            public_phase_metadata=str(phase_file),public_phase_sha256=sha(phase_file),frames=len(ids),arrays=sorted(arrays),
            action_schema_sha256=module.SCHEMA_SHA256,
            final_observed_odometry_estimate_only=arrays['observed_odometry_xy_yaw'][-1].tolist()))
        print('CAUSAL_TRAIN_SOURCE_EXPORTED',group,len(ids),flush=True)
    result=dict(schema='integrated-public-state-and-skill-training-export-v1',manifest_sha256=sha(manifest),macro_source_audit_sha256=sha(audit_path),
        decoder_sha256=sha(decoder),public_navigation_state_source_sha256=sha(Path(__file__).with_name('public_navigation_state.py')),
        exporter_source_sha256=sha(Path(__file__)),source_count=9,roles=['train'],frames=sum(r['frames'] for r in rows),episodes=rows,
        declared_initial_pose=dict(xy=[-.08,0.],yaw=0.,origin='Registered task-reset initialization, not measured running simulator pose'),
        body_goal_reference='Current public-proprio-integrated planar estimate; known declared static task map',
        odometry_warning='10Hz trapezoidal integration retains drift; no true-pose correction, smoothing or truth-accuracy claim',
        recorded_future_motor_stream_exported=False,private_truth_arrays_read=False,validation_or_test_data_read=False,
        normalization_fitted=False,model_trained=False,physics_steps_started=0,
        consumer_requirements=['Only observation history through the decision timestamp may be encoded.',
            'Predict using the candidate declared skill parameters, not the ground-truth next recorded skill sequence.',
            'Native controller source/mode must match the intended deployed controller; provenance hash is not a safety certificate.',
            'No direct action-outcome evidence for absent NAV_STEP .03/.07m parameters; do not silently claim coverage.',
            'Current graph still prescribes B/C identities; no autonomous target-selection benefit is implied.'])
    write_json(output/'manifest.json',result);print('CAUSAL_TRAIN_EXPORT_COMPLETE',sha(output/'manifest.json'),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('manifest','decoder','audit','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();export(a.manifest,a.decoder,a.audit,a.output)
