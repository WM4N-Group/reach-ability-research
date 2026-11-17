# PREPARED L0 FF-only完整后继：只修已明确的helper预载/CPU承接，再做自身资格

b7f09967…程序已zero1失败/main0/closed，KeyError发生于实际run helper门之前未预载`registered_arm_ff`；Runtime/world/原FF实验未到，旧计数/费用/None/UNKNOWN保留。**本v2不是恢复旧根或换ID盲试**：只兑现已定点验证的导入顺序修正，并将同一24-helper集合真实纳入actual CPU prepare；原FF-only物理假设与此前唯一选案不变。

## 唯一实验差分与预算

- 原fresh[-.08,0,.33]/seed3701/20ms FIFO/1kg/.6m/目标[1.7,0]、原初臂姿/reference/positions/velocities/KP/KD/腿FF均不变。唯一动力学差分仍是6臂FF0→原PushEntry LIVE `qfrc_bias[p.dids[12:]]`；不是STOW pose＋纯gravity_data/零qvel/额外forward。
- 原stepper封存expected bytes前生成候选，原Runtime.step/issue+ACK/FIFO不变；原六初始化动作/原settle结束条件无新增settle、reset/写qpos/清FIFO/history或扫seed。
- 原witness constructor/validate与同次单guard、boundary driver/FF源码均保持此前字节。一次完整原12N/contact/range±1mrad/geometry/速度/effort/FIFO/goal门，PASS或拒绝到首边界即停；无task query/option/Actor/完整PUSH，边界PASS不是PUSH成功。
- 新scope/worker/controller/AUTH明确v2；**自身zero≤1、main≤1、retry0**，各300wall；main11sim/2200cmd/2400calls。native4GiB含64MiB reserve、两launcher总512KiB、raw2GiB/RSS4GiB/GPU3GiB/owned40GiB，原1s probe/oldest≤2s不降。旧b7/bef等scope不复开，不借zero/授权/FD/lease。

## 仅软件承接修正

模块顶层早期import纯stdlib构造器。`_preload_and_verify_execution_helpers`在CPU prepare的module-path根扫描前先导入与原run **同一24个helper**并逐个验exact frozen path/SHA/no symlink，返回数目完整后才放行。原run helper门AST不变，不删列表或移到world后，不改变任何Actor/guard/阈值。未来新文件也被既有module-path/inventory检查覆盖。

新2项stdlib CPU fixture核同原24集合、prepare只调用一次且早于根扫描、所有helper导入/文件门、缺失/漂移在CPU拒绝；不是实际native资格，也未重跑旧9/6/3或完整套件。此前FF/owner源码完整测试原件不追改。**只有新完整freeze、实际私有CPU prepare记录所有24项、fresh计划/H/UUID/进程/容量/四canonical、安全资源phase、原真实PerGpuLease及本程序自己的zero/审图齐后才main**。代码保管/默认disabled不是native部署/准入。

实际执行/计数/结果只看Data STATUS/H与本scope manifest，README不宣已启动或修复。物理是否改善joint3或完整门仍待新实际；不归Actor重训，不影响NAV/CLIMB非GPU合同准备。科学分母与全部旧未知/失败/原片/费用不改。
