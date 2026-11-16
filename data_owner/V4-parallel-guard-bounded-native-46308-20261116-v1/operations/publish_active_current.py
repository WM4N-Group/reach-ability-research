"""One Data-only current-state publication after actual new program dispatch.
No worker/H/cap/source mutation; old actual result history is preserved.
"""
from pathlib import Path
import json,hashlib,datetime,os,fcntl,tempfile,re
M=Path(__file__).resolve().parent;B=M.parents[1];now=datetime.datetime.now().astimezone().isoformat();sha=lambda raw:hashlib.sha256(raw).hexdigest();pp=json.loads((M/'latest-readonly-pointer.json').read_text());raw=Path(pp['path']).read_bytes();assert sha(raw)==pp['sha256'];x=json.loads(raw);q=x['H_scope'];assert q and q['active']and q['component_zero_dispatch_count']==1 and q['task_main_dispatch_count']==0 and x['local_H_mirror_matches_at_observation']
assert not x['actual_small'].get('result.json'),'If already ended, publish actual closeout instead of active claim'
inv=json.loads((M/'inventory-control-proof.json').read_bytes());cfg=json.loads((B/'workers'/M.name/'protocol.json').read_bytes());assert inv['program_sha256']==x['program_sha256']==q['whole_program_freeze_sha256'];assert inv['members']==498 and cfg['wall_cap_s']==21600 and cfg['metadata_path_read_threads']==8
assert sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes())==cfg['main_plan_sha256']
capture_samples=[]
for line in x['event_tail'].splitlines():
 try:
  row=json.loads(line).get('payload',{})
  if row.get('event')=='cold_capture_actual_sample':capture_samples.append(row)
 except json.JSONDecodeError:pass
