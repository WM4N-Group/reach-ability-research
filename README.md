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

## 当前研究状态（2026-11-15，覆盖下方历史快照）

新端46308三source五DEV已closed：full-4左右PASS、full-2左PASS/右PUSH卸载异常未达CLIMB、full-1左PASS。完整分母5、first-PREPARE4，原失败/未知费用不丢。只证明原AINav工程和有限公开信息，非Reach优化收益/论文贡献。公开增量测量原件留远端，小摘要见operations/G2_FULL1_AND_FINITE_COHORT_20261115.json。

**当前新用途有限协议：** protocols/2026-11-15/G2-new-purpose-finite-cohort-v1/；固定full4 TRAIN6/full1 CAL3/full2 VAL3、最多12新main，whole-scene分组、只未来新数据。TRAIN类/状态不足即No-Go，不自动扩批/旧DEV改fit。每split仅一scene且DEV-informed，不是未曝光TEST、统计功效或G5 holdout；不能通过排除原full2right宣告完整族已合格。Data唯一物理owner，新TRAIN01/02已PASS closed并真实提取两条因果48槽/原READY与CLIMB监督行；仅一个TRAIN scene/2prefix，未齐6不fit或提前判gate。03 plus-left在13:39 H快照已派唯一main，04—06未派、CAL/VAL仍阻。真实fit0；无需再问已授权小高层训练用途/经济许可。

TRAIN先fit/heldout后只评价的时序循环已修复，见operations/G3_TRAIN_FIRST_FROZEN_EVALUATION_CN.md；下一真实TRAIN闭合就G3单次高层critic和常量/均值基线或有限否证，接续新协议G4三策略/G5多决策/G6，而非止于本gate。原Actor/WM/DINO/真机暂停，12N/4s/identity/immutable/guard/support/QP/FIFO/CLIMB stop不变。完整接续见docs/AGENT_HANDOFF_CN.md顶部。

### 23:45计划接续（覆盖旧机器恢复前置）

最新用户明确停追旧46174，不等待旧端CAS/锁/结果恢复。旧left的zero1/main1已消耗、终态UNKNOWN和全部已知/未知花费保留；新46308按独立同设备cohort完整left/right各一次，不重开旧root或与旧left拼配。新端已有Data的Python3.11.16环境候选及逐148成员同pin的SDK/四Actor，不再因本组此前另一个3.11.13 probe要求全栈重装。仍须Data新authority/设备程序绑定与实际own-zero。见 `protocols/2026-11-14/LONG_TERM_PLAN_2345_CN.md` 和 `native-prefix/NEW_HOST_G1_CONTINUATION_CN.md`。
