> 后续源码自审：高台终点wrapper保留原RegisteredNavMachine类型与同一个只读native_nav身份，避免原outer-contact/live-source守卫因外层wrapper丢失owner类型而拒绝；NAV完成仍不等任务完成，拒绝stack/replacement，未再构造或进入NAV。新增6项明确SOFTWARE owner接缝检查，不是原生资格/真实失败或E成功。static-deck、40cm及全链仍未解决，scene/Actor/全部原门未改。

# AINav接任V4五组：精确资产移植与能力缺口，不是原生通过

2026-11-15，按22:53总计划。当前优先A/B=VLM+WM无/有共享优化，C/D=原AINav无/有同一共享优化，E=无VLM/WM/优化的固定规则；主比较B−A/D−C。旧API0 greedy/multistep两组不是这五组的代理。

## 2026-11-16：目标层标称值接缝修正＋实际高台终点source接线（未native执行）

**不能让接触沉降把公开layer改成新profile**：真实box top可为.1998m，公开CLIMB destination/NAV layer仍.20。source observation现在保公开声明layer，实际top另记并须过原.01m几何门；不是把public/native option改成实测小数、四舍五入r.qpos或降容差。原validator仍要求公开NAV height与该声明layer完全相同、actual feet/selected contacts/height tolerance照原门。新增非整数沉降回归避免.1998 private plane与.20 public参数精确比较时人为BLOCKED，.189/.6/NaN照拒；旧source35未借此宣称物理失败或修复成功。

`task_terminal.ActualClimbChain`只在当前真实原CLIMB succeeded回执/原stop witness/实发command hash/同world/时钟边界记录原private binding与公开destination，保留immutable绑定SHA。最后须从ground连续正向到真正goal_deck、≥2个真实成功transition；不接受VLM reaches_goal、单CLIMB、拼另一world/clock或蓝图补后果，不硬编码哪个箱先后。所有原3placement/NN/STOW_VERIFIED当前几何仍须成立。

final `v4-goal-elevated` NAV现在只可包装**真实在goaldeck/.60层**的原RegisteredNavMachine（ground同XY拒绝），原NAV成功另记，然后用原RegisteredHoldMachine继续其真正protected-arrival owner、bounded2s内逐实际200Hz命令读goal_deck contact/4脚≥12N、原速度/tilt/足高/goal bounds与连续.5s dwell。没有新world/teleport/万能HOLD或加额外任务路线，原option/owner预算连续，不从片长判成功。

只有真正collector给出的同tick、current executor/session/原NAV＋owner-stop/3placements/CLIMB chain/真实deck-contact proof才可让driver完成；E收到该typed proof、自己的实际placement/support/terminal-pending状态匹配且一次性验证才确认complete，字符串/布尔/goal/ref/仅类型正确但未collector来源的对象均不能自签。A—D共用同一private物理终点，不依赖预测tree reaches_goal。此source已接assembly/factory/coordinator/driver，**不等于终点已实际过**；当前static deck/.20→.60原20cm技能域、后继source链和A/B WM bootstrap仍未解决，五组main仍0。

## 2026-11-16：有限单次CLIMB→NAV的factory／inner+outer guard／共同候选已同步接源（未native验证）

不再只交独立adapter。`V4TaskFactory`现在在**选中NAV private ExecutionBatch**的短生命周期context内，从原成功CLIMB已登记的真实source observation＋原placement建立/缓存typed live witness；普通PUSH/CLIMB仍走原completed-witness路径。原NAV `_validate_option`仅source registry lookup一处精确可逆适配，原公共anchor/参数/height/4脚12N/goal-margin检查都在。selected constructor只为真实该类型调用其同次`nav_type`，普通ground/arrival/stow仍原constructor。assembly把原ActualPlacementEvidence交给factory，driver在真CLIMB receipt边界登记source，selected judge用相同registry/witness逻辑。

**外层同步**：`execution_entry`仅对真正entered/installed原RegisteredNavMachine＋该exact typed NAV owner/registry/executor允许所选source对象feet contacts，仍原forbidden-body；不能只改inner guard放行。保存历史public→private native option的**精确对象绑定**，新query/新NAV constructor不能让旧CLIMB真实private hash消失；这是私有实发owner证据，不是把旧RGBD alias带入新public帧，current aliases仍每次重建，clone/value-equal option不冒原对象。

