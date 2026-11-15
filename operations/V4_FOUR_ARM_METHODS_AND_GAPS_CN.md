# V4五组：A—D真实方法代码首版、B/D共用优化与原源能力缺口

2026-11-15。接续22:53最新五组计划26b67d55…（本轮先读取22:40四组版，写配置前发现更新并转五组），覆盖旧“WM完全不调用/当前只有API0两组”口径；仅当前V4允许现有WM推理，不开WM/DINO/Actor重训或真机。A/B=VLM＋WM无/有优化，C/D=原AINav无/有同一优化，E=AINav负责的预先固定规则策略（VLM/WM/本优化全关）；B−A/D−C主对比。原A视觉拒绝/B资源截尾与OBS/bulk根不恢复。

## 已直接实现（不是仅画schema）

源码均在`research/task_conditioned_reachability/execution_preparation/`：

1. `v4_successor_choice.py`：B/D调用**同一个**有限候选完整后继名义reference travel选择器；完整路径成本包括source实际声明的准备/退出/connector。未知项不补0、raw-WM terminal elapsed不当成功链成本、partial path不当完整scope；任一路径UNKNOWN/partial/预算截断保留原backbone决定，**optimization_applied=false**，不冒方法有效。已知名义路径可按后继总成本改首动作（测试覆盖局部1＋后继100 vs局部2＋后继0）。标准枚举不是新求解算法，不认证动态安全。
2. `v4_backbone_adapters.py::AinavSuccessorAdapter`：C/D先真实调用原`AinavPlanner.select`；object/skill proposer、tree evaluator、advisor/arborist、replanning全部保留。C直接返回原Selection，不调用新cost；D只在同当前合法树根内pre-dispatch更换确切option，并同步原pending primitive，原observe/observe_intent/reject_intent继续消费**真正被选**option的原回执。软件已用原纯planner/contract源码核真实pending→选中分支history推进/错误回执拒绝/拒绝后advisor接续，不以另写假planner冒原接缝。
3. `VLMWMIntentPlanner`：新实现并明确命名的**V4 direct-VLM＋原7a6 raw-WM决策路线**；不是API0有限贪心，也不谎称原FiveBox host已适配V4。每个fresh原public query先取真实WM evidence，给与C/D同provider/model的实际vision backend，生成并选择1—5条完整公共技能计划（每条≤16），按原候选精确匹配首intent；实际技能终态/拒绝后携带原feedback在fresh query重规划。没有原图固定路线/物体字母角色表。原只读prerequisite拒绝后允许同sim-clock的新query携带实际拒绝反馈重规划，不用“必须物理时间前进”削弱基线；完全相同旧batch replay仍拒绝。B沿同一路线调用与D相同的后继选择器；新增优化关闭不等基线无规划。**生产模式默认拒绝软件fixture roles/伪WM metadata；测试须显式software_fixture=True，日志标明fixture，不得拿测试backend代真实运行。本轮不曾调用真实API或WM。** 这是一份明确新方法实现，不能未经接口验证就当历史原基线等价。
4. `v4_raw_wm_adapter.py::OriginalBehaviorWMAdapter`：代码实际调用原`model.predict_behavior(... terminal=True)`，不是常量预测stub；核已加载eval对象所对应remote checkpoint7a6原SHA、source当前public observation/因果query、public60/独立target8/11维公开动作/实际query-clock，16候选一批；不构造Runtime/Actor、不自动下载/加载权重、不造native history。只有source既有真实IO能供给这些对象时才可运行。
   - 保原六维**translation**顺序/learned std/raw native成功或失败event elapsed/raw logit，成功Finish成本/出口world pose/后继READY/成功概率均UNKNOWN，不做成功概率或整链代价伪转换。
   - V4绝对PUSH goal没有公开相对action11推距时返回UNKNOWN，不能减私有实际箱位/静态initial pose凑推距；CLIMB只有目标surface而无原public approachXY亦UNKNOWN；target8缺失/未解歧保缺，不能填0再说已预测。
   - 至少有真实当前model forward且有效raw evidence才允许A/B路线选取；所有行UNKNOWN则明确停在“WM方法不可用”，不会WM开关=true而实用无WM。新V4 query/raw预测是未标定模型输入输出，不扩大旧7a6成功Finish/后继ready No-Go结论。
5. `build_v4_planner('A'|'B'|'C'|'D',...)`四组明确factory：D拒收暗加WM，A/B拒收把原AINav对象换名当WM路线。只组装方法对象，不建transport、读key或发native命令。

