# G2当前优先问题与隔离约束（2026-11-15 02时）

## 接续已有方法源，避免两个新gate并行浪费物理次数

已消费AINav 01:30交付的`G2_NEXT_REGISTERED_LAYOUT_SOURCE_OPTION_NOT_QUEUED.json`（SHA4ea6158a…）。其原登记full-2与已实跑full-4保持Actor/控制/材料相同，有确切新layout来源：lane_y -1.9 vs -2.0、step宽1.5 vs1.4、bridge长3.0 vs3.2、gap .15 vs .2。当前Data build_plan仍literal full-4，full-2并未接入当前真实caller或取得动态资格；不能只改label/UUID。

**Reach当前优先接续这一source-owned full-2最小资格问题**，而不是同时要求Data执行本组上一轮center/upper-entry另两prefix提议。后者是原库真实合法引用的候选问题，但只增加同scene前缀，不能解决更强的scene/祖先隔离；原请求文件保留为“派发前暂停的备选”，不删除、不称已执行。两个方案都没有由本组分配scope、预约资源或派发。此优先级不是修改原总计划/他组代码/权限，也不是等待新的经济签字。

当前最小新问题：**使用原registered full-2场景及它自己的公开目标，在same Actor/init/seed4301/三请求/CLIMB original下，left/right原生前缀链能否实际完成并产生有信息的first-PREPARE输入？** full-2需使用lane_y=-1.9，PUSH absolute(2.3,-1.9,0)，NAV prefix原引用所定y=-1.75/-2.05、x=.5-.58；CLIMB destination .2。不要套full-4的(2.3,-2)目标或声称只改变一个前缀变量，这是预先声明的**跨登记layout条件资格**而非纯几何因果/优化器收益对照。

建议资格pilot最多两新main/条件各一次、fixed left后right，scene/source/公开目标/实际caller由AINav交精确版本，Data复用已成功v2原runner、私有expat/环境/SDK、new freeze/own-zero/lease/watchdog/原门。沿既有G1信息与失败分母协议，不新增logger/reader合同，不等critic或全部UNKNOWN。source不符/原门拒绝/失败/缺PREPARE照实保留，不换seed/goal/scene凑成功。**此处只是待source-binding的最小方案，不是合格物理包、scope或派发。** 若已有同任务合法在途/closed，先接续消费，禁止创建第二批。

## 分组设计纠偏：condition数不等于scene数

前一份4-prefix的2TRAIN/1CAL/1VAL设计已明确只是弱condition-disjoint原型；它不满足本轮要采用的**whole-scene/祖先隔离**，不能称未见layout验证。不能将同full-4的left放TRAIN、right放VALIDATION，或按candidate arm/不同frame/sourceID/新seed拆分来声称跨场景性能。

新G2训练用途协议需要先冻结source scene→split映射：

| 角色 | 当前可指明来源 | 状态 |
|---|---|---|
| TRAIN | 未来新采集的full-4条件族，所有prefix/arm/复用祖先归同split | 原G1为DEV，不能拿现有pair训练 |
| CALIBRATION | full-2若经当前caller/动态/信息资格通过后的未来新用途数据 | 目前只有源候选，未合格/未采训练资料 |
| VALIDATION | 第三个真正有任务相关变化且source-qualified的scene族 | 尚未选定/资格；没有就不能宣称三分组数据集可fit |

同一source scene的所有prefix/arm和未到达决策attempt都随scene走同split。多个条件可在TRAIN中用于state variation，但独立scene数另报，不把prefix当额外scene。

**不为了填第三组盲跑原plan里full-3/full-5**：源上它们相对full-4只改远端gap，对当前PUSH→首次CLIMB的任务相关信息/后果尚无证据，不能仅换sceneID就称有信息的独立条件。full-1原登记case还带C质量/摩擦默认差，与full-2/4不同，不可假称同材料几何-only；如以后选它须明确scope/因素并由owner资格，不在本文件预定数据角色或派发。第三场景问题要有source与当前预测目标依据，而非按结果追胜。

两个scene目前不足以支持TRAIN/CALIBRATION/VALIDATION三个互斥scene split。这是**正式训练cohort的准入缺口，不阻full-2这项已缩小的source资格测量**，也不是等所有感知/大模型完备。不把无CAL的两scene试验暗称已校准部署。如后续改成仅TRAIN/EVAL的未校准原型，必须明确另一个更弱协议/结论范围，而不改现有冻结8组协议或训练器数据角色。

## Source scene key与代码保护

Reach在自己的未来dataset adapter从Data已保存的原protocol/actual-config/constructor来源生成`source_scene_sha256`：以实际scene_recipe、原场景构造源SHA、物理scene/材料配置等规范化内容为依据，不用episode/source/scope/UUID/路径/case显示名称给相同scene造不同组。相同scene再reset或不同前缀不会变成不同scene；规范化定义/默认材料解析及版本必须随新数据协议冻结。

这是**Reach-owned训练表的metadata**，绝不放入48物理预测槽，不要求Data新增日志或生成NN表。数据来源资格仍由真实原件绑定核验；一个手填hash或此数学检查不能证明scene真实性、独立性或相关性。

本轮只对已有critic准入补一个必要保护：新协议声明`require_source_scene_isolation=true`时，必须同时给出覆盖三split的固定`scene_split_assignments`，每个row及unreached attempt要匹配其scene固定split；换conditionID也拒绝跨split。旧condition-only协议保持原字节与原兼容行为，但报告明确标`CONDITION_ONLY_NOT_SCENE_ISOLATION`，不冒场景隔离。heldout另报scene_groups，不混condition_groups；这不认证物理资格或泛化。

代码检查在46308运行，3新场景隔离检查＋既有31项共34通过；只是SOFTWARE算术/准入，不读实际G1作fit/不输出研究权重。G3真实训练行/fit仍0；scene协议/第三source/样本规模及统计/停止规则未固定，不启动12/24main训练采样。已授权的小高层未来新数据用途无需重问，旧DEV/audit/GT仍不fit，Actor/WM/DINO/真机暂停。

## 正在做／下一项／独立备选

- 正在做[G2]：与已有AINav full-2源对接，固定whole-scene/祖先分组与有限source资格问题，防两备选gate同时派发。
- 下一项[G2→G3]：source/信息与完整分组可用后冻结**全新未来TRAIN用途**cohort、样本依据/停止规则，再真fit/分组评价/简单基线；无class variation则No-Go不挖失败，随后G4—G6。
- 无需外组备选：scene泄漏保护已完成这一最小修复，不扩数据认证wrapper/复跑fixtures；后续可核现有feature是否缺失task相关变量，但不偷偷加GT、按旧结果挑阈值或另造模型。
