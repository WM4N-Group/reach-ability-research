"""Optional offline original-journal -> Data index bridge. No execution gate.

No control callback, extra observer, Runtime.step, receipt drain, state restore,
model, resource lease or launcher. Never writes/repairs the source journal.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

DATA_READER_SHA = 'dec9d769ccd4c4d4a80c2cfe707227236ba2905bb0c50bbb9fb0cded7700ec2a'


def need(value, message):
    if not value:
        raise ValueError(message)


def digest(value, *, native=False):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=native,
                                    allow_nan=False,separators=(',',':')).encode()).hexdigest()


def read_journal(path, *, max_bytes=256*1024*1024):
    """Verify the exact flushed bytes. Completeness/closure is NOT inferred."""
    path=Path(path)
    need(path.is_absolute() and path.is_file() and not path.is_symlink(), 'Explicit original journal file')
    need(type(max_bytes) is int and 0 < max_bytes <= 256*1024*1024 and path.stat().st_size <= max_bytes,
         'Bounded offline evidence input')
    extract={'intents':[], 'bindings':[], 'receipts':[]}
    receipts={};previous='0'*64;raw_hash=hashlib.sha256();rows=0;faults=[];size=0
    with path.open('rb') as stream:
        for line in stream:
            size+=len(line);need(size<=max_bytes,'Journal grew beyond offline bound')
            raw_hash.update(line);record=json.loads(line)
            need(type(record) is dict and set(record)=={'sequence','previous_sha256','payload','sha256'},'Original Journal envelope required')
            actual=record.pop('sha256')
            need(type(record['sequence']) is int and record['sequence']==rows
                 and record['previous_sha256']==previous and digest(record)==actual,
                 'Changed/reordered original journal; do not repair or skip')
            payload=record['payload'];need(type(payload) is dict and type(payload.get('event')) is str,'Typed original event')
            event=payload['event'];pointer={'sequence':rows,'event':event,'envelope_sha256':actual}
            if event=='skill_intent_selected':extract['intents'].append(deepcopy(payload))
            elif event=='intent_native_execution_bound':extract['bindings'].append(deepcopy(payload))
            elif event in ('ainav_native_receipt','intent_actual_native_outcome'):
                receipt=payload['receipt'];need(type(receipt) is dict,'Literal recorded receipt required')
                if event=='intent_actual_native_outcome':
                    need(payload.get('native_option_sha256')==receipt.get('option_sha256')
                         and any(b['native_option_sha256']==receipt.get('option_sha256')
                                 and b['intent_sha256']==payload.get('intent_sha256') for b in extract['bindings']),
                         'Secondary actual receipt must bind this exact selected intent/native option')
                key=digest(receipt,native=True)
                if key not in receipts:
                    receipts[key]={'receipt':deepcopy(receipt),'sources':[]}
                    extract['receipts'].append(receipts[key]['receipt'])
                need(not any(x['event']==event for x in receipts[key]['sources']),
                     'Duplicate same-namespace receipt delivery; do not mask it as cross-log dedup')
                receipts[key]['sources'].append(pointer)
            elif event in ('ainav_chain_hard_stop','ainav_dispatch_failed','engineering_intent_rejected'):
                # A chain error is not rewritten to a synthetic native failed receipt.
                faults.append(pointer)
            previous=actual;rows+=1
    provenance=[]
    for key,row in receipts.items():
        sources=row['sources'];primary=any(s['event']=='ainav_native_receipt' for s in sources)
        provenance.append(dict(receipt_sha256=key,option_sha256=row['receipt']['option_sha256'],
            literal_status=row['receipt']['status'],source_refs=sources,
            exact_secondary_outcome_without_primary=not primary))
    return dict(extract=extract,journal={'path':str(path),'sha256':raw_hash.hexdigest(),
        'rows':rows,'last_sha256':previous,'closure_or_full_run_completeness_certified':False},
        receipt_sources=provenance,nonreceipt_error_events=faults,
        role='EVIDENCE_NOT_PLANNER_INPUT',new_native_receipts_inferred=False)


def load_Data_reader(ref):
    need(type(ref) is dict and set(ref)=={'path','sha256'} and ref['sha256']==DATA_READER_SHA,
         'Exact published Data reader, no silent repin')
    p=Path(ref['path']);need(p.is_absolute() and p.is_file() and not p.is_symlink()
        and hashlib.sha256(p.read_bytes()).hexdigest()==DATA_READER_SHA,'Data source bytes changed')
    name='_ainav_Data_record_reader_dec9d769'
    if name in sys.modules:
        module=sys.modules[name];need(Path(module.__file__).resolve()==p.resolve(),'Conflicting already-imported reader path')
        return module
    spec=importlib.util.spec_from_file_location(name,p);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    try:spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name];raise
    return module


def index_original_journal(path, *, data_reader_ref):
    projected=read_journal(path)
    # Exact existing Data function. Its raw-array/Finish/ready NO_COVERAGE stays
    # unknown. Dedup here only removes byte-identical receipts recorded twice by
    # the original coordinator/authority, not distinct budget windows/outcomes.
    indexed=load_Data_reader(data_reader_ref).index_extract(projected['extract'])
    return dict(data_index=indexed,original_journal=projected['journal'],
        original_receipt_sources=projected['receipt_sources'],
        nonreceipt_error_events=projected['nonreceipt_error_events'],
        role='EVIDENCE_NOT_PLANNER_INPUT',new_native_receipts_inferred=False,
        Runtime_or_Actor_world_API_or_physics_started=False,
        raw_record_storage_or_physical_qualification_generated=False)
