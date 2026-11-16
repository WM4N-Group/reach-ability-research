# 新窗口接续 Reachability 组（完整交接prompt）

用户因上下文过长换窗口，**不是研究停工或暂停**。先完整读取本文件，再走最短入口核最新；不要从通读历史、重跑原AINav、重复CPU套件或再建接口开始。保留全部dirty，不重启closed，不把AINav工程/标准搜索/局部CPU倍率说成Reach方法收益。不创建子agent、新chat、Goal或自动化。

## 1. 工作区与最短入口

主代码仓库：`/home/yuanyue/reach-ability-research`，main；GitHub `WM4N-Group/reach-ability-research`。本次交接只改说明；交接前研究HEAD为deaad30，交接后实际HEAD请用git log核，不把本句当最新commit。主仓库交接前clean。

原继承dirty仓库：`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL`，feature/go2-piper-reachability-p0，HEAD4c998be60b2264999c5c033a2d011843bfd202a5，index空；所有dirty/untracked完整保留。只同步本组docs/AGENT_HANDOFF_CN.md，先核与主仓原bytes一致；不reset/clean/全量add/提交继承dirty。不覆盖人工报告。

最短读取（顶部当前段，不通读历史）：
1. 主仓AGENTS.md、docs/AGENT_HANDOFF_CN.md顶部；同目录WORKSPACE_STATE.json。
2. `/home/yuanyue/main/汇总/各小组下一步研究计划.md`。
3. `/home/yuanyue/main/反馈与同步/Reachability组/当前进展.md`、`下一步计划.md`顶部。
4. `/home/yuanyue/main/work/data-team/STATUS.md`当前段、`/home/yuanyue/main/work/ainav/docs/STATUS.md`顶部。
5. 有新正式交付才增量消费。不要重复已核原journal、数组cold或旧测试来刷进展。

## 2. 当前最高优先：PERF-01给真实结论，不扩接口

总计划2026-11-16 21:47，SHA：
`4af564bbc558a558ce1b42f91fda8e0b48db77ad47fa7a497475d091129d4a10`。

先消除重复I/O造成的吞吐瓶颈，再新增E/五组/bulk。Data唯一物理owner/runner交付主责；AINav只配合准确guard/fresh入口接缝；**Reach仅非阻断地核关键安全、费用和比较口径，不增加研究签字/新wrapper/main前置**。不要再刷完整旧CPU套件或多套同功能源码。

性能scope：同E20场景/初态/控制/资源/相机，独立新程序、自己的必要zero/lease/watchdog；优先预登记2000命令/10sim（4000/20sim只可派发前选，不能看结果选）。可复用原已记录prefix，不重跑旧root。覆盖冷启动、快路径、周期审核、收束/flush/编码；报告step分位、exclusive项与命令/回执/帧完整性。

结论只选：达到目标／未达目标但有效测量／未形成有效测量。系统≥5×、稳态静态审计<10%是目标，不是已经发生。两工作回合仍没真runner进入zero/测量就停追加非必要软件，报唯一阻塞及owner，不靠新报告当完成。

## 3. 最新实际状态：PERF-01首轮已zero失败closed，main0

scope：`data-46308-perf-NAV2000-indexed-20261116-v1`
program：`cbc751e43b257e291ddc8fa46073d567e7c53bb704b951fece30c83df786fc04`
Data代码a9baad32…，原控制源04a9c0fe…，AINav guard87a5c4f…/package dc856dac…。

实际own-zero1、main0，已关闭/no retry。**准确结论：未形成有效测量，不是未达5×的有效测量。**
- cold Runtime、原Actor辅助校准和task0 EGL相机已发生；task0步/0sim，aux1世界/6.505sim。
- zero wall17.761942499s，RSS2170261504，GPU peak645922816bytes，known/close_errors=[]，final logical82911bytes。
- 在`Data library_maps.py:13 / executable_file_maps()`扫描RX文件闭包时抛：`Deleted executable mapping; no trusted file identity`。
- **FrozenFiles/indexed install之前失败，新indexed guard没有实际安装**；无任务命令/回执/主录像/性能窗口，speed ratio、step分位、audit share都UNKNOWN，不能用zero除旧main。
- 原异常漏记具体映射名，**原zero究竟哪条mapping仍未知**；不冒JIT/驱动/恶意篡改唯一原因，不无条件skip所有deleted。

