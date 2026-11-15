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

## 已实现一个确切执行接点，不伪称整个host已连接

当前`RegisteredSkillSessionFactory.prospective_push_contract`只按object查一个固定contract，不能同时消费同箱两个目标。新`multi_goal_factory.factory_class`默认off，显式true才基于**原源SHA2da2c075…**生成仅该方法查找key的有界派生：

```
(object_ref)  ->  (object_ref, SAME option.original_push_goal_sha256)
```

原exact query/opaque-ref→registered body/model/world/FIFO/support与contract hash保护完整保留，变更可逐字逆还原。新caller需在只读query preparation阶段为每个真实prospective native goal array产生原seal，并建对应原PlacementContract；factory只消费真正选中的option/controller。两策略共享该extension，旧发布模块/当前TRAINworker不改；这不是绕original goal seal或允许改世界目标。

## 仍必须完成的真实接线/qualification（不是新增经济/回执门）

1. 新scene fresh Runtime的**真实原SDK startup/capture支持witness**要接现有同world NAV/PUSH factory，不能伪造零步owner、偷用旧failed-A前缀或把旧五箱runner的一堆profile开关当本包资格。
2. 新caller接上每query两个目标的prospective goal/contract seal、本包factory、当前RGBD/对象association与动态entry原门；asset/库签名可消费不等actual Host installed。
3. 远端ground终点须复用真实NAV protected-arrival owner并检查任务条件/四足≥12N与原停稳，不宣称已有ground通用HOLD；目前最终支持停稳adapter尚未连接。不能凭到区域或两placement回执就说完整任务成功。
4. Data真实模型compile/robot-signature/SDK/foot friction/自身zero与动态资格，至少一个共同原门计划存在性须有原件；未合格前不派A/Bmain、不预约/旁路锁。本组当前physics0/A-B0/video0。

这四项是当前具体代码/运行缺口，继续实现而不是等critic。已落地constructor/有限目标/原contract extension，不以README或fixture宣布T-COMPLEX-01完成。Reach可并行实现真正同域A/B，Data可据源码核新环境装配；不要求额外AINav消费回执。

## 原片/技术范围（未来新freeze）

同一预先固定960×540/10Hz live第三视角、两arm同相机lookat/distance/azimuth/elevation，原onboard192×128完全不改；完整母版/模拟tick-time/frame映射/结束/丢帧记录，A/B各1×+同钟并排1×，可另4×预览。禁止历史state重渲染/补帧/拉长先结束视频；旧warehouse不顶替。本包没有录像产物。

首pair预期独立新DEV A/B各main至多1，先资格后冻技术上限/预算/执行顺序，失败原片也发布；不改布局追胜，不热改当前TRAIN的240sim/watchdog。批量100/≥10有意义组是新总计划目标，不把本scene或重复frame凑独立组；WM/底层训练/真机不开放，evaluation_ready=false/TEST0/五箱false保持。