capture_sample=capture_samples[-1]if capture_samples else None
point=x['last_timing_checkpoint'];progress='当前已启动新worker，真实分段耗时以原profiling流为准，未把CPU fixture当native提速。'if point is None else f"已观测原checkpoint {point['task_steps']}命令/{point['task_sim_s']:.3f}任务sim、{point['wall_s']:.3f}wall；分段仅本组件实测，不是方法收益。"
if point is None and capture_sample is not None:progress=f"原capture sample已到{capture_sample['time_s']:.3f}任务sim（该样本complete={capture_sample['complete']}，不是整链/技能成功）；首400步profiling checkpoint尚未到，不先报native提速。"
record=dict(at=now,observed_capture_sample=capture_sample,role='EXACT_SOURCE41_PARALLEL_CURRENT_GUARD_NEW_BOUNDED_COMPONENT_ACTUALLY_DISPATCHED_NOT_FIVE_ARM',source_commit=cfg['new_source_owner_commit'],program_sha256=x['program_sha256'],program_members=498,authority_sha256=inv['authorization_sha256'],scope_id=cfg['scope_id'],actual_worker_PID=None if x['process']is None else x['process']['PID'],new_component_zero_dispatches=1,five_arm_main_calls=0,API_WM_fit_calls=0,source41_native_qualified=False,latest_observation=str(Path(pp['path'])),latest_observation_sha256=pp['sha256'],actual_timing_checkpoint=point,old_closed_programs_and_costs_unchanged=True,concrete_repair_not_just_39_plus_longer_wall=True,wall_capacity_design=cfg['wall_capacity_design'],caps={k:cfg[k]for k in ['task_world_steps_allowed','task_world_sim_cap_s','wall_cap_s','output_cap_bytes','own_GPU_cap_bytes','own_RSS_cap_bytes','CPU_threads','metadata_path_read_threads']},resource_snapshot=inv['resources'],no_cross_tick_cache_or_module_filter=True,original_native_rules_not_extended_or_weakened=True,no_layout_or_model_or_J_purpose_change=True,not_native_success_or_HD_task_video_or_method_gain=True)
with(M/'Data-source41-exact-program-active.json').open('x')as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')
paragraph=f"- **具体41源修复后的新完整bounded资格已实际派发，不是旧scope重跑：** AINav immutable **2ab8b8ae…/41源＋7 parent**已逐SHA接入；原全CURRENT module Path.resolve并行8纯读/前后双遍＋原guard字节码两遍、callback/world/owner检查保留，五组共同底座，不归因BD优化。Data新program **{x['program_sha256'][:12]}…/498成员**、authority{inv['authorization_sha256'][:12]}…已fresh资源→远端directory/file flock SHA-CAS freeze→默认OFF prepare(task0)→唯一component-zero1/main0；PID{x['process']['PID'] if x['process'] else '见原child'}，H镜像一致，旧v1/v2/bulk24/asset/capture仍closed且所有其他H字段保留。仅API0公开首箱PUSH→20cm CLIMB→同箱top-centre NAV（最多一次共有ground approach），**不是C/E方法或整场/五组成功**；fresh Runtime/FIFO，旧静态MJB只读，不恢复旧state。{progress}新独立cap仍180task sim/36000步/1GiB、GPU0原UUID/双inode、own3GiB/RSS4GiB/CPU36,37，Torch2线程＋元数据8读线程；基于具体代码修复另设计有限21600wall（.55×36000＋1800初始化/额外guard余量，非时长保证）/60s teardown reserve，不改旧1800wall或任何Actor/12N/4s/FF/effort/QP/FIFO/CLIMB stop；原生拒绝/资源截断照留、无自动retry。新worker记录实际Data guard/step分段、每400命令checkpoint和精确capture完成边界，finally关自己的metadata线程并保原native/writer/lease teardown。fresh owned26,136,450,560bytes/40GiB、预留13,421,772,800bytes、quota未知。原件：`{M/'Data-source41-exact-program-active.json'}`；五组main/WM/API/fit/完整任务HD片仍0，布局及J用途不变。\n"
newstamp='更新：'+now+'（北京时间；计划be3aa7e5…未变；**source41具体并行全路径guard修复后，新准确bounded component-zero1在途/五main0；旧v1/v2等全部保持closed，不借用旧资格**）'
oldnext='Data文件访问分段已完成并与AINav热点观测交叉界定；接续需具体保语义的源码/运行条件改进，而非再重复同一probe。'
newnext='已有source41具体保语义guard修复并冻结/派发独立新bounded资格；当前只跟踪其真实分段吞吐与原native端点，按新有限预算收束，任何失败/censor不自动重试。'
proof=[]
for path in [B/'STATUS.md',B/'README.md',B/'AGENTS.md',Path('/home/yuanyue/main/汇总/各小组进展汇总.md')]:
 before=path.read_bytes();pin=sha(before);shared=path.name=='各小组进展汇总.md'
 if shared:
  i=before.index('## Data组\n'.encode());j=before.index(b'\n## ',i+1);prefix,suffix=before[:i],before[j:];chunk=before[i:j].decode()
 elif path.name=='STATUS.md':
  a=b'<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';z=b'<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=before.index(a)+len(a);j=before.index(z,i);prefix,suffix=before[:i],before[j:];chunk=before[i:j].decode()
 else:prefix=suffix=b'';chunk=before.decode()
 assert oldnext in chunk and 'Data-source41-exact-program-active.json'not in chunk
 chunk=chunk.replace('\n**下一步**\n','\n'+paragraph+'\n**下一步**\n',1).replace(oldnext,newnext,1)
 chunk=re.sub(r'更新：2026-11-16T06:56:35\.384629\+08:00[^\n]*',newstamp,chunk,count=1)
 chunk=chunk.replace('## 当前最高执行入口：bounded-v2原wall resource-censor已closed，先定位吞吐，不盲重跑/借39资格','## 当前最高执行入口：source41新准确bounded资格在途，旧v1/v2仍closed，不冒五组结果',1)
 out=prefix+chunk.encode()+suffix;dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);ffd=None
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX);ffd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW);fcntl.flock(ffd,fcntl.LOCK_EX);st=os.fstat(ffd);assert sha(path.read_bytes())==pin and(path.stat().st_dev,path.stat().st_ino)==(st.st_dev,st.st_ino)
  mode=st.st_mode&0o7777;fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.Data41-cas-',dir=path.parent)
  try:
   os.fchmod(fd,mode)
   with os.fdopen(fd,'wb')as f:f.write(out);f.flush();os.fsync(f.fileno())
   assert sha(path.read_bytes())==pin;os.replace(tmp,path);os.fsync(dfd)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
  assert path.read_bytes()==out and path.stat().st_mode&0o7777==mode
  if shared:assert out[:i]==prefix and out[-len(suffix):]==suffix
  proof.append(dict(path=str(path),before_sha256=pin,after_sha256=sha(out),mode=mode,peer_bytes_preserved=shared,only_Data_current_changed=True))
 finally:
  if ffd is not None:os.close(ffd)
  os.close(dfd)
with(M/'active-current-publication-proof.json').open('x')as f:json.dump(dict(at=now,CAS_flock_atomic_preserve_mode=True,files=proof,no_inflight_source_cap_or_H_mutation=True),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(program=x['program_sha256'],source41_new_component_in_progress=True,progress=progress,shared_Data_only_updated=True),ensure_ascii=False))
