"""Bounded read-only download of actual live-camera video; no launch/rebuild."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import time


def main():
    p=argparse.ArgumentParser();p.add_argument('--host',required=True);p.add_argument('--remote',required=True);p.add_argument('--local',type=Path,required=True);p.add_argument('--main-dir',type=Path);args=p.parse_args()
    start=time.monotonic();last=None
    code='''from pathlib import Path
import json,sys
r=Path(sys.argv[1]);result={}
for name in ['sdk_terminal.json','physical_terminal.json','demo-result.json','video-supervisor-launch.json']:
 p=r/name
 if p.exists():result[name]=json.loads(p.read_text())
pid=result.get('video-supervisor-launch.json',{}).get('pid');result['supervisor_alive']=pid is not None and Path('/proc',str(pid)).exists()
p=r/'run/native-video-frames.jsonl';result['recorded_frames']=sum(1 for _ in p.open()) if p.exists() else 0
print(json.dumps(result))
'''
    while time.monotonic()-start<7200:
        proc=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',args.host,'python3 - '+shlex.quote(args.remote)],input=code,text=True,capture_output=True,timeout=45)
        if proc.returncode:print(proc.stderr,flush=True);time.sleep(15);continue
        state=json.loads(proc.stdout);last=state;print(json.dumps(state,ensure_ascii=False),flush=True)
        if 'physical_terminal.json' in state or (state.get('sdk_terminal.json',{}).get('returncode') not in (None,0)) or not state['supervisor_alive']:break
        time.sleep(20)
    if last is None:raise RuntimeError('No remote state, no invented video')
    # Full source and the ONE completed demo are small enough; no simulation replay.
    proc=subprocess.run(['rsync','-a','--exclude=__pycache__','--exclude=permits','--exclude=*.pyc',args.host+':'+args.remote.rstrip('/')+'/',str(args.local)+'/'],capture_output=True,text=True,timeout=300)
    if proc.returncode:raise RuntimeError(proc.stderr)
    video=args.local/'run/native-run-original-speed.mp4';metadata=args.local/'run/native-video.json'
    ready=dict(schema='native-live-video-download-v1',remote_snapshot=last,video=str(video),downloaded_video=video.exists(),
               source='live Isaac env.render RGB frames, NOT log reconstruction',deadline=time.monotonic()-start>=7200)
    if metadata.exists():ready['recording']=json.loads(metadata.read_text())
    (args.local/'video-ready.json').write_text(json.dumps(ready,ensure_ascii=False,indent=2)+'\n')
    if args.main_dir:
        marker='<!-- user-native-video-demo-result -->'
        outcome=ready.get('recording',{}).get('actual_task_outcome','未取得完整录像终态')
        block=f'''{marker}
## 用户要求的原生录像演示已收尾｜{time.strftime('%Y-%m-%d %H:%M:%S%z')}

单次原生画面演示状态：{outcome}；视频文件已同步={ready['downloaded_video']}。不是状态日志重建，不作为新增独立研究样本或方法收益证据。
视频：`{video}`；核验：`{args.local/'video-ready.json'}`。本次收尾后不再自动运行；原六格的未运行P3已按用户要求停止，其剩余一个预约仅用于本次录像演示，总物理上限仍16。

---

'''
        for name in ['当前进展.md','下一步计划.md']:
            path=args.main_dir/name;original=path.read_text()
            if marker in original:continue
            first,_,rest=original.partition('\n')
            if path.read_text()!=original:raise RuntimeError('Sync page changed concurrently; no overwrite')
            tmp=path.with_suffix('.native-video.tmp');tmp.write_text(first+'\n\n'+block+rest.lstrip('\n'));os.replace(tmp,path)
    print(json.dumps(ready,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
