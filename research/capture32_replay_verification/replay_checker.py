#!/usr/bin/env python3
"""Artifact checker only. Never imports torch/planners/candidate code or runs replay.
check: verify a main-supplied manifest and data-only replay output against that oracle.
A machine match always requires human replay-source/dependency provenance review.
"""
import argparse
import ast
import base64
import hashlib
import json
import math
import struct
from pathlib import Path
from datetime import datetime
from evidence_paths import EvidenceRoots, MODULE_DIR, add_evidence_arguments, contained_file

# No workstation-specific default roots. Configure explicitly from CLI.
ROOTS = None
CONTROL = RUN = REVIEW = VERIFICATION = None
ORACLE_HASH = 'caf13905d13e09365ada338a5f8a3de2aaba6618d416d3cc6995116e158c5d0a'
CONTRACT_HASH = '4671265ad219f3018be4c97b39d32e65757e6398e0ad8e912c38f4c7fd623f20'


def configure(args):
    global ROOTS, CONTROL, RUN, REVIEW, VERIFICATION
    ROOTS = EvidenceRoots.from_args(args)
    CONTROL, RUN, REVIEW, VERIFICATION = ROOTS.control, ROOTS.run, ROOTS.terminal_review, ROOTS.verification
    return ROOTS


def read_contract_and_oracle():
    if ROOTS is None:
        raise ValueError('Explicit external evidence roots required')
    oracle_path = contained_file(VERIFICATION, 'original_oracle.json')
    need(sha(oracle_path) == ORACLE_HASH, 'Historical reviewer oracle SHA mismatch')
    contract_path = MODULE_DIR / 'input_contract.json'
    need(sha(contract_path) == CONTRACT_HASH, 'Pinned input contract changed')
    return load_json(oracle_path), load_json(contract_path)


def verify_original_bindings(oracle):
    # Oracle path strings retain historical provenance; resolve ONLY trusted role mapping.
    required = {'control_manifest', 'run_manifest', 'events', 'payloads', 'prior_pair_index', 'native_frame'}
    need(set(oracle['original_bindings']) == required, 'Original evidence role set changed')
    for key, item in oracle['original_bindings'].items():
        need(sha(ROOTS.original_path(key)) == item['sha256'], 'Original evidence binding mismatch: ' + key)


CONTROL_HASH = 'b8703a23c3372786818b6dac51f9c03387f8a52c535e8e0715701784b177e567'
RUN_HASH = 'a537eec248ea47d4480284d63b3afd1f6f49515e82f37482eb93863b2c1fa0a4'
INPUT_HASH = '8ac5b98832d4af5f17f519cd558996ccc79ff943d2f1348a27ea30389c7e4acf'
MASK_HASH = 'cd4e126b59bab7afa56fcbb9255a9c8a8964fef8298aa1ecd64f55cd0a9a1a4d'
PAIR_INDEX_HASH = '10960f276ddf14388412f702e450a16996b3bcdfd337e6da8625b9662ff2771e'
LAST_HASH = '8ce59afb8e1a8d626b3aa32b17c81f27d3203f1b21962a7836c1a057293c4671'
IDENTITY = dict(source_id='sim2real-main-team-v022r2-fresh-ground-fallback-a',
    candidate_version='wm07-fresh-ground-fallback-v022r2',source_manifest_sha256=CONTROL_HASH,
    env_index=0,simulation_step=9411,time_s=188.22,capture_id=32,
    planner='expanded_ground_support_pose',role='original',ordinal=1)
INITIAL = 'joint_load_IK_angle_translation_tripod'
COMPLETE = 'complete_support_path_full_swing_four_load'
SAMPLING = dict(engine='torch.quasirandom.SobolEngine',dimensions=5,scramble=True,seed=913,
    count=32768,position_span_m=.16,angle_span=.5,chunk_size=64,
    path_leg_reserve=.010,support_samples=21,swing_phase_samples=41,landing_probe_samples=5)
DTYPES = {'float32':('f',4), 'float64':('d',8), 'int64':('q',8), 'bool':('?',1),
          'python.float':('d',8), 'python.bool':('?',1)}
