# Data worker有界软件/文件系统诊断（非物理实验）

时间：2026-11-16T06:56:35.384629+08:00。计划SHA `be3aa7e587e5aa990375d1085dde6affc497861c1d45ab01862edc2793501845` 未变。

- 实际closed-v2 worker的文件访问语句分段、只读元数据取样，每项3次；没有导入/执行worker、没有伪造active authority、没有lease/world/Actor/WM/forward/API。旧H、AUTH、worker/protocol、result/ledger/journal在诊断前后逐SHA相同；本机H镜像一致，Data native worker0，四canonical原inode的/proc/locks无持有记录（不是新lease）。
- H为104,312bytes；H+AUTH两次JSON读取/解析+AUTH SHA中位 **1.934ms**；旧输出25文件的原rglob/is_file/stat式扫描 **18.751ms**；inode检查约 **0.020ms**。不能据此删除/稀释Data owner、预算或锁检查。
- 原PerGpuLease的两个nvidia-smi查询各中位 **106.074/68.027ms**（三次明显波动）；原代码在≥1墙钟秒/force时查询，不是每条200Hz命令都查，不能直接乘978当成本。Torch/CUDA计数调用未测。
- 新独立诊断目录3×4KiB的flush/fsync中位 **2.161ms**，不是旧journal/真实writer的flush成本；旧流未写、未回放。
- 总wall **14.463338080s**（含du及读核）、峰RSS **23629824bytes**，独立probe12,288bytes，CPU诊断cap90s/512MiB；Data owned **26134756352bytes/40GiB**，provider quota未知。

## 结论与接续

与AINav06:46独立CPU metadata观测的全模块guard1.244s/Path.resolve1.236s相比，这次Data实际文件访问切片小得多。**这是缩小候选成本范围，不是原v2逐tick完整profile/全wall归因，更不是已修复、native提速或方法收益。** 未重测AINav1325模块、未采用其无稳定改善的parent-sharing负候选、未迁环境、未作cross-tick cache/module过滤或放松guard。

具体候选源侧仍由AINav维护；Data先保持全部scope closed，不因39源/新ID/更高wall盲重跑。必须有具体保安全语义的程序或运行条件改进后，再对新准确完整程序冻结/必要资格；不重用旧once。五组main0、WM真实forward0、完整任务/HD影片资格未建立；J2a尚无采集/fit/GPU派发。

原结果与summary勘误均沿原parent/assessment child，未改旧scope、原源、预算、Actor、12N/4s/FF/effort/QP/FIFO/CLIMB stop。

原始小profile：`/home/yuanyue/main/work/data-team/manifests/V4-worker-software-io-diagnostic-46308-20261116-v1/Data-actual-worker-metadata-slice-profile.json`；解释：`/home/yuanyue/main/work/data-team/manifests/V4-worker-software-io-diagnostic-46308-20261116-v1/Data-software-io-assessment.json`。
