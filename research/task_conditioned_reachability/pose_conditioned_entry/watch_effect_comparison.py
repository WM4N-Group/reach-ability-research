"""One-shot read-only monitor + outcome report; no recurring automation or App.

An experiment stop/missing cell is not patched or restarted by this watcher.
It publishes once to owned progress/plan pages, never commits arbitrary files.
"""
import argparse,fcntl,hashlib,json,os,shlex,subprocess,time
from pathlib import Path
from build_effect_comparison import write_report

TERMINAL={'COMPLETED_APPROVED_SEQUENCE','PHYSICAL_STOPPED_PRESERVE_UNSPENT','STOPPED_SDK_SUPERVISOR_FAILURE_NO_RETRY',
    'WAIT_TIMEOUT_NO_SDK_CLAIM','WAIT_TIMEOUT_AFTER_SDK_UNSPENT_PHYSICAL','QUEUE_STOPPED_PRESERVE_NO_RETRY'}


def snapshot(host,remote):
    code="""from pathlib import Path
import sys,json
r=Path(sys.argv[1]);q=json.loads((r/'approved_queue_state.json').read_text());f=r/'physical_ledger.json';l=json.loads(f.read_text()) if f.exists() else {}
print(json.dumps(dict(queue_status=q['status'],ledger_status=l.get('status'),starts=l.get('starts',0),active=l.get('active'),entries=l.get('entries',[]),queue_pid=q['pid'])))
"""
    proc=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',host,'python3 - '+shlex.quote(remote)],input=code,text=True,capture_output=True,timeout=40)
    if proc.returncode:raise RuntimeError(proc.stderr.strip())
    return json.loads(proc.stdout)


def sync_finished(host,remote,local,entries):
    cmd=['rsync','-a','--include=/source/***','--include=/*.json','--include=/*.log','--include=/runs/']
    for item in entries:cmd.append('--include=/runs/'+item['output_name']+'/***')
    cmd+=['--exclude=*',host+':'+remote.rstrip('/')+'/',str(local)+'/']
    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
    if proc.returncode:raise RuntimeError(proc.stderr)


def publish(main_dir,out,report):
    if main_dir is None:return
    stamp=time.strftime('%Y-%m-%d %H:%M:%S%z');marker='<!-- pose-effect-comparison:'+report['source_manifest_sha256']+' -->'
    for name in ['当前进展.md','下一步计划.md']:
        path=main_dir/name
        if not path.exists():continue
        original=path.read_text()
        if marker in original:continue
        followup=('下一步先核本批配对和机制是否触发，不自动扩批或将剩余6次当新授权；完整穿障碍导航另锁协议。'
            if report['complete'] else '下一步先按具体中止/缺证原因处理；未运行仍unknown，不重试替换或擅自扩额；若还有在途作业，按原条件收尾。')
        block=f'''{marker}
## 自动研究效果对比已生成｜{stamp}

**结论：**{report['conclusion']} {report['mechanism_note']}

- source SHA：`{report['source_manifest_sha256']}`；新协议实际启动{report['starts']}/8；状态`{report['ledger_status']}`。每臂2个初态，仅开发先导，不是独立泛化或完整穿障碍导航。
- [打开研究效果对比HTML](<{str((out/'研究效果对比.html').resolve())}>)；[Markdown报告](<{str((out/'研究效果对比.md').resolve())}>)；完整数值/配对在同目录`comparison.json`。
- 包含全部注册格、成功/失败/unknown、同初态姿态差异、总耗时和实际退让消费；旧2次与旧14格记录不改。
- {followup}

---

'''
        first,rest=original.split('\n',1);updated=first+'\n\n'+block+rest.lstrip('\n')
        # Avoid clobbering another editor's change made after the read.
        if path.read_text()!=original:raise RuntimeError('Owned page changed during report publication; artifact retained, no overwrite')
        tmp=path.with_suffix('.comparison.tmp');tmp.write_text(updated);os.replace(tmp,path)


def main():
    p=argparse.ArgumentParser();p.add_argument('--host',required=True);p.add_argument('--remote-root',required=True);p.add_argument('--local-root',type=Path,required=True)
    p.add_argument('--main-dir',type=Path);p.add_argument('--watch-id',default='r2');p.add_argument('--max-wait-s',type=float,default=18000);a=p.parse_args()
    if not 0<a.max_wait_s<=18000:raise ValueError('Read-only watcher wait cap exceeded')
    if not a.watch_id.replace('-','').isalnum():raise ValueError('Invalid watcher identity')
    root=a.local_root.resolve();root.mkdir(parents=True,exist_ok=True)
    prefix='comparison_watcher_'+a.watch_id
    lock=(root/'comparison_watcher.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    owner=dict(pid=os.getpid(),started_unix=time.time(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        report_code_sha256=hashlib.sha256(Path(__file__).with_name('build_effect_comparison.py').read_bytes()).hexdigest(),max_wait_s=a.max_wait_s,
        can_launch_App_or_physical=False)
    with (root/(prefix+'_owner.json')).open('x') as f:json.dump(owner,f,indent=2);f.write('\n')
    journal=(root/(prefix+'.log')).open('x');previous=None;seen=-1;last=None;began=time.time()
    def emit(value):
        line=json.dumps(dict(time=time.time(),**value),ensure_ascii=False);print(line,flush=True);journal.write(line+'\n');journal.flush()
    try:
        while time.time()-began<a.max_wait_s:
            try:
                state=snapshot(a.host,a.remote_root);last=state
                signature=(state['queue_status'],state['ledger_status'],state['starts'],len(state['entries']),json.dumps(state['active'],sort_keys=True))
                if signature!=previous:emit(dict(event='state_change',**state));previous=signature
                if len(state['entries'])!=seen:
                    sync_finished(a.host,a.remote_root,root,state['entries']);seen=len(state['entries'])
                if state['queue_status'] in TERMINAL:break
            except Exception as error:emit(dict(event='readonly_monitor_error',error=str(error)))
            time.sleep(30)
        if last is None:raise RuntimeError('No source state could be read; no invented result')
        sync_finished(a.host,a.remote_root,root,last['entries'])
        out=root/'comparison';report=write_report(root,out)
        publish(a.main_dir,out,report)
        result=dict(owner,ended_unix=time.time(),report_dir=str(out),conclusion=report['conclusion'],starts=report['starts'],
            complete=report['complete'],all_raw_cases_preserved=True,source_status=last,deadline_snapshot=last['queue_status'] not in TERMINAL)
        with (root/(prefix+'_result.json')).open('x') as f:json.dump(result,f,indent=2);f.write('\n')
        emit(dict(event='COMPARISON_READY',report_dir=str(out),conclusion=report['conclusion'],complete=report['complete']))
    finally:journal.close()

if __name__=='__main__':main()
