# G2新用途：有限12-main条件critic cohort（v1，采集请求，不是物理派发）

**当前缺项已从“第三source”转为可执行的新用途采集。** Data三源发布 `01e2571a3e5a5ca3244264f9de8219fe6c19518c5176442d728ee067ce7de240` 包含5个closed DEV attempt：4请求链PASS、1前驱PUSH异常；4个CLIMB PREPARE、1未达。全部旧DEV仅用于事前域设计，不能转TRAIN/CAL/VAL。原失败及旧UNKNOWN/基础设施失败费用继续保留。

## 有限问题与固定样本

仅问：**原首次CLIMB PREPARE时的合法公开45D＋候选实际名义偏移，能否在未来新采集中预测原READY与请求CLIMB终点，比TRAIN常量成功score／均值耗时更有描述信息？** 不声称post-PUSH准备能修复上游PUSH，不把短请求链称全课程导航。

| whole-scene角色 | 原registered scene | 新前缀 | 每前缀候选 | 新main上限 |
|---|---|---|---|---:|
| TRAIN | full-4 | left、right | original、lateral_plus_0p04、lateral_minus_0p04 | 6 |
| CALIBRATION | full-1 | left | 同三候选 | 3 |
| VALIDATION | full-2 | left | 同三候选 | 3 |

**最多12新root，每root own-zero≤1/main≤1，无重复seed/reset，无替代/自动扩批。** 此为4个已观察到合法PREPARE的scene-prefix条件上，三候选的最小完整factorial；只有3个scene、每split仅1个，不是12独立场景、不是功效保证。48维/6 TRAIN极小样本，预期可否证，不能据此批准部署。

- whole-scene键由完整原registered case、材料、seed4301、初始化语义及原constructor SHA规范化产生；prefix/arm/frame/reset/新scope/UUID/purpose不改变scene键。同scene全部候选、前缀、失败、未达必须同split。
- 三scene共享原constructor/Actor lineage，且历史DEV结果已曝光。这里仅是**future acquisitions、fit-source-config隔离**，不是未曝光任务/独立TEST或G5盲holdout；不能把同源配置差异夸为独立生成群体。
- **full-2 right不再试。** 它原PUSH卸载FF交集空、未到CLIMB，无successor输入/标签。本cohort明示只覆盖既有5个DEV scene-prefix中的4个已达条件，不将它删除/修成负行，不称full2左右完整族已合格。历史5支4/5链成功和4/5到达，与未来新cohort的attempt分母分表；不得拿新条件成功率替代历史完整链表现。若论文目标要求full2右支可靠性，需另定更早时点/动作/horizon，不能由本模型冒领。

## 现有源如何被真正消费

只用Data现存native runner／原3请求consumer／public observation／journal与当前同stow绑定，不要求新NN表、logger、经济许可或消费回执。

1. full-4/full-2用现有source-owned `registered_layout_conditions_v1` 返回的原protocol、runtime_config、requests与候选payload；source SHA见JSON。full-1用**已成功原独立full1 plan**，原protocol canonical SHA `7492762cbb1b3a268d5a2a7d4d148956a32d4a675e83e1a29bf7099d60e13d55`，C质量1kg/μ.3明示，不能放宽原full2 helper材料guard来冒用。
2. 每个新root在tick0按冻结candidate payload走现有`install_preexecution_choices`→`selection_from_payload`/`bind_to_host`。全程三候选固定分配，不用critic在线选；到first PREPARE再截因果特征，必须在候选controller执行前。新freeze含本协议SHA、用途/角色、精确源delta、三请求、候选、原Actor/SDK、同root zero/main与新lease。旧closed程序不热改/不续跑。
3. 原物理protocol/成功门不为训练改写；新采集用途在新manifest登记。原生420sim cap保持，**外围resource watchdog240sim／2400wall更严**；触达该上限仅resource censor，不作native failure。zero另限180wall；各自aux仍≤10.5sim。原12N/4s/identity/immutable/support/guard/QP/FIFO/CLIMB stop全部保留。
4. 保留八公共字段、原RGBD/45D、原journal/commands/录制、result/cold/ledger/CAS。Data无需产NN训练表。Reach只用现存48槽、原source event、READY/原请求终态构造未来新行；图像几何/metadata/私有pose不入新增特征。raw留远端。

**尚未分配scope/预约GPU/派发。** 本文件与JSON是Reach给Data可消费的固定研究协议，不是本组接管物理owner。Data依已有技术准入生成新程序即可，不需另等研究问题/模型或经济许可。若真实caller不能消费某项，报告那个具体source delta，不能改旧freeze或以新fixture代替运行。

## 顺序、停止和训练

固定ordinal1—6收TRAIN，闭合后立即按JSON检查：至少2个TRAIN prefix组、2个公开proprio状态、≥3成功行及≥1真实**决策后**native失败、source/stream和48槽完整。不满足就**No-Go停在实际已耗数量，不fit，不派CAL/VAL，不换seed/挖失败补类**；未运行行显式NOT_DISPATCHED而不是失败/已花0。TRAIN数据合格才激活引用本协议SHA的训练manifest，真实fit一次；此不可变协议的`qualified_entry_condition_family=false`不能回改成“早已合格”。

模型严格沿已有stdlib logistic300步/lr.1/L2.01＋ridge L2=1，TRAIN-only标准化，常量score/均值基线。不得用CAL/VAL调参。CAL仅3行诊断，不宣称概率校准或置信保证；score .5仅离线诊断。随后按固定次序收CAL7—9、VAL10—12，源绑定/安全完整性损坏或共享基础设施问题立即停，其他字面失败保留并各root不重试。全部12结束即停采集，不自动扩24。

完整attempt成本包括zero/aux/main/未达/失败/censor；未知费仅lower bound。决策未达没有feature/CLIMB标签；native failure只能由决策后原源证据判定，无终态回执则保留缺失；censor不当失败、失败elapsed不当成功耗时。缺测None/mask，不取nearest/后READY帧或补零。按scene/prefix/arm报告成功/失败、到达率、MAE/RMSE、Brier/logloss、失败漏报/误拒和弃权/费用。缺失败分母为None，不是0%漏报。

探索性时间MAE相对TRAIN均值改善门槛事前设为0.100sim s，仅工程描述门槛，不是显著性/精度界。无论赢负都不直接G4部署：一个CAL与VAL scene不足风险认证。本批能产生G3真实拟合或有限否证；**不单凭本受限族宣告G2整体/论文贡献或G5验收完成**，后续G4三策略/G5多决策需新的独立固定协议。

容量按Data当次1.5GiB/root预留，共18GiB，低于所报14root算术空间；不是provider quota/lease保证，不授权占用其他组资源。代码/小协议在本地和GitHub；大产物在46308。