五组共同目录新增**仅3个**事前固定box required top-centre NAV（声明几何，非live pose/正确路线）：当前30 intents=20 NAV/6 PUSH/4 CLIMB、27 anchors，PUBLIC_DECLARED_MAP/PUBLIC_EFFECTS已同源更新。只表示有限候选；选错当前support/缺源12N/关联/原required placement/typed owner仍拒绝，不开放任意连续XY／任意高度，也不添加.2平台PUSH。现接线仅**一次真CLIMB→NAV**，后续动态NAV/下一CLIMB source链与static/40cm、高台完整终点尚未接通，不能把本次接源称整链或原.2 NAV→PUSH缺口修复。

同阶段纠正一个source probe语义：未来NAV goal未选定时，不能把“当前base XY”误当未来goal而额外强加.35/.3 goal-margin；未知goal只以私有矩形中心探针核该表面存在合法目标，真实base仍须在原source region、4脚/所选contact12N/足高等原条件。**真正选中的公共goal仍由原factory/constructor/arrival核原margin**，不降低原门、不把中心探针作为planner输入/控制目标或可行路线。

新8项明确mock integration＋2个private old-owner/context新增回归，连受影响factory/driver/公共目录/entry/source/adapter共79项软件检查（同套两端，不是158试验）。初次旧“方法指针完全不override”静态assert失败保留：现在只为selected NAV包context，原Task completed-witness implementation本身未改；新增原路径delegation与新context清理检查，不用改安全expected遮掩。实际Runtime/Actor/physics/API/source-read/NAV尝试仍0；原19/25已closed组件不借zero或重开。

> 同阶段source自审修正：构造完成／仍在旧CLIMB边界待装配，不等于新NAV已installed/entered。report现分native_NAV_constructed、constructor_pending_at_source_boundary与实际active_native_NAV_owner，后者核executor当前session/owner/skill/entered/时钟/非failed。原12项＋新增pending/active回归共13项；旧source481ee5c未实际运行，此修正不改任何物理结果。

## 2026-11-16：typed live CLIMB→原NAV adapter源（尚未装入factory/目录）

新增`climb_nav_adapter.nav_class`／`make_live_source_witness`默认OFF。它不是把上一版只读Observation直接加入NAV的accepted类型：新`LiveClimbNavSourceWitness`必须消费**同tick真CLIMB source观测＋保留的原成功PUSH placement/NN/STOW_VERIFIED/当前required geometry**，构造私有SceneRegistry view（原objects/goal不变，仅增唯一source surface），持两个原实发global18参考、原guard和软硬limit交集；不是cold Capture/failed-PUSH/HOLD。

原RegisteredCompactNav仅两个source site做精确可逆变化：accepted tuple显式加该新live类型；contact guard给**其真实source对象**entered refs，仍原forbidden-body逻辑。原NAV `update`／Actor／`command`／`after_step`／protected arrival／report全原样继承，原world/FIFO/history/goal/effort/rate/frame检查不删；Reach原H/新treatment因子也不变。不猴补原模块或改Actor权重。

**交接生命周期**：constructor前只认原same-tick succeeded CLIMB；只许一次构造，失败撤销。constructor完成后，只有真正安装且entered的原NativeOptionSession/RegisteredNavMachine、exact native-nav owner、原executor/current issued tick才可继承contact authority，别的owner/failed/expired/旧source重放均拒绝。源placement当前几何继续过原gate，不发明放宽的drift阈值。NAV完成边界再核所选箱实际4脚法向≥12N及原height/footprint/goal margin，原arrival/stow继续必须通过。

**不能把站稳12N门错套成NAV全程四脚不离地**：原NAV是有摆腿的步态，入口／arrival保四脚12N；active gait由实际新NAV owner及原controller/guard/contact/effort/footprint约束，不继续用已过期的旧CLIMB stopped-pose当活动owner，否则会人为禁止原NAV走路。此处没有降低原入口/成功门，也没有拿新类型证明原policy可靠。

