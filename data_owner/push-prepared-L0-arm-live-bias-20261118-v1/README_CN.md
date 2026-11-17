# 新PREPARED L0：原注册六臂live-bias FF-only，到首次完整注册边界即停

06:03主计划a4607b32…要求择一，AINav06:07已撤pose＋纯gravity候选，选Data既有FF-only。这里只实现这一个差分，保持fresh原初姿/seed3701/20ms延迟/reference/gains/腿FF/目标/箱质量尺寸/200Hz。旧bef已closed：同次joint3 +1.605081332mrad超原允许上界.605081332mrad、Actor0；不是复开旧root或换ID补日志。

## 唯一假设和有限问题

将原startup默认命令的六臂FF由0换成原`PushEntry.command`的LIVE `qfrc_bias[p.dids[12:]]`，能否在同一原settle控制流结束时满足完整原注册入口？live bias可含速度项，≠另建gravity_data/零qvel/forward；不改arm pose、不偏reference、不放宽1mrad/碰撞/12N/effort/FIFO等。物理效果未证，不宣旧失败唯一因果或Actor需/无需重训。此入口是**PREPARED L0**，不是未修改原standalone L0/自然L1；不能用于失败恢复。

## 接线与安全

- 原stepper文件不变。新owner构造后、首次`next_command`前把已pin的唯一command-source装入`startup.default_command`；原stepper先从它构造候选，再封存expected bytes，随后原Runtime.step/真实delay FIFO/逐步issue+ACK。不事后改sealed命令/r.last，不补造ACK。
- `l0_witness.py`相对c05原observer仅owner的前述安装/标签/report变化。原`OriginalL0Witness.__init__/validate`及同次单guard函数AST逐字结构相同；原完整12N/contact/范围/geometry/速度/effort/FIFO/immutable检查不降。不调用原finish导致PASS二次validate；与上一boundary程序一样仅真实witness constructor完整校验一次。
- 新boundary driver只到首次完整真实边界，**无task query/option/session/Actor**；原拒绝保留并停止，PASS也不续完整PUSH。所有动作与原六初始化动作/clock/finally/费用/同钟直录保留，无额外settle/seed/姿态选择/reset/清FIFO或历史。
- exact question/scope新配置、完整freeze、actual CPU prepare、自身zero/审图、fresh H/计划/进程/容量/双UUID/四canonical及原PerGpuLease仍全部必需。代码/CPU检查不授GPU权限，不借旧zero/AUTH/FD/lease；真实owner01a1e4e1。

预算是**新程序自身zero≤1、main≤1、retry0**；各300wall，main11sim/2200cmd/2400calls；4GiB native含64MiB reserve/两launcher总512KiB/raw2GiB/RSS4GiB/GPU3GiB/owned40GiB/1s probe/oldest≤2s均不变。闭合后不以另一ID继续同一物理问题。有限边界通过≠完整PUSH/技能SR/鲁棒性/重训结论。

## 新的软件检查

`test_prepared_integration.py`只跑本差分新增6项：FF在expected seal前生效；旧zeroFF/假ACK拒绝并闩锁；同原settle1301命令与六动作/无extra；原Actor前置保留；完整witness/单guard AST不变；边界PASS/拒绝都不连task/不重call。私有CPU6/6过；NumPy明确fake世界/外部计数ACK，不是物理/Actor/lease/完整native prepare。未重跑原9项、旧完整套件/安装本机NumPy/下载环境。首轮9项中共享gain alias失误和修正原件仍保在上一source stage。

本README不表示已封存/prepare/派发；实际状态只看Data STATUS/H和新manifest。原bef/3b/947等所有closed/count/费用/UNKNOWN不追改。NAV/CLIMB原合同/入口准备可并行，不因本项串行冻结。
