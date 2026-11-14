# REV021｜REV017–020 独立增量核验的小型本地归档

这是研究工具、CPU反例与历史回执的**归档**，不是控制器、部署包、可直接RUN的目录或新授权。预算变更仍待用户决定。本次不启动SDK/环境/物理，不重跑历史成功审计、旧CPU套件或原checker；不从310sim续接，不把旧raw补写成功，不push。

## 保存的独立结论

| 原审核 | 小型原件及边界 |
|---|---|
| REV017 | r2g **拒绝**：UNKNOWN时通知I/O可使owner等待抛出；复合shell可掩盖ps/GPU采集失败。CPU反例是合成数据，不是新物理。r2g未被本归档修复/重新授权。 |
| REV018 / r2 | 真实r2 SDK配置绑定通过，但source因owned-PGID文本豁免缺陷被拒绝；保留此层次，不能把SDK通过写成source接受。 |
| REV018 / 最终r3 | 仅quiet顺序/collector身份修复后，原PGID反例闭合；真实**新r3** SDK原件满足原同digest门，最终`ACCEPTED_FOR_BASELINE_RUN`。不是r2继承重标，原gate未放宽。源码接受仍不是main RUN。 |
| REV019 | 此后经main授权的唯一正式baseline，墙时2336.441560s失败闭合，子timeout rc124；**1次尝试/0成功/0retry，保留分母**。实际推进至保存step15500/310sim/climb_exit，raw缺失≠0tick，且310不是精确终态。stop附近断言的因果未独证。 |
| REV020 | 当前95事件与v13首95的解析字段/类型/顺序/sim时间一致，310点7共同字段一致；仅记录前缀一致，不是连续全状态或未保存尾段/NAV成功。转向运行时预算/吞吐问题，不把未证接线/物性当根因；未定位具体瓶颈，预算失败不剔除。 |

旧8101/4kg/.4/model199+.50只属独立开发baseline；原cfg.push_distance=.60与实际dx>=.50事件共存，未改旧控制。当前Goal、数据/失败身份和原成功/安全门保持；不以历史成功给本次补成功，也不否定旧成功。

## 文件与原件身份

- `receipts/`：7份小型**原字节**独立接受/拒绝/终态回执及真实r2/r3 SDK envelope。
- `cpu_evidence/`：4份小型原CPU/离线结果；阶段结果里“待SDK”是当时状态，由最终receipt及真实SDK原件更新，不篡改旧阶段结果。
- `canonical_checkers/`：6份已执行独立checker的原字节快照（拒绝反例、PGID窄修复、SDK原件核验、终态计分、前缀比较）。**禁止直接执行/import这些快照**：它们保留历史硬编码路径、输出目录及当时活进程/锁表假设，移到归档后不具备原布局；某些顶层代码会写所在目录。它们用于审阅/复用已核逻辑，未来若移植须显式绑定输入/外部输出并单独验证。
- `offline_checks.py`：薄的只读、stdout输出入口；只复用已有JSON/AST比较，无runner模块import/SSH/SDK/进程创建。外部输入必须显式指定并先匹配固定原SHA；缺件/错SHA报错，不找替身、不下载、不生成原件。
- `canonical_evidence_index.json`：33项canonical绝对路径/原SHA/大小/归档映射。17项byte-exact小文件已复制；原日志、报告、source/authority等只引用。大v13报告SHA沿用REV020独立核验，本REV021不重读大报告做旧审计。
- `archive_sha256.json`：本子树其余文件的SHA（不含自身，避免循环）。`workspace_intake.json`及根`evidence/2026-10-19/rev021-stage2-verification-local-milestone.json`记录归仓前分支/clean状态与验证范围。

历史receipt内的绝对路径和嵌套`evidence_sha256`仍指**canonical外部原件**，不是相对本归档的承诺。原完整日志/video/report、progress/raw、模型权重、环境/缓存、部署及SDK源码均未vendoring。`verify-archive`只验证本地已保存副本/索引，不宣称所有外部数据可用、SDK健康或RUN-ready。

## 只读使用

归档自检（本次只执行此模式，不调用旧测试）：

```bash
python3 -B research/stage2_incremental_verification_20261019/offline_checks.py verify-archive
```

未来显式授权的**离线**复算用法（本次未执行，不能当迁移后已跑结果）：

```bash
python3 -B research/stage2_incremental_verification_20261019/offline_checks.py compare-prefix \
  --progress /explicit/path/to/original/progress.json \
  --old-report /explicit/path/to/v13/report.json

python3 -B research/stage2_incremental_verification_20261019/offline_checks.py compare-pgid \
  --r2-runner /explicit/path/to/frozen/r2/run_source.py \
  --r3-runner /explicit/path/to/frozen/r3/run_source.py
```

第二模式先校验已审r2/r3 runner SHA，然后只编译固定四个纯函数AST，用有界合成快照/回调检查PGID反例；不import外部模块，不实际进程/锁操作。它不是运行外壳或新的物理验收。原REV017完整反例和其它checker的历史执行结果见小型CPU原件；没有把这次归档包装成旧套件新一轮通过。

本次验证仅：归档文件/SHA一致性、Python源码内存语法compile、显式staging清单/体积/禁入物检查。薄入口的外部compare模式未重新执行，不能声称所有迁移后功能都重新验证。未新增第六份docs文档；只在既有RESULTS记录本里程碑。