调用方应使用返回witness的`witness.nav_type`（与其精确类型seal同次生成），不能再另调nav_class生成另一type。**当前还未接V4 factory的source resolver/选中NAV构造、outer contact authority和同support公共NAV目录**，所以不是可执行handoff资格；下一步须把内外guard及query/witness/dispatcher同步接上，不能仅让某个inner guard放行。新12项只类型/phase/one-shot/源码可逆及原方法identity的SOFTWARE fixtures，未构造任何真实NAV/source或调用Actor/physics/API；Data仍须新准确程序必要资格。static/40cm/完整高台终点与WM bootstrap未因此解决。

## 2026-11-16：原CLIMB真实终态的NAV-source必要证据观测（不是handoff准入）

新增`climb_nav_source.read_actual_climb_nav_source`默认OFF，Data实际guard后只接受**当前已成功/entered的原NativeOptionSession、RegisteredClimbMachine、ActualClimbSupportWitness**，核同世界model/data/FIFO、selected private option/opaque/body ID与registry。新driver只在真实CLIMB succeeded receipt边界调用，观测PRIVATE evidence，不发控制命令，不喂VLM/WM。**还没有把它接成原NAV可接受witness，也未改变原support/contact gate或宣称CLIMB→NAV已打通。**

来源不是“按终态姿态补两个命令”：原executor的first_command_time/previous_tick/current200Hz时钟、entered/session归属、原session.last_two的两个finite global18位置参考、最后一个与真实r.last.position逐值一致均核，初始化重复seed/过期/别的session拒绝。保原native CollisionGuard实例的真实sim别名，读原robot软限位与硬限位交集，不重建cold capture/failed-PUSH或改p.soft_limits/原Actor/增益/FIFO。

从实际选中box geom、四个实际foot body/geom和**mj_contactForce的法向世界Z投影**，独立核每脚在该目标箱顶≥12N；总foot force够大却脚还在地面／其他箱／侧墙摩擦不算。复用原NAV四脚高度/矩形/12N/goal margin谓词。私有SurfaceSpec提议名`climb_nav_source__<object>`避免SceneRegistry object/surface同名碰撞；**不写registry、不扩NAV目录、不更改公开声明**。原CLIMB stop success但下一source不足时只记necessary_source_ready=false，不把原CLIMB回执改失败。

该类型故意不是Capture/Arrival/PushStow，没有伪装成原NAV `.validate`接口；只读样本**下一物理步即过期**。后续真正typed-owner bridge/原NAV constructor/guard与外层contact授权仍须准确实现并新程序资格。新13项只pure predicate/来源接口/12N、实际选中contact vs total load、side contact、source ref、history与expiry的显式SOFTWARE fixtures；必要实际reader/原CLIMB/下一NAV均未调用，不能冒新物理成果。

## 2026-11-16：首次主运行前明确旧共同H与本次新后继优化，不削弱C

已消费Reach `V4_PREPARATION_FACTOR_ISOLATION_CN.md`的源码风险：上一版driver原7 helper中的installer在所有arm都装旧Reach H，不能把A/C/E的“本次新优化OFF”字幕误写成所有历史算法kernel都0，也不能为了字面0删除共同底座、削弱完整C。**本组当前决定保留原来已选的legacy-common H，五组相同；它不是此次B−A/D−C treatment。** 新后继优化仍只B/D开，E规则不调用VLM/WM/新优化。精确定义与视频字幕见`PREPARATION_FACTOR_POLICY.json`；尚无五main，没有把旧组件或未触发callback说成已污染/已优化成功。

新`factor_scope.install_legacy_common`在fresh task0显式接`arm`，核真实method adapter的`.enabled`因子（E精确原RuleBaseline）、非fixture及同一journal；不能在capture448步后换因子。全部native stow aliases先原source/check/globals预核，任何已有callback或别名漂移都拒绝，不移除hook伪装OFF；原callback身份guard保留。driver末尾不再把旧always-TRUE installer覆盖回来：只借6个原capture/writer/guard方法，旧installer仅保源码核查，不作为实际方法使用。

