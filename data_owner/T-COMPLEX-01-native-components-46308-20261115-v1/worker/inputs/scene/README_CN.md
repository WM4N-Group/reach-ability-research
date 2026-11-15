# T-COMPLEX-01：新的双绕行/两箱重构真实scene源（实现中，禁止冒已可派发）

这是AINav-owned新场景源码/物理asset，不是旧warehouse review、渲染动画、WM profile或预录路线。原完整v6/283/冻结技能核继续；本包是独立新scene/source接入，当前TRAIN6在途完全不改。Data仍唯一物理owner；不在本机/本组构造world。

## 已落地的物理资产/候选

- `scene.json`固定13×6m围墙场地、两件**原full4 B同尺寸2.4×1.4×.2m/.5kg/底μ.4/足顶μ.8**箱，均在ground。原初始robotXY(−.08,0)、yaw0、seed4301，不需要.2上第二次PUSH、不靠20kg/超高障碍卡基线。
- 两箱初始X1.7/5.4，Y0；共同任务要求两件分别按原verified-placement门完成最终X2.3/6.0，再进入远端ground目标[8.5,9.5]×[−.7,.7]并原支持停稳。不是给某方法额外自由度或手工正确顺序。
- 共用有限PUSH目标：a={1.85,2.3}、b={5.55,6.0}，只能同Y、world +X。每个初始drive包含原+.11 offset后≤.8m；不是侧推/拉回/yaw连续域。短目标为真实中间摆放，不直接冒任务最终完成。两个对称公共waypoint通路在y±1.8，路径应由Reach算法基于同一声明几何/新公开观测生成；地图不含正确路线/对象次序。
- `complex_scene.construct_into_native_spec`是真正原SDK MjSpec构造函数，给原spec增加两freejoint碰撞箱、围墙，保robot/actuator不动；原非任务push_box仅在**第一次step前**放至场外原大ground支持区，避免掉落或20kg规划陷阱。接触pair按原compiled foot body→geom身份生成.8顶足摩擦，不用名字猜测。它不创建/编译模型、不forward Actor、不step，必须Data fresh owner/lease/冻结程序调用。
- `registry()`复用现有`SceneRegistry`的ground实体/终点表示，不偷套legacy C必须在.4的几何。`placement_contract()`直接生成原`PlacementContract`（.02 XY/.01 dock/.12 native settled/原+.11 drive），没放宽门。

## 准确的静态机制与隔离存在性证据

首箱a推到最终2.3时其far face在3.5，会占掉后箱b原world+X approach（front4.2−.58=3.62）的机器人/足底空间；先推b到6.0能保留该次操作空间再处理a。可选短摆放也改变未来入口，不是增加固定NAV数。对象/目标/连接均有共同有限选择，但是否在真实native中形成死局须实测，不能仅凭保守AABB宣布物理证明。

`static_qualification.py`按实际asset矩形、声明保守footprint/clearance、有限同向扫掠与visibility graph做**隔离名义存在性枚举**，不手写成功DAG。已找到名义共同可行解，并测得a先最终放置后b approach名义受阻。该证据只在本组PRIVATE qualification manifest，不在public_task/给策略的asset里；在线方法不能导入其witness。它不是MuJoCo碰撞/动态安全/成功概率、A/B运行或原生可行性验证。Footprint .45+.035是开发保守假设，未测误差界。

三个有效选择机会需在真实决策轨迹中核：先对象、该对象短/最终目标、连接南/北通路（后续仍需另一重构/最终连接）；不能仅靠声明计数就通过G5。贪心与前瞻策略由Reach用同候选/同观测/同预算实现，**本包没有任何强制失败A或人工答案B**；双方都成功/失败也保全结果。

## 第二阶段已实现：真实native构造入口、query seal和原owner终点

