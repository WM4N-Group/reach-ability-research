# T-COMPLEX-01：两策略和共享几何核心已实现，尚非原生复杂场景成功

已读最新总计划（标记2026-11-15 14:00，SHA b2fb786e…）及任务书a3ade42a…：此任务优先于等critic/100条全齐；当前TRAIN6不热改。13:45版本0bfd5886…与旧53233939…仍为历史，未改先前原件。任务是原生复杂场景、两arm各一次和真实live母版，不能只交图/测试/动画。

## 本轮新增代码，不是只报计划

`/home/yuanyue/reach-ability-research/research/task_conditioned_reachability/execution_preparation/finite_multistep_planner.py`

- 同一`propose(...)`入口，两臂共用source有限候选、公共nominal状态、同一`nominal_connection`和同名义代价，天花板相同。
- A按当前任务相关合法候选的名义当前代价选最小，不手工指定失败动作；同cost tie按原catalogue顺序，不按预知输赢。
- B对同一候选图做标准有界uniform-cost搜索，默认4个**语义技能转移**深度/256 transition/.25CPU wall每决策，找到nominal终点取首动作；无解/预算不足显式退回同一A规则，不把视野外不可见冒无解。根域没完整读取或全UNKNOWN时弃权。记录实际调用/预算/回退；不能抢占恶意慢callback，超时只检测并报告。
- `nominal_connection`是共享公开2D几何：robot/arm source envelope膨胀AABB后判线段交集，触边拒绝、缺envelope UNKNOWN；给名义路径米数。它不是实际collision/support/FF/stop证书，不能用默认机器人半径/私有实时pose补参数。
- 不依赖critic；不调用Runtime/Actor/world/文件/网络。所有输出都是高层proposal，`execution_authorized=false`、dynamic_success UNKNOWN，不直接发动作或覆盖原judge。假想node不是实际world状态；执行后必须用原新观测重建root。

4个抽象算法/几何定向测试已过，只测代价/三transition搜索、UNKNOWN/预算、tie/cycle及扫掠接触。**这些不是任务场景、真实可行解、A失败B成功的实验或录像。** 此为标准搜索机制原型，不主张算法新颖性。原frozen单次choice核心不改。

## 与AINav真实场景直接接上，不造Data新表

最小方法调用如下（source adapter仍需真实几何/技能映射，不能手工答案图顶替）：

```python
result = propose(public_nominal_state,
    arcs=source_task_relevant_arcs, is_goal=source_nominal_goal,
    state_key=source_public_semantic_key, method='greedy',  # B: 'multistep'
    cost_unit='m_nominal_robot_route_plus_box_translation',
    max_depth=4, max_transitions=256, max_wall_s=.25)
# Original consumer alone maps result['action'] to exact semantic intent,
# checks actual native admission and executes; reobserve before next propose.
```

source adapter只需把AINav的**同任务真实有限候选和nominal几何转移**投到`Arc(action, next_state, nominal_cost, static_status)`；两臂用相同代码，不能B独占完整地图或私有未来。根候选必须任务相关，不能给A塞无意义低价noop来强造失败。公共model原生支持未知时保UNKNOWN；不能拿offline存在性路线/role标签/历史branch outcome当转移表。名义代价固定为公开model中的robot路线米数＋箱体平移米数（1+1）；未知不补0，源没有该分量须先给合格名义构造，不任意改权重追胜。

还需从**实际可执行任务源**给到：可选对象/目标/次序、每arc的原semantic/native映射、可公开的几何/envelope/关系、共同完整终点与实际stop、初始化及失败域。当前原NAV→PUSH→CLIMB/±.04不足两次重构和三选择，.2后PUSH未验，不猜新源；本组尚未接收此复杂scene adapter资格。次序与两个操作箱必须真实可选，不把固定脚本当在线策略。

本组接到该源后直接实现消费适配和本代码的共同几何/代价计算，不让Data替本组造方法loader/算法，不等critic。Data仅准确装配、当前技术freeze/own-zero/lease/原片。未来原生对比按A greedy→B multistep、同场景同init/seed、main各1、失败不重试；具体任务budget和录制采样由source/设备负载冻结，不改在途TRAIN限额。方法proposal已在同目录JSON固定，未冒已冻结原生程序/已入Data队列。

## 原片和验收仍缺，不以代码完成冒任务完成

必须同camera/clock的直接live第三视角，优先≥960×540、≥10Hz，实际能力先测并冻结；各arm完整1×、原frame/tick/time/丢帧/终止原因、同钟并排1×，可另4×。不能旧warehouse review、192×128放大、state重渲染/插帧/路线动画顶替；先结束者冻结原终点并标结束，不拉伸时间。无原片视频部分就是未完成，不为补片自动重跑closed。

当前仅算法核心＋共享几何函数已实现；source adapter/原生scene可执行资格/两arm真实结果及视频均未由本组消费，Data接收/排队未核。本轮新增物理0/视频0。下一项是实际source接入与A/B可执行性；当前TRAIN01/02监督与03—06闭合消费并行，不等100条全到，之后仍G2—G6。