保持同一个原v2 binder/原有限DAG kernel。只用原binder**同一字节码/默认值**的私有globals副本，把`optimize`引用包为证据计数；Reach原module/globals/kernel和native源不改，原capture/queue/selected-view/FIFO/goal/全路径/4s recheck和原返回/异常/args全保留。legacy H尝试在调用前记录，完成/异常/提出path变化分别记录；有尝试无完成保持UNKNOWN/censor，不补0。旧H events明确标legacy，B/D新selector events另计，A/C/E新selector事件拒绝；**choice事件数不是实际kernel调用次数，提出waypoint变化也不是实际命令变化/任务收益**。所有真实计算/执行开销仍进入各arm从t0账本。

构造新driver需额外显式`arm='A'...'E'`，原method与native使用同一journal对象；这是未执行的新source，不热改27或25旧program。新增11 metadata/private-namespace专项＋2个受影响driver接线回归两端核，不调用真实kernel/Runtime/Actor/physics/API；没有因本策略声明完整cost provider或整链成功。旧19/25组件仍closed，27/本版均不借zero。CLIMB→NAV/static/40cm/高台终点和A/B真实WM bootstrap缺口仍独立未解。

## 2026-11-16：V4 live observer／selected judge／原200Hz loop已接（source component，非任务准入）

新增`live_driver.driver_class(source_root=..., enabled=True)`；默认OFF。Data在fresh zero-step qualified cold components/新authority/lease下实例化，传原writer、真实public planner、journal/guard。`step_one`实际走原SupportedCapture命令及记录→真capture后`execution_entry`→原IntentExecutionCoordinator/AinavLoop/NativeOptionExecutor；不是另一物理owner或新world，也不替方法选固定路线。E可传原`RuleBaseline`，A—D须传各自真实方法adapter；本模块不设置／假造VLM/WM/优化身份或发API。

每次public acquisition只取原onboard packet＋resolver当前accepted descriptors，**重建**alias；新帧`[]`不会继承旧left alias，实例歧义不挑最大块。实际发布共同24 anchors／27语义候选（17 NAV／6 PUSH／4 CLIMB）。选中judge先核精确公共目录，再按真实private support／原12N／.16m／.25rad／placement／20cm几何检查，只在需要时发同support原NAV准备；当前画面无关联、源支撑未登记、static deck或40cm均明确拒绝。不读第三视角/private pose作planner输入。

PUSH保原绝对goal→同次原resolver goal seal/private constructor映射。Movable CLIMB使用原完整course **B的front−1.05m固定工程entry**（精确原integrated_course SHA钉住），不是新可调standoff或整链可行证明；远处可先原NAV靠近，实际CLIMB bind仍保原current native-domain门。CLIMB要求选中物体原placement回执及当前required几何，public destination=.20和真正private native hash保留，原同参数检查不删。只记录真实成功CLIMB owner/receipt，绝不把READY／declared height冒成功。

旧driver只复用7个逐method SHA核定、在当前dirty树和云端已提交版本**一致**的原stow/capture/200Hz command-writer/guard函数；不是继承其旧constructor/catalogue/judge/ground终点，也不发布后置shared-prefix dirty。owner guard显式False与异常均拒绝（同样补入execution_entry），不能把False当通过。新增13项严格SOFTWARE fixtures含真正原judge READY/PREPARE/12N边界执行；不调用native camera/Runtime/Actor/step/API。

**仍非完整五组任务**：目前无post-CLIMB dynamic-box NAV、static/40cm或真正高台owner/contact/dwell终点。若未来仅收到final NAV成功，此component会显式报`...no_task_success`，不会调用E的自签完成；full_task_terminal_integrated=false。Data可对其必要新source做独立caller资格，但不能借19-source组件zero或称E已完成，当前不请求五main。原HD视频依旧由Data的actual writer直接采集，本源未实际录制任何任务片。Reach新anchor target8源已读，**本版尚未接其causal query/96×64 association port**；不把192×128 VLM alias／off-grid图／capture冒HOLD或masked0冒实际WM输入，restore1/真实forward0保持。

## 2026-11-16：实际capture之后的共享执行装配入口（未调用native）

