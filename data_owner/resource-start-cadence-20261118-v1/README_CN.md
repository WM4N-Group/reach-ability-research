# 未资格化候选：资源producer以实际start计1s周期

唯一差分是`ResourceWatch.start`的调度：从每次成功probe实际oldest/start＋1s安排下一次，而非completed＋1s。晚唤醒后以实际start重锚，不排积压任务；probe串行，单次仍只调用一个原lease/authority/UUID/GPU/disk/reconcile composite。单次>2s、未知读失败、旧观测过龄、foreign token/PID、seal/close、失败闩锁均沿原代码；不借completion作fresh stamp，不降低原2s上界或改成更短poll，不加额外owner probe。

实测来源：原PUSH L0 program947a4b25…已zero1 PASS/main1资源截断closed。main在task840/4.2sim、原startup尚未结束/PUSH Actor0时，被真实oldest过龄门挡停。最后公布pair跨度.424352388s，下一attempt在前completed后1.000107289s才start，完成耗时.754078956s；从旧oldest到下一complete共2.178538633s。原源码确为probe完成后再wait(1)。这定位了**completion间隔额外叠加前次probe耗时**，不证明本候选在原硬件必过，也不证明.725307955s held composite内部唯一叶因/GIL/J/EGL；旧D3的2.095707215s单次producer仍会失败，不回填旧因果。

6项新软件检查：真实duration作明确software-clock反例、晚唤醒无catchup、慢但<2s串行、oldest过龄仍闩锁、>2s及未知probe仍拒绝、除start外全AST一致。最初本机测试仅float直接相等断言失配，改为浮点容差，不改生产逻辑；初失败日志保留。

这是独立future源码，不修改已冻结policy或closed L0；没有新AUTH/完整freeze/actual complete prepare/zero/main，不是资源问题已修或技能成功。下一有明确新问题/合法场景的完整候选才可选用并重新取得完整资格；绝不借旧zero或更名重试旧PUSH。原PUSH结论、原43帧1×视频、分母/费用见Data STATUS与该scope原件。
