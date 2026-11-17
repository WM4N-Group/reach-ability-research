# 后继source-only纠错：在CPU prepare/原helper门之前显式预载FF构造器

新PREPARED L0程序b7f09967…/实际code77e1c631…完整1808文件freeze和actual CPU prepare通过，但实际自身zero PID346605在`worker.run`原helper文件门读`sys.modules['registered_arm_ff']`时**KeyError**，child exit1；**zero1失败/main0/closed/no retry**。文件已存在且pin正确，并非缺文件/需下载：模块只在startup owner构造期局部import，而原helper门在构造之前。actual CPU prepare没有覆盖此presence/order承接。

这是Data软件接线故障，不是FF物理假设失败/Actor失败。异常在ConstructionReceipt/ScopeIO/watch/lease/Runtime/world/Actor构造之前；无原生result、无camera或task时钟/usage实测，**None/UNKNOWN不能回填0**。launcher wall样本13.373119413s、最终controlled logical37714B；native wall/RSS/GPU峰/aux/最终accounting仍UNKNOWN。source控制流可证明未到world，不等取得零值测量。

`worker_preload_fix.py`只对已核exact失败worker字节产生两处可逆**未来私有source文本**插入：模块顶端显式import纯stdlib的`registered_arm_ff`；CPU prepare增加其presence/exact frozen-path SHA检验。原run helper枚举和检查不删除/跳过，FF物理输入、原门、预算/任务语义均不改。**不会写入/执行/恢复已closed worker、生成AUTH/新scope/intent或重用zero。** 后继还须另有明确新完整程序身份/冻结/actual prepare/自身zero，不能直接将该文本当新程序。

新3项定点CPU最终过：用原helper门AST在显式fake模块表重现同KeyError，然后同门在预载后通过；新prepare pin断言拒绝源漂移/未知；精确逆变换/disabled/无native/frozen写。真实source-only构造器import不触发NumPy/Actor/GPU。未运行原worker.run/prepare、旧完整套件或重开任何物理scope。

两次软件测试差错原件保留：attempt1测试harness片段strip未dedent触发IndentationError；attempt2调用参数抄错远端路径FileNotFoundError；从真实protocol取路径后attempt3 3/3。均不是native重试、未掩盖失败。实际物理问题仍未测；此源码纠错也不是修复原joint3已验证。