`execution_entry.build_after_actual_capture`默认OFF。Data在fresh程序/lease/guard下、真正原SupportedCapture已完成并逐步记账后，可把现成components接到原RegisteredBindingResolver、BehaviorSessionFactory、RegisteredPushAPI、NativeOptionExecutor及上一版V4TaskFactory。**不新建world、不step、不选策略、不创建所选controller、不签完整任务成功**；原helper检查真capture类型/同world/实际issued steps与200Hz时钟，普通`complete=True`对象或零步标志不算。场景须与已确认V4逐内容相同，goal必须goal_deck/.60，不能回退旧ground-only装配。

六份PUSH合同直接由五组共同PUBLIC目录构建原PlacementContract，保持绝对目标、原.11 stop偏置/不可变goal与ground源，旧scene validator不再误消费V4。使用原ActualPlacementEvidence，只记录原NN/STOW_VERIFIED成功回执并复核当前required placement；**不调用旧ground终点wrapper**。

外层contact guard新增的不是“CLIMB被选就放行”：只凭已安装、entered的**原RegisteredClimbMachine**、private option hash/body/opaque/current model/data/FIFO同一性，给该实际目标entered_climb_refs。仍调用原>1N/forbidden-body policy，躯干/机械臂或其他箱接触照常拒绝；不把权限沿用给后继dynamic-box NAV，不给static deck许可。这样后续真正CLIMB的合法脚接触不会先被旧NAV/PUSH-only外层guard错误截断。仍需真实程序自己的必要zero验证此装配/原始流。

新增8项纯软件检查覆盖原6份合同、场景篡改、伪capture拒绝及未entered/不同机器/错hash-body-world-FIFO/contact forbidden拒绝。**不是8次仿真**。完整V4 observer/selected entry judge/200Hz driver、CLIMB后dynamic support owner、static/40cm和终点collector尚未打通，不能用此入口宣布E或五组main准入，不重复旧19-source成功组件。

## 2026-11-16：公开CLIMB→原生task factory接线（软件候选，非整链准入）

新增 `task_factory.factory_class` 默认OFF；显式启用时组合原semantic有限PUSH-goal映射与**原RegisteredTaskSessionFactory**，不改原文件/模块。它接入上一版destination binder，保留原 `RegisteredClimbAdapter.construct`、原 `NativeOptionSession` 和原完成CLIMB witness方法；真实回执仍绑定选定的private native option SHA，公开参数保持DESTINATION=.20。绑定逐一核当前RGBD opaque body与所选PUBLIC `object_ref:upper-entry`、query/source/world/FIFO；不能用另一个同高箱体替代所选对象。新acquisition清空映射，只装配精确选中项，构造失败原永久撤销门保持。

数据端已有同世界runtime/registry/resolver和实际capture完成witness后，构造方式：

```python
Task = task_factory.factory_class(source_root=original_source_root, enabled=True)
climb = Task.destination_adapter_class(runtime, registry, resolver, journal=journal)
factory = Task(runtime, registry, initial_witness=actual_capture_witness,
               journal=journal, push_backend=original_backend,
               placement_contracts=immutable_finite_contracts, climb_adapter=climb)
# 沿原NativeOptionExecutor attach。当前公开图像发布后 begin_acquisition；
# 原selected judge只在current association/entry成立时提供outer/inner，
# 其参数完全相同，仅public identity→current opaque identity改变。
factory.prepare_public_climb(outer, inner)
# bind_batch(原ExecutionBatch)只绑定；原executor选中factory(outer)才装配。
```

**不能直接套旧driver**：本factory明确不调用旧ground-only terminal wrapper；实际高台contact/dwell collector仍待driver消费，禁止因此self-sign任务成功。既有MOVABLE ground→.20路径仅完成源接线，尚无真CLIMB运行；.20后dynamic-box NAV原witness/type/surface/12N门、static goal_deck绑定、.20→.60原20cm能力拒绝均仍保留。旧19-source组件zero不借给此新版，不重开该closed scope。完整driver、共同可行整链、E成功及A—D任务原片仍未完成。

新增15项仅源/MRO/选中constructor的显式SOFTWARE fixture，含public物体错配、参数/预算篡改、过期query/图像、重放、未安装owner/失败构造和旧ground终点禁接；fixture没有真实native/Actor/physics/API调用，**不作为15次实验或整链证明**。