正式Data交付：
`/home/yuanyue/main/work/data-team/consumer-deliveries/PERF01-DATA-ACTUAL-ZERO-ELF-MAPPING-ADMISSION-FAILED-NO-MAIN-20261116-v1/release.json`
release SHA `036c8920b8ead5f4198b0d6a1323660253ed94abeb29d9f93af32bfa72132e41`，本组已核12小成员SHA。
本组记录：`operations/PERF01_ZERO_DELETED_EXECUTABLE_MAPPING_FAILURE_INTAKE_20261116.json`。

**收尾新消息，避免下一窗重复诊断：** AINav22:38回执已消费Data单次独立CUDA/EGL库诊断，result41967314…；16×16 EGL后出现8192-byte `/memfd:/.glXXXXXX (deleted)` RX，释放后消失。它不是旧zero身份恢复/唯一因果证明，也不是新性能main。Reach本次只核AINav该回执，尚未独立消费Data诊断正式原件/最新关闭状态。最短新入口：
`/home/yuanyue/main/work/ainav/consumer-deliveries/AINAV-INDEXED-IDENTITY-PERFORMANCE-REVISION-20261116-v1/PERF01_CBC_CLOSED_ZERO_FAILURE_AND_EGL_DIAG_NOT_MAIN.json`

下一步应先读这次**已经执行的**Data诊断/关闭原件，不再开同样GPU诊断。owner=Data：区分真实命名ELF与明确登记的EGL运行时生成RX，明确bootstrap/运行检查、信任、延迟及失败策略；不能按名字全放过、不能把虚拟memfd当普通磁盘文件塞FrozenFiles。解决真实接缝后，另新准确问题/版本/root/资格，不热改/复开cbc。不需要AINav新guard框架、额外经济批准或Reach签字。

## 4. 性能比较必须保留的口径

本组已核旧E20对应prefix，并保存：
`operations/PERF01_OLD_E20_2000_PREFIX_REFERENCE_20261116.json`。
- 旧2000命令/10sim：1205.163951803wall，120.516395wall/sim。
- **旧wall从main start、含prepare/初始化。** 原worker SHA dad9fa32…，start line28/progress line73。
- 新worker `window_wall_s`只计loop，不可直接作该旧1205的分母；用对应`scope_start_to_window_end_wall_s`，再单列冷启动/收束/编码。5×同口径总窗口的241.032790s仅算术阈值，不等资格。
- 旧单独init、loop-only、step p50/p95/p99/max、exclusive share、seed记录均未核得，保None，不能从400步均值造分位/把嵌套计时相加。旧4000/20sim=2481.794419576wall，仅派发前备选。
- 新step样本实际为driver.step_one＋到期video，不含前置guard；应标范围。命令bitwise/帧与周期覆盖需真实证据，不靠schema或合成图。
- 失败zero用了camera候选0（lookat[6.5,0,.2]、distance18），不是旧main最终camera1。下一新性能程序直接用旧最终lookat[7.5,0,.4]、distance20、azimuth110/elevation−58、1280×720/10Hz；旧camera SHA c9b2d3aa…。main没派，所以没有被混机位污染的性能结果。
- seed旧未记录、新也不能伪称同seed；缺项要说明，不自动开新baseline。

## 5. 已完成的性能候选，不再重复修/测

AINav indexed_identity_guard_v1：原guard核心5aa94c79…，当前正式87a5c4f/package dc856dac…；每步便宜world/session/queue/target/goal/callback/token，module≤20call或.25s，meta≤5s，canonical≤60s＋audit budget5s。静态检测时延有意改变，不宣称旧逐tick等价或绝对防篡改；blocked kernel IO需Data外部watchdog。

Data ResourceWatch**开发源8cd57028…**已改原子(oldest,completed)，最早观测计有效期，>2s完成拒绝，和87a桥每端14组合case过。**“Data仍缺pair”已过时。** 旧正式CPU包0c0eb141是历史版本，不得拿它阻挡当前接线，亦不倒贴旧测试资格。