**最新62项新软件检查＋38项旧回归共100项通过；真实VLM/WM forward/native main=0。** fixtures显式标注，原AINav纯源码测试不是原生安全/任务资格。五组纯配置/原源逐SHA入口：`protocols/2026-11-15/T-COMPLEX-01-V4-five-arm-methods-v1/`。E由AINav实现，本组不代写场景正确路线。旧research FOUR_ARM_PROTOCOL仅保历史输入，最新总计划和五组config优先。新增预算是新V4方法配置提议，不抬旧scope cap；最终程序/order/VLM身份/技术cap由Data事前freeze。`v4_outcome_summary.py`另已实现五组标量评价reader：缺arm、WM名义开启而无forward、B/D无有效优化选择均不建立方法对比，失败/censor不补成功耗时，E严禁API/WM/优化计数；高台完整成功必须有三placement、原CLIMB、实际支撑和原stop/stow证据。此reader不是native审计替身，尚无五组原件供消费。

## 不掩盖的真实阻塞／最小能力方案

### 1. 确认V4的40cm后继与static-deck caller

AINav22:51原源报告`EXACT_V4_ASSET_AND_SELECTED_CLIMB_GAP.json`核精确selected v6原谓词：ground0→箱顶.20接受，**.20→.60高差.40明确拒绝**，不是动态实验；RegisteredClimbAdapter还要求当前RGBD对应registry.objects，静态goal_deck只是SurfaceSpec，并不自动成为CLIMB可绑对象。原ground-only stop/owner桥也未到.60支持。

因此当前V4五组完整任务**均尚不可执行**，不能降低20cm门/假装平台freejoint箱体/用ground相同XY完成。原技能不变的最小共享布局备选是加真实.40中间支撑，改成0→.20→.40→.60三个20cm增量，并验证static-surface/owner桥；**这会改用户已确认设计，需共享设计决定，本文没改场景。** 或先找到已有准确40cm技能/权重/接口和资格（不擅自训练）。不声称所有仓库绝无40cm技能。

### 2. 当前WM/VLM的实际部署身份未齐

**23:46权重缺口已解除：** 通过历史精确只读索引在46308找到11,314,598bytes原7a6文件，并用逐byte复制的原五文件推理闭包在CPU实际恢复一次；BehaviorM/2,819,568参数、原normalization、eval/梯度禁用均核，禁止native/API的fence空。真实restore1、WM prediction forward0、世界/Actor/训练0；不是旧实验重启，也不说明V4 query/策略已合格。权重/源码/contract/normalization/报告SHA与下一实际IO点见V4_ORIGINAL_WM_RESTORE_AND_IO_NEXT_CN.md。不再把早先文件名检索未命中写成“缺权重待迁移”；真正待接的是原当前sensor＋issued200Hz history、target8和语义/原native动作参数映射。

**23:13 provider身份已按用户确认收束，不再等服务选择：** AINav发布原公开profile87d38fef…，官方TLS DeepSeek/deepseek-flash/thinking disabled、无fallback、原backend SHA11e5fdd8…。Reach已逐SHA接收并实现`v4_provider_binding.runtime_binding`，只读公开profile/原backend源码，返回合法构造kwargs，不读取key/env、不创建transport或API探针；实际鉴权模型元数据/served identity及受保护进程注入仍由新冻结运行核，不把“配置已定”冒“密钥已注入/调用已过”。

同时定位并修正首版方法配置的真实兼容性bug：原DeepSeekBackend构造器明确`max_calls<=100`，首版提议256会在运行前被拒。现A—D共享cap改为100，A/B类默认同100，reply≤8192/total≤1000000，E调用0。**这是未派发新V4方法配置的修正，绝非抬/改任何旧实验预算或热补frozen program。** 新8项profile/constructor/不读env/禁止HTTP换源/预算边界检查通过；原source未改，无真实API/WM调用。


### 3. source成本与准备/退出变体还需V4真实接缝，不能把回退当优化

成本接口是`path_cost(actual_public_observation, PublicPath, query_sha256=...) -> NominalCost`，只用当前公共观测和声明几何。AINav只需导出真实公共候选/支撑转换/原caller参数与合法准备退出域；**后继名义估计provider仍由Reach实现，不让AINav或Data代写研究评价器**。包含实际supported CLIMB/高台终点的公共效果映射当前缺失，不用私有存在性路线或历史标签补齐；同一provider/缺失值规则供B/D。现无合格完整V4 provider，代码正确返回UNKNOWN、保留原backbone而不声称优化已发生。当前准备/退出变体未原生接通，不能从类名宣布“全维优化器完成”。

