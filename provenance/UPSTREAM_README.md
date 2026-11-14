# GO2-PIPER Reachability

本分支承接 GO2-PIPER 技能资产，研究接触前位姿选择与 NAV→PUSH 可执行可达性。目标是提出少量可计算公式，并用配对实验检验任务效率与安全性。底层策略训练和实机部署由 sim2real 小组推进；GO2-ARX5 世界模型属于另一机器人方向。

## Start Here

- [文档目录](docs/README.md)
- [目标与验收](docs/PROJECT_PLAN_CN.md)
- [公式方案](docs/IDEA_PAPER_CN.md)
- [关键结果](docs/RESULTS_CN.md)
- [当前交接](docs/AGENT_HANDOFF_CN.md)

## Evidence Snapshot

- NAV: historical MuJoCo random-goal validation `98/100`; current hardware validation is outside this branch.
- PUSH: current `aa/model199` has Isaac reset-state single-skill results `30/32` and `32/32`; continuous NAV handoff and MuJoCo contact validation are not approved.
- CLIMB: historical Isaac validation exists; current release status belongs to the sim2real handoff and is not established by this branch.

The current policies are not approved for direct hardware contact tasks.

## Key Directories

```text
source/       Isaac Lab task and training code
mujoco/       MuJoCo runtime, models, checks, and diagnostics
scripts/      Training, evaluation, export, and provenance tools
sim2real/     Deployment and continued-training handoff packages
docs/         Five maintained research and handoff documents
evidence/     Structured experiment protocols and audit summaries
```

Policy artifacts and videos are stored outside Git under `../artifacts/go2-piper/`.
