# Reach：原生NAV前驱条件pilot的后果前分析与退出规则

2026-11-14，接收AINav18:45的现成两条件提议，**不另造采集请求、runner、特征接口或验收回执门**。`CONSUMED_PROPOSAL_PINS.json`固定本次所读源/协议。Data尚无本pilot派发或新结果证据，本文件不是物理资格、入队回执或实验结果。

## 1. 本轮唯一可回答的问题

沿AINav原请求：同full-4/v6/Actor/seed4301/固定初始化，先NAV至原已登记left或right，然后相同绝对PUSH(2.3,-2)→stow→CLIMB。CLIMB准备始终original，left后right，每条件至多一次main，总上限2，不调整原±.15引用、重扫CLIMB±.04或换seed。

**假设：合法原生前驱条件在原PUSH/stow后，可能仍留下当前决策可用的公开状态差异；反面是两条件被该链归并，或差异根本不在当前可用特征内。** 这项只检验condition source，不比较优化器、候选优劣、critic可学性或统计泛化。它不需要先训练模型或消除全部UNKNOWN。

当前AINav已给有界三请求source delta，但Data仍须在新owned程序实际显式消费`max_requests=3`并以exact3原生成功回执验整链，完成新完整freeze/own-zero/lease/fresh资源门。旧worker和closed源不热改。Reach不重跑其7软件检查，软件回执不当物理证据；本分析不构成另一个等待签字的门。

## 2. 唯一取样边界，防止条件标签泄漏

- 定位**真实PUSH/stow完成之后，原CLIMB首次被judge判PREPARE的实际intent-observation**。从新intent/journal/source binding定位，不复用旧query3编号、固定84.430钟、base `_latest_public`指针或nearest帧。
- 必须绑定Host实际query与原`intent_native_execution_bound.physical_observation_sha256`及对应原query文件。实际publisher加pending后的query与base指针不一定同值。
- 若新链此时直接READY、之前失败、query未保存或PREPARE多次：全部按事实保留；direct READY记为`NO_PREPARE_BOUNDARY_ALREADY_READY`，不是0向量、不用稍后的帧补成PREPARE。多次时只按固定“首次”规则，不挑最大差异。首次PREPARE后新观测一律不能回填此决策。
- 正常采集既有public/journal足够。Data仅保原件/source/closure，不用代算特征或研究表，不新增logger/相机/GT采集。

## 3. 两层信息评价，不混为“当前48D已可学”

### A. 现有固定48槽到底有没有状态差异？

本pilot固定同一original候选，所以前2个WORLD reference action offsets都是0。第48槽是采集age，时钟/路径/UUID不同不等于state差异；同packet正常age0也不提供入口变化。**可能承载新condition差异的是中间45个真实proprio值，不是条件名称或额外NAV历史。**

Reach在audit reader中直接按原45D顺序比较q18、dq18、gravity3、angular_velocity3、linear_velocity3，保单位/frame与全部raw逐通道差；各块分别报max-abs及L2，绝不将rad、rad/s、m/s混求一个任意总分。q按原数值报告，不事后wrap角度制造相等/差异。不调用只收ONLINE_PUBLIC的prospective extractor再把本audit材料伪装为online。

- exact数值相同只说明**这个公开表征在这个边界发生碰撞**；它不证明所有隐藏物理状态相同。
- exact数值不同只说明当前两记录可区分；无重复/独立测量误差界时，不把浮点微差称material variation/稳健可辨，更不凭此将`qualified_entry_condition_family`改true。
- 缺槽保持缺测，不填0；实际age/原Clock/source另列，不让其替代proprio证据。status文本、条件ID、query序号、绝对sim钟、declared前驱goal均不进入45D差异判据。

**结构性限制（非本pilot新结果）**：该45D是body运动、关节和投影重力，未含平面位置或heading。在同关节/同静止body状态且仅改变水平平移或绕重力方向yaw时，这些字段本来可以相同。故“前驱轨迹确实不同”不能推出“48槽state不同”；反过来这个碰撞不否证RGBD或合法相对几何具有辨识信息。无需为这一事实新添feature槽或训练器。

