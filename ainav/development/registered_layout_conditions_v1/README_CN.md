# G2有限登记布局条件源：可直接接原caller，未分配数据组或物理scope

## 当前优先级覆盖（2026-11-15 02:36，北京时间）

**当前仅接续Data已冻结/已开始的full-2 left→right source资格gate；full-4 center/upper-entry方案派发前暂停，不并行要求另一批。** 以Reach `G2-scene-disjoint-admission/PRIORITY_AND_SPLIT_POLICY_CN.md` 与Data `g2-full2-46308-20261115-v1/evaluation-inputs/G2_SCENE_GATE_PROTOCOL.json` 为当前问题原件，非本文历史提议。完整总计划仍G1→G6。

Data新owned `prepare_prefix.build_plan` 已实际调用本模块的 `LayoutCondition('full-2', side, 'original')`，同时消费返回的native/config/精确3请求；原helper SHA **458ec66e0e65e573c7e98a91e8c496b0ad8449ebcaec686e6ff338486010dcff** 未变。实际lane −1.9，left/right NAV y为−1.75/−2.05，PUSH(2.3,−1.9,0)，CLIMB .2，original准备；原max_requests3/exact3、SDK/Actor/原门均保留。02:34:57只读原件显示left自身zero1后main1已派发，right zero0/main0；不是动态成功或信息资格结论，不重复派发。

- 两个scope分别固定程序 **6ee69a5f…** / **b0c2d41b…**；旧G1 closed不复开。原center固定包作为历史/暂停备选原字节保留，不是新运行指令。
- 未来whole-scene/祖先隔离要求同scene所有prefix/arm/attempt同split；旧四prefix2/1/1草案不满足此要求。未来full-4 TRAIN/full-2 CAL仅来源设想，第三个任务相关source scene未合格，不能开正式三split训练；本gate仍DEV，绝不转fit。
- 现有 `scripts/measure_g1_public_boundary.py` 只额外放行这两个**精确scope+已冻结program SHA**，不泛化任意world；原首次PREPARE→exact intent/Observation、public-only/无GT规则未变。闭合后按原journal/ledger核验再测量。
- `scripts/compare_g1_public_values.py --pair-family G2_full2_v1` 显式指定新pair，默认仍旧G1；跨layout/cohort或左右倒置拒绝。layout/family仅metadata、不入45D/critic槽。原始RGBD/NPZ仍在远端。

按Reach在full-2结果前固定的四格DEV规则，还提供显式`--pair-family G2_cross_layout_left_v1`/`G2_cross_layout_right_v1`：输入槽`--left`必须为旧full-4的同prefix，`--right`必须为新full-2的同prefix。这是**预声明的同prefix跨layout整场景对照**，并非任意混组；错误prefix/反向拒绝。输出角色明确为full4→full2，名义点差在各自acquisition body frame，不称world位移/物体真值/纯因果/优化收益。未声明的跨layout/cohort配对仍拒绝。

下文中的“当前caller仍硬full-4／优先center”描述均为02:24及以前的**历史资格与提议**，已由本节覆盖；不删除其证据，也不把软件资格冒物理结果。

## 最初具体阻塞与实现（历史）

G1新端同设备left/right已实际PASS/closed，公开边界不是完全相同；这不证明重复性或critic可学。G2旧24main草案缺合法条件source，当前Data `prepare_prefix.build_plan`仍硬选full-4且`make_planner`只接受旧两份full-4 requests。**不能仅把condition名字/seed/UUID改成8种，也不能只换case却保留旧PUSH y=−2。**

本模块只解决“新原登记几何如何被同一完整Host真实消费”的源配置接点，不新增采样平台/训练器/控制器。`build_condition`默认off，无读取/导入副作用；显式开启后只返回既有caller字段：`original_native_protocol`、`runtime_config`、`requested_intents`、原`preparation_payload`及原公开有限candidate目录。没有Runtime构造、scope/lease/权限、训练分组或派发。

