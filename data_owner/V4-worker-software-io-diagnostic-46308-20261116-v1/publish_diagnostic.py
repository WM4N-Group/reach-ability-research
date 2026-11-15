"""Publish this CPU-metadata diagnosis once; only Data current text may change.
Never import any lifecycle/publish-once script or mutate H/old scopes.
"""
from pathlib import Path
import os,json,hashlib,datetime,fcntl,tempfile,re
B=Path('/home/yuanyue/main/work/data-team'); M=Path(__file__).resolve().parent
now=datetime.datetime.now().astimezone().isoformat();sha=lambda raw:hashlib.sha256(raw).hexdigest()
plan=Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md'); planpin=sha(plan.read_bytes());assert planpin=='be3aa7e587e5aa990375d1085dde6affc497861c1d45ab01862edc2793501845'
assert (M/'profile.exit').read_text().strip()=='0' and not (M/'profile.stderr').read_bytes()
p=json.loads((M/'profile.stdout').read_text());assert p['wall_s']<90 and p['peak_RSS_bytes']<512*1024**2 and p['native_model_import_constructor_forward_API_or_physics_calls']==0
assert p['scope_closed'] and not p['Data_native_workers']
assert p['old_pins_unchanged']['/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/registry/handoff_current_status_20261115.json']==sha((B/'registry/handoff_46308_current_status_20261115.json').read_bytes())
ain=Path('/home/yuanyue/main/work/ainav/consumer-deliveries/AINAV-V4-FIVE-ARM-ASSET-E-RULE-AND-CLIMB-GAP-20261115-v1/BOUNDED_V2_RESOURCE_CENSOR_AND_CPU_ALIAS_HOTSPOT_NO_ADOPTED_FIX.json'); a=json.loads(ain.read_bytes())
assert a['active_source_commit']=='accbe41e0fd44c893ca05b37ca880b4f22e290d9' and a['candidate_source_and_tests_preserved_not_committed_or_deployed']
def write(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
write(M/'Data-actual-worker-metadata-slice-profile.json',p)
times={k:v['median_wall_s'] for k,v in p['measurements'].items()}
assessment=dict(at=now,role='DATA_WORKER_SOFTWARE_IO_COST_NARROWING_NOT_NATIVE_SPEEDUP_OR_PHYSICAL_SAMPLE',plan_sha256=planpin,profiler_sha256=sha((M/'profile_readonly_remote.py').read_bytes()),profile_sha256=sha((M/'Data-actual-worker-metadata-slice-profile.json').read_bytes()),actual_closed_program='a0e8ada09e6cca82e1920774a0010f877b7f9821c4a766e55c3dbc07d09062f1',actual_closed_result='fe3d5f6cb9231f302ef3f919d247d9440de9ea2a5ef0456eea91d85762c922aa',measurement_median_seconds=times,AINav_own_diagnostic_original_path=str(ain),AINav_record_sha256=sha(ain.read_bytes()),AINav_metadata_guard_seconds=a['exact_guard_CPU_metadata_profile']['guard_seconds'],AINav_metadata_Path_resolve_seconds=a['exact_guard_CPU_metadata_profile']['sum_path_seconds'],AINav_no_stable_candidate_gain=True,own_slice_conclusion='H+AUTH read/parse/SHA about1.934ms; closed25-file output size scan18.751ms; these measured operations alone are much smaller than the separately measured1.244s module-path guard. GPU queries add variable tens-to-hundreds-ms cost on original>=1wall-second lease cadence, not every200Hz command.',no_original_live_guard_invoked=True,closed_authority_false_not_overridden=True,no_lease_or_CUDA_or_model_or_world=True,no_original_guard_timing_or_full_wall_attribution_claim=True,no_journal_or_episode_fsync_cost_claim=True,no_cross_tick_cache_or_module_filter_adopted=True,no_safety_budget_environment_or_actor_change=True,no_new_native_program_or_dispatch=True,no_J_training_purpose_or_fit_or_GPU_grant=True,source_owner_next='AINav: source guard/path resolution is the next concrete source-side candidate area; preserve fresh full sys.modules alias/callback and world identities. Existing parent-sharing candidate has no stable gain and is not accepted. Data will only freeze a genuinely repaired full program after concrete semantics-preserving code or operating-condition evidence; do not just extend wall/reuse39.',cost=dict(wall_s=p['wall_s'],peak_RSS_bytes=p['peak_RSS_bytes'],new_probe_bytes=p['new_independent_probe_bytes'],owned_bytes=p['owned_bytes'],provider_quota_unknown=True),limitations=p['limitations'])
write(M/'Data-software-io-assessment.json',assessment)
readme=f'''# Data worker有界软件/文件系统诊断（非物理实验）\n\n时间：{now}。计划SHA `{planpin}` 未变。\n\n- 实际closed-v2 worker的文件访问语句分段、只读元数据取样，每项3次；没有导入/执行worker、没有伪造active authority、没有lease/world/Actor/WM/forward/API。旧H、AUTH、worker/protocol、result/ledger/journal在诊断前后逐SHA相同；本机H镜像一致，Data native worker0，四canonical原inode的/proc/locks无持有记录（不是新lease）。\n- H为104,312bytes；H+AUTH两次JSON读取/解析+AUTH SHA中位 **1.934ms**；旧输出25文件的原rglob/is_file/stat式扫描 **18.751ms**；inode检查约 **0.020ms**。不能据此删除/稀释Data owner、预算或锁检查。\n- 原PerGpuLease的两个nvidia-smi查询各中位 **106.074/68.027ms**（三次明显波动）；原代码在≥1墙钟秒/force时查询，不是每条200Hz命令都查，不能直接乘978当成本。Torch/CUDA计数调用未测。\n- 新独立诊断目录3×4KiB的flush/fsync中位 **2.161ms**，不是旧journal/真实writer的flush成本；旧流未写、未回放。\n- 总wall **{p['wall_s']:.9f}s**（含du及读核）、峰RSS **{p['peak_RSS_bytes']}bytes**，独立probe12,288bytes，CPU诊断cap90s/512MiB；Data owned **{p['owned_bytes']}bytes/40GiB**，provider quota未知。\n\n## 结论与接续\n\n与AINav06:46独立CPU metadata观测的全模块guard1.244s/Path.resolve1.236s相比，这次Data实际文件访问切片小得多。**这是缩小候选成本范围，不是原v2逐tick完整profile/全wall归因，更不是已修复、native提速或方法收益。** 未重测AINav1325模块、未采用其无稳定改善的parent-sharing负候选、未迁环境、未作cross-tick cache/module过滤或放松guard。\n\n具体候选源侧仍由AINav维护；Data先保持全部scope closed，不因39源/新ID/更高wall盲重跑。必须有具体保安全语义的程序或运行条件改进后，再对新准确完整程序冻结/必要资格；不重用旧once。五组main0、WM真实forward0、完整任务/HD影片资格未建立；J2a尚无采集/fit/GPU派发。\n\n原结果与summary勘误均沿原parent/assessment child，未改旧scope、原源、预算、Actor、12N/4s/FF/effort/QP/FIFO/CLIMB stop。\n\n原始小profile：`{M/'Data-actual-worker-metadata-slice-profile.json'}`；解释：`{M/'Data-software-io-assessment.json'}`。\n'''
with (M/'README.md').open('x') as f:f.write(readme)
D=B/'consumer-deliveries/AINAV-DATA-V4-WORKER-SOFTWARE-IO-DIAGNOSIS-20261116-v1';D.mkdir(exist_ok=False)
for name in ['Data-actual-worker-metadata-slice-profile.json','Data-software-io-assessment.json','README.md']:
 (D/name).write_bytes((M/name).read_bytes())
write(D/'release.json',dict(at=now,role=assessment['role'],physical_sample=False,closed_scope_not_reopened=True,no_adopted_performance_fix=True,files={q.name:sha(q.read_bytes())for q in sorted(D.iterdir())},only_CPU_metadata_no_fit_or_dispatch=True))
paragraph=f'- **Data实际worker的软件/I/O切片已测，未冒已修复：** 06:54新有界CPU诊断只读closed-v2原路径/元数据，原H/authority/worker/result/ledger/journal SHA前后不变，未执行guard或伪造active/lease。三次中位：104,312byte H+AUTH读取/解析/SHA **1.934ms**；旧25文件output-cap扫描 **18.751ms**；lease两nvidia-smi查询各 **106.074/68.027ms**（原≥1wall秒 cadence，不是每200Hz步）；独立3×4KiB fsync **2.161ms**，非旧writer测量。总14.463s/23,629,824byte峰RSS，native/模型/CUDA/API0。对照AINav已测全module guard1.244s/Path.resolve1.236s，这些Data文件切片小得多，**仅缩小候选范围，非原v2逐tick全wall归因/已提速**；其parent-sharing候选无稳定改善未采用。四原inode无锁持有记录/worker0/H镜像一致，owned26,134,756,352bytes/40GiB、quota未知。未削弱owner/guard、未改环境/Actor/阈值或延时、未以39重跑；具体保语义source修复由AINav维护，新完整程序资格待真实改进。原件：`{D/"release.json"}`。\n'
next_old='先对壁钟/metadata-I/O瓶颈做有界定位并保原安全语义，'
next_new='Data文件访问分段已完成并与AINav热点观测交叉界定；接续需具体保语义的源码/运行条件改进，而非再重复同一probe。'
proof=[]
for path in [B/'STATUS.md',B/'README.md',B/'AGENTS.md',Path('/home/yuanyue/main/汇总/各小组进展汇总.md')]:
 before=path.read_bytes(); old=sha(before); shared=path.name=='各小组进展汇总.md'
 if shared:
  i=before.index('## Data组\n'.encode()); j=before.index('\n## ',i+1); prefix,suffix=before[:i],before[j:]; chunk=before[i:j].decode()
 elif path.name=='STATUS.md':
  marker='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->'.encode();end='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->'.encode();i=before.index(marker)+len(marker);j=before.index(end,i);prefix,suffix=before[:i],before[j:];chunk=before[i:j].decode()
 else:prefix=suffix=b'';chunk=before.decode()
 assert paragraph not in chunk and '\n**下一步**\n' in chunk and next_old in chunk
 chunk=chunk.replace('\n**下一步**\n','\n'+paragraph+'\n**下一步**\n',1).replace(next_old,next_new,1)
 # Only first current timestamp in this Data current chunk; historical stamps stay intact.
 chunk=re.sub(r'更新：2026-11-16T06:38:49\.995685\+08:00', '更新：'+now,chunk,count=1)
 out=prefix+chunk.encode()+suffix
 dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);ffd=None
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX);ffd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW);fcntl.flock(ffd,fcntl.LOCK_EX)
  assert sha(path.read_bytes())==old,'SHA CAS conflict, do not overwrite peers'
  mode=os.fstat(ffd).st_mode&0o7777;fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.data-cas-',dir=path.parent)
  try:
   os.fchmod(fd,mode)
   with os.fdopen(fd,'wb') as f:f.write(out);f.flush();os.fsync(f.fileno())
   os.replace(tmp,path);os.fsync(dfd)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
  final=path.read_bytes();assert final==out and (not shared or final[:i]==prefix and final[-len(suffix):]==suffix)
  proof.append(dict(path=str(path),before_sha256=old,after_sha256=sha(final),mode=mode,only_Data_section=shared,peer_bytes_preserved=shared))
 finally:
  if ffd is not None:os.close(ffd)
  os.close(dfd)
write(M/'publication-proof.json',dict(at=now,release=str(D/'release.json'),release_sha256=sha((D/'release.json').read_bytes()),CAS_directory_file_flock_atomic_preserve_mode=True,files=proof,no_H_or_physical_scope_mutation=True))
print(json.dumps(dict(release=str(D/'release.json'),profile_medians_seconds=times,shared_Data_only_updated=True),ensure_ascii=False,indent=2))
