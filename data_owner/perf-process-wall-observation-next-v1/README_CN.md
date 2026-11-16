# 新程序可选：父进程单调wall观测候选（默认关闭）

**不是新native资格、不是性能优化收益、不是v7重跑授权。** 针对v7已测量的准确缺口：worker wall在最后result/ledger/accounting写入前采样；launcher总wall混入fresh preflight，UTC controller→result跨度也不是独占报告成本。本候选只改下一新程序的父PIPE捕获器，保留原捕获/预算/kill/wait/错误路径。

## 使用与界限

- `ControlledProcess`原接口，仍必须`enabled=True`；新程序须把本源及原`scoped_io.py`加入完整freeze，正确相邻import路径，然后在新launcher使用。未接入任何worker/launcher，不改v7 frozen源/旧AUTH/H/原锁，不能直接启动物理。
- `finish()`成功/失败receipt新增`wall_observation`：同一父进程monotonic的capture entry、spawn begin/returned、finish entry、observed reap、drain join和receipt采样。给出preflight分离的parent-capture区间，覆盖直属child退出前的最终文件写入返回和PIPE收尾。
- **observed reap不等精确exit，spawn begin不等精确exec start；不是独占CPU/物理/报告成本。** 没有reap时相关项为None，不能补0/成功。receipt采样后的父报告序列化/写入、文件持久化、后代/内核阻塞都不冒已覆盖；原有限wait/join和不保证全进程树的边界保持。
- 不发owner stamp、不改ResourceWatch/1s-2s、不插入控制热循环或新增probe。原v7的wall/倍率/UNKNOWN不回填，canonical60s缺口也未解除。
- 只新增9项定向CPU测试：字节/末次子进程输出、非零/timeout/预算失败receipt、默认关闭、missing-reap None、重复finish拒绝、原捕获AST（剥离诊断赋值后完全相同）、与原捕获器相同stdout/stderr/原receipt。不是Actor/GPU/native测试或速度证明。

定向运行：`python3 -B /home/yuanyue/main/work/data-team/development/perf-process-wall-observation-next-v1/test_wall_observation.py`。实际日志与原freeze基线SHA：`/home/yuanyue/main/work/data-team/manifests/perf-process-wall-observation-20261117-v1/`。首次测试fixture的text reserve不足已保留；只调整测试fixture的max_open/text_buffer，未修改原ScopeIO。

下一真正工作仍是AINav合格新E/已登记数据用途；没有新资格源不盲派，本诊断本身不构成追加native理由。