- 完整基线仍`ExecutionJudgedFullCourse / execution-judged-20261031-v6`、原283谱系；不是WM-v9/profile切换。
- 只允许原plan里的**full-4/full-2**。full-2只是第二个代码来源明确的布局候选，未做此Host动态资格。full-1材料不同不默认纳入；full-3/5主要远处gap变化不自动当新的有信息量入口组。
- 两layout原Actor/控制/材料/seed4301/初始化函数保持，只取原登记几何和派生元数据。几何项包括lane、step width、bridge length等；它是完整登记layout对照，不伪称只干预一个孤立维度。
- 原pre-NAV参考仍approach:left/right（原±.15），后续原PUSH到已声明dock目标、20cm CLIMB；CLIMB准备仍原3枚举0/±.04，不扩连续动作域。函数不选择G1较快prefix或修改偏移追胜。

| 原登记layout | lane | B size(m) | C length(m) | PUSH绝对目标 | upper-entry声明XY |
|---|---:|---|---:|---|---|
| full-4 | −2.0 | 2.4×1.4×.2 | 3.2 | (2.3,−2.0,0) | (.05,−2.0) |
| full-2 | −1.9 | 2.4×1.5×.2 | 3.0 | (2.3,−1.9,0) | (.05,−1.9) |

数值保原源码运算浮点结果，不手工round后破坏catalogue精确匹配。

## 未来新cohort的实际消费点

在新owned程序中调用（`source_root`是该程序已验证的完整common-source，`integrated`/`host_profile`/`candidate_api`是原同源对象）：

```python
selection = LayoutCondition(layout_id='full-2', prefix_side='left', candidate_id='original')
condition = build_condition(selection=selection, source_root=SOURCE,
    integrated=integrated, host_profile=original_host_profile,
    candidate_api=published_candidate_api, enabled=True)
config = condition['runtime_config']
requests = condition['requested_intents']
planner = types.RequestedPlanner(deepcopy(requests), journal, max_requests=3)
# EXISTING, unchanged execution path; Data owns resource/authority/own-zero:
# runtime,... = runtime_adapter.construct_runtime(SDK,config)
# host = ExecutionJudgedFullCourse(...,config=config,planner=planner,...)
# existing candidate binder consumes condition['preparation_payload']
```

新cohort应以自己的预登记选择/requests精确白名单替换旧G1 `make_planner`的full-4两列表限制，**不是删白名单或接任意XYZ**；原`request_contract.verify_completed_requests`的exact3/三条真实matching succeeded/准备不冒语义成功要求仍保留。不热改已closed G1，原default2不改变。

原integrated.protocol/validate_protocol函数被直接调用，原HostProfile只做device overlay；模块同时pin原源码/plan/template/full_course/deployment/candidate API及callable namespace。原FullCourse实际public ref构造和原intent_catalogue源码在明确SOFTWARE ground fixture上执行，证明新requests与原语义目录逐字匹配；真实original opt-in3 planner也接受这些请求。**这些不是实际Host/Runtime/支撑READY、动态可行性、compile或own-zero。**

原语义目录本来就把task意图与native资格分开，公有目标不能证明可执行。Data新程序还须核加载的配置/模型/SDK/Actor/GL/同设备/设备锁/lease/自身zero，原12N/4s/stop/FIFO等不变；原SDK和环境按已核路径复用，不重装全栈。源配置ready不代表已完成这些资格。

## G2数据分组、下一问题和停止

**具体下一问题：** 在源上合法、实际可观测的入口/布局条件中，原同域准备候选的后继success/cost是否存在可预测的差别，还是常量成功/均值耗时即可？本模块只提供可核执行条件，不提供预测/答案。

