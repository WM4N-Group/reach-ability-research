# CLIMB外部step/ACK owner协议源码：控制步与物理步分列，未构成注册准入

沿07:03主计划，PUSH f073已closed且原canonical竞争者未知，不换ID/空卡盲试，也不冻结CLIMB非GPU接线。这里将上一单20ms源周期（e9098862…/生成算法e1100017…）接到**source-only请求/真实读者ACK协议组件**。`prepare`默认disabled，无CLI/模型/世界/Actor加载/lease/H/注册/派发；这不是已获得原生资格的执行owner。

## 新确认的原源语义

原climb/bridge.py SHA055f5c79…的`physics_step`只真实推进物理、刷新几何/力史，**不更新`sim.steps/elapsed`**；原`status()`才每20ms `steps+=1; elapsed+=dt`。因此必须用未来Data父层**独立真实物理tick**＋`sim.data.time`作5ms ACK；把`sim.steps`当物理步会错。不能为迎合ACK再手工加steps/elapsed、重复调用status或补now。原status/Stop.status仍严格每4步一次，Stop.after_step每5ms一次。

## 代码实际完成

- fresh time/counter/control steps/elapsed0、FIFO空、history None，exact原cfg/task JSON/桥源/周期编译器pins；只调用**一次原initial observation**更新原history，不清history/队列、不重置state。constructor/RNG是否真实、Model/Actor/Stop身份未认证，不能以这些fresh字段冒原初始化witness。
- 第一次请求保原control0 Actor（ready前gain0不等无调用）。每command预先封存完整5×18 bytes；ACK须独立父计数+1、原clock+.005和父层实际**issued**命令相等，不把delayed FIFO当issued。原MotorCommand/FF/PD/Actor算法不改，source组件只支持完整stop（stop=None直接拒绝，不造全0命令）。
- ACK后立即resume同一原interval：处理一次Stop.after_step，必要时准备**同一周期下一条命令**；第4个ACK drain原status/Stop.status/obs一次，然后停止在控制边界，绝不提前调用下一Actor。cap/terminal后不多发命令；source terminal即使success也不是registered receipt/完整技能成功。
- 未ACK重复、假ACK/错误计数、bytes漂移、外写world/queue/cfg/interface/goal/device、额外stateful status、原guard拒绝都fail closed/latch，无resync/回滚/reset。原native/Stop异常对象保留；部分物理钟已推进而ACK未完成的原件要由父finally记费用，不能把verified ACK0当task0或零cost。
- parent_check只是未来原cached ResourceWatch/authority callback调用点，不创建第二watch/硬件composite probe或OwnerStamp；模块不会读/占canonical锁。回调身份/独立计数与实际issued读者仍须由真实冻结父层证明，fake读者不构成物理证据。

## 新12项CPU及未完成项

12项私有CPU首次全过：default off/一次initial obs；精确4ACK/即时drain；无issue/重复ACK；误用control steps拒绝；actual bytes漂移；guard/world/cfg/interface变动；额外status拒绝；partial native异常身份/时间保留；Stop异常仍记已核issue；两周期2 Actor/8ACK/2 status；非fresh/源漂移；source假success不冒registered资格。全部**明确Fake Actor/world/clock/ACK＋NumPy存储**，未import MuJoCo/Torch/加载Actor或开GPU，无真实物理/原生prepare，未跑旧完整套件或下载/安装环境。

仍缺真实原构造器/RNG（含20ms覆盖不跳抽样）/原Model/Actor/Stop认证、Data实际step与issued读者、原注册12N/碰撞/effort/FIFO/immutable goal门、外层完整Stop/终态、有限case预算/受控原片和finally、完整freeze/actual CPU prepare/自身zero与fresh真实lease。组件report强制`constructor_RNG_Model_Actor_Stop_authentication=false`、`registered_12N_safety_finally_full_Stop_receipt=false`、`physical_or_skill_qualification=false`/`execution_permission=false`。

下一只把这些真实原组件与本协议接入完整独立parent；不借PUSH/NAV witness/zero/AUTH，不以原8N替12N、ascent替完整stop，不作SR/重训/科学分母增量。实际PUSH/旧失败/None/UNKNOWN/费用不变，资源handoff未知前不新开GPU。
