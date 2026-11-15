# Reachability research — code custody and remote execution

冻结现有 Go2/Piper 技能下的后继感知准备方案研究。**原 AINav 成功、工程接线、标准枚举或单条 DEV 录像，不自动构成本项目方法贡献。**

## 代码与运行分工（2026-11-14 用户更新）

| 位置 | 用途 |
|---|---|
| GitHub `WM4N-Group/reach-ability-research` | 持久代码版本；不存数据集、录像、环境、模型权重或密码 |
| 本地 `/home/yuanyue/reach-ability-research` | 精简代码副本与小型摘要；不批量拉取远端产物 |
| 远端 `root@180.97.68.228:46308` | 当前仿真/训练计算入口；代码 `/mnt/yuanyue/reach-ability-research` |
| 远端 `/mnt/yuanyue/reach-runs`、`/mnt/yuanyue/reach-assets` | 分别存运行产物、权重/场景资产/环境清单；不提交 Git |

密码只在连接授权中使用，不能写入 Git、配置、脚本或日志。使用当前已可用的 SSH key 连接；不复制本地私钥到服务器。

服务器是可更换的计算节点，**不是代码唯一副本**。每次运行记录代码 commit、未提交 patch（若有）、依赖/资产 SHA、GPU UUID、场景、协议和输出路径。换机先部署同 commit/核资产，再由 Data 建立新硬件资源 binding/lease、程序 freeze 和 own-zero，不能复用旧机器 UUID、锁 inode 或执行许可。共享存储的物理持久性/配额以服务商为准，不把挂载显示的容量当账号配额。

## 本次初始代码快照

- 原工程 HEAD `4c998be60b2264999c5c033a2d011843bfd202a5`，分支 `feature/go2-piper-reachability-p0`。
- 这不是原 HEAD 的 clean checkout：保存了当前工作树里的研究源码，包含此前 untracked 实现；源工作区与原 Git index/branch/remote 未清理或替换。
- `provenance/CODE_SNAPSHOT.json` 列出复制文件的逐 SHA、来源和排除项，**不是 runtime freeze**。
- `owner_snapshot/native-prefix-20261114/` 是 Data-owned 两条件 pilot 的代码副本，只供代码保管/迁移；其中旧 `/mnt/miaojigui`、GPU UUID、锁和 authority pin 是历史机器限定，**不能在新机直接运行或 sed 后冒原 freeze**。Data 维护新运行版本。
- 原代码许可证与 attribution 保留。大型 meshes/USD/PT/ONNX/NPZ、历史原始 evidence、环境、日志和视频未复制进此代码仓库。依赖这些材料的旧实验/测试不会因代码存在就自动可运行。

## 可独立运行的软件检查

在仓库根目录（纯 stdlib，不构造 Actor/Runtime/物理世界）：

```bash
python3 -m unittest \
  research.task_conditioned_reachability.execution_preparation.test_successor_critic \
  research.task_conditioned_reachability.execution_preparation.test_public_prediction_features
```

这是软件/内存 fixture 检查，不是训练样本、仿真实测或新研究成绩。历史所有 closed 根继续 closed。

## 当前优先V4五组与方法实码（2026-11-15 23:09）

最新22:53计划26b67d55…是A/B VLM＋既有WM无/有优化、C/D原AINav无/有同一优化、E固定规则（AINav负责），不是旧API0两组。Reach已实现共享后继选择核、保原AINav全roles/tree/replan及真实pending消费的C/D接缝、新direct VLM＋原7a6 raw-WM决策适配、五组scalar reader与纯配置；41新＋38原共79软件检查过，真实VLM/WM/native调用0。生产拒fixture。当前selected原20cm CLIMB拒.20→.60高差，static-deck/终点与V4因果WM IO/完整名义cost仍缺，不能称五组ready/优化已真实消费；未改设计或原门。详见operations/V4_FOUR_ARM_METHODS_AND_GAPS_CN.md及protocols/2026-11-15/T-COMPLEX-01-V4-five-arm-methods-v1/。

## 当前固定观测测量main完成（2026-11-15 22:19）

两原NAV/三fresh view已完整完成：center空→left接受cuboid_a→right空，27.515main sim/5503命令；本组独立核1058行全链及三query/两个原成功receipt，消费Data九流cold。phase已closed/PID退出但22:17 scope H仍待owner CAS；不是PUSH READY、完整任务或规划收益，left历史alias不能缓存到right终点。新共同固定观测prefix必须两方法共享费用并receipt绑定准备后的nominal start，不能沿用center；具体增量接口见operations/T_COMPLEX_01_OBS_COMPLETE_AND_NEXT_CN.md，旧实验不重启。

## 当前T观测必要条件阳性（2026-11-15 21:54）

原固定left NAV成功后的14.815sim fresh public query，原RGBD门真实接受cuboid_a；本组独立核原query/图像SHA/label与native receipt/1052行日志前缀。仍2/3边界、right在途，不能称PUSH READY或完整任务/规划收益，不挑最好帧或缓存旧alias；原A/B继续closed。见operations/T_COMPLEX_01_OBSERVABILITY_NEXT_BOUNDARY_CN.md。