- Reach须在采新数据前固定新用途协议、独立init/scene/ancestor分组、训练/校准/验证角色、样本/重复性依据和停止规则；Data按其已合格请求执行。旧G1/旧Stage-B/GT不改fit用途；本模块没有TRAIN/CAL/TEST字段或scope ID。
- 同一条件/祖先的不同candidate后果必须保留关联，不能把candidate ID/新seed/UUID当独立组。两layout×两side仅是有限**描述目录**，不自动是4独立init/scene组，更不是8组或12个已排队main。若分组不足，就如实缩小研究问题/明确缺的第三源组，不捏造heldout证书。
- 只比较已注册、native资格满足的条件。预定source拒绝/缺观测/原guard失败、未到PREPARE、资源censor全保分母；不因负结果改lane/width/seed/candidate直到成功。选定每批有限问题后再新freeze/own-zero，不能用本目录一口气扩扫全组合。
- `runtime_config`是执行端设置，包含原物理参数，**不得整块送入selector/critic**；公开候选只来自原声明reference，当前状态仍靠合法public observation。声明布局/无uncertainty不是实测pose/点归属，参数metadata不是在线状态特征。

## 已有软件资格和边界

最终10项本机stdlib差分检查通过（初版9项另保留，最终10含那9项，不算19）；包含同full-4原请求精确回归、新full-2原真实语义catalogue/source refs、有限候选/材料不变、source drift/foreign namespace拒绝和真实opt-in3 planner构造。它们都是软件fixture，物理/训练样本0。尚未被Data当前运行程序实际配置采用，不称full-2资格/新方法收益。

云端/服务器代码按用户指定code-only方式同步；原始数据、权重、环境/大产物不入Git。G1不重开，G2不自动开始fit或24main；合格后持续G3→G4→G5/G6，不以模块完成当研究目标完成。

## 02:24历史请求：同full-4 center/upper-entry源gate（已在派发前暂停）

本模块同样直接对接Reach已发布的`G2-registered-source-cardinality-gate`，**不把采用full-2布局作为这项已明确gate的前置**。full-4的prefix key现允许原left/right/center/upper-entry；full-2仍只允许left/right，避免自动把所有组合派出去。字段`prefix_side`保原API名字，值upper-entry表示离散reference key，不表示新增任意侧向控制。

- center为NAV `cuboid-2:approach:center`，(.5−.58,−2,0)。
- upper-entry为**NAV** `cuboid-2:upper-entry`，(step_docked_front−1.05,−2,0)；source0，不是让NAV上.2。之后PUSH(2.3,−2,0)/CLIMB .2与原准备original不变。
- 已与Reach精确请求文件逐字段比对，并执行原真实source reference构造/semantic catalogue和typed opt-in3 constructor（SOFTWARE fixture）。旧G1两个case不重跑，**新center/upper gate最多各一次main**来自其独立待准入问题；模块不分配scope或将有限目录所有case当已排队。

**不能由目录/semantic catalogue推出upper-entry native admitted。** 原`FullCourse._entry('NAV')`对当前非READY-arm的compact路还核实际ProtectedStow owner的face-retreat≤.18m；upper-entry相对approach:center的X多.13m，当前A轴/位姿/owner/碰撞与movement READY必须由原动态门实测。不能用初始静态蓝图推定通过/失败，更不能换backend、伪造冷启动/owner或放宽.18门来让引用可执行。原门拒绝属于本有限source-cardinality问题的有效负结果，center也可能与原隐式PUSH准备等价。

当前Data旧G1 `conditions()/make_planner`精确白名单仍只有left/right。新owned gate应按已发布新两条件声明替换白名单，保exact3终点/原门，调用本模块生成既有fields；不是热改旧closed程序。只需该gate必要接点，不要求新scene或更多wrapper/日志/消费回执。原full-2仅供后续布局/分组研究的可选源，不阻任何已合格现有同域cohort。

最终检查现11项（前述10项加这一项请求/原目录回归，**不是累计21新项**）；本机与新端相同软件检查，动态和统计资格仍未声称。