## 已接手的实际实现

- scene.json逐byte保留用户确认V4（SHA6394740e…），没有修改墙、箱体、C对接或0.60m平台追胜。research资产代码已移入本组可迁移目录，不再依赖本机research绝对路径。
- `v4_native_asset.construct_into_native_spec`只准fresh task0/FIFO空的Data spec：先加真实collision goal_deck，再调原complex_scene构造器加墙/三箱，保原robot/Actor。尚无原MjModel编译/zero/world/派发。
- `registry`实际调用选定冻结原SceneRegistry，goal.surface_ref=goal_deck/top=.6；公开投影包含平台声明，不公开private review/正确路线。不能原样套旧ground-only driver/catalogue/终点。
- `elevated_stop_sample_only`仅为私有必要sample谓词：foot Z相对.60、目标XY、每脚12N/速度/tilt原门，并需实际contact provenance的goal_deck引用。ground同XY必须false。**不是完成判据已集成**：仍缺同world原owner证明、三immutable placement、原CLIMB回执、实际contact reader、连续dwell及safe-stop caller。

## 已定位的真实阻塞，不以“高度相似”掩盖

`capability_boundary.selected_climb_rise_audit`只AST抽取当前原SceneRegistry的纯climb_geometry判定，SHA钉住，不导入Runtime/NumPy/Actor。declared geometry只是用于该纯谓词检查，不作为真实感知或控制输入：

1. ground0→箱顶.20符合该原20cm高度谓词；**箱顶.20→平台.60的.40增量被同原谓词明确拒绝**。这是选定完整v6/283当前registered路径的边界，不声称所有其他仓库/技能绝无40cm能力。不能把常数.2改成.4/降低门后称原技能资格。
2. 原`RegisteredClimbAdapter.bind`还要求当前RGBD关联映射到registry.objects中的body；goal_deck是static SurfaceSpec，不在可移动object集合。加surface registry本身**不自动打通static-deck CLIMB**。把静态平台伪装freejoint箱体或用静态GT代当前关联都不可接受。
3. 原ground-only TerminalStop核foot Z≈.022，不是高台.622；旧NAV/compact support owner、CLIMB exit→后继owner也必须逐段核实际适用域，特别不能宣称旧.2后NAV/PUSH站稳缺口已修。

**主运行前的最小方案供共享设计决定：** 若坚持当前20cm registered技能，不改Actor/原门，需一个真实0.40m中间支撑，把高度接续变成0→.20→.40→.60；它改变已确认布局/原两段预期，必须五组共享、在新主运行前明确确认/重新冻结，并另核static-surface association/owner桥。这里**没有加平台或改V4图**。另一方向只能先找出已有准确40cm原技能/权重及真实接口/资格；没有证据不能宣称已支持，更不能擅自训练。

## VLM/WM身份与后续实现

- 原AINav应复用冻结`AinavPlanner`的object/skill proposer、tree evaluator、advisor/arborist与replanning，不换成固定脚本或API0有限搜索。Reach负责A/B现有WM推理与B/D同一优化；此包尚未实现四个方法adapter，未调用WM/VLM。
- **用户已明确本轮使用DeepSeek，provider疑问关闭，不重复索key。** `VLM_PROFILE.json`复用本机既有TLS官方endpoint/deepseek-flash图像模型配置，原DeepSeekBackend及RoleRunner/原AINav树保留，旧sol_gateway profile不用于新V4。只接受既有受保护的进程环境DEEPSEEK_API_KEY，不把聊天密钥写入代码/manifest/argv/日志，也未跨组传明文。当前未构造backend/发API，未声称用户提供的密钥已注入计算进程；未来在Data预冻程序的正常模型身份资格中验证实际served model，A—D同版/同采样/预算，E调用0。
- 新source当前仅资产/必要谓词与准确边界，不能提交五main派发请求或宣称共同可行链。下一实际工作：确认选定现有CLIMB能力/最小共享设计修订，继续surface-aware实际caller与终点/已明确DeepSeek的强baseline真实VLM接缝。基础场景/registry代码可先由Data纳入必要新端组件资格；本包不是该准入证明，也不要求额外收件签字。