### B. 原public视觉中有没有额外名义可辨信息？

固定比较同钟decoded RGB/depth原数组及K/T，分别列shape/dtype/逐元素相同与否；文件编码hash只作身份，不把PNG重编码或metadata不同称视觉变化。然后直接复用原component公开关联/拒绝规则：目标当前component有效像素数、有效depth数和coordinatewise可见点median XYZ原值/差值。无唯一关联/有效深度保持UNKNOWN，不GT兜底，不在这里切换为本组上一项snapped代表点。

若45D相同而视觉不同，结论是**原始公开视觉可区分、现48槽未包含这部分信息**，不是当前critic已经能用；若只有RGB变化但任务component缺测，则仅是图像不同，不冒task-relative geometry变化。此前表面残差/p95诊断不是这些新样本的误差保证，旧GT严禁planner/fit。

## 4. 预定判定与停止，不按结果追加样本

| 观测 | 本pilot允许结论 | 后续动作 |
|---|---|---|
| 两支都到首次PREPARE、45D/任务视觉相同 | 该边界公开输入未留下条件差异；不推所有hidden state相同 | 此条件源对当前表征No-Go，不扩24main/换seed补胜 |
| 45D相同、任务视觉不同 | 当前48槽缺少这部分可辨信息 | 只保信息缺口，不宣布已合格可学；后续若确需采用视觉另以明确新方法问题推进 |
| 45D不同（无论视觉是否相同） | 两次记录数值可区分，独立重复/可靠性/排序信息未证 | 停于有限资格观察，不自动升级域/训练分组或追加成8条件 |
| 一支或两支无首次PREPARE/原链终止/材料缺失 | 原人口未完整观测，区分prefix失败、direct READY、collector/资源问题 | 保2条件分母；不补运行/插值/造零，不给成对可辨结论 |

两支结束或各自原门终止即闭合。数值不同不证明local→full ranking改变：这里每condition只运行original，没有另两候选的后果，**无法据此估计哪个准备候选更优、交互效应、counterfactual success或优化收益**。两条件也不是原24main所需8独立condition/固定组，且默认DEV审计用途；不能拿新训练授权将该pilot自动转TRAIN/CALIBRATION/TEST。后续如获新条件源，仍需真正对应新授权用途的预登记cohort，不扩大本scope。

## 5. 完整成本与失败分母

每条件新zero/aux/main的真实ledger成本保留，主链额外NAV意图的started→真实succeeded、原PUSH/stow、CLIMB PREPARE→READY、PREPARE→成功完整终点分别列，不重叠相加。完整三意图episode与旧两意图108.095s任务长度不同，不作方法快慢对照；更长不是优化更差、更短失败不是优化更好。

FAILED原stop/guard、资源censor、未到决策、原failed receipt缺失各保原语义；成功full time只在真成功时有值，其余None，失败支出单列。Data不需等Reach的结果解释或消费receipt才发布/结束。未派发时不填虚拟scope/结果SHA或臆测新GPU余量。

## 6. 当期可执行状态与不再做的事

已从“完全没有条件source提议”推进到“有当前原生intent/caller来源的两条件资格pilot提议，尚待新owned程序真实消费/资格与资源”；不继续原无来源的24main盲采。用途已确认不重问预算/训练许可，Data唯一物理owner。停止mask/bbox/代表点/像素半径扫参，停止重复空训练入口、旧release审计和owner软件套件。本组已有selector保UNKNOWN/default，不把回退original叫优化。

本文件仅在本组/共享Reach段发布接续入口；未跨chat发消息，不声称Data已接收此新两条件提议/排队。source delta由AINav维护，本组不改他组源或Data worker。dirty/closed/12N/identity/immutable/guard/QP/FIFO/4s/stop和失败账保持，新物理/训练0，TEST0/主要贡献未证。
