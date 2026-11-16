"""Data-only current state after actual new model proof; not full component/method success."""
from pathlib import Path
import os,json,hashlib,datetime,fcntl,tempfile,re
M=Path(__file__).resolve().parent;B=M.parents[1];now=datetime.datetime.now().astimezone().isoformat();sha=lambda raw:hashlib.sha256(raw).hexdigest();D=B/'consumer-deliveries/AINAV-DATA-PALETTE-V2-STATIC-DELTA-PASS-NATIVE-INFLIGHT-20261116-v1';release=json.loads((D/'release.json').read_bytes());assert sha((D/'release.json').read_bytes())=='8bcc837edaff6716bc8c3aa220e0b34466747e0a62d0a622ad261d2fb00bb893'
for n,pin in release['files'].items():assert sha((D/n).read_bytes())==pin
pp=json.loads((M/'latest-readonly-pointer.json').read_bytes());raw=Path(pp['path']).read_bytes();assert sha(raw)==pp['sha256'];x=json.loads(raw);q=x['H_scope'];assert q['active']and q['component_zero_dispatch_count']==1 and q['task_main_dispatch_count']==0 and x['local_H_mirror_matches_at_observation']and x['process']and not x['actual_small'].get('result.json');inv=json.loads((M/'inventory-control-proof.json').read_bytes());assert inv['members']==507 and inv['program_sha256']==x['program_sha256'];proof=json.loads((D/'new-common-appearance-static-delta-proof.json').read_bytes());delta=proof['common_appearance_revision']['compiled_render_only_delta_proof'];assert delta['unchanged_nonRGBA_array_count']==398 and delta['only_changed_array']=='geom_rgba'and len(delta['only_changed_rows'])==3 and delta['engine_options_unchanged']and delta['topology_names_paths_unchanged'];point=x['last_timing_checkpoint'];assert point['task_steps']>=400;plan=sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes());assert plan=='be3aa7e587e5aa990375d1085dde6affc497861c1d45ab01862edc2793501845'
summary=dict(at=now,role='AF09_NEW_EXACT_PALETTE_V2_STATIC_RENDER_ONLY_DELTA_ACTUALLY_PASSED_NATIVE_COMPONENT_STILL_INFLIGHT',source_commit='af09da7ddbaa791782cf5fd4873d14064d64b1fd',program_sha256=x['program_sha256'],authority_sha256=inv['authorization_sha256'],scope_id=q['scope_id'],PID=x['process']['PID'],component_zero1_main0=True,actual_new_MJB_sha256=proof['model_sha256'],appearance_revision_id=proof['common_appearance_revision']['revision_id'],appearance_contract_sha256=proof['common_appearance_revision']['contract_sha256'],static_398_nonRGBA_arrays_options_counts_names_paths_unchanged=True,only_changed_RGBA_rows=delta['only_changed_rows'],static_proof_subset_release=str(D/'release.json'),static_proof_subset_release_sha256=sha((D/'release.json').read_bytes()),whole_component_still_inflight_not_native_or_method_qualified=True,current_capture_checkpoint=point,post_NAV_fresh_association_and_Push_CLIMB_topNAV_success_unproved=True,old_brown_not_same_visible_environment_comparison=True,all_five_future_arms_must_freeze_same_new_asset_if_adopted=True,old_palette_v1_null_aux_usage_false_and_all_old_costs_preserved=True,staging_KeyError_missing_remote_root_preserved_only_empty_transport_continued=True,no_WM_API_fit_or_J_grant=True,whole_artifact_model_input_allowed=False,training_allowed=False,resources=inv['resources'])
with(M/'Data-af09-static-pass-component-active.json').open('x')as f:json.dump(summary,f,ensure_ascii=False,indent=2);f.write('\n')
para=f'- **af09具体SDK修复后的palette v2已实际静态PASS，独立新组件在途（非五组成功）：** 新source **af09da7d…/50**修三个target各一次、其它含匿名geom按index保RGBA；新program **{x["program_sha256"][:12]}…/507**、authority{inv["authorization_sha256"][:12]}…已fresh资源→远端directory/file flock SHA-CAS→default-OFF prepare→自身component-zero1/main0，PID{x["process"]["PID"]}，H镜像一致，旧e74/v1及所有旧scope/未知费用均未动。新MJB **{proof["model_sha256"][:12]}…**已真实编译，**398个nonRGBA arrays逐byte＋engine options/counts/names/paths全同，唯一变更geom_rgba的85/86/87三箱行**；不是仅metadata fixture。共享appearance合同75842a43…不变，若未来ABCDE采用须同此新资产，不能将旧brown当同视觉环境arm比较/BD收益。现fresh Runtime已进入原capture，checkpoint **{point["task_steps"]}命令/{point["task_sim_s"]:.3f}任务sim/{point["wall_s"]:.3f}wall**，static compile+真实delta proof7.482s；**整组件/后NAV fresh关联/PUSH→20cm CLIMB→topNAV仍未过，不签palette解决歧义或方法收益**。新独立cap180sim/36000步/36000wall(10h)/1GiB，GPU0原UUID/锁、own3GiB/RSS4GiB/CPU36,37/Torch2＋8读线程及原12N/NN/STOW/FF/QP/FIFO/4s/stop不变，不延旧scope/不自动重试。source record缺remote_code_root导致一次纯staging KeyError已保留；仅核实provider af09目录、双空暂存目录/无H注册后完成transport，非物理重跑/源hotfix。原静态子集release **8bcc837e…**：`{D/"release.json"}`，同一scope子集不加物理样本；状态`{M/"Data-af09-static-pass-component-active.json"}`。五main/API/真实WM forward/fit/J用途/完整任务HD片0，原箱/平台/布局保持。\n'
proofs=[]
for path in [B/'STATUS.md',B/'README.md',B/'AGENTS.md',Path('/home/yuanyue/main/汇总/各小组进展汇总.md')]:
 before=path.read_bytes();pin=sha(before);shared=path.name=='各小组进展汇总.md'
 if shared:
  i=before.index('## Data组\n'.encode());j=before.index(b'\n## ',i+1);prefix,suffix=before[:i],before[j:];chunk=before[i:j].decode()
 elif path.name=='STATUS.md':
  begin=b'<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';end=b'<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=before.index(begin)+len(begin);j=before.index(end,i);prefix,suffix=before[:i],before[j:];chunk=before[i:j].decode()
 else:prefix=suffix=b'';chunk=before.decode()
 assert 'Data-af09-static-pass-component-active.json'not in chunk
 chunk=chunk.replace('\n**下一步**\n','\n'+para+'\n**下一步**\n',1)
 chunk=chunk.replace('## 当前最高执行入口：source50静态name ABI资格失败已closed，未改色/未入任务，不重跑','## 当前最高执行入口：af09新palette v2真实静态delta已过、原生组件在途；旧v1仍closed',1)
 chunk=re.sub(r'更新：2026-11-16T10:34:28\.908534\+08:00[^\n]*','更新：'+now+'（北京时间；计划be3aa7e5…未变；**af09新palette v2实际仅RGBA delta已过，独立component-zero1在途/五main0；旧v1静态失败与41关联拒绝及未知费用全部保持closed**）',chunk,count=1)
 old='41真实RGBD准入拒绝与50新appearance静态ABI失败均已分别closed交付。当前先由AINav修source50对合法未命名SDK geoms的name假设；新palette当前关联效果仍未知、原41两query继续作为原问题证据，不能重开旧scope/跳static比较/降低RGBD门。只有具体合格修复到件后才评审新准确程序；当前native worker与派发队列0。'
 assert old in chunk;chunk=chunk.replace(old,'原41/current-RGBD拒绝及palette v1静态ABI失败保持closed；具体af09修复后的新准确v2已完成真实static delta并在途，当前按新固定预算跟踪capture/原NAV后fresh关联及bounded链，完整失败/拒绝/censor照留、不改原RGBD/安全门，不为采用胶水重复成功scope。',1)
 out=prefix+chunk.encode()+suffix;dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);ffd=None
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX);ffd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW);fcntl.flock(ffd,fcntl.LOCK_EX);st=os.fstat(ffd);assert sha(path.read_bytes())==pin and(path.stat().st_dev,path.stat().st_ino)==(st.st_dev,st.st_ino);mode=st.st_mode&0o7777;fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.Data-palette-v2-',dir=path.parent)
  try:
   os.fchmod(fd,mode)
   with os.fdopen(fd,'wb')as f:f.write(out);f.flush();os.fsync(f.fileno())
   assert sha(path.read_bytes())==pin;os.replace(tmp,path);os.fsync(dfd)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
  assert path.read_bytes()==out and path.stat().st_mode&0o7777==mode
  if shared:assert out[:i]==prefix and out[-len(suffix):]==suffix
  proofs.append(dict(path=str(path),before_sha256=pin,after_sha256=sha(out),mode=mode,only_Data_current_changed=True,peer_bytes_preserved=shared))
 finally:
  if ffd is not None:os.close(ffd)
  os.close(dfd)
with(M/'active-static-pass-current-publication-proof.json').open('x')as f:json.dump(dict(at=now,files=proofs,CAS_flock_atomic_preserve_mode=True,no_inflight_source_H_or_caps_changed=True),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(program=x['program_sha256'],new_MJB=proof['model_sha256'],actual_static398_nonRGBA_pass=True,component_inflight_not_task_success=True,shared_Data_only_updated=True),ensure_ascii=False))