Data受控writer/query/intent/raw/report/FD/encoder已有CPU接线；真实whole runner已生成510-member cbc freeze，且已真实zero失败，不能再说只等选源或未登记。源/权重/native ELF依赖闭包与当前mapping准入由Data落实。

CPU局部测量均已记录、不要重刷：
- Data相同93文件FUSE树1000合成calls：扫描1000→101，目录组件median4.346×。
- AINav1403模块corpus：稀疏周期2.157×，完整5s审核轨迹4.249→3.945s=1.077×；巨大非到期快路径数不能代表整个策略，首版0.619×负结果保留。
- 这些比值不可相乘，不是native系统5×或静态<10%证据。

## 6. 当前真实任务结果（不要重跑/重读old raw）

**旧E59原V4 .60m任务**：source3ab9383a/program f7dd66c5，唯一main1失败closed。NAV15.090成功，PUSH15.095开始，26.570placement短暂合格，26.630在NN_STOP首次再次失格，早于legacy H/32.910收臂；48.595才在stow后复核报错。不能把首次失格归因后来的H。9719命令，main9382.503wall，PUSH无原native成功/失败terminal，CLIMB0。full cold由Data过，本组未重算NPZ/PD。原片：
`/home/yuanyue/main/work/data-team/manifests/V4-E-first-direct-live-46308-20261116-v3/E-direct-live-1x.mp4`
1280×720/10Hz/486帧/1×，SHA172e2878…。

**新E20/C箱顶.20m＋40mm提前原brake**：用户环境适配授权原件已核，不再问原则许可。新scene08a260a4和目标不是旧.60m成功。source04a9c0f/program39ef86d5，唯一动态main1已用尽/closed；26.470早刹、27.190内部NN true但placement false、27.410确认丢失硬停。5482命令、main3522.131wall，PUSH terminal=None，CLIMB/后箱0、legacy H0/新selector0。不能拿更早失败wall短冒提速或40mm收益，不扫margin/seed/换ID盲试。275帧/1×完整片：
`/home/yuanyue/main/work/data-team/manifests/E20-prearrival40-direct-live-46308-20261116-v3/E20-direct-live-1x.mp4`
SHA2b6c43ce…；formal9成员已核，Data当次full FIFO/PD cold尚pending，不冒已过。

静态geom lookup失败、v2漏privacy writer的zero启动失败及缺失费用、E20/E59所有旧费用/用途全保。旧46174 left恢复原报告REQUESTED_API0_PASS（三所请求技能），但非整任务、新样本、当前lease或方法收益；保失联时UNKNOWN原记录，不与新right重配、不转训练。

## 7. 本组真正方法工作与未完成项

五组A=直接VLM+旧7a6 WM；B=A+新后继优化；C=完整原AINav VLM/tree/advisor/arborist/replan；D=C+同一新优化；E=固定规则，无VLM/WM/新selector。共有legacy stow H五组同开，**不是B−A/D−C treatment**。现实际两个E版本失败不能混作同一公平五组；A—D真实main/本次WM forward仍0。

本组模块在主仓`research/task_conditioned_reachability/execution_preparation/`：
- v4_successor_choice：保守完整候选选择，UNKNOWN/partial/预算不足退原baseline，标准枚举不冒新求解法。
- v4_backbone_adapters：原C/D能力不削弱；6945666修D树terminal内部前缀遗漏（7新+23受影响软件两端过），没改原树。新adapter pin c9310385…，他组旧pin/冻结不热换。
- v4_reference_cost：三阶段reference路程记账，**米不是成功秒数/动态安全证明**。
- v4_outcome_summary：619dbac后离线比较核共同execution-profile SHA/ref，不同/未知不算B−A/D−C；保单E原结果，不是新运行/审批前置。
- v4_anchor_target8：db3799c同一次call局部几何去重，不跨帧/候选语义缓存；23软件两端过。原算法合成CPU3轮：16重复1几何1296.9→81.1ms；16候选4几何1301.0→325.7ms；4唯一control317.0→315.3ms。输出/evidence完全同；当前E不跑WM，**不是当前仿真提速**。不要重复benchmark。报告V4_ANCHOR_LOCAL_REUSE_CPU_MEASUREMENTS_CN.md。
- raw WM loader/causal port/96×64 target8/条件palette关联等已代码接缝，真实现场bootstrap/三帧/200Hz已发history/absolute PUSH与CLIMB action映射仍缺。SupportedCapture不能冒HOLD/NAV；mask0/缺项弃权，不用closed帧/蓝图/private pose造输入。新颜色是声明假设非native物理ID。

