# 源码候选：fresh L0原初始化中的注册arm live-bias FF

**仅新源码/9项私有CPU软件检查；不是完整程序/actual prepare/zero/main/物理许可。** 不可直接启动旧scope或使用其zero/授权。本候选没有controller/派发入口，不接Actor，也尚未接startup stepper/完整父worker。

## 为什么现在才有这个差分

bef55f4d…已zero1 PASS/main1 closed。同次原guard唯一调用返回`arm_joint_limit`；实际joint3 +1.605081332mrad，超过compiled上界0＋原1mrad slack共0.605081332mrad。原startup命令issued/delayed arm FF均0。该新同次证据仅归入口兼容，旧3b未存reason仍UNKNOWN；主体Actor始终0，不作重训判断。

原standalone `push/bridge.py:physics_step`默认构造零FF，而原`switch/push_entry.py:command`先构造arm的live `p.data.qfrc_bias[p.dids[12:]]` FF，然后进入QP/混合/移脚。`switch/runtime.py:nav_command`也用臂live-bias FF，但按n的关节顺序，不能直接挪其整条NAV命令到PUSH。`Robot.get_gravity_compensation_forces`另有独立gravity_data/零qvel forward，**不等于这里的live qfrc_bias表达式**；不为此候选新建world、MjData或调用额外forward。

下一可验证假设是：在fresh task0开始的同一原settle控制流中，**只将arm FF替成已存在的注册live-bias表达式**，是否能让真实终点满足全部原注册门？不是只加日志/换ID重试，不放宽1mrad、clearance、12N、effort、FIFO等。**效果未知；不声称FF是旧失败唯一因果或已经修好。** 必须将这种改变控制输入的入口标作PREPARED L0，不能冒原样standalone L0、自然L1或恢复失败运行。

## 当前实际实现

`registered_arm_ff.py`默认disabled且import只有stdlib；启用需fresh task0/empty FIFO/原初姿/.005s，核exact startup/bridge/PushEntry源SHA和实际原physics_step字节码。只编译原PushEntry中构造arm命令的两条赋值，不执行原PushEntry实例/qp/blend。与原default PD构造表达式逐项比positions/velocities/KP/KD/腿FF，唯一允许非零差分为6臂FF等于当前未缩放live bias；prepare时保存原命令只读基准，避免KP/KD共享alias造成两边同时变化而漏检。输出不得alias真实状态/目标；不符即latch，不能修输入后续用同对象。

这只是command-source构造器。**尚未接原startup generator/实际issue+ACK/witness/边界driver/父worker**；不能把本CPU测试的构造次数当命令发出/physics/费用，不能据此宣称完整原安全门已过。后继若装配，必须保原settle终止/初始化写入记录，禁止新增settle/后失败reset、改qpos/目标、清FIFO/历史或扫seed。首次原边界的所有检查仍需同次单调用观察；边界通过不自动选择PUSH或获得完整PUSH资格。

## 本轮检查与保留失败

- 新9项CPU：disabled、精确唯一FF差分/无state写、live sample与无alias、目标/gain漂移拒绝、NaN/世界替换闩锁、非fresh拒绝、tamper/symlink拒绝、实际physics bytecode变化拒绝、无mujoco/torch/Actor/GPU/lease/物理资格。
- attempt1 **8/9通过、1失败**：fixture中原default和注册KP/KD共享数组，call时仅两边比较会漏掉两边同时变化。原日志/原source SHA保留。新增prepare时只读baseline，**attempt2 9/9通过**；这是源码软件纠错，不是物理retry。
- 使用已有私有Python3.11/NumPy；未在本机安装环境、未import原SDK或MuJoCo/Torch、未加载模型/Actor、未开GPU context/lease/Runtime。未重跑旧完整套件。
- 所有实际scope仍closed，在途0；新完整freeze/actual CPU prepare/自身zero/新main均0。原bef结论、计数、费用/片及科学分母不变。

具体原件：Data manifests的`push-L0-initialization-contract-source-20261118-v1/`。代码归档不是native部署。下一先完成上述私有startup接线及定点CPU检查，再决定是否存在符合最新主计划的新有限完整程序；fresh H/资源/原lease和自己的资格不能省。NAV/CLIMB合同与入口准备不因本候选串行冻结。
