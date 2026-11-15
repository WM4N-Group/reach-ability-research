#!/usr/bin/env python3
"""46308 only: assemble fully closed CAL/VAL for the one frozen critic, no fit.

The exact actual TRAIN gate/fit release pins all base artifacts. Explicit SHA-
pinned extraction reports are required; no discovery of unfinished/raw attempts.
Does not score partial CAL, write Data authority, launch or overwrite anything.
"""
import argparse,datetime as dt,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.task_conditioned_reachability.execution_preparation.frozen_heldout_dataset import assemble_frozen_heldout
from research.task_conditioned_reachability.execution_preparation.successor_aware_choice import need
from research.task_conditioned_reachability.execution_preparation.successor_critic import attempt_spending


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('training-root','authorization','output-root'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--expected-release-sha',required=True)
    p.add_argument('--phase',choices=('CALIBRATION','FULL_COHORT'),required=True)
    p.add_argument('--attempt',action='append',required=True,help='Exact extracted report PATH=SHA256; no raw Data work directory')
    a=p.parse_args();pins={}
    def pinned(path,expected):
        path=Path(path);need(not path.is_symlink(),'Regular explicit small JSON source');path=path.resolve()
        with path.open('rb')as f:raw=f.read(10*1024**2+1)
        need(len(raw)<=10*1024**2 and hashlib.sha256(raw).hexdigest()==expected,'Pinned artifact changed: '+str(path))
        need(str(path)not in pins or pins[str(path)]==expected,'Conflicting file identity pins')
        pins[str(path)]=expected;return json.loads(raw)
    root=a.training_root.resolve();release=pinned(root/'TRAIN_GATE_AND_FIT_RELEASE.json',a.expected_release_sha)
    need(release.get('schema')=='Reach-actual-TRAIN-six-gate-and-frozen-fit-release-v1' and
         release.get('status')=='GENUINE_TRAIN_ONLY_FIT_COMPLETE_HELDOUT_NOT_COLLECTED',
         'Actual one-fit TRAIN release only')
    def base(name):return pinned(root/name,release['files'][name])
    protocol=base('DERIVED_TRAINING_PROTOCOL.json');train=base('CLOSED_TRAIN_ONLY_DATASET.json')
    artifact=base('TRAIN_FROZEN_FIT.json');gate=base('TRAIN_SOURCE_FEATURE_LABEL_GATE.json')
    need(gate['status']=='CLOSED_TRAIN_SOURCE_FEATURE_LABEL_GATE_PASS_NOT_FIT_OR_DISPATCH','Original TRAIN source gate')
    auth=pinned(a.authorization,protocol['authorization_sha256']);reports=[]
    for spec in a.attempt:
        path,h=spec.rsplit('=',1);r=pinned(path,h)
        need(bool(r.get('source_pins')),'Source-bound extracted report, not arbitrary labelled rows')
        for source,expected in r['source_pins'].items():
            src=Path(source);need(src.is_file()and not src.is_symlink(),'Original source regular file')
            digest=hashlib.sha256()
            with src.open('rb')as f:
                for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
            need(digest.hexdigest()==expected,'Original closed source drift: '+source)
            need(source not in pins or pins[source]==expected,'Conflicting original source pins')
            pins[source]=expected
        reports.append(r)
    data=assemble_frozen_heldout(train,auth,protocol,artifact,reports,phase=a.phase)
    # Recheck all inputs after assembly, never silently use changing releases.
    for path,expected in pins.items():
        digest=hashlib.sha256()
        with Path(path).open('rb')as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
        need(digest.hexdigest()==expected,'Source changed during assembly: '+path)
    need(not a.output_root.exists(),'Fresh exclusive output root; never overwrite TRAIN or prior evaluation')
    result=dict(status='CLOSED_FROZEN_HELDOUT_DATASET_ASSEMBLED_NOT_EVALUATED',at=dt.datetime.now().astimezone().isoformat(),
        phase=a.phase,closed_attempts=data['closed_attempt_count'],reached_rows=len(data['rows']),
        unreached_attempts=len(data['unreached_decision_attempts']),frozen_model_sha256=artifact['model_sha256'],
        frozen_training_rows_sha256=artifact['training_rows_sha256'],spending=attempt_spending(data),
        source_pins=pins,model_refitted=False,training_started=False,metrics_evaluated=False,
        physical_dispatch=False,Data_authority_modified=False,original_training_artifacts_modified=False)
    a.output_root.mkdir()
    for name,obj in (('CLOSED_FROZEN_EVALUATION_DATASET.json',data),('ASSEMBLY_SOURCE_GATE.json',result)):
        with (a.output_root/name).open('x')as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:v for k,v in result.items()if k not in('source_pins','spending')},ensure_ascii=False))
if __name__=='__main__':main()