- `native_construction.compile_static_asset`显式default-off；Data新preflight冻权威/拿lease后传实际guard，才从原SDK PushBridge零步spec调用本场景、编译新MJB。复用SHA固定的原robot/engine signature核函数逐组件对比，原robot/actuator/engine必须同签名；新模型的offscreen≥960×540在任何task Runtime之前固定。MJB用exclusive no-replace发布到远端，SDK148成员原verify，不本地下载/不覆盖旧模型/不forward Actor。
- `construct_cold_components`复用SHA固定原`registered_runtime.construct_cold_runtime`及真实原SDK auxiliary calibration/支持初始化，seed4301/原STOW_ARM/显式CUDA；返回同一Runtime/registry/原onboard observer/SupportedCapture。没有伪造failed-A owner。**capture尚未完成**，Data的真实200Hz循环必须执行它的原command/after_step并记账，`completed_initial_witness`才接受原ActualCaptureWitness；zero-step/假complete不能准入。
- `build_common_execution_after_capture`在上述真实支持见证后接原RegisteredBindingResolver/opaque RGBD关联、原RegisteredPushAPI/BehaviorSessionFactory、同world common factory/NativeOptionExecutor与所有registered objects的接触检查；未选箱接触原>1N拒绝、selected-target native guards仍在。原factory NAV/owner转交与两阶段PUSH/stow不改。不是恢复旧五箱失败profile或任选其几十个开关；当前TRAIN/原发布模块完全不改。
- `multi_goal_factory`修正**实际每query**多目标：构造时四个原PlacementContract按自身内容SHA冻结；从原resolver真的prepare出的每个option.goal-array seal建立一次同query/object/goal-seal→原contract映射，query重复安装/旧owner仍运行/错contract拒绝。原typed query/opaque-body/model/data/FIFO/support/hash检查可逆保留，并再核实际native `[1,3]` goal XY等于该contract原drive XY（原1e-6核验口径）。不能提前用nominal数组伪造未来native seal，也不把whole-global contracts来回热改。
- `terminal_stop`不发明一个通用ground控制器：只收**真实original NAV succeeded session/witness**，复用源SHA固定`RegisteredHoldMachine`继续同一原arrival owner/guard，最多2s做私有任务验证。原两箱placement必须各有当前executor实际succeeded边界/原NN/placement/STOW_VERIFIED及matching receipt；最终仍当前测量满足原contract，不能用预期位置或过期成功代替。四脚≥12N/区域/height/足速/.03线速/.12角速/.03tilt连续.5s、丢sample重置，未过明确失败。不降低旧registry简单几何>3N门来冒本任务12N门。

以上是可调用的真实构造/控制链**源码**，不是本组已构造了世界或完成native资格。仅纯source软件检查可在本机/46308跑；构造入口仍default-off，无Data实际preflight/Model/Runtime/原owner轨迹证据，不算A/B结果。原止动后下一控制接口仍须按新scope资格。

## 下一尚欠：完整新host驱动和源/策略适配（不能跳过）

1. 在Data新程序实际编译/核机器人与scene/GL/记录、own-zero；实际startup/capture→见证→本factory这条链须真实运行/冷核，不把函数存在当原门通过。
2. **实际query/semantic-coordinator driver尚未完成**：同钟原8字段→原visual one-to-one/公开alias→两个absolute任务意图，current source/live pose只在executor私域判entry/prepare，不能把private approach或body pose喂策略。每个prepared option/原goal seal与immutable contract先封后选，NAV前驱准备仍经原技能；不得从同名静态目标直接猜entry READY。
3. Reach将同一public task/有限候选/nominal effects接其greedy/UCS core，两臂同地图/时点/费用与真实语义预算。本隔离witness9 NAV+2 PUSH，默认depth4不能假称已够；不得在线读PRIVATE存在性答案，也不得把多段连接/动画改名一原生技能。
4. driver在最后真实NAV成功后接本FinalSupportedStop/两实际placement证据，配对owner/context/cold/原stream收束；共同至少一动态原门可行计划单列资格后才新A/B各一次，失败也保原片，不追胜。

Data已读T-COMPLEX-01任务并准备资源，不等于已接收此版新源码/已排队。当前新scene actual Model compile/动态资格/对比main/原片仍0；不宣称可直接派发/任务完成。

## 原片/技术范围（未来新freeze）

同一预先固定960×540/10Hz live第三视角、两arm同相机lookat/distance/azimuth/elevation，原onboard192×128完全不改；完整母版/模拟tick-time/frame映射/结束/丢帧记录，A/B各1×+同钟并排1×，可另4×预览。禁止历史state重渲染/补帧/拉长先结束视频；旧warehouse不顶替。本包没有录像产物。

首pair预期独立新DEV A/B各main至多1，先资格后冻技术上限/预算/执行顺序，失败原片也发布；不改布局追胜，不热改当前TRAIN的240sim/watchdog。批量100/≥10有意义组是新总计划目标，不把本scene或重复frame凑独立组；WM/底层训练/真机不开放，evaluation_ready=false/TEST0/五箱false保持。
