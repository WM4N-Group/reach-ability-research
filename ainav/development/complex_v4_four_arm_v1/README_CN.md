# AINav接任V4五组：精确资产移植与能力缺口，不是原生通过

2026-11-15，按22:53总计划。当前优先A/B=VLM+WM无/有共享优化，C/D=原AINav无/有同一共享优化，E=无VLM/WM/优化的固定规则；主比较B−A/D−C。旧API0 greedy/multistep两组不是这五组的代理。

## 已接手的实际实现

- scene.json逐byte保留用户确认V4（SHA6394740e…），没有修改墙、箱体、C对接或0.60m平台追胜。research资产代码已移入本组可迁移目录，不再依赖本机research绝对路径。
- `v4_native_asset.construct_into_native_spec`只准fresh task0/FIFO空的Data spec：先加真实collision goal_deck，再调原complex_scene构造器加墙/三箱，保原robot/Actor。尚无原MjModel编译/zero/world/派发。
- `registry`实际调用选定冻结原SceneRegistry，goal.surface_ref=goal_deck/top=.6；公开投影包含平台声明，不公开private review/正确路线。不能原样套旧ground-only driver/catalogue/终点。
- `elevated_stop_sample_only`仅为私有必要sample谓词：foot Z相对.60、目标XY、每脚12N/速度/tilt原门，并需实际contact provenance的goal_deck引用。ground同XY必须false。**不是完成判据已集成**：仍缺同world原owner证明、三immutable placement、原CLIMB回执、实际contact reader、连续dwell及safe-stop caller。

## 已定位的真实阻塞，不以“高度相似”掩盖

`capability_boundary.selected_climb_rise_audit`只AST抽取当前原SceneRegistry的纯climb_geometry判定，SHA钉住，不导入Runtime/NumPy/Actor。declared geometry只是用于该纯谓词检查，不作为真实感知或控制输入：

1. ground0→箱顶.20符合该原20cm高度谓词；**箱顶.20→平台.60的.40增量被同原谓词明确拒绝**。这是选定完整v6/283当前registered路径的边界，不声称所有其他仓库/技能绝无40cm能力。不能把常数.2改成.4/降低门后称原技能资格。
2. 原`RegisteredClimbAdapter.bind`还要求当前RGBD关联映射到registry.objects中的body；goal_deck是static SurfaceSpec，不在可移动object集合。加surface registry本身**不自动打通static-deck CLIMB**。把静态平台伪装freejoint箱体或用静态GT代当前关联都不可接受。
3. 原ground-only TerminalStop核foot Z≈.022，不是高台.622；旧NAV/compact support owner、CLIMB exit→后继owner也必须逐段核实际适用域，特别不能宣称旧.2后NAV/PUSH站稳缺口已修。

**主运行前的最小方案供共享设计决定：** 若坚持当前20cm registered技能，不改Actor/原门，需一个真实0.40m中间支撑，把高度接续变成0→.20→.40→.60；它改变已确认布局/原两段预期，必须五组共享、在新主运行前明确确认/重新冻结，并另核static-surface association/owner桥。这里**没有加平台或改V4图**。另一方向只能先找出已有准确40cm原技能/权重及真实接口/资格；没有证据不能宣称已支持，更不能擅自训练。

## VLM/WM身份与后续实现

- 原AINav应复用冻结`AinavPlanner`的object/skill proposer、tree evaluator、advisor/arborist与replanning，不换成固定脚本或API0有限搜索。Reach负责A/B现有WM推理与B/D同一优化；此包尚未实现四个方法adapter，未调用WM/VLM。
- 非秘密元数据核到两份provider配置不同：本机active profile为deepseek/deepseek-flash/TLS；选定旧完整source profile为历史sol_gateway/另一模型/非TLS。**不能猜用户本轮所指服务、无声切profile或把新key发送到旧HTTP网关。** 待一次明确Base URL/模型与既有受保护运行入口；不需要再次提供明文key。未读取key/env内容、未做任何API探针。
- 新source当前仅资产/必要谓词与准确边界，不能提交五main派发请求或宣称共同可行链。下一实际工作：确认选定现有CLIMB能力/最小共享设计修订，继续surface-aware实际caller与终点/强baseline真实VLM接缝。基础场景/registry代码可先由Data纳入必要新端组件资格；本包不是该准入证明，也不要求额外收件签字。

软件14项只测原纯API/资产与拒绝边界，不是14研究样本或native资格。旧closed A/B/OBS根、bulk在途/冻结程序不改；WM只开放本任务既有推理，不恢复新训练/底层Actor/真机/第二物理owner。evaluation_ready=false、独立TEST0、五箱false保留。

## 新增E规则源（未接完整native driver）

`rule_baseline.RuleBaseline`是真实原IntentBatch/Selection/NativeReceipt接口：按公开initial X/public_ref固定工程优先级处理required placement；当前关联缺失时只试一次已声明approach NAV，fresh仍空则明确UNKNOWN/停止，不盲按时间播动作。PUSH只在真实同intent/params succeeded receipt后计入已完成；所有地面placement后，以公开最小下一高度/到goal的一跳名义距离选CLIMB，平局target_ref；无VLM/WM/B-D优化、私有pose/未来轨迹/存在性路线。每次64上界/fresh query，拒绝/失败不换seed或静默fallback。

这是场景公开几何的工程规则，不冒通用规划或最优策略；不使用V4主运行后果调优。当前.2→.6会按同原20cm域明确停止，static-deck/owner/完整终点尚未集成，E不能自行签task success。E接口代码存在不等E具备主运行资格，更不把旧API0实验改名E。
