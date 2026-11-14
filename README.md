# Reachability research — code custody and remote execution

冻结现有 Go2/Piper 技能下的后继感知准备方案研究。**原 AINav 成功、工程接线、标准枚举或单条 DEV 录像，不自动构成本项目方法贡献。**

## 代码与运行分工（2026-11-14 用户更新）

| 位置 | 用途 |
|---|---|
| GitHub `WM4N-Group/reach-ability-research` | 持久代码版本；不存数据集、录像、环境、模型权重或密码 |
| 本地 `/home/yuanyue/reach-ability-research` | 精简代码副本与小型摘要；不批量拉取远端产物 |
| 远端 `root@180.97.68.228:46308` | 当前仿真/训练计算入口；代码 `/mnt/yuanyue/reach-ability-research` |
| 远端 `/mnt/yuanyue/reach-runs`、`/mnt/yuanyue/reach-assets` | 分别存运行产物、权重/场景资产/环境清单；不提交 Git |

密码只在连接授权中使用，不能写入 Git、配置、脚本或日志。使用当前已可用的 SSH key 连接；不复制本地私钥到服务器。

服务器是可更换的计算节点，**不是代码唯一副本**。每次运行记录代码 commit、未提交 patch（若有）、依赖/资产 SHA、GPU UUID、场景、协议和输出路径。换机先部署同 commit/核资产，再由 Data 建立新硬件资源 binding/lease、程序 freeze 和 own-zero，不能复用旧机器 UUID、锁 inode 或执行许可。共享存储的物理持久性/配额以服务商为准，不把挂载显示的容量当账号配额。

## 本次初始代码快照

- 原工程 HEAD `4c998be60b2264999c5c033a2d011843bfd202a5`，分支 `feature/go2-piper-reachability-p0`。
- 这不是原 HEAD 的 clean checkout：保存了当前工作树里的研究源码，包含此前 untracked 实现；源工作区与原 Git index/branch/remote 未清理或替换。
- `provenance/CODE_SNAPSHOT.json` 列出复制文件的逐 SHA、来源和排除项，**不是 runtime freeze**。
- `owner_snapshot/native-prefix-20261114/` 是 Data-owned 两条件 pilot 的代码副本，只供代码保管/迁移；其中旧 `/mnt/miaojigui`、GPU UUID、锁和 authority pin 是历史机器限定，**不能在新机直接运行或 sed 后冒原 freeze**。Data 维护新运行版本。
- 原代码许可证与 attribution 保留。大型 meshes/USD/PT/ONNX/NPZ、历史原始 evidence、环境、日志和视频未复制进此代码仓库。依赖这些材料的旧实验/测试不会因代码存在就自动可运行。

## 可独立运行的软件检查

在仓库根目录（纯 stdlib，不构造 Actor/Runtime/物理世界）：

```bash
python3 -m unittest \
  research.task_conditioned_reachability.execution_preparation.test_successor_critic \
  research.task_conditioned_reachability.execution_preparation.test_public_prediction_features
```

这是软件/内存 fixture 检查，不是训练样本、仿真实测或新研究成绩。历史所有 closed 根继续 closed。

## 当前研究状态

三分支 Stage-B 已 closed：2 PASS、1 原 CLIMB stop_deadline；raw 排序反转未达事前双100ms material 条件。测量与代表点对照已经闭合，保留 mixed/负结论，不继续扫阈值追全胜。

下一物理问题是原生 NAV left/right 前驱是否在相同 PUSH/stow 后留下公开可辨的首次 CLIMB PREPARE 条件。最多两条件各一次，固定 original 准备；只检验 condition source，不是三候选优化收益或24-main训练准入。Data 唯一物理 owner；新机器资源门、exact3 原生回执、完整 freeze/own-zero/原12N/4s/stop/guard/QP/FIFO不放宽。

高层小型后继 critic 仅获授权使用**未来新预登记数据**训练与离线评价。旧 audit/隔离 GT 不转 fit，当前合规新数据仍0；没有真实训练中的模型。Actor/WM/DINO/真机不因迁移自动开放。

完整历史/接续见 `docs/AGENT_HANDOFF_CN.md`。原始工程 README/AGENTS 保存在 `provenance/`，其中旧机器/在途快照不能覆盖本文件的新存储与机器决定。
