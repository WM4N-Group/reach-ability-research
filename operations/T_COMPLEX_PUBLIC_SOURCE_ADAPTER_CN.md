# T-COMPLEX-01：实际公共source已接入模型与原select/feedback接点（仍非原生A/B）

> **2026-11-15新入口：** AINav三箱v2公共source与原scene driver已出现；Reach新增source-bound factory/完整公共catalogue校验及原Coordinator接缝检查。见`operations/T_COMPLEX_01_SOURCE_V2_OWNER_ENTRY_CN.md`。下文v1/三箱仅提议是历史，不代表当前v2仍未实现source；v2动态资格/A-B/原片仍未过。

已消费AINav `development/complex_dual_route_v1/PUBLIC_TASK.json` SHA630016fe…、FINITE_PLACEMENTS SHA575191d2…；部署source32efd758…。只读这两份公共文件，不读/import private static qualification、存在性路线、scene.json或真实私有pose。Data已14:00确认任务/资源准备（owner intake402ba333…），但场景整机/方法包未ready，未排队/派发/录像。旧“未确认收到任务”不再作为现状。

## 新实现

- `complex_public_model.py`直接把source四个同向PUSH目标、两箱尺寸/声明位置、墙、公共waypoints、共同远端goal投到同一有限模型。两策略都用相同visibility最短路、包络膨胀AABB、箱体扫掠检查与名义NAV距离＋箱平移距离，不硬编码对象正确顺序。只能+X、含原.11 drive≤.8、原.58 approach；都是模型必要条件，不是动态资格/成功概率。
- 初始化机器人reference(-.08,0)是source README公开实验先验，不是私有当前base测量；包络半径.45m是两臂共同固定名义假设，**不是已验证foot/arm/tracking界**。没有读取private qualifier的半径/正确路线。所有节点都是nominal intended-placement/reference，不能当实际world状态。
- `complex_intent_planner.py`实现原`select / reject_intent / observe_intent` seam：仅接原public IntentBatch，拒private ExecutionBatch；逐新batch只选实际存在的唯一NAV/PUSH option，不制造goal/opaque-body/ref或跳过缺失waypoint。保持原Selection/Primitive类型，匹配原实际interaction/receipt后才推进nominal context；失败不推进预测状态，拒绝/未知fail-closed。没有world/Actor/锁/数据写权限。
- terminal NAV成功或预测到goal都**不等完整任务完成**。必须source原两/all placement＋远端区域＋ground protected-arrival/四足12N/停稳共同verifier给原证据ref，才`confirm_original_task_terminal(...)`。没有通用ground HOLD凭空替代；该source terminal adapter仍需AINav真实接线。
- 所有route waypoint/动态approach与多个goal须在共同source语义catalogue里注册。缺/重名会明确报错，不让Data代造算法。NAV declaration浮点同值匹配仅1e-12用于.5-.58与-.08的表示差，实际选原option，**不改native参数/目标容差，不是nearest sensor/frame**。

## 实际公共source的CPU结果及限制

`evaluate_complex_public_model.py`在实际公共几何上调用相同A/B核心，fence禁private qualifier/存在性文件/scene/模型或world。可重复得到：A名义任务未完成，B名义可完成。**这只是public模型的counterfactual诊断，不是A原生失败/B原生成功，不是视频或Scene动态可行证书。** 不把模型预测状态作为live观察反馈。

更重要：当前adapter成功的v1模型只有**两次非强制重构选择＋一个强制final NAV bundle**；第三个bundle不自动算第三个有效选择。不能凭9段NAV/11技能或宏动作图达到T任务/ G5要求。源码默认4深度已明确为decision bundle，不是4个native语义动作；真实请求数逐记录，物理全任务budget仍需source/Data冻结。

这不是断言v1整个scene不可能有第三选择：源可以给出真实有后继影响的在线对象/目标/连接分解并证明，不能拿NAV padding顶数。另给**可选**`protocols/2026-11-15/T-COMPLEX-01-third-choice-proposal/`：第三件同B prototype/ground/+X有限目标、适当延长场地/远端点。通用模型不写正确顺序，三件目标必须都满足；名义成功路径有3个非强制重构选择。**它只是Reach公开几何提议，原生asset constructor/资格未实现**，不能冒AINav已交source或要求Data运行，不热改v1/当前TRAIN。

## 准确剩余／接线

1. AINav fresh原SDK startup/capture/scene constructor→共用dispatcher、目标seal＋原factory、最终ground原protected-arrival verifier接线/资格；公共waypoint/对象目标到真实原semantic option目录映射。
2. Reach将本seam直接接到其新host，不让Data写方法；确认实际≥3有效选择，不把预测/被迫动作数当证明。若采用第三箱提议，由AINav先独立新asset/source版本与资格，不覆盖原v1或追原生输赢改场景。
3. Data沿原owner、真实zero/lease/限额/母版准入A/B各一次；当前旧TRAIN生命周期仍原锁。HD第三视角与各1×/同钟并排还无本组已消费产物，不能填“已完成”。

当前方法8个定向算法/语义反馈软件检查过（含拒private batch/缺waypoint/失败不假推进/terminal不偷判），不是物理或8研究数据。T native main0、视频0；标准搜索机制原型不冒新算法。当前critic TRAIN另按原2f82530d…完整源门训练，不喂本任务的私有存在性路线/旧DEV。
