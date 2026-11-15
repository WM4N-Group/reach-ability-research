# 独立有界观测资格问题：原NAV侧入口能否解除首次RGBD歧义？

**这是待Data独立新程序资格的measurement source，不是当前A/B的修复热补或成功方案。** 当前A/B frozen `b08f51bb…`保持；A失败根不重开，B若按原协议继续须同旧源/规则，不能只给B换本版。该观测研究不算T任务完成、第三有效选择或贪心/前瞻对照，也不改布局/颜色/相机/物理材料/原视觉和成功门追胜。

## 来自真实失败的最小可辨问题

A唯一main在原SupportedCapture真实448步/2.240sim完成后，首次真实公开query `31b92b0e…`的objects为空。greedy确实选cuboid_a的PUSH(1.85,0,0)，但原视觉关联缺失使原judge拒绝，**没有发任何NAV/PUSH交互option**。它不是名义几何死局或B胜利；A scope ledger stopped/closed，不重试。

本组对这同一既存public RGBD仅在CPU执行原proposer（source837e95ec…，未改阈值/未开world/未读episode NPZ、GT或权重）：warm两连通片2153与727pixel、各100%有效depth/geometry_valid=true，原single_visible_hypothesis对二者均原样拒绝。同帧没有其它原family。不能拿最大的当目标、合并碎片/静态pose/声明初态替代关联；这两个片段是同一箱还是不同物体仍未证明，不能单凭颜色推归属，也不能据此宣称换三种颜色必修复。

**下一问题只测必要条件：** 保原三箱几何/光学rig/色彩/原64pixel/深度/无歧义/IoU .35/SDF .04门不动，两个已有原ground NAV侧入口参考是否能得到原matcher接受的当前cuboid_a？不是把可见点中位数当中心或测PUSH成功。

## 一次新episode，固定三边界，不扫到成功

1. 原实际SupportedCapture完成后的第一个public RGBD（center当前边界，不造NAV receipt）。
2. 原NAV到declared初始A entry的left参考`(-.08,+.15,0)`，真实succeeded receipt后fresh public RGBD。
3. 原NAV到right参考`(-.08,-.15,0)`，真实succeeded receipt后fresh public RGBD；到此停在同一真实原owner。

`.15`是已有原ground entry左右离散偏置，不是新侧推/自由yaw或tracking界。只发两个原NAV，每个原60sim选项预算、原支撑/四足12N/保护到达/FF/effort/QP/FIFO/接触门保留。实际到达pose不假设等于声明goal；观测来自当前真实clock/原192×128 RGBD/45D。即使第一边界已可关联也按同固定顺序保三边界，不选择最好一帧或早停充成功。任一原NAV/资源门失败即原样收束，剩余边界未达到，不替换/重置/补跑。

建议一个新owner root各own-zero≤1/main≤1；这是source提议而非已经分配scope/预算/派发。Data必须基于实际开销（旧A main448步含初始化844.49wall，不能假设旧短链吞吐）事前固定有限wall/sim/存储watchdog/lease，运行中不热改；预算停止保censor/成本。本组不分配authority、GPU或启动world。本measurement可在原B按既有规则收束后由Data安排，不改变当前pair；高优先T目标不因本文件变成层层签字。

## 明确source入口（default仍是原比较）

新`observability_qualification.py`定义独立类型/decision_source；`ComplexSceneDriver`仅在**显式purpose**时提供两个NAV候选、NAV-only capability。默认`purpose='T_COMPLEX_COMPARISON'`仍只收原greedy/multistep，原18NAV/6PUSH目录不变；禁止把脚本观测planner伪装成greedy或同源A/B。

```python
# ONLY inside Data's fresh qualified observation-study program/source snapshot.
# Keep scene/model/camera/SDK/Runtime/recorders and actual guard same as current
# successful full-host construction, but NOT its old program/zero/authority.
planner = ObservabilityQualificationPlanner(public_task(scene), journal=journal)
host = ComplexSceneDriver(components, source_root=SOURCE, bundle=SDK,
    root=ROOT, writer=original_writer, planner=planner, journal=journal,
    guard=owner_guard, purpose='OBSERVABILITY_QUALIFICATION_ONLY')
# Not the existing full-task while-not-host.complete worker: this separate
# diagnostic NEVER sets host.complete / planner.complete / original task success.
while not planner.motion_complete:
    owner_guard()
    host.step_one()
# Only after original right NAV receipt: validate actual same-world supported
# owner, acquire NEW original current RGBD, snapshot unchanged before/after.
measurement = planner.finish_from_driver(host)
assert measurement['qualification_complete'] and not measurement['original_task_success']
# Close/retain all original recorder/review/raw streams, receipts/costs normally.
```

记录三个原observations SHA/RGB SHA与原current one-to-one aliases，两个actual receipt ref，所有失败/费用与未达到边界。脚本顺序明确标为measurement，不输出A/B选择收益/全任务success。方法只读当前source原descriptor，不读body pose/GT、不从blueprint填对象，不训练。

## 退出/后续

- 若左右原NAV可完成且某固定边界出现原关联，只证明这一个必要可见性条件；**不是该视角原PUSH READY/终点成功或以后所有目标可见**。后续共同观察/entry准备机制须另固定新source/完整A/B协议，成本与信息两臂同计，旧A/B结果不覆盖。
- 若三边界仍无关联或原NAV不合格：明确本固定原感知/有限视角域No-Go/缺口，停止本研究版本，不刷seed/颜色/阈值/路线直到过。其它合法方向继续，但不宣称复杂任务能力已证。
- 当前只有source和软件fixture，**此观测episode物理0、实际两NAV/三帧资格未过**；原失败RGBD诊断是真实材料CPU测量，不混同新实验数据/fit/holdout。
