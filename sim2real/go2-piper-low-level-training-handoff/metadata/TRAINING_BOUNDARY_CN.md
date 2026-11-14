# 训练边界与验收门禁

## 冻结基线

- PUSH：`checkpoints/push/model_599.pt`，SHA-256 `aaff6614b641238ab4579c11fff8329b566904163f04d5e20cc4dab6b1ec891a`。
- CLIMB：`checkpoints/climb/model_200.pt`，SHA-256 `5cbdb0d8523a10b7f6a4870a3385afdd8289d5d87bc93408ac5c7b404ac7b548`。
- PUSH 的训练配置为 `checkpoints/push/params/`；CLIMB 的训练配置为 `checkpoints/climb/params/`。

保留原 checkpoint 不变。每项新实验必须使用新的 `experiment_name` 或 `run_name`，不得写回基线目录。

## 可以优化的低层范围

- 任务奖励、课程、随机化、初始状态与实物辨识参数；
- 动作缩放、PD 参数、延迟模型、关节速度/力矩限制和状态滤波；
- PUSH 的姿态 IK、接触准备、末端可达性和接触面约束；
- CLIMB 的接触课程、足端/机身碰撞与稳定性反馈；
- 实机只读数据回灌后的质量、质心、安装变换和执行器模型更新。

## 安全与验收约束

- 通过运动学搬运物体伪造成功；
- 降低四足落稳、指定接触、机身碰撞、姿态或终态速度门槛；
- 未经过离线、悬空和急停验证直接将新 actor 下发到实机。

## 必需记录

每个候选必须保存：源 checkpoint SHA-256、源码 Git 提交、训练 YAML、随机种子、物理参数、训练日志、两组原生报告、两组 MuJoCo 报告、导出 actor SHA-256 和明确的失败原因统计。

只有四组验收都达到每组至少 `30/32` 后，候选才可进入实机控制器的分级验证；这不是实机放行本身。