**完整公共当前reference、三阶段effects、准备退出/fresh可用性预测、完整terminal/successor cost provider仍未完成。** 不把旧case/context ID/已曝光赢家/实测失败耗时lookup当预测；不把WM raw终止时间/logit当成功Finish或READY。已授权未来新cohort小高层critic训练，不等任何旧审计数据都能fit；旧fit/CAL/VAL/bulk用途不改，未获新合法原件不refit。

## 8. 机器、操作和协作硬边界

- 当前唯一计算端：`ssh -p 46308 -o BatchMode=yes -o ConnectTimeout=15 root@180.97.68.228`。优先已有密钥；不探/保存/转述用户密码、key/token，不进argv/源码/日志。
- 主代码远端`/mnt/yuanyue/reach-ability-research`；原输出`/mnt/yuanyue/reach-runs`，既有Python`/mnt/yuanyue/data-team/env-native-v1/bin/python`。模型/环境/MJB/NPZ/日志raw/录像母版留远端，本地只code/小公共JSON/标量SHA和已有小视频副本，不搬大资产。
- Data唯一物理owner。Reach不建world/Actor、不开GPU诊断/launcher，不动peer源码/环境/guard/H/锁/进程，不抢卡；必要只读及本组有限CPU检查不冒native资格。性能runner失败也不能复开closed。
- 旧46174只在明确缺失历史资料时允许只读，不能恢复计算/旧launcher/旧lease；已恢复资料不再轮询旧端。
- 动态门/Actor/物理dt/200Hz、identity/immutable、12N、FF/effort/QP/FIFO、原NN/STOW/4s/CLIMB stop不降。不把静态审计策略变化藏成完全等价；不把readonly/chmod/hash cache当绝对防篡改。
- docs/保持原5文件。新操作说明放operations，不加第6份doc。
- 阶段进展更新本组当前/下一步及`/home/yuanyue/main/汇总/各小组进展汇总.md`，共享只换Reach段，保peer bytes；flock `/tmp/reach-shared-progress.lock`、bytes CAS、atomic replace、保mode。Reach段从`## Reachability组
`到`
---

## Data组`。
- 只selective commit/push主仓自己的code-only更改。GitHub走既有SSH443；远端先核clean/预期HEAD，再小bundle fetch+merge --ff-only，不force/reset，不动旧repo index/继承dirty。交接commit是说明，不是新性能/研究结果。

## 9. 非主线交付与心跳

汇报四模块图已经完成，路径：
`/home/yuanyue/re-nav -piper-manipulation-reachability/artifacts/presentation/2026-11-16-framework-modules-v1/`
含4张PNG、PDF、讲稿、绘图源码。它们是目标架构示意，不是实验/部署证据。用户给定DeepSeek V4.1 Flash型号未官方核实，V-JEPA Policy技能适配属拟议设计，OPEN也不代表本项目已具备原生资格；不要用图扩权限。

heartbeat automation_id=reach-yy1仍有长期用途，**交接不删除/暂停自动化**。无变化不刷同报告/旧测试，最终只回DONT_NOTIFY XML；只有实质完成/失败/状态变化/用户行动才NOTIFY。DONT_NOTIFY时XML外不发commentary/prose。当前闭合首轮性能scope不代表长期Reach任务完成。

## 10. 新窗口第一步

先核最新计划/正式交付是否比22:45快照更新；优先消费Data已做的EGL库诊断及关闭原件、确认Data实际mapping策略/新准确程序资格。**不再次运行同诊断、不代写peer guard、不扩大接口、不给main加研究许可**。记录明确新证据与唯一阻塞；真实性能窗口到达即给三分结论，计时/机位/周期/关闭成本按第4节。若无新证据，保守安静，不以重复接收回执/软件case堆积代替方法实现。
