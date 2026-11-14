"""Optional post-close journal -> owner bridge/reader -> scalar cost diagnostic.

No new capture requirement, Runtime, physics, callback or permission. A source
or closure receipt not supplied by the owner remains UNKNOWN, not self-signed.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

BRIDGE_SHA='4013453725cc923dd012cf34a06e69540d2b5bd4fd11ab5831fbd0bdfbbe4252'
READER_SHA='dec9d769ccd4c4d4a80c2cfe707227236ba2905bb0c50bbb9fb0cded7700ec2a'
RELEASE_SHA='3098297041dbfa50dd1928ee81ce28c68d3458ed544cc494dea7374177b7c49e'


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--journal',required=True);p.add_argument('--journal-sha256',required=True)
    p.add_argument('--bridge',required=True);p.add_argument('--data-reader',required=True)
    p.add_argument('--selected-release',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    attempts=[]
    def fence(event,values):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.fork','os.posix_spawn'):
            attempts.append(event);raise RuntimeError('Offline fence: '+event)
        if event=='import' and str(values[0]).split('.')[0] in ('torch','mujoco','numpy','scipy','onnxruntime','requests','httpx'):
            attempts.append(str(values[0]));raise RuntimeError('No model/physical library')
    sys.addaudithook(fence)
    inputs=[]
    def pin(path,expected):
        path=Path(path)
        if not path.is_absolute() or path.is_symlink() or not path.is_file():raise ValueError('Explicit nonsymlink source')
        h=hashlib.sha256(path.read_bytes()).hexdigest()
        if h!=expected:raise ValueError('Source/journal drift; no implicit repair/repin')
        inputs.append(dict(path=str(path),sha256=h));return path
    journal=pin(args.journal,args.journal_sha256)
    bridge=pin(args.bridge,BRIDGE_SHA);reader=pin(args.data_reader,READER_SHA)
    release=json.loads(pin(args.selected_release,RELEASE_SHA).read_text())
    spec=importlib.util.spec_from_file_location('_reach_original_ainav_journal_bridge_401345',bridge)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    indexed=module.index_original_journal(journal,data_reader_ref={'path':str(reader),'sha256':READER_SHA})
    if indexed['original_journal']['sha256']!=args.journal_sha256:raise ValueError('Journal changed during offline read')
    from .retrospective_ainav_costs import summarize
    result=summarize(indexed['data_index'],selected_manifest_sha256=release['original_reference_manifest_sha256'],
                     allow_unverified_source=True)
    # Exact selected source must come from actual owner qualification/closure,
    # not the filename or our desired release. This narrow bridge cannot prove it.
    result['original_journal']=indexed['original_journal']
    result['original_receipt_sources']=indexed['original_receipt_sources']
    result['nonreceipt_error_events']=indexed['nonreceipt_error_events']
    result['run_closure_verified']=False
    result['source_inputs']=inputs;result['fence_attempts']=attempts
    result['postprocessing_only_not_new_native_run']=True
    (out/'owner-index.json').write_text(json.dumps(indexed,ensure_ascii=False,indent=2)+'\n')
    (out/'cost-diagnostic.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(native_windows=len(result['rows']),selected_source_match=result['selected_executor_source_matches'],
        run_closure_verified=False,accounting=result['accounting'],fence_attempts=attempts),ensure_ascii=False))


if __name__=='__main__':main()
