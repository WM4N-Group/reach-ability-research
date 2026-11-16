# PERF-01 v4：只修实际PIL lazy-PNG与计时可观测性

v3真实zero1PASS/main1(448步/2.240sim)失败closed，不能续跑；失败原片/费用保留。准确trace为首次原publisher PNG保存Image.save→preinit→BmpImagePlugin，被87a严格audit拒绝。zero此前写资格PNG隐式做preinit，而main只有raw，因此自身zero没覆盖此差异。

新prepare在相同CPU依赖导入后显式调用原Image.preinit，两phase一致且在seal前；不改PIL/87a/publisher源码，不捕获后恢复，不以dummy PNG冒真实相机。仅一项CPU-only小数组PNG/NPY真实保存对严格import/exec/function安装事件零触发，源码身份逐SHA保留，非native资格。

只增加bootstrap inventory/seal主线程wall、失败末边界wall可观测性；完整2000步计时终点在量化/close之前，原run入口prepare之前起点不变。不改命令/初态/Actor/dt/动态门/lease/预算/RX策略/原最终camera，明确新版本一次own-zero≤1/main≤1。此有据修正后若再失败先做独立原件分析，不在本回合继续无界native版本链。

沿用v3真实包路径/pth/两torch synthetic missing槽策略；原PerGpuLease保历史binding，当前新H/新AUTH/OWNER仍真实01a1e4e1。主计划用本次实际fresh SHA，不热改v2/v3已冻结元数据。