软件14项只测原纯API/资产与拒绝边界，不是14研究样本或native资格。旧closed A/B/OBS根、bulk在途/冻结程序不改；WM只开放本任务既有推理，不恢复新训练/底层Actor/真机/第二物理owner。evaluation_ready=false、独立TEST0、五箱false保留。

## 新增E规则源（未接完整native driver）

`rule_baseline.RuleBaseline`是真实原IntentBatch/Selection/NativeReceipt接口：按公开initial X/public_ref固定工程优先级处理required placement；当前关联缺失时只试一次已声明approach NAV，fresh仍空则明确UNKNOWN/停止，不盲按时间播动作。PUSH只在真实同intent/params succeeded receipt后计入已完成；所有地面placement后，以公开最小下一高度/到goal的一跳名义距离选CLIMB，平局target_ref；无VLM/WM/B-D优化、私有pose/未来轨迹/存在性路线。每次64上界/fresh query，拒绝/失败不换seed或静默fallback。

这是场景公开几何的工程规则，不冒通用规划或最优策略；不使用V4主运行后果调优。当前.2→.6会按同原20cm域明确停止，static-deck/owner/完整终点尚未集成，E不能自行签task success。E接口代码存在不等E具备主运行资格，更不把旧API0实验改名E。

## 已补实际deck接触reader与连续停稳（仍非完整成功门）

`elevated_terminal.read_current_goal_sample`为Data实际runtime编写，不构造Runtime/Actor、不中断或改写世界/FIFO：按真实compiled foot geom/body与static goal_deck geom读取MuJoCo mj_contactForce；只把目标deck接触的法向世界Z分量累积到相应脚，其他箱/地面载荷和侧面法向不冒高台支撑。deck实际几何/姿态、原snapshot源SHA、原脚body与global loads也核。私有样本仅供终点验收，不进VLM/WM/优化/E特征，不能用声明高度替代接触身份。显式pair中的foot geom即使contype/conaffinity为0仍按实际contact纳入，不误排除。

`ElevatedGoalDwell`按真实连续200Hz clock/tick维持原.5s必要停稳：重复clock不积时、漏tick重置、载荷/支撑/速度失效重置，ground同XY不通过。它故意没有task complete属性/回执：原同world已成功owner/stow、三immutable placement与真实CLIMB链仍需单独接入，不把这个ready布尔冒完整任务。

新9项仅验证接触算术/顺序/多geom累积/非有限拒绝/时钟和停稳；没有调用实际MuJoCo collector或产生真实接触样本，原生ABI/平台contact动态资格仍待Data自己的新程序。没有因reader代码写好就恢复旧根或放行五main。

## 五组真实共同公开候选与效果声明

`public_candidates.py`导出原SkillIntent目录/declared_map/capability_contract与PUBLIC_EFFECTS.json。五组同序同域：ground NAV只列平台外声明点；高台终点NAV唯一以.60m目标层声明，绝不把平台下面ground同XY当终点；6个地面绝对PUSH目标保原数字、不额外加.11；3个物体与static deck的CLIMB均保public DESTINATION高度，private source support/20cm rise/当前关联仍由native judge建立。原IntentBatch契约与真实E.select已接通软件seam，但不是V4实际runtime caller已完成。

公开效果只列请求的reference/placement/destination和必须原回执，实际exit pose、成功概率、后继成功耗时全部None；合法准备/退出变体尚未原生导出时显式UNKNOWN，不补0、不把G2偏移直接挪来。Reach自己实现共同完整代价provider，本组不替其研究评价；不造WM public60/target8/真实issued-history。

## 当前硬交付目标与并行授权

用户最新明确E规则必须完整实跑成功，A—D各自交完整直接live原片，失败/API或资源截断也留全片；软件checks/示意图/进程exit不替代。E若未成功只报告实际失败阶段并修具体新版本，不能洗旧失败或在原closed root反复重试。五组共同执行底座先资格，正式顺序/策略与源结果前freeze；E后果不能反调其他方法后还声称同一未见对比。

