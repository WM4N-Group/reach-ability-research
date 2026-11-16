# E20 ARRIVAL v3：单个40mm提前进入原brake的DEV假设

## 为什么不是换ID盲试
旧E59在26.375sim已实际提交全零requested-velocity history，26.570sim到达时
箱体仍有0.366m/s的X速度，60ms后dock越过原10mm门。Data完整FIFO/PD cold通过。
因此不是“漏发零速度”或“关闭FIFO检查就解决”，也不是后面的H收臂路径导致首次失格。

本版只试一个新假设：在ground/+X/原box prototype的有向dock gap进入(0,40mm]、
Y/高度仍在原域且箱体还沿+X运动时，提前进入**同一个原始安全筛查brake**。
保留原task_geometry_pass原值，不把这个触发写成placement合格或成功。
40mm是从已暴露旧DEV选的单点工程假设，不是动力学认证/停止距离预测或新优化器。
不扫margin、不按失败再追胜补样本。旧状态上predicate会在26.470触发只是离线条件计算，
**不能用旧后续轨迹预测新控制下会停在哪里/成功**。

## 不改的东西
原283/Actor、原public goal与native drive goal、body reference、原NN clock/0.5s、
原安全FIFO/FF/QP/12N与原保护stow/4s/stop、最终XY20mm/dock10mm门均不改。
新class仅重载update的原brake进入时点，_begin/_confirmation/_verify_complete/
next_command/after_step/complete/results全部继承原对象，无伪测量/成功label。
若提前停不足、NN不确认、最终placement不满足或任何原guard拒绝，仍真实失败，不补成功。
原source/closed scope不改，不接管Data源/进程/H、不新建另一world。

## 实际接线
Data fresh进程将本目录置sys.path最前，仍compile_static_asset→construct_cold_components→
e_entry.build_E_driver。新task_factory在选定PUSH原session构造后、任何PUSH命令/admission前，
只对原prepare/未brake/未confirmed machine接新subclass，原native/services/session保持同对象。
非PUSH不接；live/重复替换拒绝。原destination/CLIMB20/NAV和最终三placement证明全部保持。
场景仍08a260a4的E20任务；不是原0.60m任务成功，也未证明新20cm链或动态修复。

## 单次下一程序
候选code不是运行许可/已派发。Data可在新完整freeze、fresh lease、原必需own-zero与原有限资源门后，
只派新scope main≤1（no retry），完整direct-live原片从task0保留。无需额外经济审批、WM/VLM、
另一无关component或“先全链成功”的循环前置。原受影响功能/安全门不放宽。
同时采用同source中的原已验证batch32 guard与e_resource_perf_v1资源helper，记录实际loaded分项。
如果Data发现具体source/安全调用硬阻塞则准确拒绝，不以本README推native资格。

## 软件证据边界
22新增状态机/构造边界fixtures＋16 E20＋8 E入口本机通过；全部明确fake runtime/receipts，
无新Runtime/MjData/Actor/模型/physics/API调用。两个测试fixture错误（误读原literal、缺inner.sha）
已保留并修正fixture，未改原成功expected或控制源遮掩失败。原生资格/成功/视频仍未取得。
