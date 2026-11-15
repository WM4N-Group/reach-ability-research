# T-COMPLEX-01 v2：Reach已给出真实source可调用的公共规划器（非派发许可）

> **2026-11-15 16:45更新：** Data d48fba0e…已验证d486组件：原camera/冷Runtime/INPUT8/GPU0 CUDA-GL及live HD单帧真实PASS；旧camera blocker解除。d486 wrapper已调用本组四模块factory，旧“base三模块”状态不再当前。完整task/实际capture/动态可行计划/A-B/视频仍未验收，组件zero不能代替新全程序的自身zero。见operations/T_COMPLEX_01_NATIVE_COMPONENT_PASS_INTAKE_20261115.json。

2026-11-15。总计划14:00/b2fb786e…未变，复杂任务优先。新增AINav三箱v2公共资产已存在，不再说“只有Reach三箱提议”；v1与其closed组件失败不覆盖、不重开。v2原生动态资格仍未过，本文件不是完整native程序freeze。

## 直接接入原scene driver

Reach主代码 `/home/yuanyue/reach-ability-research`，计算副本 `/mnt/yuanyue/reach-ability-research`。以下仅构造公开规划器，不构造world/Actor，不发命令。Data原caller应已将**本次冻结的原AINav pure source namespace**和Reach代码根加入导入路径，按source版本构造自己的components/writer/guard；Reach不接管它们。

```python
from research.task_conditioned_reachability.execution_preparation.complex_source_adapter import build_source_bound_planner

planner = build_source_bound_planner(
    public_task_path=public_task_file,
    expected_task_sha256='99d660dee6c044eb4f531cbf72877df7edbc29fcb6cbaf99273a839ab1bfab1d',
    finite_placements_path=finite_placements_file,
    expected_placements_sha256='fd295678be5a14c93be25c94ca7966d888413c9dfbd1f473ae5d232ef0cc2a0b',
    method=arm_method,  # A='greedy', B='multistep'；仅此项不同
    journal=original_journal,
    terminal_target_ref='cx-goal',  # AINav当前source-owned共同终点ref
)
# 由Data在其新source/program own-zero/lease门内调用AINav原入口：
# ComplexSceneDriver(components, source_root=..., bundle=..., root=...,
#                    writer=..., planner=planner, journal=original_journal, guard=...)
```

公开文件同SHA小型副本在 `/mnt/yuanyue/reach-ability-research/protocols/2026-11-15/T-COMPLEX-01-source-v2-methods/`。如source改公开文件（包括文本），须新pin/新版本，不自动接受最新文件。`COMMON_METHOD_PROTOCOL.json`固定四个方法文件SHA及公共预算；不是Data新原生程序/source/资源的freeze替代。

## 本轮准确补齐的接缝

- `complex_source_adapter.py`从两个**完整SHA验证**的公共文件建同一模型；每个原public IntentBatch核完整且有序的NAV/6PUSH声明域、唯一终点ref，缺/增/重复/重排/私有ExecutionBatch/旧观察均明确拒绝。只返回原Selection/Primitive，不制造任何native option或seal。
- 不再仅核“选中的option存在”，而让搜索域与每个真实query的整个公共catalogue一致；无私有existence路线/实际base或箱pose/未来结果输入。
- 原IntentExecutionCoordinator按原PREPARE保留同一PUSH intent、fresh acquisition后再READY；准备NAV的receipt不算算法新选择、不把预测箱位置更新。实际interaction成功才推进nominal context，失败/未知不假推进或重试。
- 原共同终点仍由AINav scene driver原placements/成功NAV arrival/witness/四足12N停稳证明后调用`confirm_original_task_terminal`；预测到goal或NAV receipt不等task成功。critic不部署也不阻塞T。

## 已运行的检查，不冒物理

本地13个定向单测通过。另使用**原AINav IntentBatch/ExecutionBatch/Selection/Primitive/BehaviorOption/NativeReceipt/IntentExecutionCoordinator**及source原`nav_declarations(PUBLIC_TASK_V2)`完成87条软件断言（含源声明一致性、PREPARE不推进、完整域/旧query/私有batch拒绝）。观测与receipt全是显式SOFTWARE fixture，没有world/Actor/图像读取/真实gate/训练数据；不是87物理或独立科学样本。

三箱v2的公共名义图中两策略均有3次非强制重构选择；A名义弃权，B名义到goal后**仍等原终点证明，complete=false**。这不是A原生失败/B原生成功，17个软件interaction也不是17次有效决策。真实≥3选择、延迟机制、同条件动态可行计划、A/B与完整原片仍待Data新程序执行证明。标准uniform-cost不是Reach新算法贡献。

## 当前真实阻塞与已有G3进展

Data已真实编译v1模型/registry/robot-engine签名，原MJB缺`wm_onboard_rgbd`，在CAMERA_ABI fail closed；组件zero1/main0已耗且closed。此为source组件故障，不是方法输赢；camera修复由AINav，不能只加任意同名相机或热补旧root。v2仍需独立完整新程序资格/自己的zero/lease/直接live录像；本组没有宣称Data已采用本包或排队。

首次TRAIN-only拟合已于15:04完成一次并冻结，**不能因Data历史gate=false/fitNone重训**。实际gate/fit release在 `/mnt/yuanyue/reach-runs/G3-TRAIN-only-20261115-v1/TRAIN_GATE_AND_FIT_RELEASE.json`，SHA `670d4eb5062f903ecdadb200acbd2744647388888f8070e1066a527a2813bdd3`。原immutable采集协议不回改；之后CAL7–9仅诊断同model，VAL10–12不调参、不在此放行。T合格先占资源窗口，不等critic/100条。
