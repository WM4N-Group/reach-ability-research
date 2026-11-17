# 公平 C/D 独立 NAV DEV：Data 源装配与事前协议

**未达到 M1/native 资格，未创建新 scope、AUTH、lease、own-zero 或 main。** 默认 OFF，不能改旧 PERF/E worker arm 后运行；不改原 Actor、V4 任务/成功门、guard87a 或任何 closed scope。当前代码是未执行开发候选，code-only 保管不等物理部署资格。

## 当前入口及精确源选择

- `/home/yuanyue/main/work/data-team/development/cd-dev-pair-20261117-v1/cd_entry.py` 的 `build_cd_driver` 保原完整 `method_entry.build_original_cd_method`、`live_driver.driver_class`、C 原 roles/tree/replanning、D 同技能底座与共同 B/D cost；核一份最终原 FactorJournal 同时绑定 wrapper/baseline/roles/driver。不选择、不评价、不步进、不建后端/world。
- 新 `assemble_nav_dev_sources` 选择 AINav **v3 b9a3960b…**、common prelude、actual-query boundary，以及原四个共同 driver/backbone/factor/asset。`source_selection.py` 额外核 **Reach 五模块**，不再误把旧 a33/v2/c931 当可接当前源。所有选定 bytes 在直接模块 import 前核验；这 **12 份选定源不是全部 native 导入闭包**，后者仍须全程序实际 prepare/inventory。
- 装配顺序：D-only 创建同 episode、尚不可评价的 cost → 原 method/driver/最终 FactorJournal → C/D 同一 common NAV prelude → D-only 安装原 actual-select(batch) seam。C 无 cost/treatment，D 不换 planner 类型/身份；provider 留到真实首 query 才用真实 batch 和最终 journal 构造，不猜 query ID、不重采图、不注入 private pose。
- 新函数返回只读 `NavDevSourceAssembly`，`dispatchable=false`、`DEV_acquisition_and_receipt_terminal_complete=false`，**不是 `task_loop` 可直接消费的 driver**。尚无 DEV acquisition/终态 adapter，不可把原 V4 driver.complete 冒 DEV 完成。异常不 retry/fallback；未来父 worker 仍负责 partial cleanup。
- 两入口默认关闭直接返回 None，不读 source/protocol，不调用 guard 或 import AINav/Reach。

## 明确采用的事前 DEV（不是原 V4 降级/替代）

`CD_DEV_PROTOCOL_DRAFT.json` 已采用并按 SHA 核 AINav `NAV_DEV_DECLARATION.json` 与 `INITIALIZATION_AND_RNG_ADDENDUM.json`：原物理场景不变；同 common prefix **007** 后，用原已有公共 NAV refs **008/001 两处访问，再 finish000**。不强制 VLM 树/首选顺序，不给 D 独占路线。名义矩形/半径是公开声明，不是实测 clearance 或隐藏 pose。

事前 **C→D**，每 arm 最多 own-zero1/main1、retry0；seed **2026111701**，Python/NumPy/Torch/选定 CUDA/child PYTHONHASHSEED 原初始化前应用，**具体 RNG 实现尚未装入 worker**。同 seed 不冒隐藏态精确配对或可重现 VLM；API 原采样不臆造 seed。

每 main **60 task-sim / 1200 scope-wall / 12000 issued commands**；Data 再限定 **12064 driver calls**（允许最多64额外 no-step/receipt transition，总 cap 可提前 censor，不能续 command/sim/wall/API）。每 own-zero wall180；每 main 输出≤4GiB，合计新输出≤10GiB。全部只是选定 prospective 上界，未实际预留或授权；freeze 前仍核 aux/prepare/编码/tail/RSS/GPU 与 fresh owned 容量。

原 backend caps100 calls/8192单次tokens/900000总tokens、roles90s、planner5plans 继承，不是新 API 额度；DEV 另声明每 main≤6 method queries/每 query≤8 roles，**父 worker 尚待 enforcement**。首 arm 下个真正任务响应留 served-model/per-role usage/完整树；后 arm 同实际 served model/请求配置，不用 requested alias 代 actual，不重跑旧 query 补字段。

共同公平信息/原安全/模型与预算/compute policy、全失败/UNKNOWN/censor/实际费用与直接 live 1×视频保留。名义 reference_travel_m 不塞实测秒数；全 UNKNOWN fallback 不算 M1、changed decision 不等收益、首 DEV 不作独立效果估计。

## 已有步进组件与当前最短剩余路径

`task_loop.py` 的有限 step/同 stop-state health/ScopeIO/watch、原 fast-health 每次一次、unknown 计数、最后 live capture、一次不可逆 seal 与费用边界保留。原 ResourceWatch oldest/completed 原子 pair、1s/2s、pre-issue guard 不改，不抢父 watch/lease/writer/observer/encoder 收尾。loop usage_known 只指 task 计数/时钟，不覆盖父 phase UNKNOWN；不能抢占阻塞 API/kernel，原信号/watchdog 不可省。

1. **AINav/Data 任务 adapter**：同 C/D public goal/catalogue/prefix/visited 公开信息，原 accepted NAV receipts 驱动 visit/finish terminal；当前原 V4 acquisition/terminal 不能直接用。v3 actual-query seam 已存在，不再写成没实现。
2. **Data 外层 worker**：受保护 backend 构造和完整 API/role/model 公平记账、query/role cap enforcement、初始化 RNG、partial finally、ScopeIO/FD/视频、aux/RSS/GPU/尾费、全源导入闭包与 actual prepare。
3. 新完整 freeze/登记/实际容量预留、自身必要 zero/真实 canonical lease 后，才能固定 C→D main；不借任何旧 zero/AUTH，不抢 J 进程/锁。

## 本轮定向验证与证据

13 项新 Data source-delta/装配顺序 CPU 检查＋6 项受影响原 Data 回归通过。实际读 7 AINav/5 Reach 源和2声明 SHA；factory-order 用**明确 synthetic factory/driver**，没有构造真正 verified backend/原 FactorJournal/LiveDriver，不冒真正 API/query/机器人或优化结果。未重刷旧17/23全套、AINav7/63/14、Reach套件，未读 key/重下环境。

证据：`/home/yuanyue/main/work/data-team/manifests/cd-actual-query-assembly-20261117-v1/`；历史首装配17项和task-loop23项保原独立证据，不双计。

source-only prepare（始终 dispatchable=false，不 import 原方法/后端）：
`python3 -B /home/yuanyue/main/work/data-team/development/cd-dev-pair-20261117-v1/prepare_pair.py /home/yuanyue/main/work/data-team/development/cd-dev-pair-20261117-v1/CD_DEV_PROTOCOL_DRAFT.json`

当前 protocol 指本机源路径，不能当远端 worker 配置运行。