# Top-level ready predicates only. No imitation of the underlying physical calculations.
GATES = [
 dict(id='body_path_gap',metric='gap',op='>=',threshold=.010,unit='m',
      producer='climb_body_clearance.support_path_geometry[0]',definition='Minimum over21 body poses of sampled SAT separating-axis base-box gap; conservative bound, not exact mesh clearance.'),
 dict(id='support_joint_margin',metric='path_margin',op='>=',threshold=0.,unit='rad_equivalent',
      producer='climb_body_clearance.support_path_geometry[1]',definition='Min over21 poses/all joints of nominal joint-limit slack minus.01 and torque-bias command joint-limit slack; not Cartesian distance.'),
 dict(id='support_ik_error',metric='path_error',op='<',threshold=.001,unit='m',
      producer='climb_body_clearance.support_path_geometry[2]',definition='Max FK(inverse(local))-local Euclidean residual over support path samples and feet.'),
 dict(id='leg_path_gap',metric='legs_gap',op='>=',threshold=.005,unit='m',
      producer='climb_body_clearance.leg_path_gap',definition='Min over21 poses/4legs/3links of actual primitive-box separating-axis gap. The separate .010 path_leg_reserve is a ready-only preference, NOT this hard gate.'),
 dict(id='swing_loaded_joint_margin',metric='sm',op='>=',threshold=.03,unit='rad_equivalent',
      producer='climb_guidance.swing_path_preview[0]',definition='Min selected swing nominal joint slack minus.01 / gravity-loaded command slack and landing reload joint/effort slack; torque slack divided by30, not meters or native measured torque margin.'),
 dict(id='swing_ik_error',metric='se',op='<',threshold=.001,unit='m',
      producer='climb_guidance.swing_path_preview[1]',definition='Max inverse/forward Euclidean residual over all feet and41 swing+5 probe samples; not only selected foot.'),
 dict(id='swing_primitive_gap',metric='sg',op='>=',threshold=.005,unit='m',
      producer='climb_guidance.swing_path_preview[2]',definition='Min primitive-box gap over41+5 samples/all modeled links/legs.'),
 dict(id='four_support_minimum_load',metric='minimum',op='>=',threshold=8.,unit='N',
      producer='climb_guidance.four_support_path_loads[0]',definition='Minimum estimated balanced vertical force across21 samples/all four planted feet, not native contact load.'),
 dict(id='four_support_residual',metric='residual',op='<',threshold=.1,unit='native_mixed_force_moment_norm',
      producer='climb_guidance.four_support_path_loads[1]',definition='Peak Euclidean norm of balance residual [sumF-weight,sum(dxF),sum(dyF)] after clipping/rescale over21 samples; raw N and N*m components, not normalized or pure N.'),
]
SOURCE_FUNCTIONS = {
 'recovery_math/climb_guidance.py': ['expanded_ground_support_pose','triangle_margin','predicted_support_com',
    'support_load_preview','balanced_vertical_loads','tripod_support_clearance','front_raise_candidate_ready',
    'front_support_height','edge_lift_reference','swing_path_preview','four_support_path_loads','four_support_path_checks'],
 'recovery_math/climb_body_clearance.py':['support_path_geometry','base_box_gap','leg_path_gap','leg_link_poses','primitive_box_gap','multiply_quaternion'],
 'recovery_math/climb_leg_kinematics.py':['LegKinematics.__init__','LegKinematics.from_usd','LegKinematics.reordered',
    'LegKinematics.forward','LegKinematics.inverse','LegKinematics.jacobian','rotate_vector'],
 'support_frame_geometry.py':['actual_box_query','current_geometry_frame','geometry_frame_context'],
 'support_stage_queries.py':['gravity_edge_apex','box_points','ground_clearance'],
 'solver_frame.py':['MathFrame.box_query_pose','MathFrame.box_relative_orientation','MathFrame._yaw',
    'MathFrame.orientation','MathFrame.vector','MathFrame.actual_ground_height','MathFrame.box_canonical_points'],
 'frozen_math.py':[], 'frozen-math-sha256.json':[],
 'frozen_math_source/climb_leg_kinematics.py':['rotate_vector'],
 'frozen_math_source/climb_body_clearance.py':['multiply_quaternion'],
 'frozen_math_source/piper_climb_completion.py':[],
 'box_frame.py':[], 'fresh_ground_fallback.py':['expanded_enter','expanded_return','mask_record'],
}
# Computation-path functions that this nonempty full original call must exercise.
RUNTIME_MIN = {f'{f}::{name}':1 for f,names in SOURCE_FUNCTIONS.items() for name in names
               if name not in ('LegKinematics.__init__','LegKinematics.from_usd','LegKinematics.reordered',
                               'front_support_height','ground_clearance','MathFrame.actual_ground_height',
                               'geometry_frame_context','expanded_enter','expanded_return','mask_record')}
