# 新机器部署与持久代码

## 2026-11-14 已核目标

SSH：`ssh -p 46308 root@180.97.68.228`（凭据不在仓库）。

- hostname: `is-ddj7fmngzagfchvv-devmachine-0`
- GPU0 4090 UUID: `GPU-297c1146-bcec-a8ee-8437-d9603392a2e1`
- GPU1 4090 UUID: `GPU-6d66aa68-9a3f-fdcf-89b7-f98d4106fa39`
- 23:06 两卡均 total24564MiB/free24080MiB；仅当时快照，非持有 lease 或未来容量保证。
- `/mnt/yuanyue` 挂载可用，平台显示容量不代表个人 quota。
- 既有 `/mnt/yuanyue/ainav-native-env-20261112-v2/bin/python` 是 Python3.11.13，metadata 中 NumPy1.26.4/torch2.7.0+cu128/MuJoCo3.3.2/scipy1.13.1/osqp1.1.3/imageio2.37.0/Pillow11.3.0。
- 当前旧 worker 资格要求 Python3.11.16 和另一绝对 prefix/硬件 binding，故**依赖版本多数相同仍不能直接签旧 worker native 资格**。不为通过检查降低/删除 pin。

## 目录职责

- `/mnt/yuanyue/reach-ability-research`：Git 代码 checkout。
- `/mnt/yuanyue/reach-runs`：仅新运行的产物/ledger/metadata，不当 Git 仓库。
- `/mnt/yuanyue/reach-assets`：必要 SDK/机器人 mesh/冻结 actor/资产 pin 清单，不在 Git。
- 已存在的他组环境/资产只读观测，不修改、不覆盖；不拷贝或修改他组 authority/锁/closed roots。

## 无需向服务器复制 GitHub 私钥的部署方式

本地 checkout 保存云端 remote。可在本地构造只含代码 commit 的 `git bundle`，通过 SSH/SCP 传到新服务器后 clone；核 commit 与 tree 后把远端 origin 设为 GitHub 仓库。若服务器不能访问 private GitHub，后续仍可本地 fetch + bundle 部署，无需上传个人私钥或打开 agent forwarding。

换服务器只部署代码与必要资产，不能搬旧执行根当新任务；由 Data 迁移其 owned 运行包/资源 binding，在新程序 freeze/真实 own-zero/lease后执行已登记两条件。不能本聊天另开第二执行 owner，不能让环境 probe 自动开物理世界。

## 本次验证边界

部署后只运行独立软件检查与依赖/设备可见性 probe；不构造原 Runtime、Actor 或物理世界，不启动真实数据训练，不重开旧 root。后续真实仿真和未来合规训练均在本目标服务器；本地仅维护代码与小报告。

不可将 SSH 可连、CUDA 可见、软件测试通过，写成“仿真实验已跑/critic正在训练”。

## 已完成部署核验

代码e716e6d在该节点27项软件检查通过，CUDA available/2 devices，MuJoCo3.3.2导入成功；无tensor/Actor/MjModel/MjData/Runtime/physics构造。首轮绝对路径导致的11项软件错误保留后，已仅改test loader并复测。MIGRATION_20261114.json记录小型摘要，不含原数据/权重/凭据；这不是native运行资格或真实模型训练。
