# 相同真实决策前缀下，Reach两策略已产生不同意图，B已被原NAV consumer执行（仍非任务收益）

本轮补齐的不是新fixture或重复原AINav成功，而是**本组独立读取实际A/B已记录原数据，核研究选择确实进入原执行器**。原A失败/原B在途/同b08 source、e72ddbb2…协议与全部旧closed保持，不改控制或重跑。

## 决策之前到底是否相同？

在46308以NumPy只读两支前3个已完成immutable command chunks，独立逐dtype/shape/bytes核**前448个实际capture命令**：issued、delayed、torque、raw_torque、q_before、dq_before、physical_tick、time_s全相同，ticks恰1—448。不是用seed标签或world0图片代替控制前缀相等。

两支2.240sim的真实第1个public Observation也完全相同，**仅RGB文件存储路径不同**；仍保留A31b92b0e…/Bb0d229fe…两个原canonical SHA，不覆盖成同hash。只在比较的内存副本排除path，原文件不改；RGB原文件bytes/depth/calibration保持source pins。两支objects均空，因此没有给B额外视觉身份或GT来选路。

A462行closed journal和B取读时**完整append-only前缀**均独立验原hash链，读取前后确认既存B前缀不改；B前缀不是终态日志，不升级为B结果/整条轨迹相等。

## 实际不同选择与原执行消费

| | A greedy | B multistep |
|---|---|---|
| 同一root名义候选 | 6（不是6个已准入原target） | 6 |
| 实际第1个高层bundle | cuboid_a→(1.85,0) | cuboid_c→(9.7,0)，先必要原NAV路径 |
| 实际规划wall | .004115272s | .195403451s |
| examined transitions | 6 | 127 |
| shared greedy fallback | false | **false** |
| 第一个实际semantic intent | PUSH cuboid_a→(1.85,0,0) | NAV cx-nav-000→(-.08,-1.8,0) |
| 原native消费 | 当前RGBD门拒绝，task option0 | 原NAV option **3fe554cb…**安装、原Actor实际forward、**physical tick449/time2.245**已发首task命令 |

B actual intent SHA、原private interaction binding及原option SHA逐项对应，params完全一致；不是只写选择日志或Data代写固定路线。采样时已看到319个原`registered_NAV_actual_actor_forward`事件，但这**不等319个选择/原NAV已成功/已PUSH重构**。B仍第1个bundle/首段NAV，后续名义路径和最终目标是预测，不是已发生的事实。

这是标准bounded uniform-cost在原公共模型的实际消费证明，**不是新搜索算法/已证明主要贡献**。原Actor/guard/QP/FIFO/12N/4s/stop、观察/布局/同GPU/预算均未改，未加载或重训高层critic。

## 当前尚不能下的结论

- 不宣称B已完成首NAV、3次有效决策、PUSH/placement或完整任务，更没有A败B胜/完整母版验收。
- A实际在最初的当前观测可用性门前失败，未执行原拟几何陷阱。即使B后续通过，也不能凭这对就把差异归因延迟通道耦合，或称强“当前原生合法候选”greedy已输。
- B的.1954s满足本次.25s search预算；若后续触发整个native/recording/guard wall或资源cap，必须按原资源/执行证据分类，不把通用执行开销全部说成多步搜索计算超限，也不临时热抬cap。
- Source新的两NAV/三视角观测研究仍独立source问题，不并入在途B，不改旧A/不挑大片/降门/补PUSH。

原artifact：`/mnt/yuanyue/reach-runs/T-actual-predecision-control-consumption-20261115-v1/ACTUAL_PREFIX_AND_ORIGINAL_NAV_CONSUMPTION_v2.json`。小型无原数组副本在`operations/T_COMPLEX_01_ACTUAL_FIRST_DECISION_CONSUMPTION_20261115.json`；reader `operations/check_complex_actual_predecision_pair.py`禁止torch/mujoco/onnxruntime/网络/子进程，只读原数据。v1/v2是同一已在途trial的读者完善，不是新数据/两次物理对照/额外Actor运行。全部原数组只远端。
