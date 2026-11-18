# 单次原canonical租约ownership观察（资源only，不是仿真/zero/物理准入）

按08:03主计划，先从软件接线转真实ownership/安全phase；不能用idle＋新ID重试FF zero。这里是明确不同的**资源协议观察问题**：在peer已terminal/原FD关闭且独立reacquire释放的真实证据、fresh无Data/J controller/collector与目标无compute、真实owner/H/PID/freeze/原helper齐后，仅调用原PerGpuLease.__enter__一次，随后原__exit__立即关闭自己的FD。失败也闭合，不循环enter、不改原源/绑定/O_RDONLY/LOCK_EX|LOCK_NB、不借旧lease/zero，不构建Model/MjData/Actor/GPU context。若peer开始新native phase，H/enter前直接停止。

original Python exception trace observer只在原__enter__代码的exception/成功return点读取有限FD/proc metadata；不替换flock或原body。失败点FD在原cleanup前读取，异常元数据失败不能覆盖原异常；成功读own FD并原样释放。最多2事件/16refs/.25s扫描，缺失或空proc记录不证明全局idle/谁持锁，不回填旧f073/L1原因。只记fstype/device/mountpoint，不记录mount source/options或argv/env/凭据。

一次资源attempt，zero0/main0/world0；输出64KiB、30wall、owned40GiB自限/provider quota UNKNOWN，完整资源程序freeze/实际CPU import prepare后才可resource run。success只说明这一次原协议实际取得并释放，**不是后继物理授权/可转移FD/own-zero**。H仅本新resource key，directory+file flock/SHA-inode CAS/atomic replace/保mode/保全部old peer。默认无enabled无动作。所有closed scope不恢复，Data维护owner不重复claim。
