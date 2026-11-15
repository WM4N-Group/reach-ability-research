"""Publish actual closed-pair evidence, Data section only; preserve peer bytes."""
from pathlib import Path
import os,json,datetime,hashlib,fcntl,stat,tempfile,subprocess,shlex,base64,ast
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');sha=lambda b:hashlib.sha256(b).hexdigest();now=datetime.datetime.now().astimezone().isoformat()
hr=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();h=json.loads(hr);q=h['active_T_COMPLEX_full_program_scope'];co=h['T_COMPLEX_full_program_v1'];assert q['arm']=='B'and not q['active']and q['zero_dispatch_count']==q['main_dispatch_count']==1
proofB=json.loads((M/'B/original-release-proof.json').read_bytes());D=B/'consumer-deliveries'/Path(proofB['release_path']).parent.name;r=json.loads((D/'release.json').read_bytes());audit=json.loads((M/'B/actual-main-cold-audit.json').read_bytes());assert all(r['nine_stream_checks'].values())and co['branches']['B']['actual_public_delivery']['release_sha256']==proofB['release_sha256']
plan=Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md');planpin=sha(plan.read_bytes());assert planpin=='b2fb786ec002b1e88ed4fc56a0bbfbac21d62cd788dacdda7d9fceb1a774c5a9'
I=B/'manifests/T-COMPLEX-observation-and-bulk24-source-intake-20261115-v1'
body=f'''## Data组

更新：{now}（北京时间；主计划仍14:00/b2fb786e…；T复杂首对A/B均真实闭合，B按原冻结wall停止，非B算法失败或方法胜负；已审计、发布同钟直接raw视频证据）

**最新真实终态／未重跑**
- **B唯一main已结束并CAS closed：** 原b08f51bb… source、B program0ba38395…、own-zero1/main1全保；原capture448步/2.240sim完成，实际首NAV cx-nav-000→(-.08,-1.8,0)原factory admitted/installed，原NAV Actor共**{r['actual_NAV_actor_forward_count']}次**。终态原错误 **`{r['source_error']}`**；resource_censored={str(r['resource_censored']).lower()}、task_success={str(r['task_success']).lower()}。真实主世界**{r['actual_task_sim_s']:.3f}sim/{r['actual_physics_steps']}步**，public bundle/实际高层选择仍**{r['actual_original_public_queries']}**，terminal native receipt **{len(r['actual_native_terminal_receipts'])}**、placement/重构**{r['actual_task_reconstructions']}**；未补造NAV成功/失败回执，不把Actor数当选择数或三有效选择。原625sim/4800wall/3GiB cap、Actor/12N/4s/FF/QP/FIFO/stop全程未改，closed不retry。原result **{r['source_result_sha256']}**。
- **资源／用量按实闭合：** B含自身zero/双aux合计**{r['actual_scope_including_zero_aux_sim_s']:.3f}sim/{r['actual_scope_ledger_wall_s']:.9f}ledger wall/{r['actual_scope_output_highwater_bytes']}bytes高水位**，all_usage_known={str(r['all_usage_known']).lower()}。冻结pair global_stop={str(co['global_stop']).lower()}保留，H **{sha(hr)}**；native已退出、两canonical锁原inode释放、无在途／未自动排新scope。资源wall停止不归因Reach .1954s search超限；recorder censored仅非成功标志，不混同resource censor。
- **B原流只读cold已完成：** 九项连续200Hz/FIFO/原PD/硬clip/previous-actions/同program与model/视觉review/teardown检查全过，{audit['journal_chain']['rows']}行journal原链；{audit['visual_frames']}原RGBD＋{audit['review_frames']}review＋**{r['direct_HD_raw_frames']}直接960×540 HD raw帧**，按实际physics tick完整grid、源SHA前后相同，无新Runtime/Actor/Renderer/replay。A原capture448步后的RGBD唯一关联门失败仍原解释，不是PUSH控制失败/几何死局；A closed15.250sim/880.527903158wall/218453439bytes、7afea491…发布不变。

**可交付与科学边界**
- **1×/同钟pair现已真实编码：** 仅消费这对原live-capture raw，A/B单片与同simulation-clock pair留46308；不重渲染、不插帧、不用旧TRAIN片，原960×540未裁切，状态注释只在新增头栏。A结束后为明确黑色“无后续观测”说明页，非冻结／补造世界；视频采样周期.1s、末帧容器时长不冒精确native终态时刻。**这是失败／资源截断episode完整可用证据，不是任务成功母版、三有效选择或lookahead胜出。** manifest `{M}/closed-pair-direct-video-manifest.json`，原视频路径/SHA与frame逐一映射均在内；本地仅小预览/metadata。
- **配对同信息证据不越界：** 两独立own-zero的numeric model/full integration state/INPUT8/HD相同，A/B实际capture前448命令8通道逐值相同、实际2.24首public observation（仅排除RGB存储path）/RGB/depth/K/T/45D相同，实际首选择A PUSH vs B NAV确实不同；不把初始nominal候选当当前原生合法候选、不用源观测域负例证明强greedy已输。只有这首对DEV/source资格诊断，无完整任务或前瞻优势证据。
- **正式B＋pair原件已发布并挂权威H：** release **{proofB['release_sha256']}**；`{D}/release.json`。A原发布/全部closed失败与旧46174 UNKNOWN尾部保留，视频/raw/MJB/权重不回本地或Git。

**下一独立工作／保持边界**
- 不因本pair资源停止而抬cap复跑。优先准备独立**OBSERVABILITY_QUALIFICATION_ONLY**测量新程序：已收c3c695b5…26源，固定capture→两次原NAV(−.08,+.15)/(−.08,−.15)→3真实边界、0PUSH，须按measurement终止，不套全任务while-not-complete；不挑最好帧/补视角/宣称PUSH READY。当前仅code接收，未新scope/freeze/lease/派发。另将当前真实吞吐与静态全module Path.resolve线索交source owner独立核等价开销优化；**尚无独立benchmark因果证据，不删安全检查，不改冻结pair**。
- bulk24仍原0fff23aa…五源／Reach0f9e0e03…24 ordinal、4几何/8contexts×3/一既有TRAIN祖先，scope/program均None，未预留全24容量/派发、未扩其余36组合。首优先T不等critic/百级全齐；长期≥100新尝试/≥10有意义组、唯一owner逐GPU滚动覆盖保留，不刷同输入或把观测测量计TRAIN。
- TRAIN6原13758867…4PASS2失败/27query、真实一次fit3371ac20…/modela8b1f165…gate=true冻结，Data不refit；CAL07原PASS119.345task sim及9249faef…不动，**CAL08/09与VAL10—12仍0/0**。后续按独立有效scope逐支准入，不与尚未释放的冻结authority混跑；旧closed/UNKNOWN/费用不洗，WM/DINO/Actor重训/真机/第二owner/新自动化不开。

**详细入口**：`{M}/README.md`、`{M}/B/`、`{D}/release.json`、`{I}/FUTURE_SOURCES_RECEIVED_NOT_DISPATCHED.json`。工作目录仍`{B}`，计算仅46308；本地＋GitHub保存code，远端保存大仿真／训练原件。
'''
(M/'README.md').write_text('# T复杂首对已闭合：A原关联门失败／B原wall资源censor；直接raw同钟证据已发布\n'+body.split('\n',1)[1]);entry='## 当前最高执行入口：T复杂首对A/B均closed；B原wall资源censor，非方法胜负，直接raw同钟证据已发布\n'+body.split('\n',1)[1]+'\n';proof=[];remote=[]
src=(M/'publish_full_program_current.py').read_text();tree=ast.parse(src);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='update');fn=ast.get_source_segment(src,node).replace('.before-full-program-A-main','.before-closed-B-pair').replace('.T-full-A-','.closed-B-pair-').replace('（北京时间；T完整程序A自身zero/cold通过、唯一main实派，B0/0；不是已完成对照）。','（北京时间；T复杂A/B已closed；B原wall资源censor，非方法胜负；原流审计与直接raw视频已发布）。');exec(compile(fn,'Data-only-closed-pair-updater','exec'),globals());update(S,True)
for name in ['STATUS.md','AGENTS.md','README.md']:update(B/name)
code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));r0=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
for suffix,text in [('stdout',r0.stdout),('stderr',r0.stderr)]:
 with(M/('closed-B-pair-entry-mirror.'+suffix)).open('x')as f:f.write(text)
with(M/'closed-B-pair-publication-CAS-peer-proof.json').open('x')as f:json.dump(dict(at=now,proof=proof,remote_exit=r0.returncode,H_not_written_by_entry_update=True,old_sources_and_counts_unchanged=True),f,indent=2);f.write('\n')
assert r0.returncode==0,r0.stderr;print('Published actual closed B/censored pair evidence; Data section only, peer bytes preserved')