for f,n in [('recovery_math/climb_body_clearance.py','support_path_geometry'),
 ('recovery_math/climb_body_clearance.py','leg_path_gap'),('recovery_math/climb_guidance.py','swing_path_preview'),
 ('recovery_math/climb_guidance.py','four_support_path_loads'),('recovery_math/climb_guidance.py','four_support_path_checks')]:
    RUNTIME_MIN[f'{f}::{n}']=11


def need(condition,message):
    if not condition:raise ValueError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def load_json(path):
    def pairs(items):
        result={}
        for k,v in items:
            need(k not in result,'Duplicate JSON key: '+k);result[k]=v
        return result
    return json.loads(Path(path).read_text(),object_pairs_hook=pairs,
                      parse_constant=lambda s:(_ for _ in ()).throw(ValueError('Nonfinite JSON '+s)))
def same(a,b):return canonical(a)==canonical(b)
def shape_flat(value):
    if not isinstance(value,list):return [],[value]
    if not value:return [0],[]
    parts=[shape_flat(v) for v in value]
    need(all(p[0]==parts[0][0] for p in parts),'Ragged tensor')
    return [len(value)]+parts[0][0],[x for _,flat in parts for x in flat]
def f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]
def typed(value,dtype=None,shape=None):
    dims,flat=shape_flat(value)
    if dtype is None:
        leaf=flat[0] if flat else None
        dtype=('bool' if type(leaf) is bool else 'int64' if type(leaf) is int else 'float32') if dims else ('python.bool' if type(leaf) is bool else 'python.float')
    need(dtype in DTYPES,'Unsupported dtype '+str(dtype))
    if shape is None:shape=dims
    need(math.prod(shape)==len(flat),'Tensor shape size mismatch')
    code,_=DTYPES[dtype]
    if dtype in ('bool','python.bool'):need(all(type(v) is bool for v in flat),'Bool conversion forbidden')
    elif dtype=='int64':need(all(type(v) is int for v in flat),'Index dtype conversion forbidden')
    else:need(all(type(v) in (int,float) and math.isfinite(v) for v in flat),'Nonfinite/nonreal tensor')
    raw=struct.pack('<'+code*len(flat),*flat)
    return dict(dtype=dtype,shape=shape,values=value,sha256_le=digest(raw))
def tensor_check(value,expected=None):
    need(isinstance(value,dict),'Typed tensor/scalar object required')
    need(set(value)=={'dtype','shape','values','sha256_le'},'Tensor schema mismatch')
    actual=typed(value['values'],value['dtype'],value['shape'])
    need(actual['sha256_le']==value['sha256_le'],'Tensor byte hash mismatch')
    # JSON values must be exactly representable in the declared dtype, not silently rounded inputs.
    _,flat=shape_flat(value['values'])
    if value['dtype']=='float32':need(all(f32(x)==x for x in flat),'Non-float32 JSON value')
    if expected is not None:need(same(actual,expected),'Typed original input/return mismatch')
    return flat
