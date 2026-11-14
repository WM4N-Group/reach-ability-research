"""Rebuild a frozen model's input-only query from acquired TRAIN sensor streams.

No model or scorer call, future outcome arrays, native action, private catalog or
holdout reads. This verifies runtime input compatibility, not model task success.
"""
import argparse,importlib.util,json
from pathlib import Path
import numpy as np
from visual_shadow_model import INPUT_KEYS
from .streams import sha,write_json
from .integrated_dataset import checked_chunks
from .task_boundary_request import FirstNAVBoundaryRequest


def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def verify(root,decoder,model_encoder,normalizer,expected,output):
    root=Path(root);decoder=Path(decoder);model_encoder=Path(model_encoder);normalizer=Path(normalizer);expected=Path(expected);output=Path(output);output.mkdir(exist_ok=False)
    protocol=json.loads((root/'protocol.json').read_text())
    if protocol['role']!='train' or not protocol.get('nav_parameter_training_case'):raise ValueError('Registered controlled TRAIN source only')
    if protocol['nav_parameter_training_case']!='nominal-control':raise ValueError('Frozen reference query is the registered nominal TRAIN source')
    ledger=[json.loads(line) for line in (root/'integrated-stage-events.jsonl').open()]
    completion=next(x for x in ledger if x['event']=='B_native_goal_and_original_finish_complete');anchor=float(completion['time'])
    receipt={k:completion[k] for k in ('time','event','stage')}
    intents=load_module(decoder,'_request_pinned_intents');encoder=load_module(model_encoder,'_request_frozen_task_encoder')
    builder=FirstNAVBoundaryRequest(json.loads(normalizer.read_text()),encoder.state_input,encoder.action)
    control_path=root/'episode/control-boundaries.jsonl';closure=json.loads((root/'episode/closure.json').read_text())
    if sha(control_path)!=closure['control_boundaries_sha256']:raise ValueError('Frozen public control stream changed')
    controls=[];reader=intents.CausalPhaseDecoder();macro=None;started=None
    for line in control_path.open():
        row=json.loads(line)
        if row['time_s']>anchor+1e-7:break
        name=reader.push(row)
        if name!=macro:macro=name;started=row['time_s']
        controls.append(dict(time_s=row['time_s'],macro=macro,started=started,body=np.r_[row['q'],row['dq'],row['public_body_proprio']].astype(np.float32)))
    cursor=0;episode=root/'episode';index=json.loads((episode/'index.json').read_text());seen=0
    for z in checked_chunks(episode,index,'visual'):
        stop=False
        for i,stamp in enumerate(z['timestamps_s'][0]):
            if stamp>anchor+1e-7:stop=True;break
            while cursor+1<len(controls) and controls[cursor+1]['time_s']<=stamp+1e-7:cursor+=1
            c=controls[cursor]
            packet={name:(z[name] if name in ('camera_K','T_base_optical') else z[name][:,i:i+1]) for name in INPUT_KEYS}
            builder.append_acquired(packet,declared_macro=c['macro'],macro_declared_at_s=c['started']);seen+=1
        if stop:break
    body=controls[-1]
    request=builder.build(decision_time_s=anchor,actual_public_body=body['body'],body_observed_at_s=body['time_s'],known_B_completion=receipt)
    arrays=request['context_arrays'];comparisons={}
    with np.load(expected,allow_pickle=False) as reference:
        if set(reference.files)!=set(arrays):raise ValueError('Reference contains fields beyond input-only model schema')
        for key,value in arrays.items():comparisons[key]=bool(np.array_equal(value,reference[key]))
    path=output/'observed-context.npz'
    with path.open('xb') as f:np.savez_compressed(f,**arrays)
    result=dict(schema='acquired-stream-to-frozen-model-query-compatibility-v1',passed=all(comparisons.values()),
        root=str(root),source_protocol_sha256=sha(root/'protocol.json'),decoder_sha256=sha(decoder),frozen_model_input_encoder_sha256=sha(model_encoder),normalizer_sha256=sha(normalizer),
        input_only_reference_sha256=sha(expected),rebuilt_context_sha256=sha(path),array_exact_equality=comparisons,
        archive_bytes_identical=sha(expected)==sha(path),actual_frames_processed=seen,provenance=request['provenance'],
        builder_source_sha256=sha(Path(__file__).with_name('task_boundary_request.py')),
        model_calls=0,optimizer_updates=0,native_physics_steps=0,private_catalog_or_future_outcome_arrays_read=False,validation_or_test_data_read=False,
        native_dispatch_connected=False,task_or_model_planning_success_claimed=False)
    write_json(output/'query-provenance.json',request['provenance']);write_json(output/'compatibility.json',result)
    print(json.dumps(result),flush=True)
    if not result['passed']:raise ValueError('Rebuilt runtime query differs from frozen model training/score input')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('root','decoder','model-encoder','normalizer','expected','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();verify(a.root,a.decoder,a.model_encoder,a.normalizer,a.expected,a.output)
