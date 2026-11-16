"""Publish first real phase costs + exact45 candidate intake; no hot source/H mutations."""
from pathlib import Path
import json,hashlib,datetime,os,fcntl,tempfile,re
M=Path(__file__).resolve().parent;B=M.parents[1];Q=B/'manifests/V4-parallel-guard-bounded-native-46308-20261116-v1';sha=lambda raw:hashlib.sha256(raw).hexdigest();now=datetime.datetime.now().astimezone().isoformat();p=json.loads((Q/'latest-readonly-pointer.json').read_bytes());raw=Path(p['path']).read_bytes();assert sha(raw)==p['sha256'];x=json.loads(raw);scope=x['H_scope'];assert scope['active']and scope['component_zero_dispatch_count']==1 and scope['task_main_dispatch_count']==0 and x['local_H_mirror_matches_at_observation']and not x['actual_small'].get('result.json');capture=x['actual_small']['actual-supported-capture-completion-boundary.json'];assert capture['task_steps']==capture['report']['actual_steps']==448 and abs(capture['task_sim_s']-2.24)<1e-7 and capture['report']['complete']and capture['report']['stable_seconds']>=.5-1e-7 and min(capture['report']['metrics']['foot_normal_N'])>=12
point=x['last_timing_checkpoint'];assert point['task_steps']>=1600 and point['metrics']['original_native_execution']['commands']>=1152;v=json.loads((M/'Data-source45-received-no-hot-adoption.json').read_bytes());assert v['active_source41_program']==scope['whole_program_freeze_sha256'];plan=sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes());assert plan=='be3aa7e587e5aa990375d1085dde6affc497861c1d45ab01862edc2793501845'
report=dict(at=now,role='FIRST_ACTUAL_EXACT41_CAPTURE_BOUNDARY_AND_LIVE_SOFTWARE_PHASE_COSTS_NOT_SUCCESS_OR_CAUSAL_SPEEDUP',program_sha256=scope['whole_program_freeze_sha256'],source_commit='2ab8b8aed166f74039db25e50fc7cabf1e0610cc',raw_observation_path=p['path'],raw_observation_sha256=p['sha256'],actual_capture_completion_boundary=capture,actual_last_checkpoint=point,avg_capture_plus_assembly_wall_per_command=point['metrics']['capture_or_assembly']['wall_s']/point['metrics']['capture_or_assembly']['commands'],avg_native_execution_loop_wall_per_command=point['metrics']['original_native_execution']['wall_s']/point['metrics']['original_native_execution']['commands'],Data_guard_cost_overlaps_step_intervals_not_additive_total=True,no_original_v2_matched_counterfactual_or_method_speedup=True,no_native_Push_CLIMB_topNAV_success_inferred=True,usage_still_inflight_no_final_ledger_or_cold_NPZ_audit=True,source45_received_not_hot_adopted=v['cloud_commit'],five_arm_or_WM_API_fit_calls=0)
with(Q/'first-actual-capture-and-phase-costs.json').open('x')as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
readme=f'''# Source45方法候选只读收件＋Source41在途首次真实分段成本\n\n{now}，主计划{plan}未变。\n\n- Data逐SHA核远端不可变0270381f…的45个V4成员，并保存392,192bytes精确代码副本。仅AST解析，不import、构造backend/roles/caller、不发API/加载模型、不重复owner的fixture；parent370未重审/不冒资格。对41仅README/factor_scope变，新增backbone_entry/method_entry与两测试；41的guard/live_driver/scene/执行/终点collector字节未变。\n- 新C/D构造接线提供原full-course roles/tree/planner＋同一Reach选择器，默认OFF；C无新cost provider，D须显式共有B/D callable。task0时FactorJournal同对象接到wrapper/原planner/roles，拒绝已用计数/pending/分裂sink；旧无marker的API0技术policy分支仍原样。真实认证backend/方法决策/cost/WM/任务资格均未由源码或dunder-new软件检查证明。未来四组API容量保持原full-course100/8192/900000，不能误用1M实现上限；本次API0组件不调用任何backend。\n- 当前唯一物理在途**仍是41源**，program edb78627…/498，PID167290，component-zero1/five-main0；不热换45、不将41结果倒贴45、不新增scope/转J/重复成功点采用胶水。\n- 已保存41本次448命令/2.240sim真实capture完成边界：连续.500s，四脚≥12N。首真实profiling checkpoint1600命令/8.000sim/1352.424wall：capture＋装配449调用/448命令/331.180s，native执行loop1152调用/1152命令/956.766s；Data owner/resource guard7563次/483.217s。**guard成本与step区间重叠，不能相加造总成本；此loop含原控制/守卫/记录，不是纯Actor时间。** 仍只有原NAV Actor/goal-hold-arrival-capture事件，不能凭此造PUSH/CLIMB/topNAV succeeded/failed回执。\n- 这不是CPU fixture，也不是匹配反事实/system/BD收益证明；源41仍在途，最终result/ledger/原NPZ冷审未到。仍按21600wall/180sim/36000命令/1GiB及原native门收束，不加时/重试/改Actor/箱/平台/布局。\n\n收件：`{M/'Data-source45-received-no-hot-adoption.json'}`。真实阶段原件：`{Q/'first-actual-capture-and-phase-costs.json'}`。\n'''
with(M/'README.md').open('x')as f:f.write(readme)
para=f'- **41本次capture完成与首真实分段成本已记录，45新方法胶水仅候选：** 41源edb78627…的本次capture在**448命令/2.240sim**完成，原边界连续.500s/四脚≥12N，未用后来的gait报告回填；真实checkpoint **1600命令/8.000sim/1352.424wall**，其中capture＋装配449调用/448命令/331.180s，原native执行loop1152命令/956.766s；Data owner/resource guard7563次/483.217s。**guard与step区间重叠，不能相加；loop非纯Actor计时，非与旧v2匹配反事实/方法提速**。原NAV Actor及goal-hold-arrival-capture事件不等terminal/语义PUSH成功，本组件仍在途、无最终result/ledger/NPZ cold或五组结果。并行只读收件AINav **0270381f…/45成员**逐SHA/392,192bytes：新增原C/D roles/tree/planner＋同一Reach适配构造、task0共享FactorJournal连接wrapper/原planner/roles；默认OFF，backend认证/实际VLM/cost/WM/完整方法未验证。未来A—D原full-course容量100/8192/900000，不用1M实现上限；本次API0不调用backend。41 guard/live_driver/scene字节与45相同，但factor_scope已变，**绝不热换在途41或把41实际结果记成45资格，不为胶水重复成功scope**；41仍原21600wall/180sim/36000步/1GiB，无新scope/fit/J用途/布局变化。原件：`{Q/"first-actual-capture-and-phase-costs.json"}`、`{M/"Data-source45-received-no-hot-adoption.json"}`。\n'
proof=[]
for path in [B/'STATUS.md',B/'README.md',B/'AGENTS.md',Path('/home/yuanyue/main/汇总/各小组进展汇总.md')]:
 before=path.read_bytes();pin=sha(before);shared=path.name=='各小组进展汇总.md'
 if shared:
  i=before.index('## Data组\n'.encode());j=before.index(b'\n## ',i+1);prefix,suffix=before[:i],before[j:];chunk=before[i:j].decode()
 elif path.name=='STATUS.md':
  a=b'<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';z=b'<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=before.index(a)+len(a);j=before.index(z,i);prefix,suffix=before[:i],before[j:];chunk=before[i:j].decode()
 else:prefix=suffix=b'';chunk=before.decode()
 assert 'first-actual-capture-and-phase-costs.json'not in chunk
 old='原capture sample已到1.425任务sim（该样本complete=False，不是整链/技能成功）；首400步profiling checkpoint尚未到，不先报native提速。'
 assert old in chunk;chunk=chunk.replace(old,'本次capture已在448命令/2.240sim真实完成；首分段checkpoint1600命令/8.000sim见下，仍不冒整链成功/方法提速。',1)
 chunk=chunk.replace('\n**下一步**\n','\n'+para+'\n**下一步**\n',1);chunk=re.sub(r'更新：2026-11-16T08:27:40\.496394\+08:00','更新：'+now,chunk,count=1)
 out=prefix+chunk.encode()+suffix;dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);ffd=None
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX);ffd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW);fcntl.flock(ffd,fcntl.LOCK_EX);st=os.fstat(ffd);assert sha(path.read_bytes())==pin and(path.stat().st_dev,path.stat().st_ino)==(st.st_dev,st.st_ino);mode=st.st_mode&0o7777;fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.Data-stage-cas-',dir=path.parent)
  try:
   os.fchmod(fd,mode)
   with os.fdopen(fd,'wb')as f:f.write(out);f.flush();os.fsync(f.fileno())
   assert sha(path.read_bytes())==pin;os.replace(tmp,path);os.fsync(dfd)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
  assert path.read_bytes()==out
  if shared:assert out[:i]==prefix and out[-len(suffix):]==suffix
  proof.append(dict(path=str(path),before_sha256=pin,after_sha256=sha(out),mode=mode,only_Data_updated=True,peer_bytes_preserved=shared))
 finally:
  if ffd is not None:os.close(ffd)
  os.close(dfd)
with(M/'Data-only-stage-publication-proof.json').open('x')as f:json.dump(dict(at=now,files=proof,directory_file_flock_SHA_CAS_atomic_replace_preserve_mode=True,no_worker_H_cap_or_method_hot_switch=True),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(source41_capture448_complete_component_in_progress=True,actual_checkpoint_commands=point['task_steps'],source45_candidate_only=True,shared_Data_only=True),ensure_ascii=False))
