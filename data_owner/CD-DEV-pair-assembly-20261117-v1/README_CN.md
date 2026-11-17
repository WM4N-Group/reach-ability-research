# 主线C/D首个DEV对照：Data装配组件与事前协议草案

**这不是M1完成、native资格、新freeze/AUTH、GPU任务或优化收益。** 原PERF worker仍只允许NAV2000，不能改个arm直接运行；所有旧scope/冻结源/消费者发布不改。当前只交一个能被未来独立worker调用的默认关闭装配组件及两arm配置预览，不新建scheduler/签字平台。

## 唯一代码入口

`cd_entry.build_cd_driver(..., enabled=False)`直接返回None，不读文件/导入AINav/调用guard/建world。未来独立新程序显式enabled后，先检查5份当前实际源码pin与模块解析路径，再委托原`method_entry.build_original_cd_method`＋`live_driver.driver_class`。保原C的roles/tree/replanning、D同技能底座/公共输入/共享B-D cost接口及统一legacy H；验证wrapper/baseline/roles/driver只用同一原FactorJournal。构造不得select/generate/step，不重置counter或二次评价cost。

原backend由AINav按原构造器安全生成并提供，本入口不读凭据/env/opener、不认证/探测/API；原backbone还会验证真实类型、profile/model的image+text能力/caps。profile声明deepseek-flash；AINav现已在一条历史记录query通过原认证/真实三role响应/选择，但actual served-model label、逐role usage/完整链未保留，不借此称live C/D或重跑旧query。original source caps从原run_full_course AST字面量保留：100 calls/8192单次tokens/900000总tokens、role timeout90s、plan_count5/terminal_bonus10，**不是新增API使用许可**。

调用者仍独占真实Runtime/observer/writer的构造、partial异常句柄、finally/费用/原lease/新root/真实video监督。本组件不创建或关闭world，不取lease，不接管peer进程；异常原样传播，不自动retry/换planner。它只支持当前原V4 scene身份，不能暗换更容易布局；更小支持域须明确声明并另冻结对应实现。

## 结果前的DEV草案，不冒资格齐全

`CD_DEV_PROTOCOL_DRAFT.json`固定C→D、各最多1own-zero+1main、无retry，同公共任务/初始化生成机制/原技能安全/模型与预算/硬件负载政策；全尝试费用/失败/UNKNOWN/完整live 1×视频都保留。新鲜生成初态不冒隐藏状态精确配对；此第一DEV不是独立效果估计。方法必须记录真实优化调用、同query路径评价、KNOWN/UNKNOWN、baseline→最终决定、fallback与执行后再观察；全UNKNOWN回退不是M1完成，名义reference_travel_m不塞实测秒数。

`prepare_pair.py`只核当前小源码/true-default-off并生成两份初始同配置预览，`dispatchable=false`。当前四项具体接线缺口（不是新审批，已接13:41接口新进展）：
1. **AINav**：`backbone_entry._checked_backend`需要原profile/model image+text的新独立任务的实际served-model label/逐role usage/完整树与共同live caller；历史记录query真实API/选择已过，不再泛称从未有响应或缺key。
2. **Reach**：`CompleteReferenceCost(initial_state, forecast, is_terminal)`已有`PublicNavReferenceCost`，只支持`DECLARED_GROUND_NAV_VISIT_AND_FINISH`。现缺准确独立DEV的Observation.goal与同query PUBLIC初始/真实receipt reference transport；现V4 goal和PUSH/CLIMB不在该域，不私改goal/用private base pose或旧J事实填预测，也不等全域模型完美。
3. **Data**：本轮`task_loop.run_task`/`make_cd_phase_health`已补步进/预算终止/读数与seal；外层构造/partial finally、backend初始化费用、精确任务budget/IO/lease/导入闭包仍需接线并完整actual prepare，旧PERF NAV-only/2000cap绝不照搬。
4. **共同任务**：具体受支持DEV任务/初始化/RNG与有限任务预算尚未选择，保留null，不静默降V4高台、不用看过的赢家路线。它们必须在首结果前进入新完整freeze；之后每arm自身zero/真实lease→main，不借旧zero。

## 定向验证范围

`python3 -B test_cd_entry.py`：17项新Data检查。功能接线使用明确stub factories，仅验证本包装的参数、顺序、ledger身份、default-off、拒绝/无retry与协议公平性；**没有真正构造原FactorJournal/已验证backend或LiveDriver、没有证明机器人/C/D/优化有效**。原AINav6+5/旧63+14不重刷。真实5源码SHA/default-off source prepare是本机小文件检查，不是完整新程序prepare，更不是remote部署资格。

本机source-prepare：
`python3 -B /home/yuanyue/main/work/data-team/development/cd-dev-pair-20261117-v1/prepare_pair.py /home/yuanyue/main/work/data-team/development/cd-dev-pair-20261117-v1/CD_DEV_PROTOCOL_DRAFT.json`

实际日志与精确blockers：`/home/yuanyue/main/work/data-team/manifests/cd-dev-pair-assembly-20261117-v1/`。代码可先code-only同步；当前路径选择指向本机源，不能当远端worker配置直接执行。

## 本轮续作：C/D步进、健康门、收束与费用组件

`task_loop.py`不建world/后端/lease/ResourceWatch，不构造或关闭父资源。调用方必须已使用原`cd_entry`、真实ScopeIO/ResourceWatch及直接live recorder，watch/health/ScopeIO必须是同一个stop-state对象。`make_cd_phase_health`每次恰调用原RSS/GPU/wall fast-health一次，只核新任务冻结skill子集；原ResourceWatch原子(oldest,completed)/1s-2s和真实lease probe均不改，不生成owner stamp。`run_task`要求传原watch及该匹配health，保原driver.step_one与pre-issue native guards；不把False step返回、单技能成功或forecast当任务终态。

独立command/driver-call/sim/全scope wall有限cap；异常后按实际Runtime计数保最后直接live采集，视频错误不覆盖原错误，unknown usage保None不借旧zero。异常序列化只含类型/白名单整数counter，不dump backend身份/headers/异常参数。可用ScopeIO在所有退出只尝试一次不可逆begin_finalization，缺handle/失败明确记录；父watch/lease/writer/observer关闭、编码、报告仍由外层负责，组件不能抢其清理ownership。

新22项CPU用假driver/物理时钟及**真实原ScopeIO/ResourceWatch＋synthetic probe**定向核：no-step/caps/原health与skill子集/无额外probe/last pair不刷新/异常实际读数/late completion/视频错误/敏感参数不入receipt/unknown/不可逆seal/父收尾权属。不是原生driver或GPU/backend资格，不重跑原17项与AINav旧套件。对阻塞step/API/内核，组件不能强行抢占；原全scope信号/watchdog仍必须由外层保留。loop与step wall排除父cleanup/encode/report，不冒all-inclusive/独占CPU；费用/整数counts是audit，不作模型输入或M1/算法收益证据。

本轮定向命令：`python3 -B /home/yuanyue/main/work/data-team/development/cd-dev-pair-20261117-v1/test_task_loop.py`；新日志`/home/yuanyue/main/work/data-team/manifests/cd-task-loop-20261117-v1/`。整体程序仍未freeze/注册/部署/own-zero/main。