## 最新bulk24实际数据边界（2026-11-15 21:29）

Data首个新几何g01/left/original已原生完成三个请求；本组独立核4093行原链和首PREPARE因果48槽，READY相对13.500s/完整请求CLIMB相对23.540s，数值非冻结TRAIN6精确重复但不证可学习/方法收益。原raw为192×128非HD；48向量留远端，未fit/预测/评分或改旧cohort门。T OBS仍无终态。见operations/BULK24_FIRST_PUBLIC_BOUNDARY_CN.md。

## 当前独立观测资格测量（2026-11-15 19:48）

Data新program9fdd2076…的自身zero2136ddd7…真实通过，唯一main已在46308执行固定两NAV/三view；本组已核26source SHA及原zero/ledger，当前仅初始view和第一NAV，无终态/资格No-Go/任务或方法收益。新150sim/57600wall测量cap不是旧A/B提预算，旧pair仍closed。见operations/T_COMPLEX_01_OBSERVABILITY_NEXT_BOUNDARY_CN.md；完整read-only intake与无数组snapshot保在旧工作区ignored evidence/2026-11-15/T-observability-ownzero-open-main-intake-v1。

## 当前T首对闭合（2026-11-15 19:21）

A原RGBD关联门拒绝保持；B唯一main因原wall watchdog停止（resource_censored=true），主世界12.720sim/2544命令，1次研究选择/原NAV option1/Actor-forward524、terminal receipt0/重构0。两支均未完整任务，不能宣称lookahead收益或搜索超时。已独立核原A462/B995行完整journal链及原三视频SHA，原片是完整可用失败/截断episode而非成功母版。下一为已收源的独立固定两NAV观测资格与新源吞吐准备，Data唯一owner，不重启旧root/抬旧cap。见operations/T_COMPLEX_01_CLOSED_PAIR_AND_NEXT_CN.md。

## 当前T实际方法消费（2026-11-15 18:37）

本组独立读原A/B记录：前448个capture命令8通道逐字节相同，第1public query仅存储path异。A首PUSH拒绝保持；B实际多步选择C(9.7,0)、规划.1954s无greedy fallback，首原NAV(-.08,-1.8)已安装并于tick449/time2.245发原Actor任务命令。只证明真实研究选择进入原consumer，不是NAV成功/三选择/任务收益；B终态与视频待原件，源/Actor/原门不改。见operations/T_COMPLEX_01_ACTUAL_FIRST_DECISION_CN.md。

## 当前T真实负结果（2026-11-15 17:35）

A原唯一main82952392…已FAILED_NO_RETRY/ledger stopped，非仍在途：实际capture448步/2.240sim后第一PUSH前原RGBD同色组件未消歧、当前objects=[]，无任务NAV/PUSH native option。原像素API离线一次确认两个depth有效warm候选均被原guard拒绝；不改阈值/GT回填/重跑。没有几何死局/方法胜出或G3负标签证据。原23 live帧保留、未有完整A/B视频；B终态未消费。见operations/T_COMPLEX_01_FIRST_MAIN_FAILURE_CN.md。

## 当前T执行状态（2026-11-15 17:09）

完整Data A/B已按e72ddbb2…冻结，A原own-zero15947a2e…已PASS；17:01:56 owner快照的A唯一main已派/在途，B待自身zero/main。4方法SHA同本组，当前source为b08；不再写全程序未装配或重复派zero。未消费main终态/完整task/有效三选择/任务视频，不把in-progress当成功或原AINav工程当方法贡献。见operations/T_COMPLEX_01_FULL_PROGRAM_ZERO_AND_MAIN_INTAKE_20261115.json。

## 最新进展（2026-11-15 16:45）

T三箱v2的原camera/冷Runtime/INPUT8/GPU0 CUDA-GL真实组件预检已PASS并closed（Data d48fba0e…），source d486四模块wrapper与本方法SHA一致；尚无完整SupportedCapture/task/A-B/原片资格，组件zero不能借给不同全程序。新用途bulk24已预登记0f9e0e03…：4几何×2prefix×3候选，全部同full4 TRAIN祖先，不refit当前model、不动CAL/VAL，T优先。见operations/T_COMPLEX_01_NATIVE_COMPONENT_PASS_INTAKE_20261115.json与BULK24_LANE_WIDTH_COLLECTION_CN.md。

## 最新T实现进展（2026-11-15 15:48）

已接AINav三箱v2公共source与原IntentExecutionCoordinator接缝；新增完整SHA/全catalogue门的source-bound factory，Data可直接传入原scene driver。两端各13定向单测，本地87原类/helper与远端53原类子集断言是软件而非真实A/B。v2公共图3个非强制名义重构选择不等真实动态资格；原生A/B和原片仍0。Data v1组件zero因原camera ABI缺失closed，须源修复新程序own-zero，不重开。首次TRAIN-only拟合保持冻结、不重训。入口operations/T_COMPLEX_01_SOURCE_V2_OWNER_ENTRY_CN.md与T_COMPLEX_01_SOURCE_V2_METHOD_RELEASE_20261115.json。