用户同时明确尽量并行、充分利用服务器。仍Data唯一physical owner；AINav不自己开world/改Data进程或锁。新scope可按Data合法隔离lease/CPU/GPU/显存与HD录制容量并发，不是限制为必然一GPU只能一world；已有bulk专slot/CPU与watchdog不能热改。先实测必要own-zero资源，再决定同卡多world是否安全；没有method/native资格不为占卡而启动假任务，不把空闲快照当lease。

## Data现在可直接调用的V4原生资产/冷Runtime入口

`native_entry.compile_static_asset`与`native_entry.construct_cold_components`已接到原完整host真正构造函数，不再只有外部asset callback。两函数默认enabled=False；只有Data传自己的fresh authority/resource guard、原已核common-source/SDK bundle、exclusive output model/new runtime路径并显式enabled=True才进入真实构造。AINav未自行调用、没有获取新lease或启动world。

新入口在**私有globals副本**执行精确原native_construction的同一函数字节码，只换3个明确V4 callbacks：load_scene、fresh geometry构造、registry。旧模块/源/已冻程序未改；原source/SDK核验、机器人/actuator/engine签名、onboard camera ABI、fresh model exclusive发布、Actor/Runtime初始化和capture原门仍走原实现。V4 static deck真实几何和goal_deck=.60 registry不能静默退回旧ground-only scene。源码/依赖逐SHA，原kwargs默认值也保留。

Data可先用**新组件scope（必要zero≤1/main0）**做原生V4 asset/model/camera与初始Runtime资格，GPU0按fresh lease隔离，GPU1原bulk不动；不必等WM/current-query/完整40cm方案才编译资产。该组件不是五组main/E成功、不是旧zero复用，也不放行CLIMB/static-deck/完整高台终点。任一失败保实际诊断/成本，不在原root热修或自动重试。

调用示意（仅接口说明，不是本组已执行）：

```python
from native_entry import compile_static_asset, construct_cold_components
asset = compile_static_asset(enabled=True, source_root=exact_common_source,
    bundle=exact_verified_sdk_bundle, output_model=new_exclusive_model,
    expected_scene_sha256=exact_V4_scene_sha, guard=Data_fresh_guard)
components = construct_cold_components(enabled=True, source_root=exact_common_source,
    bundle=exact_verified_sdk_bundle, model_path=asset['model_path'],
    model_sha256=asset['model_sha256'], expected_scene_sha256=exact_V4_scene_sha,
    guard=Data_fresh_guard, journal=original_journal, actor_device=isolated_device)
```

5项新软件检查覆盖default-off、guard先拒绝、原函数字节码不变/三callback隔离、精确原registry高台与默认scene身份。它们没调用MuJoCo/Actor/Runtime，绝不冒真实compile/zero过。下一步看Data原生结果修具体阻塞，不继续用通用测试数量替代实跑。

## CLIMB destination/source已补不改原回执的私有binder

`destination_climb.adapter_class`默认OFF。它只覆盖精确原RegisteredClimbAdapter的bind：public SkillIntent和真正BehaviorOption仍保DESTINATION height（例如.20），实际SOURCE height从当前已验证owner witness/registry私下取得（例如0）；调用原RegisteredTerrain.climb_geometry，原20cm/.01/current RGBD/唯一registered object/body/旋转/位置门不变，再核target top与public destination一致。原construct方法**原样继承**，原ClimbBinding保存base_height；原constructor本来读该geometry而不把option.surface_height当source，所以无需造shadow params、删same-params检查或改option/receipt SHA。

必须传当前原ExecutionBatch/同一个选中option、current query clock/原图SHA与live source witness，binding前后原world/FIFO不变，并将两种高度/同native option hash写private journal（不进model）。8项新软件检查含：原AINav observe_intent的same-params与receipt-hash检查原封不动通过destination=.20、改回source=0仍拒；.20→.60仍由原20cm门拒、static goal_deck仍因非movable current-RGBD object拒。测试用明确geometry/receipt fixture，没有实际CLIMB构造或actor。

这解决**参数语义接缝的代码**，不是V4完整factory/driver、static-deck binding、CLIMB→NAV owner或40cm能力已经接通。现场调用与资格仍待Data实际程序。Data若已冻结19-member原生组件source/程序b125b188…，必须继续该immutable版本，不把这个后续binder热补进去，也不因更新重跑其组件scope。
