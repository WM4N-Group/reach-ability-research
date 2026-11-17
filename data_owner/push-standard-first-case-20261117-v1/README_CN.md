# 第一有限PUSH case：原标准单箱＋自然NAV前驱（不是90次或旧D3重跑）

已选首个case `PUSH-SDK-STANDARD-NAV-L1-20261117-v1`：原SDK `nav-push`，seed3701/20ms，原1.2×1.2×.2m/1kg箱初始[1.1,0,.1]，Runtime从[-1,0,.33]开始，原NAV目标[-.02,0]后自然PUSH .6m。native drive/public目标均[1.7,0]、mode=uncompensated，**不补.11m追成功**；原native终态、20mm public/10mm dock、卸载/完整STOW分别记录，不能互相冒充或降门。策略history只保原入口本来初始化，不新增reset/teleport/清FIFO。源/待资格见`CASE_NOT_AUTHORITY.json`。

**没有把现V4场景冒L0标准。** 现`complex_scene.validate`正确限定2/3个2.4×1.4×.2m/.5kg对象，不接受该原标准单箱；本目录不改它。只用原generic SceneRegistry声明实际`push_box`1.2×1.2×.2m/ground，以新独立asset承接原SDK geometry，不移动旧模型/场景。严格L0原独立settle/启动尚未接续，不谎称现L1就是L0。

`standard_asset.py`默认OFF；enabled仅可在新qualified静态构造程序中、持原PerGpuLease/ResourceWatch1s/2s、受控ScopeIO后调用。实际一步是原CPU PushBridge(time0/FIFO0)＋原camera-only hook/一次静态重编译：核原robot/engine signature、尺寸/质量/goal、原192×128机载camera ABI及HD capacity，用有上限的内存MJB buffer→ScopeIO，**没有C文件名写绕过计量**。不创建Runtime、load/forward Actor、初始化CUDA/Renderer或发physics command，不导出/恢复qpos/qvel状态。

`asset_worker.py`/`asset_control.py`为一次独立静态asset操作（world constructor≤1/step0/Actor0，**不是own-zero/技能main**）：120wall、RSS4GiB/GPU3GiB、128MiB单buffer、256MiB controlled output＋1MiB launcher、disk floor2GiB。新全程序freeze/实际CPU prepare/当前owner-PID AUTH/H/原UUID锁与容量缺一不可；目录+file flock/SHA-inode CAS/atomic/mode，child失败先finalization再写闭合proof，无自动retry。失败asset不许当合格模型；旧scope/费用/UNKNOWN不改。

静态asset有资格也**不等下一PUSH worker已完成或可dispatch**。还需真正同世界parent、原注册goal/force/FF/PD/FIFO/STOP/stow全部门、实际Actor接管/模块/entry reset/退出记录、完整原片/费用与新整程序冻结/自身zero。现PUSH leg/arm真实激活分母仍UNKNOWN，不以这个无Actor静态构造补0或新SR；C++ GIL候选不编译/不热换，也不借其名义改2s。case/asset/worker真实阶段只以Data STATUS/H/原件为准。

## 当前最高接续：该asset操作已closed，移除额外资产前置

2026-11-17 23:56实际program **f49854cbb52c…**在原`PerGpuLease.__enter__`返回前报`BlockingIOError errno11`；world构造0、Actor/命令0、task时钟未建立、MJB不存在，asset1/own-zero0/main0，已closed/no retry。原错误未保存栈帧，**不能断言具体是某个flock、NVML进程创建或J/GPU负载**；前后锁空也不授予重试。原件`/home/yuanyue/main/work/data-team/manifests/push-standard-first-case-20261117-v1/ACTUAL_STANDARD_ASSET_CONCLUSION.json`。上面的asset worker/controller现在只保历史，不再作为推荐待运行入口，不修改其冻结副本/结果。

首case定义保留，但**下一直接接原`mujoco_zyh.runtime_adapter.construct_runtime(bundle, config)`的`scene_recipe='zyh_native_single_box'` camera-only源构造**，不再先跑另一轮独立asset。这条已有入口直接创建fresh标准Runtime/原模型，不要求外部MJB；已核`scene.configure_scene`此分支不做research三箱/20kg/地形替换。完整PUSH parent仍须接原注册安全、public/native目标及完整退出门、实际模块调用/原entry reset元数据、原片、partial与全部账、原真实lease/1s/2s。不是运行裸CLI、绕canonical、改Goal或跳自身zero；完整新程序尚未资格化。

后继worker在现有异常报告加有上限的file/function/line traceback（不记locals/凭据），以免再次把不同EAGAIN叶段混为“GPU忙”；资源前检补进程/线程余量与安全phase交接。禁止用这次事后空闲换GPU/新ID盲重试、跨进程借FD/lease、放宽2s或让J停工。当前PUSH真实Actor激活/终态仍未取得，本次不计Actor物理失败。