AINav新source公共构造器/caller和名义阶段接口发布后，Reach可直接接这4个方法对象；Data沿既有runner装配五组，不另建物理owner，不等待泛化auditor/critic采齐，不增加Reach收件签字门。只有真实方法输出到原native消费、实际WM和VLM计数及B/D有效优化选择证据到齐，才可报有效五组对照。当前evaluation_ready=false/五main0/视频0。E资格齐备可以先跑、不等WM，但不得利用E结果调其余方法后还称同一未见比较；次数/order与原片仍由Data事前固定。

## 旧OBS正常收尾已补消费（不作为V4结果）

Data正式完整release785bd9db…的本地34小成员与远端全部35成员SHA已核（第35项为保远端的原1×视频），same result a2252439…/原1058行全链与本组先读原root一致。当前H为OBS inactive/CLOSED_ACTUAL_MAIN_PASS，不再等该scope CAS；视频未下载/解码，本组只核文件SHA。这个三view测量仍task_success/AB=false，不能成为五组的任何一arm。bulk02—04正式release已出现但本轮转V4优先未伪造新增训练行，04上游FF失败未到CLIMB首PREPARE，不作CLIMB负类；模型与旧用途全保。

## E信息权限核对（源码静态审阅，不冒原生资格）

已读AINav新FIVE_ARM_METHODS.json与RuleBaseline源码74827bd0…：选择依据是公开initial-X/public_ref排序、原fresh one-to-one alias、公开required goal和source候选/支撑高度；原receipt前不推进，缺关联最多一次公开approach，失败/拒绝不重试，无VLM/WM/本优化或私有存在性路线。明确工程规则先验，符合E角色；完整native/terminal仍未接，不能从6项source软件测试宣称E已可完成V4。E由AINav持有实现，本组不另写第二份或在五组结果后换成正确路线。

用户后续要求三箱参数适配原技能，已补统一轻箱参数锁与7项检查；当前scene三箱本已匹配，未修改数值/平台，具体见V4_BOX_PARAMETERS_CN.md。

## 2026-11-16 06:15：新component失败独立消费与五组reader身份隔离

Data原35源/程序788c6116…的第一次component_zero因私有catalog缺`model_input_allowed=False`在task0首帧writer边界closed，result1469fdb2…/release3daf48d2…；Reach独立核12本地小成员及13远端原小文件SHA、读取literal result/ledger。任务0命令/0sim/0归档帧、capture未完成/选择0/选中技能controller0，不能因内部C执行底座flag称C或E失败，更不能造PUSH/CLIMB/NAV负类。原aux1world/6.505sim、24.690580467wall、12,013bytes known另记；成功成本None。空流cold字段为真不代表实际PD/视觉覆盖，491成员freeze完整性这里只消费原audit报告、不冒本组全重算。

本组`v4_outcome_summary.summarize`现要求输入行明确 `run_role='V4_FIVE_ARM_TASK_MAIN'`、`source_phase='main'`、实际原件绑定的 `source_task_main_dispatch_count=1`（拒bool），并拒`component_not_C_or_E_method=True`。source adapter须从真实冻结/dispatch/原结果提取，不能手填把component升级；纯reader本身不是原件证明。真实main即使method unavailable/0API也保分母，只不建立有效方法对照。新增5项针对性回归，连受影响methods/reference/provider=74纯软件检查本地/46308两端过，非物理试验。

Data已经独立冻结原35源＋自身privacy-annotation adapter的v2程序a0e8ada0…/492成员；06:10:08 snapshot在途、423实际capture采样/2.115sim、尚无terminal/result，**不是v1恢复、不是E/C/main，也不是新的39源资格**。本组不操作其H/锁/driver/once。AINav新39源305a48b3…已接有限CLIMB→NAV factory/outer/public30intent和高台终点source及明确私有双禁止标志，逐成员SHA只读核过；仍软件，40cm/static deck/后续source链及真实WM/完整cost/exit缺口不由接线自动消失，不借19/25 zero。

小摘要`operations/V4_BOUNDED_RECORDER_FAILURE_INTAKE_20261116.json`不含帧/数组/模型，失败包whole_artifact_model_input_allowed=false/training=false/不转J保持。总计划be3aa7e5…新增J2a只为候选未来TRAIN-only工程评审，不热换当前五组或授本批训练。
