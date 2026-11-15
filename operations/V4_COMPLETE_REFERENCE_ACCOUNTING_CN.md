# V4共享完整参考路程核算：已实现，但真实公共效果模型仍未绑定

2026-11-16 04:18（北京时间）。本增量是Reach自己的名义目标计算组件，不是完整V4动力学provider、物理资格、方法收益或新搜索算法。

## 这次实际增加了什么

`research/task_conditioned_reachability/execution_preparation/v4_reference_cost.py` 的 `CompleteReferenceCost` 可直接作为既有B/D适配器的同一 `path_cost(observation, path, query_sha256=...)`。每条候选从**同query公共名义当前参考状态**开始，逐步传播公开名义状态，不更新native/world/planner物理状态。

每步必须完整给出 preparation → skill → preparation_exit 三段有来源的机器人参考XYZ折线；阶段间、步间及下一状态端点必须精确连续，不能隐含瞬移、略去连接段或把未导出的退出当零。显式声明的静止阶段可以是两相同端点，其**参考路程**为0，不表示收臂、验证或等待时间为0。完整目标为所有步所有阶段的折线路程和（m），并非秒、期望成功成本、碰撞风险或控制器可行性证书。

完成标签不能只信VLM的 `reaches_goal` 或树叶：必须由公开任务模型的完整terminal谓词核最终预测状态；截短叶或未知terminal返回UNKNOWN/None。每个forecast绑定同query、准确public primitive和传播前状态SHA，不能用另一路径、旧query或bulk后果缓存。当前参考缺失不回退静态initial blueprint，任一步准备/退出缺失不补0；明确名义refutation保留为名义排除，不改native gate/receipt。

分阶段标量及来源写 `reach_v4_complete_reference_cost`，交既有shared selector进行全域/预算/UNKNOWN处理；并非增加另一个搜索器。生产A—D适配器拒绝显式 `software_fixture=True` 的cost provider，防软件fixture被误接成真方法；A/C原OFF路线不求cost，B/D仍共享实现。

## 如何接，不由Data代研发

Reach下一步仍需实现/绑定三项**真正公共名义模型**：

1. `initial_state(observation, query_sha256=...)`：公共可用、当前的名义参考与已核公共效果；缺失返回None，不能读private pose或以箱initial坐标冒live。
2. `forecast(observation, primitive, state, query_sha256=...)`：由声明几何/原技能可用接近和退出域生成三阶段参考、名义effects；非原件/权重WM推理或bulk实测标签，不读未来轨迹。组件现在没有替源猜一个PUSH/CLIMB exit。
3. `is_terminal(state)`：完整任务三placement＋目标层终止的**名义**谓词；后续真实placement/CLIMB/高台停稳必须原native另验。名义模型永远不替真实成功门。

AINav已导出27公共intent/24 anchors，但 `PUBLIC_EFFECTS` 的preparation-exit variants仍空；static deck、动态支撑owner与.20→.60原20cm域冲突未解决，故**当前没有把此accountant绑定到生产五组、也没有合格的KNOWN_NOMINAL整链cost**。不能把纯核算器描述为“完整后继估计已完成”，不能将上游工作交给Data或拿标签/正确路线填回调。

## 本轮验证与源变化

- 新14个核算专项＋2个适配器接线/fixture隔离回归，连既有受影响methods/provider共**65项纯软件检查**，本地和46308既有Python均过；是同一套软件检查的两端复核，不是130试验/训练行/物理样本。不重跑bulk reader、模型restore或旧capture。
- AINav最新32成员source package SHA `adfe550793150ae69d474062d634d9a4c9bd1b2d4100dd23be5ffd3a6434eff5`逐成员SHA只读核过。新 `climb_nav_source` 在真实CLIMB回执边界读取必要同world/contact/12N/实际发出reference证据；**尚非原NAV可接受的typed-owner bridge**，本组未调用该实际reader或改他组源码。不能把这个新增观测器当CLIMB→NAV闭合/借旧zero。
- 本轮WM forward/Actor/physics/API/fit/critic评分0。原7a6、legacy-common H五组同开、B/D新treatment、所有closed/失败/用途及继承dirty不变；bulk24已收束，不追加、不refit、不转J。平台/布局旧询问不重复、不擅改。
