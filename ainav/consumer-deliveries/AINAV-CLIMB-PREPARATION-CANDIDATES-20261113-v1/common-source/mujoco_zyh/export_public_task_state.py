"""Augment the exact frozen9-source TRAIN export with current69D public state.

Does not train or modify other windows' model adapters. Future state arrays are
supervision only; a consumer must slice context at the prediction anchor.
"""
import argparse,importlib.util,json,time
from pathlib import Path
from collections import Counter
import numpy as np
from .streams import sha,write_json
from .public_task_state import assemble_public_task_state,SCHEMA,SCHEMA_SHA256


def export(manifest,decoder,output):
    manifest=Path(manifest);decoder=Path(decoder);output=Path(output);output.mkdir(exist_ok=False)
    m=json.loads(manifest.read_text())
    if m['roles']!=['train'] or m['source_count']!=9:raise ValueError('Frozen9-source causal TRAIN export required')
    if sha(decoder)!=m['decoder_sha256']:raise ValueError('Pinned causal macro decoder changed')
    spec=importlib.util.spec_from_file_location('_task_public_state_decoder',decoder);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    write_json(output/'state-schema.json',dict(schema=SCHEMA,sha256=SCHEMA_SHA256))
    rows=[];started=time.monotonic()
    for row in m['episodes']:
        if row['role']!='train' or sha(row['path'])!=row['sha256']:raise ValueError('Train source/role/hash changed')
        root=Path(row['original_root']);boundary=root/'episode/control-boundaries.jsonl'
        closure=json.loads((root/'episode/closure.json').read_text())
        if sha(boundary)!=closure['control_boundaries_sha256']:raise ValueError('Public control history changed')
        current=None;began=None;times={};reader=module.CausalPhaseDecoder()
        for line in boundary.open():
            control=json.loads(line);macro=reader.push(control)
            if macro!=current:current=macro;began=control['time_s']
            times[int(control['control_tick'])]=(macro,float(began))
        with np.load(row['path'],allow_pickle=False) as z:
            K=z['camera_K'];mount=z['T_base_optical'];states=[];valid=[];reasons=Counter();valid_by_macro=Counter();counts=Counter()
            rgb_frames=z['rgb'];depth_frames=z['depth_m'];depth_valid=z['depth_valid'];proprio=z['proprio'];timestamps=z['timestamps_s'].copy()
            for i,stamp in enumerate(timestamps):
                tick=int(round(float(stamp)/.02));macro,macro_started=times[tick]
                rgb=rgb_frames[i];depth=np.where(depth_valid[i],depth_frames[i].astype(np.float32),np.nan)
                sample=assemble_public_task_state(rgb,depth,K,mount,proprio[i],time_s=float(stamp),declared_macro=macro,macro_declared_at_s=macro_started)
                states.append(sample['state']);valid.append(sample['geometry_valid']);counts[macro]+=1
                if sample['geometry_valid']:valid_by_macro[macro]+=1
                elif macro in SCHEMA['explicit_task_appearance_cues']:reasons[sample['geometry_missing_reason']]+=1
            values=np.asarray(states)
            if not np.array_equal(values[:,:45],proprio):raise ValueError('Public proprio was changed during state assembly')
        path=output/(row['source_group']+'-state.npz')
        with path.open('xb') as f:np.savez_compressed(f,public_task_state=values,timestamps_s=timestamps)
        record=dict(source_group=row['source_group'],role='train',original_public_source=str(row['path']),original_public_source_sha256=row['sha256'],
            state_file=str(path),state_file_sha256=sha(path),frames=len(values),source_control_contract_id=row['source_control_contract_id'],
            frames_by_current_macro=dict(counts),valid_front_frames_by_macro=dict(valid_by_macro),missing_front_reasons=dict(reasons))
        rows.append(record);print('PUBLIC_TASK_STATE_EXPORTED',row['source_group'],len(values),dict(valid_by_macro),flush=True)
    result=dict(schema='causal-public-task-state-training-export-v1',source_manifest_sha256=sha(manifest),decoder_sha256=sha(decoder),state_schema=SCHEMA,state_schema_sha256=SCHEMA_SHA256,
        state_source_sha256=sha(Path(__file__).with_name('public_task_state.py')),exporter_source_sha256=sha(Path(__file__)),
        source_count=len(rows),frames=sum(r['frames'] for r in rows),episodes=rows,wall_seconds=time.monotonic()-started,
        future_state_supervision_must_be_separate_from_context=True,normalization_fitted=False,model_trained=False,new_physics_steps=0,
        validation_or_test_read=False,private_catalog_read=False,declared_appearance_task_cue_not_learned_selection=True,
        full_target_pose_or_lateral_alignment_certified=False,physical_action_admitted=False,
        consumer_requirements=['Actual context state only through anchor timestamp; future states are prediction targets only.',
            'Use the geometry-valid flag, never treat missing zero geometry as safe or reached.',
            'Declared task macro/age are observed executor declarations, not future skill outcomes.',
            'No pose-integrated relative target or future motor command is a model input.',
            'Match each model to the native controller contract and record missing action support.'])
    write_json(output/'manifest.json',result);print('PUBLIC_TASK_STATE_EXPORT_COMPLETE',sha(output/'manifest.json'),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('manifest','decoder','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();export(a.manifest,a.decoder,a.output)
