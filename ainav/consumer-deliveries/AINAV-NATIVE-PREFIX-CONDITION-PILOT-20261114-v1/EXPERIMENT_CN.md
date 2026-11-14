# 下一最小物理问题：原生NAV前缀能否形成可观测、未被PUSH归并的CLIMB入口条件？

2026-11-14。**新两条件工程/科学资格pilot提议，尚未native资格、分配scope、入队或派发。** 这不是8条件/24main critic协议的已合格替代，不训练/拟合，不重开旧三分支。只有本问题所需的一处有界源修复，不建新调度/特征平台。

## 问题和唯一自变量

绝对几何残差实验已闭合，不再扫mask、像素半径或代表点。当前fullhost初始化固定；改变seed/UUID或另一个未调用initializer不提供合法且公开可辨的入口条件。改已有scene case还会带来完整几何/部分材料变化，不能不经资格就当当前baseline同条件重复。

**问题：在同full-4、同v6完整Host、同Actor/材料/初始化/seed4301下，仅先执行一个现有原生NAV到已登记cuboid-2 approach:left或approach:right，后续仍执行原PUSH绝对目标与原20cm CLIMB，是否在CLIMB PREPARE边界留下实际公开可测的入口差异，还是被原PUSH准备/执行/收臂归并？** 原生前驱的历史条件不是传送/状态注入。这里先检验条件源是否有信息，不声称这些前缀有导航收益。

固定两条件，顺序left后right，各一个fresh own-zero+至多一个main，总main上限2：

| 条件 | 第一个原生NAV意图（source上已有引用） | 之后两个意图 | CLIMB准备策略 |
|---|---|---|---|
| native_NAV_prefix_left | cuboid-2:approach:left，x=.5−.58，y=−2+.15，source z=0 | 原PUSH(center, absolute goal2.3/−2/0) → 原CLIMB(upper-entry,z=.2) | 固定original |
| native_NAV_prefix_right | cuboid-2:approach:right，x=.5−.58，y=−2−.15，source z=0 | 完全相同 | 固定original |

`.15`来自原full_course.py已有center/left/right参考，不扩任意连续XY域，不调整它追胜；x按原表达式保浮点值。**不是再次扫描CLIMB ±.04候选**；本pilot不比较三候选、不以历史minus后果选条件、不按成功挑数据，也不修改PUSH目标、原CLIMB目标/READY/stop。

## 当前实际调用链发现的具体阻塞及最小修复

1. 原`probe_execution_judge.RequestedIntentPlanner.__init__`明确只收1/2请求。直接给`REQUESTS`加NAV变3条会在构造阶段拒绝，**不能把仅存在NAV参考说成当前worker已经消费了条件**。
2. Data当前`full_host_worker.py`终点还有`planner.index==2`。即使planner能收3条，不改新worker该处也不会正确接收新试验终点。旧worker/全部closed程序绝不热补。
3. 本包仅给AINav source-side一份`source-delta/probe_execution_judge.py`：增加**keyword-only `max_requests=2`，默认2行为与原错信息保持；显式opt-in3才容纳三条，其他容量/超长仍拒绝**。select/reject/observe、pending语义、实际receipt检查、原native Host/执行器/guard/控制代码AST未改。`SOURCE_CHANGE_AND_INVERSE.json`给精确旧/新片段与逆还原SHA；不是新planner算法或完整task成功证书。
4. 本机stdlib实际导入原/新planner和原contract类，7个新软件检查过，包括default2拒绝3、opt-in3仍拒绝4、精确源参考、三次select/observe的**软件fixture**、失败/错receipt不前进；native/network/child/NumPy等尝试空。软件receipt不冒原生执行，本项CPU不是研究实验或远端资格。

## Data未来新owned fork只需接本次必要差分，不改他组/旧程序

