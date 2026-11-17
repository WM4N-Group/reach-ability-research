# 已执行并closed：只到首arm准入边界的同次观测

**candidate2已执行并closed/no retry。** 实际code71ede87e…/programbef55f4d…，1807文件freeze/actual CPU prepare＋own-zero PID342906 PASS；唯一main PID343307在原startup1301步/6.505sim stable后，原目标guard只调用1次并直接返回`arm_joint_limit`。同次compiled joint3上界0rad、原slack1mrad、实际q3=+1.605081332mrad，超允许上界0.605081332mrad；只joint3触发原容差调整后的拒绝条件。诊断问题已回答，但原门拒绝/无PUSH query或Actor/不定重训；旧3b未存的reason/同刻pose不追补。原片/费用/后继入口修正对象见Data STATUS。

 candidate1 program1064a61d… actual CPU prepare过，但派前PASS分支复核发现原owner.finish会在真实witness构造校验后再validate一次；本“首同次边界”问题不能预设拒绝，已在zero0/main0/H无key时拒绝，旧freeze/AUTH不改。candidate2保原startup两个前提，仅调用真实OriginalL0Witness构造一次（其完整原validate仍在），不调用第二次finish/validate，不伪witness、不去阈值；同一尚未派发scope/问题，不是物理重试。

事前唯一问题：在原L0部署case的一次fresh启动中，原CollisionGuard实际返回哪种joint/body-pair原因，同次实际q/dq/compiled ranges是什么？3b405已closed且该同刻值不可从q_before恢复；本候选不重放/恢复它，不运行完整PUSH、不追Actor成功，不把新同case观测追改为3b405唯一原因。

- 复用原[-.08,0,.33]/seed3701/20ms/1kg/.6m case与原startup初始化，无额外settle/新seed/调margin。选用e705f268同次observer，只包一次原guard，原need/12N/contact/velocity/effort/FIFO/goal门不降。
- `boundary_driver.py`只复用原startup/逐步ack/原writer与guard，在一次真实witness构造完成/全原检查通过时**终止在边界**，不调用原connect/factory/public query/EntryJudge/任何Actor。原guard拒绝仍原样停止并在owner保留记录，不重试。软件boundary完成不是完整技能成功；native主字段仍full_task_success=false，诊断是否回答单列。
- 该新问题own-zero≤1/300wall、main≤1/300wall/11sim/2200cmd/2400driver call、retry0，足够原最大10.5sim初始化但不留PUSH60s执行路径。原native aggregate4GiB含64MiB reserve/launcher总512KiB/raw2GiB/RSS4GiB/GPU3GiB/owned40GiB/1s/2s不改，provider quota UNKNOWN。母版/命令/失败/费用完整保。
- worker/controller沿原生命周期，仅新问题/路径/有限cap/禁止所有task option、选boundary driver，旧freeze/AUTH/policy/canonical/binding不改。GPU0同一execute目标compute门在H/计数/child前，外层fail-fast；GPU0有非Data compute/安全phase未知时不派、不抢停/借锁/因GPU1空就换卡。
- 本程序已完成有限资格并用尽zero/main，不能再派；任何后继须独立明确差分/完整freeze/实际prepare/自身zero/审相机/fresh资源与原lease。7项新CPU只测禁用、边界后不连技能、不多发/不冒成功、拒绝原异常/不重试、cap前停；另补terminal-none-executor/禁query及OwnerStamp原子oldest两项；e705的7项同次observer检查复用，不刷旧完整套件。

本scope不是90次/效果消融/重训/真机。若后续得到joint/geometry原因，也只说明该新run的入口条件，不定Actor坏或原3b因果。诊断main耗尽即closed，不再下一ID补日志或继续PUSH；已有科学用途与分母、J独立任务原样。

`boundary_install.py`是既有indexed constructor adapter的未来私有差分：保原engine.boundary/Runtime.step/全部原检查，仅显式允许已终止的无executor边界（不是造空executor），并禁止任何intent；同时把OwnerStamp来源明确改为成功原子pair的oldest而非last_ok/completed，2s/真实watch.check不降、不重复硬件probe。原3b real-watch检查结果不追改，不据旧stamp字段反推旧物理unsafe；旧helper原样保留。
