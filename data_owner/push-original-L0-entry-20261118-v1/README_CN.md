# 下一入口：严格原标准PUSH L0初始化源码（不是可执行程序/资格）

目标是补“原标准合法入口下主体Actor与完整尾段”的证据，不是重开closed L1、改seed追成功或去掉NAV仍称自然L1。

- 来源原SDK `push/play.py`（SHA12a922f1…）和`push/bridge.py`（fafcc5c7…）；本轮只取6个必要小源、逐项对原SHA256SUMS核同，没有重新下载环境/模型或跑旧套件。
- 标准fresh初态为**[-.08,0,.33]**，不是L1 Runtime[-1,0,.33]；seed3701/20ms、1.2×1.2×.2m/1kg箱[1.1,0,.1]、+.6m/native-public[1.7,0]、uncompensated不变。`derive_fresh_L0_runtime_source`只给私有Runtime INITIAL X一个可逆constructor hunk；原camera/calibration三hunk仍适用，原Runtime.step字节码相同。原SDK文件/Actor不改，但生成的Runtime源明确是初始化variant，不冒“执行源码全未改”。本目录不构造它。

## 必须显式保留的原初始化，不可混作连续交接

原`play.settle`并非“始终无位姿写入”：初始脚底Z调整、实际承重后回写起点XY和基座速度归零，结束前还做原controller.reset/applied_commands零/history=None。**仅可在结果前明确登记的fresh L0、首Actor之前执行这些原动作**；不能在NAV后的L1调用，不能用它修复任务中失败或清FIFO。初始化、主体/退出及原aux world费用必须分开；不从任务时钟减掉已发生的物理步。

原初始化stable门是四脚力范数>3N及原速度/时钟门，**不是注册PUSH的12N承重/完整入口、native NN、公目标/卸载/STOW成功证明**。后续必须保留原注册更严格的门；不能把startup stable直接冒准入。

## 已有源码与实际CPU验证

- `l0_startup.py`把原settle的两个physics_step调用点精确改成逐步请求，并在6个原写入/reset之后加有上限私有元数据。逆向AST恢复全部原算法；不重写沉降/稳定循环，不增加“沉降到成功”的重试。默认PD构造来自原Bridge.physics_step的原MotorCommand AST，不手写另一套gains/FIFO。
- caller必须用原Runtime.step真实发一条命令后ack，Runtime异常必须传入native_error并原样传播/闩锁；没有实际.005s/计数+1或命令不一致、重复next/skip会闩锁。world/data/queue原对象、dt、fresh原初态和实际Actor调用计数0均检查；模块自身不会推进物理。ACK数不是费用总步数：即便无有效ACK也单列实际clock/counter，不抹去异常前已发生的物理。真实Actor前初始化、全部命令/原片/guard仍由**尚待接好的完整parent**拥有。
- `qualify_source.py`默认OFF；实际私有Python3.11.16过原函数/constructor/source编译与明确软件fixture：1301个**伪世界外部clock/count ack**、6个原动作位置、默认PD表达式与拒绝路径；4N软件fixture可过原3N启动但不够12N，特意禁止把它当准入。**没有import Torch/MuJoCo、Runtime/MjModel/MjData/Actor/lease/真实physics0**，不是完整程序actual prepare、own-zero、main、数据或SR。

## 仍缺什么；当前不得派发

原注册12N/FF/FIFO/原历史与immutable goal的**真实L0完成witness**、单次原PUSH body/完整退出、实际leg/arm/root/phase记录及ScopeIO/原片/费用/finally仍须接成一个完整parent。原SupportedCapture有task0/原自己实际发命令约束，不能在settle后伪装成它或回填其计数。source startup finished不等PUSH成功。物理预算/完整freeze/actual prepare/自身zero全未完成，不借closed L1的0fa40c…zero/AUTH。

物理准入也不是GPU空闲推测：后继controller目标卡foreign-compute拒绝已接同一执行分支、在H CAS/计数/child之前；单卡外另一GPU可忙，不永久按组锁卡。这只是未来源码（5项CPU检查），不是live资源修复、原子交接或OwnerStamp；后续竞争仍由自身原PerGpuLease/canonical/UUID/PID与原1s/2s判定，所有外层shell fail-fast，不动他组进程/锁。当前全部原scope继续closed，新物理0。
