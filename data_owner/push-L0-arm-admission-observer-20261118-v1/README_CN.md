# 未资格化源码：原L0手臂准入同次观测（不改guard/入口控制）

接04:03主计划的唯一可辨缺项：3b405原startup1301步/6.505sim stable后，12N/contact函数先返回，原CollisionGuard非空但returned reason/同刻实际joint pose未保存。原scope已closed，q_before早5ms不能充同刻；本差分不回放旧guard/新建旧世界，不补造3b405唯一叶因，也不定PUSH Actor需/无需重训。

当前文件仅供未来明确新问题的完整parent选择，不是新AUTH/完整freeze/actual prepare/zero/main。旧3b405/947a及所有closed源原样，不能因本README重跑、借旧zero或删除碰撞门。

## 精确差分

- 保原`OriginalL0Witness.validate`所有检查顺序/阈值，尤其`need(not reason,...)`不改。只把原**一次**`CollisionGuard.check(q,allow_hand_contact=False,record=True)`包进同次metadata函数；默认禁用即拒绝，不调用guard、不冒PASS。
- 调用前复制该次实际q/dq、compiled model hard ranges/joint names、task tick/sim，记录原1mrad slack对应的布尔比较；不拿上一命令q_before、估算或静态URDF冒实际后态。不改qpos/qvel/queue/history/goal，不调用第二个guard/MjData/physics/Actor/owner probe。
- 原reason/异常先存在**外部startup owner**，而非可能在构造失败时未赋值的`owner.witness`上。worker既有finally→startup.report即能封尾；只保一个最新bounded audit与计数，不建新journal/framework。保原异常对象/类型/errno，即便errno属性本身读失败也不替换主异常。
- 仅白名单存`arm_joint_limit`或原body-pair/5位小数distance字符串；其它非空reason只留hash/类别，仍原样返回使原门拒绝，不泄露任意异常文本。未知/坏sample而原guard返回空时额外fail closed，不能一边丢观测一边准入；这属于明确更严格的输出完整性行为，不宣称全语义零差分。
- body-pair distance是原return中已四舍五入值，不是再次mj_geomDistance。此audit永不作为owner freshness/model input；同次原子pair/1s/2s/PerGpuLease等没有改版。新增准入metadata开销尚未实测，不宣称性能收益。

7项新CPU检查覆盖默认OFF、同一次原参数/flags与快照隔离、构造失败owner仍保存joint拒绝、geometry原返回不重查、原异常/坏errno属性、未知reason/NaN样本不可放行、整个旧witness逆AST与单guard/no-world-call。夹具均是软件数组/假guard，不是实际3b405原因或物理成功。本机尝试因未装NumPy未运行，日志保留；只用已有私有Python3.11/NumPy做CPU验证，不安装/下载环境或重刷旧套件。

## 原独立与注册条件差

Data已有原source比较显示：原play.settle的stable仅证明3N范数/基座速度/XY等启动条件，不能证明注册12N、arm joint/collision/effort/FIFO或完整退出。原独立main在settle后进入双Actor，再按显式分支调用FinishController；注册cold capture自身有实际QP/arm准备与更严COMPACT_TRANSFER/dwell/guard。本L0替代入口先过真实12N及原arm安全再建立自己的witness，随后仍原PushEntry→Actor。这个**检查顺序/入口条件差**是可核事实，不证明注册guard错、原独立一定会成功或Actor坏；不通过删门/伪SupportedCapture连接两者。

未来仅在owner冻结明确新诊断问题/有限预算/完整源并取得必要own-zero/fresh lease后，才可部署本观测。当前不派新的物理，不把GPU1空闲当授权；已观察GPU0有非Data compute时不抢停/借锁/换卡。CLIMB原RNG/startup/Stop源准备仍可并行，不等此项补齐。
