# G2三登记scene的实际资格边界与下一批方法接线

2026-11-15 12:33（北京时间）。项目完整基线仍ExecutionJudgedFullCourse/execution-judged-20261031-v6、原283谱系；Data唯一物理owner。此文不是新训练协议、scope、日志合同或派发门，不复开任何已closed结果。

## 新增真实结果：full-1 left闭合

程序`3b5e9d4d4366479394cf825419f47f6c1875c32519fca26c40762ffa4e82ee8f`，Data发布release `2bae0f2abe72c19dfbc756102e995ce6c5eff0a7d36c42e7cfa8112531285522`。原full-1完整geometry/material case、NAV left→PUSH(2.3,−1.8,0)→CLIMB .2/original、seed4301，1自身zero+1main真实PASS/closed。23869命令步/119.345主sim，1194 RGBD+review，5 native options/10 literal receipts。原NN .5000000596s、STOW_VERIFIED、原CLIMB READY和stop成功；不声明后CLIMB下一技能ready或完整far-bank成功。

AINav在46308只读核47发布成员、42原source pins、actual-config及本scope zero/main同model；原journal4100行完整hash链独立verify。原命令NPZ只消费Data九流cold/命令hash，不冒本组数组/完整动态历史重审。first PREPARE95.250s→exact judgment_ref/intent/actual Host Observation SHA→query4/age0；到READY13.495s，到成功终点24.095s。包含自身zero/aux的scope132.355sim/814.418296ledger wall，输出highwater175664393bytes。同scope phase高水位不相加。

## 原算法增量公开测量：第三scene有输入，不等三split证书

full-1新帧原proposer/component仅一次，4104有效深度pixel，名义可见点median `[.6669234585978046,.17023474707578617,-.09269799652633232]`m。两对照复用已冻结旧summary/原输入SHA，不重算旧组件。

| 按事先有限规则的同left跨layout对照 | 名义component median XYZ差(m) | L2(m) |
|---|---|---:|
|full1−full4|[.010738517002270243,.11344939501335222,−.011581444567169197]|.11454348883531568|
|full1−full2|[−.0003918828251124884,−.011411113198846606,−.0012398817283719166]|.011484963355877977|

两pair各自45D五块、decoded RGB/depth/NaN缺测位置均非exact相同，K/T相同，当前公开task alias/component唯一对应。这仅证明这两个已曝光DEV对照的合法任务表征未完全归并；每点在各自采集body frame，**不是WORLD位移、物体center/真值误差、材料作用、纯单变量因果、重复性/可学性或候选收益**。full-1原C质量1kg/μ.3与full-2/full-4 .5kg/.6等差明确，不称geometry-only。

现在source探索的真实分母是5 main/3 registered scene，4条完整链成功/4个合法first-PREPARE，full-2 right在PUSH卸载FF交集空，未到CLIMB，不能作CLIMB负标签/补第四输入。4/5只是有限探索计数不是独立评估成功率。三source索引release `01e2571a3e5a5ca3244264f9de8219fe6c19518c5176442d728ee067ce7de240` 的5 metadata及5 child release SHA已消费；5 scope共598.515sim（含zero/aux）、3722.513041ledger wall、独立scope高水位和805949466bytes。旧XML启动故障/旧端UNKNOWN/StageB等另保，不称全项目费用。

## 下一批的准确方法源：已有API足够，不再造wrapper或复跑source gate

现有`consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/climb_preparation_candidates.py`，SHA `1c40a748bd1d93e3684853b60f2dc038e673f019976d60cf33eb8195ff9942d0`，已提供original/lateral_plus_0p04/lateral_minus_0p04与`selection_from_payload`/`public_candidates`/`bind_to_host`。它们只变当前已选CLIMB的ground-source NAV-child准备goal，原semantic intent、PUSH目标、原CLIMB READY/entry/stop不变；不扩成连续域或.2支撑通用API。

| 原scene | 原CLIMB approach XY | existing原三候选NAV Y |
|---|---|---|
|full-4|(.050000000000000044,−2)|−2,−2+.04,−2−.04|
|full-2|(.050000000000000044,−1.9)|−1.9,−1.9+.04,−1.9−.04|
|full-1|(.050000000000000044,−1.8)|−1.8,−1.8+.04,−1.8−.04|

保原API浮点运算，不手工round/改task目录。表是**已有有限源码目录**，不是9main计划/合格动作人口：本三scene-left探索实际只执行original，另外两臂在新scene的native准入/原门/结果未知，必须按未来协议新scope实测并保失败/未到达分母，不能凭静态.16m disk内就称safe/READY。

当前Data full-1 gate的plan和`full_host_worker`均literal original，不能只改case/condition label就声称采到了别的arm。未来**独立新cohort caller**只需把协议已经固定的一个`PreparationSelection`在两处一致消费：

```python
selection = selection_from_payload(the_future_protocol_fixed_payload)
# existing new preconstruction plan records EXACT same payload
# Existing protected installer, SAME original Host/coordinator/FIFO:
install_preexecution_choices(host, candidate_id=selection.candidate_id, emit=evidence)
```

此处只是已存在签名与源码接点说明，不是改Data代码/运行许可。原`prefix_bindings.install_preexecution_choices`在世界0/无queue/无active owner时安装现成callback，candidate绑定后固定；不支持在同run热切arm。原common-stow在所有arm一致，partial install失败不可复用。保持exact source/init/Host/exact3真实语义终点，原guard/12N/4s/FF/QP/FIFO/stop/技术watchdog与每program自身zero/fresh lease。

full-2/4现有helper458ec66e…继续其原material guard；full-1用已成功的独立原protocol/validator路径，不改旧helper以“兼容”它。scene配方/材料/后果/UUID/scope只metadata，不能整块喂selector/critic。相关精确Data读点/当前字节pin与已有API实际输出保存在本组`manifests/G2_full1_actual_intake_20261115_v1/EXISTING_THREE_SCENE_METHOD_ARM_SOURCE_NOT_DISPATCH.json`，无需Data再造NN表/reader/logger/接口回执。

## 明确下一研究责任，不再新开第四scene凑数

1. **Reach：** 基于实际3source/不完整prefix域，冻结新的用途协议、合法有限scene/prefix/arm、source-scene/祖先split、样本量依据（或诚实限定弱原型）、停止/未到达/资源censor。旧G1/G2均DEV不能转fit；本文件不替Reach选择TRAIN/CAL/VAL或批量次数，不自动复用旧8组/24main。只有同scene reset/换prefix/arm/新ID不能制造未见scene/独立样本功效；deterministic同init重复也不自动提供新的状态人口。
2. **AINav：** 收到实际新协议后只核上述选定arm/scene的真实caller消费，必要时给有界源差分；不新增通用框架/临时callback或把固定预先arm当G4在线critic选择。G4真正后果前选择仍须在合法公开输入时绑定已训练/固定的策略，不能倒用结果/跨run热改。
3. **Data：** 在其唯一owner下复用已合格SDK/环境/runner/记录，按新协议逐新program freeze/自身zero/lease/容量批次执行，不等待critic已训练、不等待新经济签字、不重跑已成功/失败DEV root。

新数据足够即G3真critic与常量成功/均值耗时强基线→G4固定/局部/后继三策略→G5多决策与未见layout→G6；当前只是前置source/信息问题回答了，不是G2训练数据完成/整体验收。若新协议仍没定义，AINav独立接续.2后movement/compact/owner/12N/READY source合法域，不靠更多感知/metadata“成绩”替代真实研究。

WM/底层Actor重训/真机不开放，旧audit/GT不fit，evaluation_ready=false、独立TEST0、五箱false。
