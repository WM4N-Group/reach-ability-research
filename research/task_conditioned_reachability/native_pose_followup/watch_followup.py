"""Bounded one-shot read-only six-cell reporter; NEVER dispatch/retry any job."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from evaluate_followup import evaluate
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'pose_conditioned_entry'))
from watch_effect_comparison import TERMINAL, snapshot, sync_finished


def read(path):return json.loads(path.read_text())


def render(root,result):
    protocol=read(root/'source/protocol.json')
    lines=['# 新六格实际技能对照结果','',
           '**范围：**机制针对性开发先导；不是独立泛化、实机或完整穿障碍导航验收。','',
           f"- 状态：`{result['state']}`；实际启动：{result['native_evaluation']['starts']}/6。",
           f"- source SHA：`{result['source_manifest_sha256']}`。",'',
           '| seed | 方法 | 箱默认偏移/mm | 实际结果 | 任务成功 | 支撑/mm | 几何请求/mm | 已选/mm |',
           '|---|---|---:|---|---|---:|---:|---:|']
    def num(x):return '—' if x is None else f'{x*1000:.3f}'
    for item,row in zip(protocol['schedule'],result['native_evaluation']['rows']):
        file=root/'runs'/item['output_name']/'report.json';r=read(file) if file.exists() else {}
        plan=r.get('prospective_support_plan',{});preview=plan.get('box_approach_preview',{})
        lines.append(f"|{item['seed']}|{item['arm']}|{item['box_default_world_x_offset_m']*1000:.1f}|"
                     f"{row.get('native_outcome') or row['status']}|{row['primary_success']}|"
                     f"{num(plan.get('support_only_shift_m'))}|{num(preview.get('minimum_shift_m'))}|{num(plan.get('shift_m'))}|")
    lines+=['',f"观察完成率差P3−P2：{result['descriptive_success_delta']}。",
            f"共同初态/决策输入见证匹配后的完成率差：{result['matched_input_success_delta']}。",
            'None表示不可估计/缺证，不是零收益或成功；任何注册失败、拒绝、未触发均不删除。',
            '几何触发/退让差不等于收益；缺配对输入不能把完成差直接归因新公式。',
            '软件/SDK fixture不计机器人样本。原始回合、source和预算不由此报告器修改。']
    return '\n'.join(lines)+'\n'


def publish(directory,out,result):
    if directory is None:return
    marker='<!-- native-pose-six-result:'+result['source_manifest_sha256']+' -->'
    block=(marker+'\n## 新六格实际技能结果已生成｜'+time.strftime('%Y-%m-%d %H:%M:%S%z')+'\n\n'
           f"状态`{result['state']}`，启动{result['native_evaluation']['starts']}/6；"
           f"观察完成率差P3−P2={result['descriptive_success_delta']}，输入匹配差={result['matched_input_success_delta']}。"
           'None不可估计，不补零；结果含全部注册失败/unknown，未重试替换。\n\n'
           f"报告：`{out/'研究效果对比.md'}`；结构化结果：`{out/'comparison.json'}`。"
           '不自动扩批，不将机制触发冒任务收益；原始数据与账本保留。\n\n---\n\n')
    for name in ('当前进展.md','下一步计划.md'):
        p=directory/name;original=p.read_text()
        if marker in original:continue
        first,_,rest=original.partition('\n');updated=first+'\n\n'+block+rest.lstrip('\n')
        if p.read_text()!=original:raise RuntimeError('Owned page changed concurrently; no overwrite')
        tmp=p.with_suffix('.six-result.tmp');tmp.write_text(updated);os.replace(tmp,p)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',required=True);p.add_argument('--remote-root',required=True)
    p.add_argument('--local-root',type=Path,required=True);p.add_argument('--main-dir',type=Path);p.add_argument('--max-wait-s',type=float,default=14400)
    a=p.parse_args()
    if not 0<a.max_wait_s<=14400:raise ValueError('Watch time may not exceed four hours')
    root=a.local_root.resolve();root.mkdir(exist_ok=True,parents=True)
    lock=(root/'six_report_watch.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    owner=dict(pid=os.getpid(),started_unix=time.time(),max_wait_s=a.max_wait_s,can_dispatch=False,
               script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with (root/'six_report_watch_owner.json').open('x') as f:json.dump(owner,f,indent=2)
    started=time.time();last=None;seen=None
    while time.time()-started<a.max_wait_s:
        try:
            state=snapshot(a.host,a.remote_root);last=state
            signature=(state['queue_status'],state['starts'],len(state['entries']))
            if signature!=seen:
                sync_finished(a.host,a.remote_root,root,state['entries']);seen=signature
                print(json.dumps(state,ensure_ascii=False),flush=True)
            if state['queue_status'] in TERMINAL:break
        except Exception as error:print(json.dumps(dict(readonly_monitor_error=str(error))),flush=True)
        time.sleep(30)
    if last is None:raise RuntimeError('No remote state; cannot invent result')
    sync_finished(a.host,a.remote_root,root,last['entries'])
    result=evaluate(root);result['watch_deadline_snapshot']=last['queue_status'] not in TERMINAL
    out=root/'comparison';out.mkdir(exist_ok=False)
    (out/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (out/'研究效果对比.md').write_text(render(root,result));publish(a.main_dir,out,result)
    print(json.dumps(dict(report_ready=str(out),status=result['state']),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