## 最新真实进展（2026-11-15 15:04）

未来新用途TRAIN6完整闭合4成功/2原门失败，六行48槽/源标签门通过；46308已完成首次真正TRAIN-only高层logistic/ridge拟合一次，6行/1scene/2prefix，非fixture或Actor/WM训练。数据与权重只远端，模型3371ac20…文件/a8b1f165…内容冻结；常量/均值基线已记，CAL/VAL还未评价，score未校准/不部署。见operations/G3_FIRST_REAL_TRAIN_FIT_20261115.json；Data按原协议实际gate/fit pins接续heldout，T复杂首对优先资源窗口不改。

实际T公共source已进入共同model与原语义API seam，原live host/candidate注册/ground终点和native资格仍待接；只做public名义图诊断，不拿模型A/B结果充机器人成功或视频。v1 macro仅2非强制重构选择，第三有效选择未证，三箱方案仅可选新source提议。见operations/T_COMPLEX_PUBLIC_SOURCE_ADAPTER_CN.md。

## T-COMPLEX-01优先任务（总计划标记14:00）

不等critic/百级采集，先做真实复杂scene、greedy vs有限多步同条件两arm与完整live原片。Reach已实现共享nominal几何＋两策略标准搜索核心；source scene adapter/原生对比/视频尚未消费，不以抽象测试或旧短链冒完成。当前TRAIN6原门继续。见operations/T_COMPLEX_01_SHARED_METHODS_CN.md、T_COMPLEX_01_METHOD_PROPOSAL_20261115.json。物理/Data队列资格未核，不擅自占卡/开world。

## 13:45新总计划（覆盖下方旧优先级，当前冻结批不热改）

完整成功／不可恢复死局优先，时间次要；固定／greedy／一跳／多步共用候选/观测/技能/预算。向≥100次新用途main、≥10有意义组滚动扩量，新批通常12—24；当前TRAIN6仍原门，Data统一双GPU/多worker准入，Reach不另开world。并行S1/S2复杂任务域与有限多步规划，不等critic完美；当前±.04短链/两条原方案成功不是G5或方法增益。新批/源适用域与用途分组详见operations/NEXT_BULK_AND_LONG_HORIZON_PRIORITY_20261115_CN.md；尚未声称已实现复杂任务或大量派发。

## 当前研究状态（2026-11-15，覆盖下方历史快照）

新端46308三source五DEV已closed：full-4左右PASS、full-2左PASS/右PUSH卸载异常未达CLIMB、full-1左PASS。完整分母5、first-PREPARE4，原失败/未知费用不丢。只证明原AINav工程和有限公开信息，非Reach优化收益/论文贡献。公开增量测量原件留远端，小摘要见operations/G2_FULL1_AND_FINITE_COHORT_20261115.json。

**当前新用途有限协议：** protocols/2026-11-15/G2-new-purpose-finite-cohort-v1/；固定full4 TRAIN6/full1 CAL3/full2 VAL3、最多12新main，whole-scene分组、只未来新数据。TRAIN类/状态不足即No-Go，不自动扩批/旧DEV改fit。每split仅一scene且DEV-informed，不是未曝光TEST、统计功效或G5 holdout；不能通过排除原full2right宣告完整族已合格。Data唯一物理owner，新TRAIN01/02已PASS closed并真实提取两条因果48槽/原READY与CLIMB监督行；仅一个TRAIN scene/2prefix，未齐6不fit或提前判gate。03 plus-left在13:39 H快照已派唯一main，04—06未派、CAL/VAL仍阻。真实fit0；无需再问已授权小高层训练用途/经济许可。

TRAIN先fit/heldout后只评价的时序循环已修复，见operations/G3_TRAIN_FIRST_FROZEN_EVALUATION_CN.md；下一真实TRAIN闭合就G3单次高层critic和常量/均值基线或有限否证，接续新协议G4三策略/G5多决策/G6，而非止于本gate。原Actor/WM/DINO/真机暂停，12N/4s/identity/immutable/guard/support/QP/FIFO/CLIMB stop不变。完整接续见docs/AGENT_HANDOFF_CN.md顶部。

### 23:45计划接续（覆盖旧机器恢复前置）

最新用户明确停追旧46174，不等待旧端CAS/锁/结果恢复。旧left的zero1/main1已消耗、终态UNKNOWN和全部已知/未知花费保留；新46308按独立同设备cohort完整left/right各一次，不重开旧root或与旧left拼配。新端已有Data的Python3.11.16环境候选及逐148成员同pin的SDK/四Actor，不再因本组此前另一个3.11.13 probe要求全栈重装。仍须Data新authority/设备程序绑定与实际own-zero。见 `protocols/2026-11-14/LONG_TERM_PLAN_2345_CN.md` 和 `native-prefix/NEW_HOST_G1_CONTINUATION_CN.md`。
