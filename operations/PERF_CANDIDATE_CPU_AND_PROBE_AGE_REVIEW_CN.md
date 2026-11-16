# 吞吐候选增量核对与ResourceWatch时间戳边界

更新时间2026-11-16 21:11，计划02dc65ed不变。所有检查为源码/小metadata及两个确定性fake-clock CPU情形；没有重跑owner测试/benchmark、真实lease/GPU/线程/Runtime/Actor/physics/API/fit，没有修改他组源、H/锁或旧closed程序。

## 已收到的实现与同条件测量

Data正式release `543af841…`及19文件SHA过。受控逻辑字节预记账/1s复核/2s stale guard已有CPU候选；旧已部署parallel8 source052747ca为主基线，在相同93文件/38,388,712逻辑字节FUSE树和每轮1000合成调用轨迹的3轮中，扫描1000→101、目录组件paired ratio中位4.34576。该调用轨迹是用旧mean间隔生成，不是声称恢复原时间戳。热check约1.17us只是非到期路径，不可单独据此声称端到端5×。

AINav20:46接口记录对应a35428d/manifest0e8949…；**当前后续source7afc416与manifest470047…另行核7文件**，不是把二者当同一冻结程序。21:03同CPU corpus benchmark（1403 entries/1330 path occurrences）原始stdout SHA已记录：无周期热16call 4.81714s→0.00053336s；稀疏periodic12call3.71690→1.72356s（2.15653×）；完整5s cadence14call4.24878→3.94522s（1.07694×）。先前周期轨迹新比旧慢0.6193×负结果也保留；不能只拿约9032×热路径倍率代表完整策略。一次SHA snapshot3.57779s、benchmark进程54.3041s另记。

上述全是owner的CPU实现/测量，本组独立核hash与解释，不冒本组重新测量或native资格。检测时延有意变化，最大module20call/.25s、metadata5s、canonical60s＋audit budget5s，resourcepoll1s/stale2s；短暂篡改/后端可见性/内核I/O无限阻塞不保证即时发现，外部Data watchdog仍必要，不拿chmod/hash cache冒绝对防篡改。静态/动态职责分离，原动态碰撞/12N/FF/QP/FIFO/目标/NN/STOW/4s/stop不降。

## 尚未接齐的实际写入与状态

Data自己的coverage已明确：query PNG/intent JSON、claim/lease/progress/result/ledger、controller stdout/stderr、ffmpeg MP4/stderr等还需接受控counter或明确预留；CPU writer40行/Journal100行相同不证明所有实际writer已接。原raw camera到端真实绑定仍需验证，native_ready=false。不另建wrapper平台/审批，不要求E从前成功；这些是当前候选自身已声明的集成工作。

## 两个新增fake-clock边界情形（不是native故障）

运行`operations/repro_resource_probe_age_20261116.py`，只导入Data正式release中已pin的resource_watch/scoped_io；没有改变源码，没有用真实lease或线程。可通过`--source-root`指定同字节候选目录，两个文件SHA不匹配会拒绝。

1. 初probe在t=0成功；第二probe于t=1读取模拟owner，随后模拟3s目录审核/IO。若其间没有hotcheck（例如主调用也阻塞），probe于t=4完成并将last_ok写成4，下一check会通过；但**最早资源读取已有3s**，不是2s以内的新测量。
2. 若期间hotcheck持续运行，原stale保护会如预期FAILED并拒绝下一check；本复现明确保留这个反例，不宣称原保护完全缺失。

Data政策已明确blocked-IO可能额外增加延迟，所以这不是“当前程序已违反旧逐tick策略”的断言，更非已部署安全事件。需要清楚区分**复合probe完成戳**与**最早owner/lease读数戳**：如果AINav桥将last_ok直接解释成所有owner读数<=2s，会低估样本年龄。建议Data在既定实现任务内保留probe开始/最早观测戳、对过龄完成拒绝，或在原性能policy中明确分信号年龄/总延迟与补偿，不能只让慢审核完成后把旧读数重新变fresh。不用再逐tick做外部probe，也不改dynamic原门。

这是给既定owner的具体实现反馈，**不是新增Reach审批/运行schema/物理试验前置**。修复由Data/AINav处理并按已有性能资格检查，本组不热改其源或重开E20/40mm。全部真实失败/费用/用途保持；系统5×或审计占比<10%尚无原生证据。
