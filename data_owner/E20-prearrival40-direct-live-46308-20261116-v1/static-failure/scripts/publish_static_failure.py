from pathlib import Path
import json,hashlib,datetime,base64,subprocess,shlex
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;N=M.name;X=json.loads((M/'closed-static-compile-readonly-export.json').read_bytes());r=json.loads((M/'asset-compile-result.json').read_bytes());assert not r['passed']and X['scope']['zero_dispatch_count']==X['scope']['main_dispatch_count']==0 and X['H_mirror_equal']and not X['MJB_exists']and not X['task_runtime_root_exists'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();D=B/'consumer-deliveries/AINAV-DATA-E20-PREARRIVAL40-STATIC-ASSET-GEOM-LOOKUP-FAILED-NO-ZERO-MAIN-20261116-v1';D.mkdir();files={}
for name in ['asset-compile-result.json','asset-compile-freeze.json','asset-compile-authority.json','asset-compile-exit.json','asset-compile-protocol.json','source-intake.json','predeployment-static-check.json','local-predeployment-errors-retained.json']:
 p=D/'original'/name;p.parent.mkdir(exist_ok=True);p.write_bytes((M/name).read_bytes());files[str(p.relative_to(D))]=sha(p)
check={k:v for k,v in X.items()if k!='original_small_files'};(D/'closed-readonly-verification.json').write_text(json.dumps(check,ensure_ascii=False,indent=2)+'\n');files['closed-readonly-verification.json']=sha(D/'closed-readonly-verification.json')
readme=f'''# E20+40mm提前原brake候选：新静态资产构造失败；zero0/main0

新source `5a1a92b153a23a91a5ec79ef4355f36af2d3fe51`，场景08a260a4…，固定规则43998a23…，单点40mm预登记DEV假设。用户环境参数适配授权原件已读；这是新C20cm目标/通路版本，不是旧V4 .60m通过，也不能把新环境+策略+I/O变化归为孤立算法收益。

## 实际发生

- Data新scope `{r['scope_id']}`，在独立静态子程序完整485成员SHA冻结 **{X['scope']['asset_compile_freeze_sha256']}** 后，fresh GPU0 UUID/原canonical锁/容量/权威H CAS准入，仅派一次静态资产构造。
- 原SDK PushBridge零任务步资产准备，在新`complex_e_skill20_arrival_v3/v4_native_asset.py:97`执行`sim.spec.geom(obj['body_name']+'_geom').rgba=...`时，geom名字查询返回None，报 **`{r['error']}`**。本次新复杂场景`spec.compile()`尚未执行；无新E20 MJB、task Runtime、任务步或Actor forward；**own-zero0/main0**，40mm brake的动态效果仍未测试。
- 最小责任点：AINav新v4_native_asset的spec构造/新增geom名字lookup及其原SDK3.3.2行为接缝。父base构造源码明确add_geom带名，但回到wrapper查找仍None；仅凭此不猜唯一缓存/对象生命周期根因。需owner修准确spec引用/lookup，不以None dummy/跳染色/借旧.6 MJB/降低成功安全门掩盖，不在已失败spec上继续编译。
- 静态构造墙钟 **{r['wall_s']:.9f}s**、峰值RSS **{r['peak_RSS_bytes']}bytes**、task0/aux0/Actor forward0/Runtime0、close_errors=[]。原GPU own_compute_bytes/peak为None，状态CUDA_UNINITIALIZED_NO_PID_ROW；保None，不伪测量0。原费用不当主任务成功成本或货币总费。本地未冻结路径/生成器错误另附原记录，均在SSH/H/原生前被修正；未洗掉历史。

## 已安全闭合

H为CLOSED_STATIC_ASSET_FAILED_NO_ZERO_MAIN，compile计数1、zero0/main0，PID243226已结束、GPU0两个原inode3428729629/30已释放，H镜像一致，485源/SDK/构造成员在关闭后再次逐SHA一致。原scope所有冻源保持，新MJB及task root均不存在，main完整freeze/zero/相机/E20截图/原片没有被冒造。

原E59唯一main的失败、486帧完整1×原片、全流cold、40836ff0…25条原命令证据均保留。AINav已于17:35发布精确窗口消费回执，不冒其消费本新失败。下一项是其spec/geom接缝修复；修复需明确新source/资格/有限新程序，不能在此closed scope重跑。无需WM/VLM/额外模型前置或再次经济审批，但源码发布仍不自签native资格。Data不替AINav热patch其源码，不扫40mm、不换seed追胜，不改变旧scope用途。
'''
(D/'README_CN.md').write_text(readme);files['README_CN.md']=sha(D/'README_CN.md');release=dict(schema='Data-E20-preregistered40mm-static-asset-lookup-failure-no-zero-main-v1',at=datetime.datetime.now().astimezone().isoformat(),scope_id=r['scope_id'],source_commit=r['source_commit'],compile_program_sha256=X['scope']['asset_compile_freeze_sha256'],compile_result_sha256=sha(M/'asset-compile-result.json'),actual_static_dispatches=1,actual_own_zero_dispatches=0,actual_main_dispatches=0,actual_task_steps=0,actual_aux_sim_s=0,Actor_forwards=0,Runtime_calls=0,new_E20_MJB_created=False,new_E20_video_or_image_created=False,static_error=r['error'],error_location='complex_e_skill20_arrival_v3/v4_native_asset.py:97',actual_compile_wall_s=r['wall_s'],peak_RSS_bytes=r['peak_RSS_bytes'],own_GPU_peak_bytes_original=None,usage_known=True,close_errors=[],scope_closed=True,no_retry=True,old_E59_main_not_reopened=True,not_E20_main_or_PUSH_or_CLIMB_failure=True,training_allowed=False,model_input_allowed=False,files=files);(D/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n')
code=r'''
from pathlib import Path
import json,base64,sys,hashlib
x=json.load(sys.stdin);D=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/consumer-deliveries')/x['name'];assert not D.exists();D.mkdir()
for name,v in x['files'].items():
 p=D/name;assert p.resolve().is_relative_to(D);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(base64.b64decode(v))
r=json.loads((D/'release.json').read_bytes())
for rel,pin in r['files'].items():assert hashlib.sha256((D/rel).read_bytes()).hexdigest()==pin
print(json.dumps(dict(remote_release=str(D/'release.json'),release_sha256=hashlib.sha256((D/'release.json').read_bytes()).hexdigest(),all_files_SHA_match=True,no_frozen_source_runtime_H_or_old_release_change=True)))
''';payload=dict(name=D.name,files={str(p.relative_to(D)):base64.b64encode(p.read_bytes()).decode()for p in D.rglob('*')if p.is_file()});a=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(payload),capture_output=True,text=True,timeout=60);assert a.returncode==0,a.stderr;p=json.loads(a.stdout);assert p['release_sha256']==sha(D/'release.json');(M/'static-failure-publication-proof.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(local_release=str(D/'release.json'),**p),ensure_ascii=False))
