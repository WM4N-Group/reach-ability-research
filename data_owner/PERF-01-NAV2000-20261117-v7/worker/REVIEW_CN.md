# v7仅必要原始预加载配置差分，复用exact v6 worker

v6 zero1PASS/main1已closed，448步/2.240sim在原command首次import SDK runtime.blend_command被strict audit拒绝。新配置在seal前从原SDK switch路径显式import runtime，并预载已冻结NativeNAVArrivalWitness和OSQP builtin扩展。Runtime/observer交付和probe分项代码直接复用已冻结v6，不再复制/改写worker。

旧实际事件证明arrival开始于8.100sim，确在固定10sim窗口；已读原ProtectedStow/FinishController/WholeBodyQP构造与solve源码：所需imports在已pin模块中，未见exec/eval/compile/FunctionType安装。实际SDK finish/balance import、两个独立2变量CPU OSQP setup/solve fixture在strict code-event hook下成功且0代码安装事件，默认backend=builtin只观察不强改；未构造真实FinishController/MjData/Runtime/Actor/physics，不冒原生WBC资格。

5个实际NAV.command纯CPU fixture覆盖初始blend及普通段，原/prepare后的blend AST相同、预载RNG/dtype保持、无CUDA/native；original SDK/arrival/solver源和扩展全部精确pin。新程序仍需自身CPU actual prepare/新原lease/own-zero≤1及main≤1，固定2000命令/10sim/原final相机/原全部动态门与1s/2s，不扩大窗口或借旧zero，不重开v6、不回填v5 UNKNOWN。