def flatten_inputs(tree,prefix=''):
    out={}
    for key,value in tree.items():
        path=prefix+key
        if isinstance(value,dict):out.update(flatten_inputs(value,path+'/'))
        else:out[path]=typed(value)
    return out

def bool_payload(values,shape):
    need(all(type(v) is bool for v in values),'bool payload requires bools')
    need(math.prod(shape)==len(values),'Bad boolean shape')
    raw=bytes(values);packed=bytearray((len(values)+7)//8)
    for i,v in enumerate(values):packed[i//8]|=int(v)<<(i%8)
    return dict(dtype='bool',shape=shape,numel=len(values),valid=sum(values),mask_sha256=digest(raw),
                packed_sha256=digest(packed),encoding='numpy.packbits-bitorder-little+base64',
                packed_mask_base64=base64.b64encode(packed).decode())

def decode_mask(p,expected=None):
    need(p['dtype']=='bool' and p['encoding']=='numpy.packbits-bitorder-little+base64','Mask encoding/dtype changed')
    need(isinstance(p['shape'],list) and all(type(n) is int and n>=0 for n in p['shape']),'Invalid mask shape')
    size=math.prod(p['shape']);need(type(p['numel']) is int and size==p['numel'],'Mask numel mismatch')
    packed=base64.b64decode(p['packed_mask_base64'],validate=True)
    need(len(packed)==(size+7)//8 and digest(packed)==p['packed_sha256'],'Packed payload mismatch')
    need(not(size%8 and packed and packed[-1]>>(size%8)),'Nonzero mask padding')
    raw=bytes((packed[i//8]>>(i%8))&1 for i in range(size))
    need(digest(raw)==p['mask_sha256'] and type(p['valid']) is int and sum(raw)==p['valid'],'Mask payload/count/hash mismatch')
    if expected is not None:
        original=decode_mask(expected)
        need(p['shape']==expected['shape'] and raw==original,'Original mask BITWISE/SHAPE mismatch (count is insufficient)')
    return raw

def read_line(path,ref):
    with Path(path).open('rb') as f:f.seek(ref['byte_offset']);line=f.readline()
    need(digest(line)==ref['line_sha256'],'Original line hash mismatch')
    return json.loads(line)

def source_symbols(path):
    tree=ast.parse(Path(path).read_text());out={}
    def collect(nodes,prefix=''):
        for n in nodes:
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
                out[prefix+n.name]=n
            if isinstance(n,ast.ClassDef):collect(n.body,prefix+n.name+'.')
    collect(tree.body)
    return out

def write_new(path,value):
    with Path(path).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')

def statistic(masks):
    names=[g['id'] for g in GATES];n=len(masks[names[0]])
    need(all(len(masks[g])==n for g in names),'Gate denominator mismatch')
    out=[];prefix=[True]*n
    for name in names:
        cur=masks[name]
        independent=sum(not x for x in cur)
        exclusive=sum(not cur[i] and all(masks[k][i] for k in names if k!=name) for i in range(n))
        newly=sum(prefix[i] and not cur[i] for i in range(n))
        prefix=[prefix[i] and bool(cur[i]) for i in range(n)]
        out.append(dict(gate=name,independent_rejected=independent,exclusive_rejected=exclusive,
                        first_excluded_in_declared_order=newly,cumulative_survivors=sum(prefix)))
    return dict(denominator=n,order=names,scope='ORIGINAL666; cumulative order is diagnostic bookkeeping not physical causal order',rows=out)

def check_chunk(chunk,original):
    need(type(chunk['ordinal']) is int and chunk['ordinal']>=1,'Missing chunk ordinal')
    need(chunk['row']==original['row'] and type(chunk['row']) is int,'Chunk row mismatch')
    need(same(chunk['original_candidate_indices'],original['indices']),'Candidate order/index mismatch')
    combined=decode_mask(chunk['ready'],original['payload']);size=len(combined)
    need(set(chunk['metrics'])=={g['metric'] for g in GATES},'Missing/extra raw gate metric')
    need(set(chunk['gate_masks'])=={g['id'] for g in GATES},'Missing/extra subgate')
    need(set(chunk['signed_slacks'])=={g['id'] for g in GATES},'Missing/extra diagnostic slack')
    masks={}
    for g in GATES:
        tensor=chunk['metrics'][g['metric']]
        need(tensor['dtype']=='float32' and tensor['shape']==[1,size],'Metric dtype/shape changed')
        values=tensor_check(tensor);limit=f32(g['threshold'])
        bits=bytes(v>=limit if g['op']=='>=' else v<limit for v in values)
        provided=decode_mask(chunk['gate_masks'][g['id']]);need(chunk['gate_masks'][g['id']]['shape']==[1,size] and bits==provided,'Subgate mask does not implement original predicate '+g['id'])
        slack=chunk['signed_slacks'][g['id']]
        need(slack['dtype']=='float32' and slack['shape']==[1,size],'Diagnostic slack dtype/shape changed')
        values_slack=tensor_check(slack)
        wanted=[f32(v-limit) if g['op']=='>=' else f32(limit-v) for v in values]
        need(same(values_slack,wanted),'Slack sign/scale/definition mismatch '+g['id'])
        masks[g['id']]=bits
    reconstructed=bytes(all(masks[g['id']][i] for g in GATES) for i in range(size))
    need(reconstructed==combined,'Recombined subgates differ from ORIGINAL joint mask')
    return masks


def check(candidate,manifest,digest_expected,report_name):
    candidate=Path(candidate).resolve();manifest=Path(manifest).resolve()
    need(manifest.is_relative_to(candidate),'Candidate manifest outside isolated directory')
    need(not(candidate==CONTROL or candidate==RUN or candidate.is_relative_to(MODULE_DIR)),'Require separate developer replay candidate')
    need(sha(manifest)==digest_expected,'Main supplied candidate manifest SHA mismatch')
    mf=load_json(manifest);files=mf['files_sha256'];verified={}
    def artifact(name):
        need(name in files,'Unindexed candidate artifact '+name)
        path=(candidate/name).resolve();need(path.is_relative_to(candidate),'Artifact escapes isolated candidate')
        need(path.stat().st_size<=128*1024*1024,'Evidence unexpectedly unbounded')
        need(sha(path)==files[name],'Candidate artifact hash mismatch '+name)
        verified[name]=files[name];return path
    # Hash the complete small replay artifact manifest; do not rehash the large control package.
    for name in files:artifact(name)
    oracle,contract=read_contract_and_oracle()
    need(ORACLE_HASH==contract['oracle_sha256'],'Reviewer oracle changed')
    verify_original_bindings(oracle)
    report=load_json(artifact(report_name))
    need(report['schema']=='capture32-replay-evidence-v1','Replay report schema mismatch')
    need(report['contract_sha256']==sha(MODULE_DIR/'input_contract.json'),'Replay was not bound to this independent contract')
    need(same(report['identity'],IDENTITY),'Replay wrong source/capture/step/role/callee')
    need(same(report['sampling'],SAMPLING),'Sampling seed/count/range/chunk/sample-grid changed')
    need(same(report['original_bindings'],oracle['original_bindings']),'Native evidence identities replaced')
    need(same(report['input_schema'],oracle['original_input_schema']),'Input values/dtype/shape/source-derived scalar types changed')
    for name,t in report['input_schema'].items():tensor_check(t,oracle['original_input_schema'][name])
    need(len(report['return'])==4,'Original return tuple incomplete')
    for t,o in zip(report['return'],oracle['original_return']):tensor_check(t,o)
    need(report['return_margin_semantics']=='no_ready_candidate_zero_placeholder_not_best_rejected_margin','False return margin mislabelled')
    need(same(report['gate_definitions'],GATES),'Gate definitions/units/thresholds changed')
    execution=report['execution']
    need(execution['device']=='cpu' and execution['default_dtype']=='float32','This review requires CPU float32 replay evidence')
    for k in ('physical_steps','SDK_environments','GPU_calls'):need(type(execution[k]) is int and execution[k]==0,'Forbidden execution in replay')
    for k in ('python_version','torch_version','platform','blas_threads','replay_command','dtype_provenance'):
        need(k in execution and execution[k] not in ('',None),'Missing execution provenance '+k)
    need(execution['native_dtype_directly_recorded'] is False,'Native JSON did not log tensor dtype; do not fabricate its observation')
    need(report['unresolved_dependencies']==[],'Unresolved replay dependencies')
    for name in ('entrypoint','stdout_log','runtime_trace','dependency_evidence'):artifact(report[name])
    dependencies=load_json(artifact(report['dependency_evidence']))
    need(same(dependencies['actual_frame_record'],oracle['frame']),'Wrong current actual box/math frame')
    need(dependencies['model_legs']==oracle['expected_model_legs'],'Model leg order mismatch')
    for key,shape in [('hip_origins',[4,3]),('hip_lateral_offsets',[4]),('link_lengths',[4,2])]:
        value=dependencies['model_geometry'][key]
        need(value['shape']==shape and value['dtype']=='float32','Missing actual materialized model geometry')
        tensor_check(value)
    need(dependencies['model_geometry_provenance']['kind'] in ('frozen_asset_extraction','original_runtime_model_snapshot'),'Unsupported model geometry provenance')
    for key in ('source_binding_evidence','extraction_or_snapshot_evidence'):
        artifact(dependencies['model_geometry_provenance'][key])
    need(dependencies['numeric_input_materialization_matches_report'] is True,'No actual dtype/input materialization witness')
    need(dependencies['context_used_at_call'] is True and dependencies['no_mock_predicates_or_geometry'] is True,'Mock geometry/predicate cannot certify replay')
    trace=load_json(artifact(report['runtime_trace']))
    need(same(trace['identity'],IDENTITY),'Runtime dependency trace wrong call')
    need(trace['entry_input_schema_sha256']==digest(canonical(report['input_schema']).encode()),'Actual-call entry input witness differs from report')
    need(same(trace['observed_sampling'],SAMPLING),'Actual sampler witness changed')
    need(trace['initial_mask_sha256']==report['initial_mask']['mask_sha256'],'Actual initial-mask witness differs')
    need(trace['return_sha256_le']==[v['sha256_le'] for v in report['return']],'Actual return witness differs')
    calls=trace['callables'];observed={}
    for item in calls:
        key=item['frozen_file']+'::'+item['qualname'];need(key not in observed,'Duplicate function trace record')
        need(item['frozen_file'] in oracle['dependencies'],'Unbound function dependency '+key)
        dep=oracle['dependencies'][item['frozen_file']];definition=dep['functions'].get(item['qualname'])
        need(definition is not None,'Unbound original callable '+key)
        need(item['frozen_file_sha256']==dep['sha256'] and item['original_AST_sha256']==definition['ast_sha256'],'Changed computational dependency '+key)
        need(type(item['calls']) is int and item['calls']>=0,'Bad actual invocation count')
        implementation=artifact(item['runtime_implementation_artifact'])
        for field in ('actual_loaded_file','runtime_module'):
            need(isinstance(item.get(field),str) and bool(item[field]),'Missing loaded callable provenance '+key)
        mode=item['implementation_mode']
        need(mode in ('exact_import','AST_equivalent_extraction','return_observer_wrapper'),'Unreviewable computation replacement')
        if mode=='exact_import':
            need(sha(implementation)==dep['sha256'],'Exact import source bytes differ '+key)
        elif mode=='AST_equivalent_extraction':
            extracted=source_symbols(implementation)
            need(item['qualname'] in extracted and digest(ast.dump(extracted[item['qualname']],include_attributes=False).encode())==definition['ast_sha256'],'Extracted computation AST differs '+key)
        else:
            wrapped=artifact(item['wrapped_original_artifact'])
            need(sha(wrapped)==dep['sha256'],'Observer does not bind the original computation source '+key)
        observed[key]=item['calls']
    for key,count in RUNTIME_MIN.items():need(observed.get(key,0)>=count,'Actual-call dependency coverage missing '+key)
    need(observed['recovery_math/climb_guidance.py::expanded_ground_support_pose']==1,'Expanded replay repeated or callee replaced')
    initial=report['initial_mask'];decode_mask(initial,oracle['initial']['payload'])
    ids=[i for i,v in enumerate(decode_mask(initial)) if v]
    need(report['ordered_initial_survivor_indices']==ids==oracle['ordered_initial_survivor_indices'],'666 ordered indices changed')
    chunks=report['chunks'];need(len(chunks)==11,'Expected original11chunks')
    need(len(trace['chunks'])==11,'Missing actual numeric-return trace chunks')
    masks={g['id']:[] for g in GATES}
    for index,(chunk,original) in enumerate(zip(chunks,oracle['chunks']),1):
        need(chunk['ordinal']==index,'Chunk order changed')
        witnessed=trace['chunks'][index-1]
        need(witnessed['ordinal']==index and witnessed['row']==chunk['row'] and
             same(witnessed['original_candidate_indices'],chunk['original_candidate_indices']),'Actual metric producer chunk mapping differs')
        need(witnessed['metric_sha256_le']=={k:v['sha256_le'] for k,v in chunk['metrics'].items()},'Metric report not linked to actual dependency returns')
        need(witnessed['joint_mask_sha256']==chunk['ready']['mask_sha256'],'Actual joint-mask witness differs')
        component=check_chunk(chunk,original)
        for key,value in component.items():masks[key].extend(value)
    derived=statistic(masks);need(same(report['attribution'],derived),'Independent/exclusive/cumulative rejection statistics misdefined')
    need(sum(row['first_excluded_in_declared_order'] for row in derived['rows'])==666,'Joint all-false denominator changed')
    # Source/trace/provenance claims cannot prove themselves; no automatic semantic acceptance.
    for name,dig in verified.items():need(sha(candidate/name)==dig,'Candidate modified during check')
    need(sha(manifest)==digest_expected,'Candidate manifest changed during check')
    verify_original_bindings(oracle)
    return dict(status='MACHINE_EXACT_MATCH_PENDING_INDEPENDENT_CODE_AND_DEPENDENCY_PROVENANCE_REVIEW',
       candidate_manifest_sha256=digest_expected,original12_masks_bitwise_equal=True,indices_exact=True,
       original_return_exact=True,subgates_recompose_to_original=True,attribution=derived,
       checked_artifact_sha256=verified,
       human_review_required=['Actual unmocked replay entry/call graph vs emitted trace and source/AST mappings',
          'Actual model geometry asset/runtime lineage; no independent native model tensor snapshot in logged entry',
          'Source-derived dtype materialization, CPU/CUDA numeric portability and genuine execution log',
          'Raw margins/reload/effort normalization, fallback margin0 vs rejected candidate metrics',
          'No line-order causal claim or unsupported counterfactual/physical success'],
       physical_or_control_success_claim=False,stage_goal_complete=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['check'])
    add_evidence_arguments(p)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--manifest-sha256',required=True)
    p.add_argument('--report',default='replay_evidence.json')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    try:
        roots=configure(args)
        out=roots.new_output(args.output,args.candidate)
    except (OSError,ValueError) as exc:
        print(canonical(dict(status='MISSING_EVIDENCE_OR_UNSAFE_OUTPUT',error=str(exc),replay_executed=False)))
        return 2
    try:
        result=check(args.candidate,args.manifest,args.manifest_sha256,args.report);code=0
    except Exception as exc:
        import traceback
        result=dict(status='NOT_ACCEPTED_CHECK_ERROR_OR_MISMATCH',error=str(exc),traceback=traceback.format_exc(),
                    candidate_manifest_sha256=args.manifest_sha256);code=1
    result.update(at=datetime.now().astimezone().isoformat(),checker_sha256=sha(__file__),replay_executed_by_checker=False)
    write_new(out,result)
    print(canonical({k:v for k,v in result.items() if k not in ('traceback','checked_artifact_sha256','attribution')}))
    return code

if __name__=='__main__':raise SystemExit(main())
