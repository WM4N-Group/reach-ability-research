# 原CLIMB实际SDK parent接线源码：真实类导入prepare，不是完整原生资格

复用原`switch/plugins.py` Plugin（c9e87fbb…）隔离同名bridge/stop，加载实际SDK ClimbBridge/StopController类并恢复ambient模块表；原bridge/load_contract核既有Actor SHA8285bb4e…，不mock实际类/模块表，不下载或加载Actor、不构建Model/MjData/Stop/world。实际私有CPU source-import prepare过，CUDA未初始化；**不是完整program actual prepare或zero**。

native源码已接原build_model→ClimbBridge.__init__→原torch.jit.load/eval→原StopController与上一owner（1c0504aa…）/周期（e9098862…）。它在任何真实constructor前强制另一个新CLIMB完整program的active H/当前owner/PID/完整freeze/Auth/真正complete-prepare receipt/自身zero规则，以及原d44b3176 PerGpuLease当前PID的两已持FD/正确GPU授权和UUID/EGL映射；不enter/check/借用/释放lease。source receipt和旧PUSH/closed scope不能激活native构造。**本轮所有native构造flag均false，正native分支未运行/未验证。**

未来首个source recipe是原seed42001/randomization=False/.2m/.6friction/0added mass/20ms/完整stop，1200control间隔上限；不是新case授权。代码校核原7组delay抽样、XY/yaw/12腿noise及rng state，先原构造再按原play覆盖20ms，绝不skip抽样、夹改qpos或reset。CPU输出的expected初态仅原seed抽样计算，不是实际初姿/仿真观察或训练数据。

ClockedOriginalStep绑定真正原physics_step，不改PD/FIFO/力采样；只据data.time实际5ms推进维护独立物理tick/issued命令副本，不手加原control steps/elapsed。原调用抛错后已推进的时钟仍记录；时钟再读失败不覆盖原异常。新8项fake callback/clock软件检查过，和真实SDK导入prepare严格分开。首轮7项/源导入过后又收紧原guard False、GPU授权/唯一Data scope/完整freeze输入及异常元数据，最终8项＋实际导入prepare再核，原日志保留；不是物理retry或旧套件重跑。

仍缺完整source model/Actor/Stop**实际构造观察**、原注册12N/碰撞/effort/FIFO/goal全门、完整outer runner/Stop终态、受控原片/IO/预算/watch/finally和真实canonical安全phase/handoff；不能仅导入类就宣真实parent原生运行或物理准入。无CLIMB AUTH/H scope/模型/Actor/World/zero/main。不借PUSH witness/zero，不把原8N/source success当12N或registered成功，不作SR/重训结论。下一接真实完整父worker和原安全/受控IO；实际租约协调优先，不再堆旁路。
