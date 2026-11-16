# D组终点前缀候选遗漏修复（纯软件，不是方法收益）

更新时间：2026-11-16 14:14。主计划7559f685…仍E优先，此修复不阻塞E、不改原AINav/原Actor/Native安全门，也不新增物理或模型调用。

## 可复现的问题

原SkillTree.add把共享前缀合并，并在每条计划终点设置terminal。于是同一个节点可以既terminal=True又有children。例：

- 短候选：[NAV(target1)]，模型宣称到达目标；
- 长候选：[NAV(target1), CLIMB(goal)]；
- 另一候选：[NAV(target2), CLIMB(goal)]。

这是**明确软件构造**，不是当前V4的真实可行计划。原D枚举仅取无children节点，丢掉短候选；B直接消费计划列表则保留短候选。相同输入计划在此情况下产生不同待评估候选域，且短候选的未知成本可被错误跳过。这里不声称B/D在所有场景有相同proposal domain：两条规划路线原本不同；修复针对相同提议经prefix merge后的信息遗漏。

## 最小修复

在AinavSuccessorAdapter的visit函数中：

1. 对terminal节点**或**叶子生成PublicPath（terminal叶子只生成一次）。
2. 不论该节点是否terminal，都继续遍历其children。
3. 不新增假设为非terminal内部节点的完整路径；未完整叶子仍交cost provider，未知不得当零。
4. 不把terminal/reaches_goal当native成功或complete cost。原CompleteReferenceCost的完整三阶段与terminal检查仍要求显式模型输入；目前真实provider未齐，保守退回原选择。
5. 不修改原树、VLM调用次数、C流程、原selector或E；真实dispatch仍由原执行底座负责。

## 验证记录

测试文件：`/home/yuanyue/reach-ability-research/research/task_conditioned_reachability/execution_preparation/test_v4_terminal_prefix_paths.py`。

- 修复前5项：3失败、2通过。失败分别为D漏短候选、同提议B/D候选域不一致、短候选UNKNOWN未评估。
- 修复后7项：保短/长分支及唯一path ID、同提议B/D一致、terminal仍需cost/UNKNOWN回退、不造非terminal内部候选、C关闭不评cost、原树/role调用不变、partial叶子UNKNOWN回退。
- 受影响SourceSeamTests：23通过。合计本地30/30、46308同一最终代码30/30（远端报告0.134s，仅软件套件时间，非技能时间）。
- 远端Python复用`/mnt/yuanyue/data-team/env-native-v1/bin/python`；未安装/修改环境，未创建Runtime/Actor/WM或执行physics/API/fit。
- 原纯source contract/tree在现有owner_snapshot中仅用于软件fixture；没有执行owner_snapshot物理程序。

实现提交：6945666。
旧adapter SHA：38787016a99e346b92d745a8ca0884128b68356d29beb9fe28e8f140a2865689
新adapter SHA：c93103859afd24d80557a05b53f3eedd53db0e96f739f3e089a7c229c7a7a4a4

## 发布与冻结边界

代码主副本本地/GitHub/46308同步不等已有Data程序采用。AINav `method_entry`硬pin旧adapter，保留其原bytes。未来B/D确需集成时，由对应owner按新准确程序更新一致源码pin；**不要求E为此等待、不修改既有freeze/closed源**。不因本修复重新运行旧实验或增加第三方测试前置。

本次未解决公共当前reference、技能三阶段名义effects、退出与fresh观测预测、完整terminal cost、真实WM bootstrap/PUSH/CLIMB映射与高台域。不得把标准树遍历修复、fixture胜选或原AINav流程当研究创新/任务收益。
