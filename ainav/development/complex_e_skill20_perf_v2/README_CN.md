# E-SKILL20 PERF v2：仅任务调度等价提速候选

继承 eeabaac65ba8d32db336c7b449e8d85e59147957 的 E-SKILL20 环境与执行接口。
这不是原0.60m任务成功；不是旧 E59 收臂后 placement 丢失的修复。
场景、规则、原Actor、200Hz、12N/NN/STOW/FF/QP/FIFO/4s/stop 均不改。

## 唯一执行差异
`parallel_alias_guard.py` 将约1300个逐路径Future换为最多32个连续批次，
仍8线程、每个literal出现都用原Path.resolve现读两次（不去重、不缓存前缀/跨tick），
仍前后原callback/world/owner检查、rebind/异常fail-closed与close语义。
增加resolve及原检查累计计时；后者含Data owner_guard，不能与其相加。
不是libc替代，也不采用无收益的并行size扫描候选。

## 使用
Data在新程序fresh进程中将此目录放到sys.path最前。
compile_static_asset → construct_cold_components → e_entry.build_E_driver，原default-off保持。
必须新程序/lease/own-zero；旧main与旧closed根不恢复。不要求另跑无关组件或整链成功。
下一必要own-zero对实际loaded inventory读累计计时，main原400步进度可追加
`type(driver)._native_guards.engine.metrics`副本，明确计时重叠。
不得改当前Data源/环境、降低门或借测吞吐派第二world。

## 证据边界
本机27项guard、16项E20与8项E入口CPU软件通过，非native资格。
初步CPU依赖库存微测：双全读0.387→0.288s（1.34x），不是端到端仿真加速。
完整CPU配对与远端验证随consumer交付；原E59失败/全费/原片保持。
