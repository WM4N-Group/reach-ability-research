# CLIMB并行source推进：原单控制周期→外部逐5ms请求，未构成原生程序

PUSH新程序在canonical lease前停止不能串行冻结CLIMB。此模块只推进已核原CLIMB标准L0入口的**一个20ms控制周期**，不新建框架/模型/世界/Actor，不运行裸CLI，不授物理资格。

`source_interval.py`对原play.py SHA8fe257c6…严格pin/解析，不import原SDK。仅提取原Actor inference→set_action→4个5ms command/physics/Stop.after_step→finite→原stateful status→Stop.status→observation的控制AST。唯一物理调用改为yield原command；原算法语句AST不变。保留control0即Actor调用，不能把ready前gain0说成没调用Actor；每实际5ms后Stop.after_step一次，20ms末原status/Stop.status/observation各一次，不额外poll。最后drain返回(state,reason,obs)不多调用下一Actor。

在ascent-only/stop=None支路，原代码command=None表示`ClimbBridge.physics_step`内部默认policy命令，不是全0命令；此处原样保留，未来parent必须正确适配，不能编造MotorCommand。完整使用默认stop模式时须真实StopController/原支持/完整终态，ascent不代完整stop。

**明确未做**：原构造器/模型/seed42001/随机化False仍抽pose与delay RNG、20ms覆盖不跳原抽样、首次history observation、真实registered owner/12N与全部安全/命令封存与逐次issue+ACK/原finally/原同钟raw与日志、外层有限case/完整stop等还未接。原trace/viewer/capture/print/sleep是声明由未来Data父层接回的IO，不宣整个main bytewise或时间等价。必须标source-only，不能冒原入口8N已经过注册12N，不能借PUSH/NAV witness/zero/AUTH、写state/reset/清FIFO美化。

4项新私有CPU都过：假Actor在control0调用/无hidden physics；4次明确fake ACK后Stop.after_step4次且status只有1次/精确drain；None保原默认命令语义；disabled与源漂移拒绝。NumPy storage/fake Torch API明确不是实际Actor/MjData/GPU。未跑旧完整套件/加载模型/下载或安装环境；不是CLIMB freeze/actual prepare/zero/main/成功率或重训证据。

未来最短是把原构造器/RNG/初次observation和这个单周期接到一个真实外部step/ACK owner与原安全/完整Stop/finally；先CPU保负路径，再按主计划冻结有限新case及自己的完整资格。source本身不实现这个owner，不能直接派发。原贡献/来源仍属原CLIMB实现，原许可/合同与科学用途不改。
