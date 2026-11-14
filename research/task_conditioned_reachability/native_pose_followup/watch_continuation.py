"""One-shot read-only reporter for the explicit unstarted-cell continuation."""
import argparse
import fcntl
import html
import json
import os
from pathlib import Path
import shlex
import subprocess
import time
from analyze_mechanism import analyze,markdown
from evaluate_followup import evaluate
from watch_followup import render,sync_finished

TERMINAL={'COMPLETED_REGISTERED_SIX','STOPPED_GPU_BUSY_UNSPENT_RESERVED',
          'STOPPED_TECHNICAL_OR_SEVERE_NO_RETRY','STOPPED_CONTINUATION_ERROR_NO_RETRY'}


def snapshot(host,remote):
    code='''from pathlib import Path
import json,sys
r=Path(sys.argv[1]);l=json.loads((r/'physical_ledger.json').read_text());c=json.loads((r/'continuations/explicit-unstarted-v1/state.json').read_text())
print(json.dumps(dict(continuation=c,ledger_status=l['status'],starts=l['starts'],entries=l['entries'],active=l['active'])))
'''
    p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',host,'python3 - '+shlex.quote(remote)],
                     input=code,text=True,capture_output=True,timeout=45)
    if p.returncode:raise RuntimeError(p.stderr)
    return json.loads(p.stdout)


def finished(state):
    return state['continuation']['status'] in TERMINAL and state['active'] is None


def publish(directory,out,result):
    if directory is None:return
    marker='<!-- native-six-explicit-continuation-result:'+result['source_manifest_sha256']+' -->'
    block=(marker+'\n## 原剩余三格续接结果已生成｜'+time.strftime('%Y-%m-%d %H:%M:%S%z')+'\n\n'
           f"状态`{result['ledger_status']}`，累计启动{result['starts']}/6，闭合配对{result['closed_pairs']}/3；"
           f"完整注册成功率差P3−P2={result['registered_success_delta']}，匹配输入口径={result['matched_input_success_delta']}。"
           'None表示不可估计，不是零；前三次原样保留，无重试、SDK重开或新增预约。\n\n'
           f"任务报告：`{out/'研究效果对比.md'}`；机制/全成本：`{out/'实际技能机制与效果.md'}`。"
           '不把退让或模型余量增加冒任务收益，不自动扩批；原source/raw及资源停止快照保留。\n\n---\n\n')
    for name in ('当前进展.md','下一步计划.md'):
        p=directory/name;original=p.read_text()
        if marker in original:continue
        first,_,rest=original.partition('\n')
        if p.read_text()!=original:raise RuntimeError('Concurrent edit; keep report, do not overwrite')
        tmp=p.with_suffix('.continuation-result.tmp');tmp.write_text(first+'\n\n'+block+rest.lstrip('\n'));os.replace(tmp,p)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',required=True);p.add_argument('--remote-root',required=True)
    p.add_argument('--local-root',type=Path,required=True);p.add_argument('--main-dir',type=Path);p.add_argument('--max-wait-s',type=float,default=7200)
    a=p.parse_args()
    if not 0<a.max_wait_s<=7200:raise ValueError('Two-hour read-only wait cap')
    root=a.local_root.resolve();out=root/'comparison-continuation-1'
    if out.exists():raise FileExistsError('Do not overwrite a result')
    lock=(root/'continuation_report.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    with (root/'continuation_report_owner.json').open('x') as f:json.dump(dict(pid=os.getpid(),started_unix=time.time(),can_dispatch=False),f)
    start=time.monotonic();last=None;previous=None
    while time.monotonic()-start<a.max_wait_s:
        try:
            state=snapshot(a.host,a.remote_root);last=state
            signature=state['continuation']['status'],state['starts'],len(state['entries'])
            if signature!=previous:
                sync_finished(a.host,a.remote_root,root,state['entries']);previous=signature
                print(json.dumps(state,ensure_ascii=False),flush=True)
            if finished(state):break
        except Exception as e:print(json.dumps(dict(readonly_error=str(e))),flush=True)
        time.sleep(30)
    if last is None:raise RuntimeError('No state; no invented result')
    sync_finished(a.host,a.remote_root,root,last['entries'])
    task=evaluate(root);result=analyze(root);result['deadline_snapshot']=not finished(last)
    out.mkdir(exist_ok=False)
    for name,value in [('comparison.json',task),('mechanism.json',result),('continuation-snapshot.json',last)]:
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (out/'研究效果对比.md').write_text(render(root,task));text=markdown(result)
    (out/'实际技能机制与效果.md').write_text(text)
    (out/'实际技能机制与效果.html').write_text('<!doctype html><meta charset="utf-8"><title>实际技能完整对照</title><style>body{margin:32px;font:16px/1.7 sans-serif}pre{white-space:pre-wrap}</style><pre>'+html.escape(text)+'</pre>')
    publish(a.main_dir,out,result)
    print(json.dumps(dict(report_ready=str(out),status=result['ledger_status']),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
