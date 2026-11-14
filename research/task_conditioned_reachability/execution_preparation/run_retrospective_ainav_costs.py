"""Consume pinned Data published evidence view, not the old raw task archive."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--index',required=True)
    parser.add_argument('--index-sha256',required=True)
    parser.add_argument('--selected-release',required=True)
    parser.add_argument('--selected-release-sha256',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    attempts=[]
    def fence(event,values):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.fork','os.posix_spawn'):
            attempts.append(event);raise RuntimeError('Offline fence: '+event)
        if event=='import' and str(values[0]).split('.')[0] in ('torch','mujoco','numpy','scipy','onnxruntime','requests','httpx'):
            attempts.append(str(values[0]));raise RuntimeError('No model/physical/numerical library')
    sys.addaudithook(fence)
    refs=[]
    def read(path,expected):
        path=Path(path);raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Source drift; explicit repin required')
        refs.append(dict(path=str(path.resolve()),sha256=expected));return json.loads(raw)
    index=read(args.index,args.index_sha256);release=read(args.selected_release,args.selected_release_sha256)
    if release['chosen_baseline']!='execution-judged-20261031-v6':raise ValueError('Only selected full-v6 same source')
    from .retrospective_ainav_costs import summarize
    result=summarize(index,selected_manifest_sha256=release['original_reference_manifest_sha256'])
    result['source_inputs']=refs;result['fence_attempts']=attempts
    result['no_raw_original_archive_or_GT_pose_read']=True
    result['original_index_pending_baseline_field_not_modified']=True
    (out/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    cols=['decision_order','semantic_skill','semantic_target','native_skill','role','native_started_s',
          'native_terminal_s','literal_terminal_status','observed_native_window_s','native_option_sha256']
    with (out/'native-windows.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader()
        for row in result['rows']:writer.writerow({k:row[k] for k in cols})
    with (out/'push-successor-costs.csv').open('w') as f:
        cols=['push_target','observed_next_skill','observed_next_target','own_push_native_window_s',
              'observed_next_preparation_windows_s','push_terminal_to_next_preparation_end_s',
              'push_native_start_to_next_preparation_end_s','query_to_next_preparation_end_s']
        writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader()
        for row in result['push_chains']:writer.writerow({k:row[k] for k in cols})
    print(json.dumps(dict(denominators=result['denominators'],accounting=result['accounting'],
                         push_chains=result['push_chains'],fence_attempts=attempts),ensure_ascii=False))


if __name__=='__main__':main()
