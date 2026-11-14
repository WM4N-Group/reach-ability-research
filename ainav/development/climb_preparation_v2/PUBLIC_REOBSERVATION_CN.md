# 一次有界公开再观察：执行侧接缝及当前正常路径的 No-Go

2026-11-14 13:18。本开发版落实Reach已存在的 `information_action` 请求到**原** `Host.observe_public` 的执行侧保护。不新增Data日志合同/runner/技能/控制目标，不改变closed Stage-B，不产生新的物理准入。

## 已可调用的接口

```python
# 未来由既有owner在新程序中构造/验证原Host后、prefix首步前组合。
# 这里不创建Host/Runtime、不申请GPU、不安装到当前closed程序。
binding = bind_public_reobserver(
    host, expected_host_type=types.Host, enabled=True)

# 只在原成功owner已退休、原receipts已消费的决策边界使用。
# live_snapshot必须来自该次合法在线public observation，不来自历史包。
request = information_action(live_snapshot, reobservations_used=binding.used)
observation = binding.acquire_if_requested(
    request, previous_acquisition_time_s=live_snapshot['packet_time_s'])
# False request返回None且不采集。合法返回仍是既有Observation，无新schema。
# 不循环；即使取到新鲜运动，未知后继预测仍须UNKNOWN/default/弃权。
```

`enabled=False`默认不读host、不安装。expected_host_type须来自既有严格consumer，Python类身份本身不是source/lease/安全资格认证。

执行边界：

- 只允许fresh host首步前绑定一次，预算与broken状态为只读property，无reset。
- 原prefix必须已经由host锁存完成（loop与prefix_proof存在），不额外poll原NN或session.outcome。
- 同root/world/model/data/FIFO/factory/executor/coordinator/observer/publisher；原loop/runtime/executor一致，authority无active/blocked/protection，原200Hz时钟/tick一致。
- 原session若存在，必须同root；前PUSH proxy/TargetBridge仍可独立，不压平。仅succeeded/protected_exit_complete已退休边界可采；active/failed/budget_expired/待回执/待保护一律拒绝。
- 每host最多1次原capture/publication，**异常也消费预算**。不得反复传0重设、热重装、HOLD/NAV等待、额外step、恢复状态或改goal。
- 前后核原`world_snapshot`及原observer snapshot/unchanged，包含qpos/qvel/act/ctrl/FIFO，不只看时间或薄hash。异常保留原状态并抛错，由owner安全收束，不rollback掩盖。
- 返回publication/camera clock必须是真实当前物理钟；不能把cached frame重标now。即使新render成功，若与上一采集钟相同，明确`acquisition_clock_advanced=False`，不冒时间信息增加。
- 记录真实callback wall/进程CPU、sim elapsed、issued step、capture/publication数；storage保持None，仍由原runner实际统计，不能声称0开销或以此绕过原lease/watchdog/九流收束。

## 本地资格与边界

10项定向CPU检查通过。实际执行原完整Host的`ExecutionJudgedFullCourse.observe_public → FullCourse.observe_public`方法链、原Observation与NativeOptionExecutor/Session类，衔接真实Reach请求与后续UNKNOWN处理；root/proxy分离保留。

**传感capture、数值publisher、geometry/support和root状态是明确software ports。** 没有构造真实Host/Runtime/Actor/NumPy/PIL/Renderer/GPU/物理，没有远端CPU资格。隔离禁重模块/network/child为空。最初夹具漏runtime.last和Reach合法snapshot role的错误日志保留，只修夹具，未降原guard。

证据：`/home/yuanyue/main/work/ainav/manifests/bounded_public_reobservation_20261114_v1/LOCAL10_ORIGINAL_PUBLIC_CALLBACK_AND_REACH_REQUEST_CPU_v2.json`。

## 已用真实历史公开记录否定的弱解释

Data13:09新增原有公开query包release **6921b24c…/63成员**，12份实际query（每支4）。AINav逐SHA、原Observation语义SHA和physical_observation_sha精确join核过；区分base publisher文件与可能额外含pending skill_status的Host intent-observation，原绝对路径未改。

历史包保持**HISTORICAL_SEEN_DEV_AUDIT_ONLY**：只作字段/时钟/接口可用性回顾，未传入要求ONLINE_PUBLIC的前瞻API、未fit/调阈值/重放为当前观测。

- 在84.430s的原CLIMB PREPARE决策，只有35.190、53.330、84.430三条可用；第四条97.815/97.800/97.970属于准备后的READY处，不能送回早期决策。
- 这三条45D数值及对应RGB文件SHA在三个arm间分别相同。公开路径、generated target UUID、证明hash等可不同，**不是物理状态特征**。
- 同一状态配不同候选，本来就可以产生不同未来后果。因此以上相同不反证候选条件预测模型，也不证明全RGBD理论不可辨识/完整hidden state相等。
- 各query publication==acquisition，45D完整、age0；原`IntentExecutionCoordinator.__call__`本来就每个物理边界做一次原采集，同次拒绝重选复用同一immutable observation，不伪造sensor tick。
- **正常当前路径不缺一张“更新鲜照片”**。新鲜输入下Reach原逻辑不请求额外capture；同clock再拍也没有新时间状态。不能仅以“刷新照片修复时效”为理由新开物理实验。
- 决策前历史跨度49.240s但最大间隔31.100s，是稀疏query而非连续45D历史，不能证明原1s stable/3s verify。第四帧45D在arms间有差异，只能在其较晚时钟的后续问题合法使用，不拿来回填先前候选排名。

实际公开数据检查：`/home/yuanyue/main/work/ainav/manifests/bounded_public_reobservation_20261114_v1/ACTUAL12_PUBLIC_QUERIES_CAUSAL_AVAILABILITY_AUDIT_ONLY_v1.json`。

## 下一独立工作与外部缺口

本调用接缝用于真实缺/旧信息时的有界路径，不是自动加拍或新策略收益。正常时效假设已收束为No-Go；不要拿同钟重拍或扩大δ继续追胜。

下一实质方向应集中在**合法相对几何/状态估计或候选条件后果评价能力**：RGBD可见点不自动等于完整对象中心/注册reference-relative pose，body速度不能在没有合格初值/yaw/误差界时积分成可靠world pose。继续源级与开发实现；若确需模型/新数据用途，必须提出具体方案另授权，不拟合现有audit。当前缺口已不是拿不到公开原件，也不是Data未执行三支。

## 14:21原resolver约束补充（覆盖前述宽泛same-clock表述）

原CourseBindingResolver.observe只接受严格更大的physical_tick。此前软件resolver端口没有覆盖它；本开发版现已在capture前拒绝当前tick已被resolver消费的请求，并封存resolver身份，不step/reset/wait。11项再观察suite通过（新增1条原约束，其余10为既有回归）；原完整Host方法仍执行，数值/传感/几何为明确software ports。只有“同clock曾有sensor packet但resolver尚未query过该tick”的第一次query才可能返回clock未前进，**不**授权重复原query。详见同目录`PUBLIC_COMPONENT_SUPPORT_CN.md`及本轮同tick负对照；原Stage-B不改、不重跑。