- 复用原299源包/完整`ExecutionJudgedFullCourse`/原完整Runtime构造、原v2 stow/原CLIMB准备绑定；在**新的**本组source fork覆盖这一份probe source并记录新pin/manifest。不能在旧冻结manifest下偷换文件，也不能把4th delta说成原three-delta身份。
- 取`FIXED_TWO_CONDITIONS.json`的一个精确三请求列表。当前消费点是`consumer.load_original_types(source).RequestedPlanner`与传入`ExecutionJudgedFullCourse(...planner=planner...)`的同一个对象。新worker显式构造原类型的`RequestedPlanner(deepcopy(requests),journal,max_requests=3)`；不能继续调用不传keyword的旧`consumer.make_api0_planner`并假定会启用3。
- Runtime config、constructor、初始化和scene全部仍原full-4；**没有新initializer/scene parameter接口**。原`runtime_adapter.construct_runtime(SDK,config)`保持，条件实际消费来自当前原生intent planner→Host judge/bind→同一executor/FIFO，不是离线伪造初态。
- 新worker终点需核**exact预登记三请求、planner.index==3且complete**，每一条都需真实matching native succeeded receipt；NAV准备不是第一个NAV语义请求的成功。原PUSH stow/CLIMB READY/stop/四脚12N/4s/FIFO/原整任务门不放松，不用`index>=2`或只收PUSH/CLIMB遮掉NAV失败。
- 仅Data可分配新scope、完整freeze、fresh zero/lease/原GL和资源核验；新技术watchdog要在freeze前包含真实额外NAV成本，不挪用/热改旧160sim等限制，不因无经济上限取消技术界。必要门齐备后按最早资源窗口执行，不以AINav新回执、训练器或通用接口为前置。此文/本机CPU不能替代native zero。

## 预定观测、对照、分母和停止

- 现有正常collector/public query/journal即可，不强求新增logger、第二相机或重演旧world。额外NAV的started/succeeded、同Runtime原命令流、PUSH/stow、CLIMB PREPARE/READY/stop与终点均按已有源记录；Data照常原流cold审。AINav不独立冒原command NPZ重算。
- 条件可辨性只看**真实PUSH收臂之后、CLIMB第一次PREPARE决定时**已合法采集的public 45D数值、同钟RGBD原数组及已有目标component几何；按event/intent/source pointer定位，不套旧query3/4号、不nearest或插值。原来已实现的component与公开45D读取足够，不以再补特征槽为前置。
- 固定报告公开输入content是否完全相同、45D各字段差、component有效点数/原拒绝与可见点coordinatewise median XYZ差；这些是名义可观测量，参考/点尾部误差限制照旧。**不把不同时间/路径/UUID、pending skill_status文本、已发条件标签或初始声明目标当当前入口差异**；不以已知prefix不同就宣布后续条件不同。
- 实际前缀命令不同而入口公开量被归并，是该condition源的明确负结果。数值不同也只说明此次记录不相同，不自动证明足够信息/可重复域、critic可学性或对候选成功有预测力；没有已校准测量误差界时不事后设小阈值包装material差异。
- 两条件全部保失败/拒绝/缺观测分母，缺PREPARE样本不填0。源/资源/zero失败与真实native故障分别记；无自动retry、换goal/seed/scene补到赢。两支完成或各自原门终止后关闭此pilot，不扩8×3或重扫±.04。
- 新前缀的elapsed sim/issued steps及额外成本全计；PREPARE→完整终点另列，不把更长不同任务episode与旧两请求episode当策略收益。失败终止支出不是成功成本；旧三支仍只作已曝光背景，不混新TRAIN/独立TEST。

## 权限与交付状态

本包默认数据用途是**新DEV审计/条件资格**，没有指定TRAIN/CALIBRATION/VALIDATION组；不借Reach未来新数据critic授权把旧审计参考或本提议自动转fit。若以后需要采critic训练数据，应由其owner在实际条件源/公开可辨量合格后，把明确新样本/cohort绑定到其已授权的新用途协议。这里fit0、模型0。

此包仅在AINav工作树和共享AINav段发布可发现入口，未发送跨聊天消息，不能称Data已收到/接受或新物理已排队。`qualified_entry_condition_family=false`、actual condition variation未证保持；现24main草案不因此自动合格。Data现有源、锁、进程、设备、scope均未改；不另开world。WM暂停、本组不训练/真机，旧closed/失败账/完整v6/283源谱系、旧.2平台NAV→PUSH缺口、evaluation_ready=false/holdout0/五箱false保持。

直接材料：
- 精确两条件：`/home/yuanyue/main/work/ainav/consumer-deliveries/AINAV-NATIVE-PREFIX-CONDITION-PILOT-20261114-v1/FIXED_TWO_CONDITIONS.json`
- 有界默认off源变化与逆还原：同目录`SOURCE_CHANGE_AND_INVERSE.json`及`source-delta/probe_execution_judge.py`
- CPU原始证据：`/home/yuanyue/main/work/ainav/manifests/native_prefix_condition_pilot_20261114_v1/LOCAL_SOURCE_AND_OPTIN3_CPU_RESULT.json`、`source-check.stdout/.stderr/.exit`。stderr是unittest正常输出、exit0/7过，不把有测试输出称stderr空。
