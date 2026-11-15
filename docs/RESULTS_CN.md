# 关键结果与证据边界

## 2026-11-15 13:04：新用途12程序已真实冻结、首TRAIN已派main；修复TRAIN先fit与heldout门的时序循环，不改原协议

- 已在46308只读核Data新cohort12个freeze SHA、每个plan和实际prepare/worker/installer的freeze成员：原2f82530d…协议、whole-scene split、condition、assigned arm、attempt ordinal和new-purpose一致。首TRAIN full4-left-original程序b738125e…，13:04:02 H已CAS_DISPATCHED_MAIN、own-zero/main各1；其余11未派，CAL/VAL被TRAIN门硬阻。静态匹配不冒native成功；首main终态未消费，不改Data源/进程/锁/authority，不重发。
- 发现真实G3软件时序阻塞：原训练入口要求三split齐才fit，但原协议要求TRAIN6先fit才采CAL/VAL，形成循环。已加TRAIN-only一次fit及CAL/VAL frozen-only评价：保全三scene map/全部阶段attempt、原class/state/成功≥3/后决策失败≥1门；later heldout拒进earlyfit，完整TRAIN snapshot/模型hash冻结，评价不refit/不导出第二model。有限协议禁止误用legacy full-cohort重拟合；未改变原协议SHA、样本/模型/阈值，不加采样合同/预算许可。
- 新8定向回归+原23 learner回归在本地/46308各31过（非62独立研究样本），仅软件，不是科学数据或模型训练。真实training rows/fit仍0，原false资格协议未回改；六TRAIN真实闭合后才决定derived training manifest或No-Go，不挖失败补类。下一消费首新用途原件、按既有reader精确绑定first-PREPARE并取原48槽与真实终点，再收完整TRAIN门→一次fit或有限否证，CAL/VAL只用该冻结模型。
- 入口`/home/yuanyue/reach-ability-research/operations/G3_TRAIN_FIRST_FROZEN_EVALUATION_CN.md`。用户目标G3—G6未完成，原DEV/GT不得fit、旧dirty/closed/原门/上游失败与未知费用/独立TEST0/主要贡献未证保持。

## 2026-11-15 12:44：三source DEV原件已消费，full-1真实PASS；新用途有限12-main协议已固定（未派发/未fit）

- full-1-left程序3b5e9d4d…119.345sim/23869commands，12:22:34 CAS PASS closed，正式2bae0f2a…47成员与三源01e2571a…5成员/child pins逐SHA核。原9流cold过；zero+aux共132.355sim/814.418296ledger wall/175664393bytes。first-PREPARE原Journal/Observation绑定95.250→READY13.495→原请求CLIMB终点24.095sim，非far-bank整任务或优化收益。
- 在46308只算新full1帧一次，旧full4/full2 proposer重跑0。full1原component4104有效pixel；同left对full4/full2，q max差.231462240/.046942592rad，名义median L2差114.543489/11.484963mm；decoded RGB/depth异、K/T同。各自body frame的名义差，不是WORLD运动/object pose/误差界/稳健可学性或收益，误差boundNone。raw45D/数组留远端。
- 历史完整5attempt/3registered scene：4链PASS/1前驱PUSH异常、4first-PREPARE/1未达；5scope598.515sim/3722.513041ledger wall/highwater和805949466bytes，旧UNKNOWN/启动失败另保。full2right未达不能作CLIMB负行，closed不重试，不再泛称缺第三source。
- 已发布`/home/yuanyue/reach-ability-research/protocols/2026-11-15/G2-new-purpose-finite-cohort-v1/FINITE_COHORT_PROTOCOL.json`，SHA 2f82530d1f880892c631c7b62cc79bfbd72d57e1b369faf99f542d02d4a53eda。固定full4两prefix TRAIN6/full1-left CAL3/full2-left VAL3，三候选各一次、whole-scene/祖先同split，最多12新root/own-zero/main，无seed/replacement/追失败。full2right原失败保全，明示新条件域仅4/5已有DEV context；不能凭缩域宣告完整族/全链/G2整体验收。
- 这是DEV-informed、每split1scene的探索性新采集，不是未曝光TEST/G5 holdout/功效保证；旧5DEV不fit。TRAIN闭合须2prefix/2公开状态/≥3成功及≥1决策后native失败且source/48槽完整，否则No-Go，不fit/不派CAL/VAL/不补类。通过才一次冻结高层fit与TRAIN常量/均值基线，CAL仅诊断、VAL不调参，缺失败率None、不据3行部署。下一Data按现有runner生成新用途freeze/自身zero/lease，不需新经济许可、logger/NN表或训练模型；本组尚未分配scope/预约/派发，fit0。
- 正在做G2可消费cohort；下一真实TRAIN闭合→G3真fit或有限否证→新协议G4三策略/G5多决策→G6。无需外组备选是基于既有负例明确模型适用域，不刷fixture/空wrapper；原dirty/closed/12N/4s/identity/immutable/support/guard/QP/FIFO/stop/WM暂停与主要贡献未证保持。

## 2026-11-14 14:55：用户“运行”已确认限定新数据高层critic用途；CPU训练入口已执行，真实fit因新合规数据0停止在准入

- 用户直接回复前条用途确认“运行”，已记录USER_AUTHORIZATION.json，SHA4dab4c18…：仅未来新预登记数据的小型高层success/cost模型训练与离线校验。不是旧audit重标、Actor/WM/DINO/真机/第二owner/closed重启授权；这一用途不再等待用户重复确认。
- 新successor_critic.py已实现单CPU正则logistic未校准成功分数＋ridge当前/成功完整时间头、train-only归一化/常量成功与mean-time基线、group校准/验证报告。后继feasibility仍UNKNOWN/未部署，未校准score不冒成功概率/guard许可。失败进success头但不填成功耗时，资源censor/未到达决策的尝试分母和费用分别保留；同condition不可跨split/旧角色和前授权数据拒绝。
- 已实际执行训练入口（RUN_STATE_NEW_DATA_GATE.json）：WAITING_NEW_AUTHORIZED_DATA_NO_FIT，qualified rows=0/model_written=false/training_started=false/physical_dispatch=false；没有真实拟合模型或GPU训练进程，不用旧三支/12query补位。13项软件准入/数学检查过，fixture只在测试内存算术、未输出研究权重，portable同13不加样本。
- 基于Data现成draft已填本组新用途请求DATA_EXISTING_DRAFT_FILLED_REQUEST_NOT_DISPATCH.json，仍dispatch/admission=false，不改Data manifest/H/queue。仅提议上限8获资格有信息量条件×3候选=24main，4train/2cal/2validation为流水线最小值非统计power，组按共同condition/scene祖先，不按帧/arm或seed-only分。没有实际条件/seed/scope分配，不采集到赢。
- 当前精确前置：AINav须给当前full-host获资格/公共可辨的entry variation源；当前runtime_adapter→stall_stow initial_base固定XY[-.08,0]/compact arm，另一个未调用registered initializer不是已接入旋钮，新seed/不可观测heading不自动有信息。未合格则在24支前No-Go，不盲跑。Data只需新授权原public/query/result/journal/closure及角色/祖先，不替Reach造NN表/训练；Reach自行提取48/标签。必须绑定Host实际intent-observation/physical_observation_sha，不用base _latest_public冒pending query。
- 授权与请求已写本组/共享汇总供接续；当前工具无可用跨聊天派发入口，未声称已通知其他聊天/任务排队或获Data派发回执。下一步是合格新方法/条件与数据，而非再问经济预算或放宽用途；没有新数据时入口绝不旧数据fallback。
- 入口`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-11-14/new-data-successor-critic-v1/README_CN.md`、USER_AUTHORIZATION.json、NEW_DATA_PROTOCOL.json和RUN_STATE_NEW_DATA_GATE.json。全部dirty/旧新closed/失败账与原12N/4s/identity/immutable/guard/QP/FIFO/stop保持，本轮真实数据训练/新物理/远端/Runtime/Actor/GPU/采集0；P0 raw非material/TEST0/主要贡献未证保持。

## 2026-11-14 14:21：P1建立物理特征视图防metadata捷径，下一高层模型/新数据用途须明确授权（未启动）

- 新public_prediction_features.physical_features直接从现有合法Problem+exact候选生成48固定槽：2实际WORLD reference偏移、45公开proprio、1采集age。NN数值视图不含UUID、路径、Observation/program/model SHA、opaque检测ID、candidate名称、绝对sim clock或actual结果；原身份绑定/日志仍保留元数据。它是防误混，不是恶意Python沙箱或source真实性证明。
- 11项定向检查过：仅改metadata/path/hash/opaque UUID/绝对钟且物理/age不变时特征不变，真速度变化保留；原Taskreference被移动、foreign candidate、混采集钟/stale拒绝；没有packet时45D+age为None/false mask，不当静止0。单位/frame明确，WORLD offset不冒BODY误差；pose/heading/latch/合格skill-clock/后继模型缺口保留，特征相同不证明完整hidden-state或允许actual重用。
- 不新增Data合同/日志/采样/模型训练器；没读旧公开包或轨迹作训练样本，portable同11不加样本。既有selector/完整后继feasibility与cost分离、UNKNOWN/default/live安装限制保持，Stage-B负/弱结论不重复审计或改阈值。
- 已把当前预测能力所需最小决策写具体：若要小型高层candidate-conditioned成功/完成cost模型，需用户另明确授权仅使用未来新预登记数据作训练与离线校验。旧P1/P2/v1/v2/三分支/12历史query全部audit-only；底层Actor/WM/DINO/真机/第二物理owner不动。按init/scene/祖先组隔离train/calibration/eval、失败/资源censoring分开、guard failure不造回执、不把短失败当成功时长；具体新任务/数量仍需事前冻结，不是本请求即新run许可。
- 未获明确用途确认前不启动训练/fit或为其采样，继续不依赖许可的解析/接口工作，不假称已经有预测器。当前不是等Data复跑pilot；需决策的是一项数据/模型用途变化，不是总经济预算。详细范围和约束在`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-11-14/physical-predictor-features-dev-v1/README_CN.md`。
- 本轮所有dirty/旧新closed/失败费用和原12N/4s/identity/guard/QP/FIFO/stop保持，新world/远端/Runtime/Actor/GPU/训练/真实采集/物理0，TEST0/实际优化收益与主要贡献仍未证。

## 2026-11-14 13:54：正常路径fresh缺图假设收缩；P1补公开RGBD名义可见点，不偷换对象/入口位姿

- 已看AINav13:22原public再观察/真实12query可用性结论：正常coordinator决策已有fresh同packet45D与RGB，same-sim-clock重拍无新增时间状态；本组不重跑12query/63成员比较，不为“再新鲜一张图”开scope。原一次refresh只保故障/旧缺测量路径，不当正常收益假设；完整RGBD是否充分仍未证明，不能扩大成信息论不可能。
- 新public_depth_geometry.visible_point从原public camera_K/T_base_optical+optical-Z深度做名义optical→body可见点计算，纯stdlib/无定位GT/训练/采集。严格区分optical Z与ray range/world高度，核像素边界/原causal钟/finite proper rigid矩阵；缺失/NaN/非正或旧ONLINE深度保持UNKNOWN。10项定向几何/来源检查过，portable同10不加科研样本。
- 表面point不是对象center或registered reference-relative pose：没有foreground/对象关联/误差资格，原public object geometry仍unknown/unavailable空值，calibration/depth物理误差界及exact pixel-center alignment未证，native READY/支撑/完整cost仍UNKNOWN；矩阵数值容差不冒物理边界。
- 仅以历史公开包6921b24c…的original第三帧84.430s固定中心pixel做一次格式/单位/矩阵数值AUDIT检查，核使用的index/query/calib/depth SHA，不比较后果挑像素；未送selector/模型或转ONLINE/fit。首次HxW假定读拒绝后按真实publisher HxWx1核严格布局，留错误说明；无新帧/世界/Renderer。原source已fresh而对象geometry仍unknown，真正缺口转向可见点→任务对象关联→entry-relative几何/不确定性→完整后继评价。
- 既有公开信息→selector、live非fresh不能安装和完整后继feasibility/时长分离均保持；P0原三支全closed/2成功1 stop_deadline/raw非双100ms不改。下一只研究合法相对几何的来源/误差，不用body速度无界积分成world pose，不拿第四后准备帧倒灌，不重扫±4cm/换seed/profile追胜。
- 入口`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-11-14/public-depth-visible-point-dev-v1/README_CN.md`，源码public_depth_geometry.py。全部dirty/旧新closed/失败成本/原12N/4s/identity/guard/QP/FIFO/stop保留，本轮真实采集/远端/Runtime/Actor/GPU/训练/新物理0；接口数值工具不冒优化收益/论文主要贡献。

## 2026-11-14 13:28：P1明确分离后继完整可行性与耗时，修复cost-only误当未来可行的开发路径

- 通过CPU接口反例实际复现旧dev choose在当前PASS/未来有限时长但未声明后继完整可行性时仍选plus，前后输出已留存；不是原物理安全事故或Stage-B minus失败原因，当前冻结pilot从未运行这一假预测器。
- 在原public_preparation_selector内部新增CompleteSuccessorEstimate，包含既有candidate/input/model-bound Estimate与独立future PASS/REFUSED/UNKNOWN、完整execution+原stop范围/prospective来源。旧cost-only Estimate仍兼容，但未来状态自动UNKNOWN；READY/geometry-only或audit角色不能充后继完整预测。source/role声明不自动证明校准/用途，未新增Data合同/worker或模型训练权限。
- 所有方法共用原三候选/同输入/每候选一次cost+future缓存，无额外模型/GT调用。current-only仍用当前目标；完整方法在未知竞争者前弃权/原default，明确future REFUSED保留但不参加成功时长取最小、不换成大罚时。original未来REFUSED不能default重放行；全部拒绝无完整方案，future PASS但缺成本头仍UNKNOWN，当前gate/预算/identity/原tie规则不被覆盖。
- 13项新语义检查＋26项既有selector/公开信息回归共39通过，portable同39不双计。原条件CPU fixture现显式声明是假设future PASS，不冒真实模型；首版3项fixture把local全1的tie误预期成plus已保留失败日志，修正测试输入而不改原tie规则。无新科研seed/物理样本。
- 下一缺口仍是合法输入上的已验证完整后继评价，不是等Data再跑三点；本次只是预测缺失时方法行为变正确，当前真实预测器仍无、接口完成/方法待能力。若需新数据用途/小模型先单列授权，旧audit不fit，actual不送planner。
- 入口`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-11-14/successor-feasibility-separation-dev-v1/README_CN.md`，源码public_preparation_selector.py，回归test_complete_successor_prediction.py。P0两成功一原stop_deadline、raw反转/非双100ms全部保持；冻结core/效应协议/Data包/原native成功门不改，全部dirty/旧新closed/失败费用保留。本轮world/远端/Runtime/Actor/GPU/真实采集/训练/物理0。

## 2026-11-14 13:13：P1公开动态观测已真正接到共同selector，live评估与fresh安装时序分离

- 本轮不重复Stage-B审计/不再消费旧结果充进展；在既有public_preparation_selector增加with_public_observation，直接把原Observation.value公开45D和public_information派生描述接到既有Problem/InputSchema/DecisionInput/共同evaluator，不新造Data合同/动作。固定、greedy、full方法共用同一动态snapshot/每候选一次预算，原三payload/control profile/terminal predicate/原成功门不变。
- 必须原target在声明map中唯一、XY/源高度严格与registered reference一致；不nearest join或偷移CLIMB成功圆。新鲜同packet/完整公开向量才附加；旧/缺/钟歧义拒进入成本评价，交上轮一次合法refresh路径。raw/派生值不扩private baseXY/latch/contact/未来/audit信息，未知tilt保持None/UNKNOWN。原problem与原observation不被变异，不累积未经授权的controller历史。
- 真实能力边界落实代码：非零时刻snapshot的Task为LIVE_PUBLIC_INFORMATION_EVALUATION_ONLY_NO_HOT_INSTALL，哪怕phase字符串FRESH也不materialize；tick0可通过原pure selection API但原binder还须独立核实际fresh host。CLI可接原观测JSON/显式now/source-role，跑通fresh0、live10、stale10→now10.2三例（全CPU schema，不是实测），stale成本调用0并只输出一次采集请求；函数/CLI不调用采集/Host/binder/step。
- 新增10项真实owner纯API→动态信息→selector集成检查＋原16回归，共26通过，portable同26不双计；不是新物理/新科研seed。无已验证动态cost模型时输出仍UNKNOWN/原default或弃权，optimized_candidate_id=None，不以fresh速度预测完整停稳/宣优化收益。
- 下一独立项：对齐AINav原安全决策边界的public snapshot/实际采集成本和合法相对几何；live重选目前仅可评估，不具现binder安装能力，需AINav后续版本而非Data装配/改闭合v1。前瞻完整后继评价与必要数据用途/模型权限仍是具体缺口，不泛等Data再跑三点、不拿旧audit拟合。
- 入口`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-11-14/public-information-selector-integration-v1/README_CN.md`，改动源码public_preparation_selector.py/run_public_preparation_selector.py，测试test_public_selector_information.py。上一完整三支P0结论保持：2 PASS/1原stop_deadline、raw反转但非双100ms、无统计/泛化/主要贡献。全部dirty/旧及新closed/失败成本与原12N/4s/guard/QP/FIFO/stop保留，本轮新world/远端/Actor/GPU/物理/真实采集/训练0。

## 2026-11-14 13:04：已执行12:50长期计划P0完整三支评价，转入P1公开信息可辨识性；不是等待Data或复扫偏移

- 完整消费正式三分支release4de5ca66…/35成员，核各program/result/ledger/closed/九流cold和Data封存源绑定prefix/实际控制比较，不重复原数组或完整journal审计。三个scope都closed：original13.385/23.665s PASS，plus13.370/24.450s PASS，minus到READY13.540s后原stop_deadline，成功full cost=None。minus无原final failed receipt，保guard异常，不补造；21.920s失败耗时不记成功节省。
- 本组独立原效应入口已对真实全三条ObservedBranch运行：COMPLETE_OBSERVED_TABLE，current_greedy=plus、successor_aware hindsight=original，raw strict=True，双100ms material=False（局部gap.015/完整gap.785）。minus不是greedy赢家，failure_compatibility_switch=False，不挑成功子域或硬凑失败切换。完整候选后果已齐，非三支全成功耗时表、非两个在线策略/统计因果/泛化；TEST0/主要贡献未成立。
- 三支六字段至tick16886逐字prefix相同，plus/minus首次issued差异17603/17571、torque17607/17575（消费Data有源计算，不冒本地数组重算/完整hidden-state相等）。总zero/main/aux362.355sim、ledger2462.917wall、最终高水位482712475bytes；原始live帧1081/1089/1064保留，不为日志/片长重跑。12:05前“等第三支/只有1或2支”的旧状态现在全部过时。
- 选定下一问题Q-info：合法public动态观测及至多一次新采集能否补齐后继选择信息，哪些缺口不能靠再采解除？不是重扫±.04/换seed/profile/门。本组public_information.py已直接接原Observation.value的q/dq/重力/角速/线速布局，计算body motion/关节速度/tilt描述；拒private pose/latch/contact、audit输入、future钟/错shape，不把类别support或运动描述冒READY/未来cost。
- 新信息策略：旧/缺合法测量可请求一次既有public采集（函数不调用采集/物理，原owner安全边界与实际成本照常）；预算用尽则保原行为/弃权。测量已fresh但相对pose/latch/动态评价器仍缺，直接PREDICTION_UNRESOLVED，不无意义poll、不造HOLD/NAV或优化赢家。publication与packet钟不一致时不推造proprio时刻。12项定向CPU检查通过，portable同12不翻倍、例子非新科研样本。
- 当前不再有本批Data待执行阻塞。P1内部缺口是合法相对状态/原controller记忆适配及已验证的完整后继评价能力；public全观测是否充分尚未证，不能偷用audit GT或旧actual拟合。后续对照同候选/技能/信息/采集预算，信息mask消融对所有方法同步；若fresh测量齐备仍无预测，标接口完成/预测不可用，不强行赢家。真runtime重选仍需AINav后续版本，不热改已闭合v1；若需小模型再具体核新数据用途/授权，本轮未训练/扩权。
- 入口`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-11-14/stage-b-complete-and-observability-v1/P0_RESULT_AND_P1_NEXT_QUESTION_CN.md`、`COMPLETE_RESEARCH_EVALUATION.json`及源码public_information.py。本轮新world/远端/Runtime/Actor/GPU/物理/训练0，全部dirty/旧及新closed/失败成本/原12N/4s/guard/QP/FIFO/stop保持；新包不加消费者回执或Data准入前置。

## 2026-11-14 11:47：新Stage-B original真实PASS/cold/closed已消费，当前本组1/3；部分交付reader已跑，不能判H1

- 已消费Data11:29新original结果及11:10完整470成员freeze记录：program a9a8a9bd…，scope data-climb-prep-stageB-original-20261114-v1，zero/main各1已封账，CAS CLOSED_ACTUAL_MAIN_PASS/active=false。main21619步/108.095sim、9项cold literal全true。本组核本地main-result/ledger/sourceSHA/program/close联接，未重审原数组或本机缺失的完整journal；不再写“只有CPU/等freeze”。
- owner source-bound真实构造分析已消费：84.430s原CLIMB PREPARE后的零offsetproposal匹配实际RegisteredCompactNav goal(.050000000000000044,-2)与真实PUSH stow witness、原warmup3.24，323条NAV actor telemetry。第一次PREPARE84.430→READY97.815为13.385s，完整任务终点108.095、remaining完整23.665s。官方zero+main及两次aux总121.105sim/ledger840.987768wall，主任务耗时与全成本分开，不双计。
- Data实际原始live第三视角1081帧已记录，非状态回放；可选视频不作native/评价门。本次步数与旧v2相同不证明数组/hidden state同一，不是新优化收益。原scope已闭合不重开。
- 本组离线reader按真实异步发布作必要差分：声明仍全三域，只放真实收到original ObservedBranch；plus/minus未发布结果不伪造result SHA/NOT_RUN/失败/时长，列unavailable并输出NO_CONCLUSION_INCOMPLETE_TABLE，raw反转/material均None。全三支仍走原效应函数，不改冻结协议/双100ms/core/clock或Data日志。差分7项软件检查过（新增3/调整1/其余回归），portable同7不翻倍；实际部分评价CLI已跑，非再造合成研究seed。
- 本组已收到1/3真实成功分支、完整H1比较0/TEST0，不把original成功写成排序反转/论文贡献；其余两支由Data按固定顺序自主推进，不等待本组报告/开发v2/额外日志或auditor。后续真实record到达直接本组评价，仍需source/init/prefix与实际控制差异证据；actual不送planner/fit，开发版UNKNOWN路径独立保留。
- 入口`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-11-14/stage-b-original-partial-consumption-v1/ORIGINAL_BASELINE_AND_PARTIAL_TABLE_CN.md`，实测摘要`ORIGINAL_ACTUAL_BASELINE_CONSUMED.json`、同域输入`observed-branch-records.json`与最终研究输出`PARTIAL_RESEARCH_EVALUATION.json`。本轮远端/GPU/Runtime/Actor/训练/新物理0；所有dirty、旧closed/失败成本及新original closed与原安全成功门保持。

## 2026-11-14 11:26：按11:15解耦新计划完成开发版选择器，不再以等待Data停止方法开发；当前实验包不改

- 已完整读取11:15新计划。本轮实改方法代码而非再接收release：public_preparation_selector.py直接调用AINav现有public_candidates/selection_from_payload，实现同域三候选完整枚举、原固定/当前贪心/后继完整目标、同公共输入/同三次评价预算，产出可由原纯API materialize的不可变PreparationSelection。v2 direct stow是共同底座，不虚构第四NAV方案；开发版不要求Data重装/排资格/补回执，已有Stage-B worker/source/协议pin保持。
- 可解析几何已计算原/±.04准备ref、WORLD frame、名义reference displacement/原.16entry圆成员关系与中心margin；几何单位是米，不冒真实base→goal距离/完成秒数，也不把nominal margin当tracking/支撑/collision/QP保证。当前最小信息预算仅4个原注册public字段，不扩base世界XY/脚力/后验cost权限。
- 动态cost/原native admission预测未有模型：UNKNOWN时可显式abstain无payload，或KEEP_OWNER_ORIGINAL_DEFAULT且optimized_candidate_id=None，不把default包装成优化赢家。原方案REFUSED/预算超限时不回退放行；条件前瞻evaluator若未来有合法来源，可直接复用既有Estimate/Costs，当前known但successor unknown不会让贪心冒完整优化。无WM/训练/fit或旧actual输入。
- 原binder只允许fresh Host首步前安装已准确处理：开发版限定fresh-host不可变计划，拒绝LIVE_PREPARE_BOUNDARY等热装materialize；不假宣已接后续runtime重规划，不为这个后续接口需求热改当前实验。库不bind/构造Host/Runtime/发控制。
- 本组离线入口run_stage_b_effect_rule.py直接读既有Domain/ObservedBranch，独立运行全三分支raw/双100ms/tie/失败/censoring最终研究评价，不要求Data替跑研究报告，不新增Data日志合同；纯JSON表不证明物理provenance/pair/控制差异。新20项针对性软件检查通过（16方法＋4离线入口；portable同20不翻倍），两实际CLI验证分别原default/严格弃权，都是静态公开schema例子不是新实验。
- 入口`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-11-14/public-preparation-selector-dev-v1/README_CN.md`，纯stdlib可复用包在同目录dev-package/reach_preparation_dev。**自己具体工作：** 开发版selector/解析几何/未知路径/强基线和自己的最终reader已能独立运行；内部真实能力缺口是动态后继预测，不假称只有等物理就有模型。**唯一共用外部实测阻塞：** Data现包新程序准入/真实三分支结果，不再泛等候选/模板/逐层回执。10:47“无新结果仅维护”不作为本组后续实现停工理由。
- 本轮未改原已交付评价core/clock/效应协议或任何Data/AINav源，不新建scope/world/lease、不运行远端/Actor/GPU/物理/API/训练。全部dirty/closed/旧失败成本/No-Go/原12N/identity/immutable/guard/QP/FIFO/4s/stop保持；新H1物理0/TEST0、实际优化收益/主要创新仍未成立。

## 2026-11-14 10:47：消费Data新worker装配，同起态输入和分支差分已核；不重复CPU套件，完整新程序/原生资格仍未发布

- 最短入口最新为Data02:51 release e24695b8…/22声明成员，已全SHA独立核验。本组只读runner比较三软件probe的plan，精确仅candidate_id/preparation_payload.candidate_id/scope_id三处差异；统一requested task/source/profile/config、原seed4301、同common v2 stow，实际source caller的软件NAV y=-2/-1.96/-2.04。没有重跑Data11测试/3probe、prepare入口/安装器，也不把heartbeat次数补写成期间运行。
- 共同初始输入SHA bf3e2e1f…跨三分支相同，科学preregistration b3a63bd2…；原config仅actor_device cpu→cuda:0，四原Actor SHA声明/原初始化来源已pin。不是actual model/RNG隐藏态等价，本组未远端读/load权重；真实Host/Runtime/capture/geometry/QP/动力学构造仍未资格。原归档alias导入CPU失败保留，新方案只bind已加载exact namespace/原活跃类，partial failure不能复用，不造第二package或降identity门。
- 可选live camera已接新worker，192×128/stride20/128MiB，明确camera-on overlay而非热改前版off draft；真实GL/model-data/clock/容量资格仍随新program zero验证。普通录像问题不改native标签/重跑权限，mutation仍安全stop，不回放补旧片。
- 新freeze应追加02:46已确认效应补充39f4dc5b…与原协议dfea3ec2…；Data历史draft仍写Reach pending不等现在未同意，也不热改已发布bytes。双100ms描述性反转/全raw失败tie/censoring保持，不是native成功阈值/统计或物理许可。源pin见`FUTURE_FREEZE_EVALUATION_INPUT_PINS.json`。
- 精确下一步由Data完成新全程序/fenced entrypoint/source-SDK-assets-Actor-authority freeze、fresh lease/本程序own-zero/一次main；本组不再泛等候选/N3/JSONL/helper/起态来源。无新资格/后果时不重复已过CPU/旧审计充进展；只消费下一份新程序或真实结果并核source/prefix/实际控制/完整后继与全部失败成本。动态cost模型仍UNKNOWN，两在线选择器不冒已部署。
- 入口`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-11-14/stage-b-worker-assembly-consumption-v1/DELIVERY_MANIFEST.json`及同目录`ASSEMBLY_INPUT_COMPARABILITY_AND_NEXT_NATIVE_STEP_CN.md`。本轮远端/原Runtime/Actor/GPU/API/训练/物理0，无新scope/ledger/world，所有dirty与closed/失败成本/原成功保护门保持。新H1物理0/TEST0，主要贡献仍未成立。

## 2026-11-14 02:48：已独立接收Data N=3/JSONL/完整终点与原环境helper；确认后果前100ms描述性补充，剩真实集成/初始化/新freeze

- Data新release697d7273…全部332声明成员逐SHA通过，本组实际调用其原stageb_protocol.draft，得到全三分支/空roots；native-import fence无尝试，不调用materialize/造scope或派发。Data已采用本组dfea3ec2…协议，N=3而非两算法、原JSONL decision/READY/receipt与完整两请求endpoint的CPU接缝已闭合；最新13项为Data软件检查，本组不重复跑/计作实证。原outcome无intent的ABI修正已按bound event/hash连接保留，不造新字段。
- 消费原NumPy1.26.4/NavSkill/EfficientNav helper回执，原SDK navigation7b5758a4…/profiles4bfb33cc…；真实helper profile deadband .035、position tolerance .13/stop ratio .5（stop半径.065）、cold warmup3.24、hold1。预声明软件远态三body请求[.5,0,0]/[.5,.4,0]/[.5,-.4,0]，近态三者全0并latch。不是全状态结构性同义，也不保证真实分支不同motor；后者含原RegisteredCompactNav/capture/root-proxy/geometry/QP/动态仍未资格，真实新program绑定未freeze。
- 正确决策域解释：近态/yaw0原judge若READY，本来不做准备干预，不能单据近态全0否证PREPARE域。同snapshot若原XY误差>.16触发PREPARE，±.04目标均距>.12>.065，不能初始全落stop圆；仅瞬时必要几何，不保证3.24warmup后/整链，也不增加private selector输入或新安全门。
- Reach现确认Data 100ms后果前描述性提案，补充文件SHA `39f4dc5ba75085d744d6abbb54c15789a98e8aa1fc041ecc59db08d2d9e11dc8`：原1e-9严格反转/全部raw gap仍报；材料性严格反转须局部优势和整链劣势两项均≥.1s，失败兼容差异/tie-break分别报，完整三分支缺失/censoring不下H1结论。一个配置一次机制pilot无方差/统计/泛化；不是native成功阈值或部署oracle。新stage_b_effect_rule.py及12项新规则软件检查通过（portable同12不翻倍），CPU表不当物理例。
- 精确剩余：Data实际caller/factory/root-executor/前PUSH proxy接线，共同scene/Actor/constructor/initial-state/RNG pins和统一v2 stow，合入此supplement后新完整freeze/fresh zero/lease/一次main；如录像则同新程序zero核live相机，不为补片/日志重跑。本组不再把三候选/模板/helper写成未接收，也不靠改δ/seed/profile追胜。动态cost模型仍UNKNOWN，两线上优化器继续弃权。
- 入口`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-11-14/stage-b-data-intake-and-effect-rule-v1/DELIVERY_MANIFEST.json`，说明`DATA_HELPER_AND_PREOUTCOME_AGREEMENT_CN.md`与`PREOUTCOME_EFFECT_AGREEMENT.json`。新H1物理0/TEST0；本轮远端/GPU/Actor/原Runtime/物理/API/训练0，全部dirty/closed/原保护门与失败成本保持。上一01:47“profile全未知/等N3模板”只作历史，以此接收状态为准。

## 2026-11-14 01:47：原NAV横向请求实际是三值分区；不同goal未必不同控制，尚无整链等价/否证

- 不重复旧实验/owner套件。本组沿固定AINav common source增量核清原`EfficientNav.update`：body-y的MIN_SPEED与SPEED_LIMIT同为.4，drive/warmup结束/未position-latch时请求恰为−.4/0/+.4，由原严格deadband与符号分区决定。三目标即使误差不同，也可处同一请求分区；不能把4cm goal变化当连续控制变化或线性代价改进。
- 新`nav_request_equivalence.py`逐SHA＋原update AST检查原常数/strict deadband/floor/clip/无slew，并提供native-private标量分区诊断。15项新专项检查通过，portable同一15项也过，不翻倍；不是原NumPy/完整类/Actor/物理资格。native实际profile/deadband仍UNKNOWN，不填默认、不扩大公开输入、不送planner/fit。
- 整体速度/电机/轨迹等价仍UNKNOWN：world-y偏移会经yaw旋转影响body-x，latch/stop-ratio、历史、Actor与arrival也会分叉。另已核原make_compact_nav的.24s warmup会被RegisteredCompactNav恢复为原skills profile，不能误用.24或调warmup/死区追控制差异。
- 原consumer已有requested_velocity/observation/action/issued与实际warmup/arrival事件；不用为此加日志或复跑。Data下个CPU intake用实际profile/同snapshot核原原生update分辨率，未来新预登记机制结果再逐层定位goal→请求→Actor→实际控制及完整后继；单瞬时相同不下整链结论，同控制归并则No-Go，不改δ/seed/profile追胜。
- 入口：`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-11-14/preparation-nav-request-resolution-v1/DELIVERY_MANIFEST.json`与同目录`REQUEST_RESOLUTION_AND_NATIVE_CHECK_CN.md`。00:55三分支协议SHA dfea3ec2…及原程序全部不变；Data N=3/JSONL接缝/原环境资格仍待owner绑定。本轮远端/GPU/Actor/物理/API/训练0，新H1物理0/TEST0；全部dirty与closed保留。

## 2026-11-14 00:55：已消费AINav真实三准备候选与Data新模板，不再等抽象domain；仍无新物理资格

- 本组逐SHA接收AINav有限CLIMB准备域release0c17d2e7…／299成员及Data配对录像模板26df0107…／18成员，共317项；只作发布完整性，非native验收。真实原NAV／world-y±.04m候选接入Task/Domain/InputSchema，所有arms共用v2 direct stow三文件新fork；原CLIMB reference/门不变，旧stow-only loader不可套新profile。
- 已实际执行owner纯stdlib `public_candidates`与三次`selection_from_payload`，没有调用bind_to_host/构造Host或Runtime。当前最小输入仅公开静态target/原注册approach/源高度，不再要求private base世界XY去套之前projection probe；private脚力/pose/后验cost不进选择器。三候选只是声明不同payload，实际motor差异仍UNKNOWN。
- 新 `successor_preparation_intake.py`/runner交付具体Stage-B全三分支机制协议，当前=首次原CLIMB PREPARE→NAV准备/退出后的新鲜READY，完整=相同原点→原CLIMB完整回执及两请求终点。PUSH/v2 stow共同前缀为沉没成本，整episode费用另报；prepare重复/空隙/停稳/失败全部包括。所有cost/feasibility模型未知，两优化方法均弃权，未伪造可部署策略比较。
- 新 `preparation_stage_clocks.py`验证future journal整SHA＋原hash-chain，按同intent/native option/exact judgment_ref读proposal `/payload/time_s`、READY `/payload/state/time_s`与回执 `/payload/receipt/time_s`；取第一次PREPARE而非最短/最近段，失败原标签保留，不推断Actor激活或task成功。仅CPU fixture测试，未重读旧物理日志。37项新检查通过，portable同一37项也过，不翻倍计数。
- 已定位两个模板接缝：Data当前materialize硬编码两个`current_only_baseline/successor_aware`策略arm，不能冒Stage-B三固定分支；其stage reader只收单JSON/固定STAGES，须显式接JSONL hash-chain与`preparation_decision`。本组协议已给足source级pointer，最终两请求endpoint/可选内部时钟由新worker绑定，不用缺字段重跑。
- 下一最小动作：Data消费协议SHA `dfea3ec252ad995fcb9f4c0ed7f368b3b570e94dcef826bea6577ad68003371d`，增补N=3预登记和JSONL见证，并在自有staging核actual NavSkill/profile/root-proxy身份与真实消费；之后才完整新program/fresh zero/lease/一次main。每候选最小机制pilot而非统计泛化；同控制归并则No-Go，不调δ/seed追胜。原live第三视角仅随新信息运行、可选且不改native门，不补旧片。
- 总入口：`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-11-14/successor-preparation-owner-intake-v1/DELIVERY_MANIFEST.json`；具体协议/接缝在同目录`OWNER_BOUND_STAGE_B_PROTOCOL.json`与`OWNER_INTAKE_AND_NEXT_NATIVE_BINDINGS_CN.md`。本轮物理/远端/GPU/Actor/WM/API/训练0，新H1物理0/TEST0，所有closed/dirty及旧direct等价/NoRankReversal负结论保持。

## 2026-11-14 00:36：新计划Stage-A软件/协议交付，尚未新增H1原生实证

纯stdlib successor_aware_choice接口与原固定/直接强基线/当前贪心/后继完整代价四方法就绪；同domain/profile/信息schema/evaluator/cache与预算，audit/前瞻类型分离，Unknown不当0/pass，复合与拆项成本互斥，失败/censoring与全部费用保留。34项新专项软件检查通过，不当新实验或H1证据。

原DEV scalar table仅负向检查：capture起current16.935→15.680、chain40.040→39.345，局部/整链都选direct，strict rank reversal=False。不能把.560后继罚时当排序反转；旧.695sim与所有失败/cost保持，未重审整流/重跑物理。

具体最小扩展probe是保持原EntrySpec/任务/门不动的private NAV准备reference选择。原_native_nav使用同名ref写执行表，需owner分离准备ref与交互spec后核真实不同消费；标准内半径投影、原终点误差界仅是必要几何设计，无新native域/权限/动态保证。问题/最小状态/配对执行与原始视频规则已写入`evidence/2026-11-14/successor-aware-choice-stage-a-v1/`；物理/evaluator模型能力/新域资格未取得，不宣称在线整链选择器或论文主要创新完成。冻源与dirty全部保留。


### 2026-11-13 20:34 后继.560s罚时的原阶段定位（无新物理/新收益）

原闭合P2/v2 CLIMB分解为−.005（motor→first_clear）＋.015（clear→handoff）＋.545（handoff→reported stable_start）＋0（stable_confirmed前1s）＋.005（confirmed→terminal）=.560s。主要.545s来自报告的handoff后到进入稳定段，原2.665→3.210s；NAV13.380和全stop配置不变，stable1s/verify3s不删。不是已证明的具体状态/接触/全局控制phase原因，也不识别Actor时钟或产生未执行cost预测；只支持本单对中READY/相同NAV时间不足以唯一描述后继耗时这一回顾结论。

新增5个小parser检查与原字段冗余交叉核验通过，不算新实验/安全资格/方法收益，不改gain/hold或为此重跑。证据`evidence/2026-11-13/stow-v2-actual-control-consumption-v1/SUCCESSOR_CLIMB_STAGE_DIAGNOSIS.json`；主净.695sim/direct等价和所有失败/cost不变。


### 2026-11-13 19:28 精确结果对补充（不新增实验/收益结论）

本组独立最终bound reader已消费Data223046f7…六字段前缀与已核source，精确候选/P2/终态联合单DEV eligible=true；与Data先前调用收据相同。净.695sim和DIRECT_BASELINE_EQUIVALENT不变，不冒本组NPZ或hidden-state/强因果重审。原初稿保留，追加`stow-v2-actual-control-consumption-v1/EXACT_PAIR_BOUND_CONSUMER_RECEIPT.json`，无新物理或采样。


## 2026-11-13 18:31：真实v2准备控制已消费并完成接续，仅直接基线等价DEV单对

Data17:56 release442844ec…、program acf46aa6…正式zero/main PASS/cold/closed已消费；实际21619步/108.095sim。选择[0,2]直达同compact、2 waypoint变1，原4s验证保持。本组独立核记录有限图、选择/终态消费、源freeze/fork/current-runtime和原时间端点；Data issued数组前13750步同P2、13752首次差异保留为owner证明，不称本组NPZ/几何重放或完整hidden-state一致。

capture→stow局部少1.255s；stow→CLIMB多.560s（NAV仍13.380s，CLIMB10.275 vs9.715），总108.095 vs108.790净少.695sim，不能只报局部好处。selector wall与名义schedule界不当实测净收益。完整原输入未记，input replay UNAVAILABLE，不补造/重跑；DIRECT_BASELINE_EQUIVALENT，非新DAG算法/统计因果泛化或主要论文贡献。

新最终scope121.105sim/808.077436wall，旧v1失败81.760sim/537.467477wall与P1/P2全部保留。成功ledger stopped=False不等未闭合：release/CAS inactive及两closed rows已证，不加failure-stop新门。该路径收束为工程强基线，不做同动作DAG/直接伪A/B；其他合法自由度/真实未测后继问题另立新协议，绝不复开当前scope。

证据`evidence/2026-11-13/stow-v2-actual-control-consumption-v1/ACTUAL_CONTROL_AND_NET_COST_CONSUMED.json`及`effects-and-source.json`。本轮Reach新增物理/Actor/GPU/API/训练0，dirty保留。


## 2026-11-13 16:58：v2原端CPU已接收，明确新控制协议；无v2物理效果

Data16:33正式62f60132…已逐SHA消费，bundle3016ec48…精确匹配，非扁平原session/placement wrapper与NumPy/queue/reference CPU通过；geometry/capture/QP仍fixture。供owner新program/scope/fresh-zero的同目标PUSH→stow→CLIMB协议已发布，不复开失败v1，不重跑P2。当前固定两waypoint仍只有原/直接，主要算法贡献及实际收益未成立。

新结果读取器按完整新freeze/fork/current-runtime/283源/原SDK与可逆consumer核源，精确绑定候选-P2结果/前缀，不再把旧失败program或lineage签作v2。新增8源资格＋2绑定软件检查通过；合成正向metadata不算真实freeze/实验。对真实旧v1失败的负向读取保持FAILED/所有收益None。可选host.tick的after-step滞后一拍只作源序注记，不改原成功/采样门、不为日志重跑。在线v1/v2与原核心/hook均未修改。

证据同`evidence/2026-11-13/stow-target-view-repair-v2/`：`OWNER_NATIVE_V2_RECEIPT_CONSUMED.json`、`FOLLOW_ON_CONTROL_PROTOCOL.json`、`source-pair-and-effects-tests-final.txt`、`v1-rejected-as-v2-source-evidence.json`。


## 2026-11-13 16:22：首实际stow干预scope失败，根因与v2修复分开

新d7d42515…程序zero PASS，但main在68.750sim/13750命令首次选择边界被本组v1错误`session.runtime.sim is owner.s`判断拒绝，FAILED_NO_RETRY/closed，选择0/路径改变0，stow复合终点与CLIMB均未完成。最终新增成本81.760sim/537.467477wall完整保留；Data正式release462df53e…及9项原流cold已消费，全部13750 issued byte相同P2 prefix仍注明owner数组证据，未重审/重跑。此为接入缺陷，不是直接路径动态失败或方法收益。

原factory按设计用proxy.sim=selected view承载native，同时NativeOptionSession持主Runtime；v1 flat fixture漏此关系。新v2只修身份模型，不删检查：同root/精确proxy/view、同model/data/FIFO、原context与实际issued seed；原hook/核心/T/所有安全与4s门不变。8项原factory+真实NativeOptionSession构造CPU回归过（Machine/geometry/capture仍fixture），尚未v2 owner采用/物理。不复开/热改失败v1；需新owned CPU资格，之后任何物理仍新program/scope/fresh zero。

两waypoint条件域仍仅原/直接，DAG非新求解贡献。真实失败效果reader所有收益None，不能较短失败当省时。证据`evidence/2026-11-13/stow-target-view-repair-v2/ACTUAL_V1_FAILURE_AND_V2_REPAIR.json`及`OWNER_V2_CPU_INTAKE.json`。


## 2026-11-13 15:59：原环境接收与新own-zero已实到，尚无main优化效果

Data15:26回执已独立消费：真实loader/NumPy/queue/reference CPU过，2源变/281原，geometry/capture/session仍fixture。新程序d7d42515…准确绑定本组未改动的v1；实际fresh own-zero/cold PASS（e280e374…，任务命令0、已安装真实class callback、选择未触发）。15:49 main唯一派发登记1次，未冒main闭合或收益。

P2原实际2 waypoint决定固定域仅原/直达两策略，排除在此scope拿第三路径/DAG当新算法的说法。12.935s受影响motion+tracking窗口为audit-only，不是可节省预测。新效果reader18项、窄NPZ prefix比较器6项小软件检查过；它们为本轮真实结果归因服务，不作研究样本或native安全资格。只有精确本candidate/P2任务/source/prefix及原消费/4s/完整成功证据齐时，才给单DEV pair局部与后继净效果；仍不证明新求解算法/泛化。

原在线v1未改，无Reach物理/GPU/API/训练新增，不复开closed实验。证据：`evidence/2026-11-13/stow-path-choice-consumer-v1/{owner-native-intake-consumption,actual-own-zero-adoption-observed,POST_CLOSE_EFFECT_CONSUMPTION}.json`。


## 2026-11-13 15:08：准备路径选择及准确原consumer绑定（CPU），P2后继增量已消费

18核心＋18源级/作用域测试通过；默认关闭的两源别名delta精确可逆，仅当前ground PUSH/confirmed/精确stow实例，在原capture/queue门后、原full-path recheck前选择原waypoint子序列。固定原update/begin_segment/command前缀执行已证明selected waypoints进入原desired/select_reference入参；状态/geometry/queue/数组均软件fixture，未实际native NumPy/QP/电机/在线验证，不是安全资格或物理收益。

P2原query/后继两option+observation+execution batch/CLIMB两judgment独立重算匹配；真实NAV准备13.380s，stow→CLIMB23.105s，Actor激活时刻未知。未重做Data命令大数组审计，共同17137步bitwise相同仍明确为owner结论。它仍是原AINav成功，零Reach收益证据。

明确限制：直接可行时T单调次可加＋L∞三角不等式使直接同端点路径已是schedule目标最优，等价已有11-05直接收臂；标准DAG/完整枚举不是新算法。实际tracking/settling/后继任务增益与主要论文创新未成立。原4s验证/支撑/QP/FIFO/每步guard不删，旧负结果不改。下一步是owner新fork原环境资格/完整program freeze/fresh own-zero，不复开P1/P2，不补第三条原流程演示。

证据：`evidence/2026-11-13/stow-path-choice-consumer-v1/IMPLEMENTATION_AND_BOUNDARY_CN.md`及`ground-climb-incremental-consumption-v1/consumption.json`。本轮无物理/模型/远端/训练任务。


### 消费关键路径增量｜2026-11-12 22:17：离线分析已可重定位，不依赖旧/home

- Data新目录与原分析固定来源路径不兼容，已实现显式context路径映射和封存source-only包，而非另建执行器/模型。23文件/321065字节，无checkpoint/传感器数组/actual归档；原Data验证代码和公开规则/manifest保留原SHA，四个本组模块path-only差分显式发布，不静默repin。
- 正式包`evidence/2026-11-12/portable-offline-analysis-v1/accepted-bundle`，manifest SHA660c8be6…312fa。所有输入仍须独立SHA；无映射不能fallback扫描/读旧环境，默认拒fixture，输出不能覆盖源包。公开manifest历史摘要元数据保持角色，不宣称未曝光。
- 实际在本地新临时根、-I/-B/-S进程并禁止旧/home、网络/子进程/模型物理库后，完成原Data单个封存fixture的阶段/修复消费及原规则/BehaviorOption摘要，3正/3准确原因负例通过。5路径边界过；27项仅复核直接改动的两个consumer专项，原数值与UNKNOWN/role保持。初版一个负例因缺前步文件不能证明角色拒绝，日志保留并修正后正式过。
- 未远端部署/核Data环境，不把隔离CPU称其新端资格或新样本。本轮0新forward/物理/Actor/GPU/API/训练；科学判断/原SLP与standoff No-Go不变。使用与diff见本包README_CN/accepted-release/source-path-only.delta.patch，主报告第13节。
- 资源口径同步：按Data最新发布，新端GPU0已获其专项授权，真实full4已编译但zero/main仍未启动；不再用旧原GPU1-only当它的当前权限缺口，也不据此给Reach占GPU。唯一启动仍Data，B3/预算不扩。继续等实际技术/后果新增，不空转或重复A/fixture。


### 接续分析新增源绑定修正｜2026-11-12 19:45：几何目标不冒原已选CLIMB目标

- 新`exit_repair_evidence.py`及CLI在完整后继耗时缺失时保留位置/朝向修复分量、原native categorical反馈；复用已有Data闭合结果，不重新回放或生成科学样本。
- 关键源码事实：原NativeSceneFactory的CLIMB检查用option.parameters的goal_world_x/y，非退出实测箱位自动重算。故旧“front−1.05”诊断只有在该front确实用于生成所选intent时才是其native参考；实测箱几何代理另标HYPOTHETICAL重规划，actual native修复值默认None。
- 已实现真正有数值的原目标通路：读取原BehaviorOption完整字段，执行冻结原class校验/digest并与原next-option SHA join，才计算max(0,||p−goal||−.16)m；换goal借旧SHA拒绝。该量只针对固定参考球、不签路径/动态/时间/Actor-ready；原world-yaw门.25rad的修复另列rad，不混成本。
- Data当前entry tap已有ready/reasons/scope/profile/tick/next-option SHA，但未给goal XY原件。新consumer保留原分类反馈，无需等完整R/C；不因此阻塞G1或扩大B采样。后续可附带原selected option公开参数/SHA，不由Reach替Data补目标/改hook。
- 11专项通过，两个既有fixture结果只读augmentation：PM缺状态/check则UNKNOWN；phase例原check真被保留但无goal/EXIT几何仍无native修复/full-ready。没有真实B位置量、不同候选收益或原生动作输出。源拷贝cwd/三引号错误日志留存，修复后通过；旧已发布模块/peer源保持。
- 稳定主报告第12节，证据`evidence/2026-11-12/exit-repair-evidence-v1/`。A真实三行已消费不重跑；B仍Data已授权、技术未过/未运行。0新神经/物理/GPU/API/训练，不继续用表面重复测试替代真实进展。


### 真实A到达即分析｜2026-11-12 19:08：单批三行响应已补齐，结构性不充分仍成立

- WM18:57正式发布真实A v4，Reach自行消费，未代跑/再加载模型。独立pin发布/result/3行输出/replay/postcheck/closure，实际通过owner raw_batch_payload真实分支进入本组四级分析器，无fixture opt-in。新代码`consume_authorized_A.py`及5项只读消费专项过。
- 原7a6同B query三推距box dx(anchor-body)=.273019/.469440/.658860m，robot dx=.262890/.453091/.740659m，未成功条件化native终止elapsed=18.006195/19.368282/20.678875s。三对响应已可比，box−robot dx分别+.010129/+.016349/−.081799m；不是world净空/实测后果或连续梯度。不能因.2 event time短就推荐.2。
- 0.6原重放head通过（mean最大差1.19e−7m，elapsed1.91e−6s），仅数值一致性而非质量/标定/安全。WM原attempt约10.304wall/2线程、1loader/1共享filter/1batch，无重试，decoder/GPU/Actor/physics/API/训练0；Reach本轮只读，新增forward0。
- 四级充分性：模型响应三行可比较；无阶段绑定有效误差区间→无保证排除/支配；原成功或失败终止头→成功阶段cost仍未知；完整after-Finish/姿态/臂/载荷/actual-ready缺→可执行选择仍UNKNOWN/online_action=None/dispatch=false。三行真实输出验证原结构性No-Go，不等第二批同类raw解锁字段。
- 证据`evidence/2026-11-12/real-A-consumption-v1/accepted/`与稳定主报告第11节。A已完成，不再写待许可/运行，也不重跑A；B仍已授权Data唯一owner、等待真实技术就绪，不把A当model-free链前置。新增Data闭合接续分析模块继续等待真实B，不用标签拟合或在线倒灌。


### 长程计划接续实质增量｜2026-11-12 19:03：Data闭合评价→接续成本/强基线已实际打通（软件产物）

- 已读18:42新版并采纳长期自主推进，覆盖旧“当天停止/A待逐次许可/B未授权”。A限定单query单批CPU推理已归WM自主范围；B已授权Data原GPU1最多3Dev及预算。Reach不重复请求或代owner起world/加载7a6；技术资格仍分别由WM/AINav/Data真实闭合。
- 新增`observed_handover_analysis.py`＋CLI，直接只读消费Data阶段评价/lifecycle，复用其verify_closed/timeline_summary/sum_disjoint/validate_evaluation，不复制采集器/制造新标签。输出仅offline_dev_outcome_analysis，拒online/fit/norm、fixture默认拒、版本/时钟/role/hash不符拒；原actual audit-only/holdout用途不变。
- 已实际消费Data封存4个EXPLICIT_FIXTURE：phase正常native2.005s、PM正常405已发记录/native2.020s但均缺后继准备终点C=None；guard保留2已发且完成cost空；存储失败保留“观察已发2/持久化1”与INCOMPLETE_EVIDENCE，不记零执行/快成功。没有重放Data source-hook/Actor命令，0新实测/预算消耗。
- 最小假设H1：同候选表里仅native PUSH+Finish最小的排序，可能因query前剩余准备/后继准备不同而反转。实现固定离线参考、native-only回顾参考、C=后继准备程序结束−query的枚举回顾最小；失败/缺端点不补0，重叠Finish不相加、receipt后等待计入。回顾表最小是评价参考而非在线可部署策略，标签不回灌预测。
- 严格同状态不靠query hash或“同B事件”推定；默认独立前缀为observational unmatched，另有设计引用才标“声明受控”，分析器不认证隐藏状态相同。缺候选/重复/混版本不抹掉，不生成物理全域结论。后继准备结束也不冒Actor-ready，当前actual_next_ready仍None。
- 退出几何若Data新LABEL具备原Finish后/tick/state-SHA匹配则可算箱角点/机器人/原CLIMB B参考/后续HIGH投影诊断；原native front=center−登记length/2，与旋转箱min_corner_x分开。当前发布fixture没有EXIT_GEOMETRY，保持None，没有补造实际状态。
- 16项新专项通过；H1仅一条FUNCTION回归示例展示不同排序，不充真实3秒收益。源码末尾三引号导致一次SyntaxError已保留日志并修复；无任务/状态变化。证据`evidence/2026-11-12/observed-handover-v1/`；稳定主报告第10节。既有SLP和standoff No-Go保留，贡献暂收缩为任务条件接续建模/公平评价，不主张新求解器。
- 当前真实A/B数据尚未到，实际在线选择/任务增益仍未证。后续按长期目标衔接A充分性与B真实接续，不以小包结束停研究；无有意义新增输入时安静等待唯一owner技术/数据更新，不重复fixture/文档空转，不向peer派任务。


### 午后联调收尾增量｜2026-11-12 14:21：WM新v3运行器/默认关闭profile已实际软件消费

- WM新source/doc到达后自行继续本轮联调，之前“未发布”断点已在软件层解除；新增`verify_wm_v3_interop.py`，前后源/输入SHA一致，不改他组文件。
- 实际读取其已结束fake-cli三行结果，经owner raw_batch_payload：默认拒fake，显式fixture映射后交本组真实analyzer。三行raw响应可比，成功阶段成本不可比，可执行选择false；未重新调用其runner/load/filter/batch，仍无新.2/.4真实预测。
- owner ResearchProfile→request→config→原relative-entry相同code object→原compiler base_goal赋值fixture，消费本组HYPOTHETICAL.545/.58/.615，XY−.045/−.080/−.115m，与几何profile一致。原0.58函数identity/global不变、非原参数模型适用性UNKNOWN、native_dispatch guard拒绝。仅nominal-view软件fixture，Z为明示sentinel，未构造world/Actor或实际private参考。
- 证据`evidence/2026-11-12/afternoon-sufficiency-geometry-v1/WM-v3-actual-software-interop.json`及acceptance。两项主体＋同轮实际软件联调完成，R2静态No-Go/原0.58最优不变；真实runtime资格/自然重放与A推理许可仍未通过，B另批，不再重复fixture凑工作量。


### 午后两项主体交付｜2026-11-12 14:12：充分性分析＋source Piper几何局部对照均完成，结果为结构性收缩

- 按12:55新版计划完成R1/R2，不重做上一轮CLIMB/时钟/域盘点、不扩SLP样本。新增`model_sufficiency.py`与`projected_arm_geometry.py`，原始数据在`evidence/2026-11-12/afternoon-sufficiency-geometry-v1/`，主报告沿用`evidence/2026-11-12/native-v9-discrete-selection-v1/NATIVE_V9_DISCRETE_SELECTION_AND_RESEARCH_DECISION_20261112_CN.md`第9节。
- R1为可运行四级分析器：模型动作响应（六维差/离散secant，不冒连续梯度）、有合法query/phase绑定区间时的作用域必要排除/同模型成本支配、成功阶段时间比较、实际可执行充分性分层。实际归档仅.6，.2/.4不补fake。即使3行raw都到齐，原6位移/事件time/std也不补成功条件化退出状态、完整姿态/臂/足载荷或native-ready；结构性不足，不再把多等一轮同类输出当解法。
- R2使用原Piper XML/robot+collision profile、原helper和名义关节曲线，保护Piper/link1–5共6个hull/3056原顶点，对真实B来源前缘作保守半空间分离；65固定FK点加原hinge全域lever的采样间隙界，sample max.422604m/model upper.442012m。不是任意二次函数，有限采样max不冒连续上界；不含tool/腿/自碰撞/IK重定向/接触动态/实际跟踪。
- 明确HYPOTHETICAL研究点.545/.58/.615（原35mm几何clearance尺度扰动，不是控制允许域）：分离余量67.988/102.988/137.988mm，全通过该几何分量。固定0.58、同域完整枚举、通用MILP均选0.58；cost是base参考偏移m，不是秒。本例约束未激活、未发现优化增益。固定曲线下margin对standoff为仿射，不需要新求解器；不加rail/扩范围追胜。
- 目标一致性仍缺：只移base不重定向IK会令工具参考也移35mm，不能据几何更空声称同PUSH目标仍可执行。old7a6没有standoff通道。GeometryStudyProfile默认不扩域，真实域仍单点.58，所有输出dispatch=false；未消费未发布的WM新profile当成已验证能力。
- 本轮实际复核已调用WM公开事件source API、消费真实producer v2能力，R1新增11专项/R2六专项通过。新午后runner实际输出/新standoff prototype在所查入口未发布，相关联调明确未完成，不用mock冒接入。初次mesh路径编译错误（FK前）留log，隔离spec只修文件解析；最终65点trace逐值复现，总130软件FK/2静态编译，不是两次任务；0神经model load/forward、物理/Actor/Renderer/API/GPU/训练/远端。
- 当前可独立完成实现/数值/分析已闭合；真实候选排序UNKNOWN、物理排除/保证支配空、无动态收益。下一只对新增已发布输出/profile作本轮必要联调；新A推理和B物理各需单独许可及真实技术资格，不因准备包已存在就运行；不自动新场景/新算法/次日阶段。


### 当日计划验收｜2026-11-12 11:41：真实CLIMB约束/三候选表与WM时钟v2已联调

- 按11:12更新的“一工作日”计划，新增有源`native_climb_continuation.py`及运行入口，完成当天可独立实现/验证，不重做域/坐标/selector交付、不扩SLP样本。主报告沿用`evidence/2026-11-12/native-v9-discrete-selection-v1/NATIVE_V9_DISCRETE_SELECTION_AND_RESEARCH_DECISION_20261112_CN.md`第8节。
- 关键任务分层修正：PUSH B即时后继CLIMB B为GROUND→B，原准备目标`(F_B−1.05,lane)`、approach半径.16m；**不要求此时B已对接HIGH**。真正B→HIGH是更后的CLIMB HIGH，移动源接缝原门为`|gap|≤.01m`且需实际承重顶面/foot-radius/source polygon，不是overlap越大越好。
- 原源码门已绑定SHA/单位/阶段：源层.05m、yaw.25rad、speed.12m/s、tilt.30rad、原零臂.12rad或独立verified compact分支、四足源载荷各严格>4N且共同注册顶面；model点不签native。退出分离阈值无独立依据则None，不设0、不借.58或1.05；.12速度是entry门，不用它换算NAV秒数。
- 真实归档B三请求的CLIMB B准备x为−.35/−.15/.05m；后续HIGH请求dock余量为−.39/−.19/.01m（只属目标设计）。0.6原预测条件点距其CLIMB B目标.562185m，approach余量−.402185m；若阶段正确应需原NAV准备，**不判整候选失败**。该箱点若后来保持则HIGH双侧dock余量−.048745m；无阶段/误差/接触依据，不作真实排除/支配。
- 已自行消费WM刚发布phase/time v2：20.678873s是query→native option终止（成功或失败），未成功条件化，不能填成功PUSH+Finish或推断其已完成。复用owner cost_admissibility，成本按非重叠阶段覆盖；已知合计可保留，但不得重复其Entry/Finish，部分时间不补0。名义cost-only可比较不依赖伪造实际ready，真实表当前完整cost仍缺。
- 21项本轮专项通过；有源规则JSON/三候选CSV/WM-v2消费/最终源码快照在`evidence/2026-11-12/native-climb-requirements-v1/day-acceptance-final/`及父目录。真实选择UNKNOWN、实际排除=[]、带保证支配=[]；0新推理/物理/Actor/API/GPU/训练/渲染/远端，不读offline actual ledger。
- WM当日standoff建议已读：可能改变同目标下准备/接续修复，但未验证收益，且action11无standoff通道，旧同query预测无法区分它。不为凑连续维度放guard/改动作描述；先补原三点阶段效果。后续最小新forward/真实3分支补证及数据用途分别需明确许可与技术资格，旧No-Go/strict=False/closed roots保持。


### 来源增量｜2026-11-12 09:25：已绑定真实归档B前态/单0.6预测，显式更正WORLD +X

- 自行消费WM新发布0.1.1及owner EventEffectSources（独立SHA），不是等待转交或重复空接口。真实归档事件behavior-decision-0001/query51.675、RGBD51.6、B/front prior0.5m；不是live传感器、不是新采样。
- 重要坐标更正：原consumer实际`goal[:,0]+=distance`沿WORLD +X，不按箱yaw。旧0.1.0文字不再采用；新诊断明确pin0.1.1，旧API/pin与他组文件保持原样，不暗换/改控制。
- 真实来源的三请求设计gap为0.4/0.2/0m；单0.6有原发令前7a6预测，模型front1.158744682/robot x0.670773942m，模型纵向投影搭接0.058744682m。只作该query点预测诊断，不借给0.2/0.4、不以std作界、不称实际支撑或Finish/ready。
- 预测elapsed20.678873s为原terminal option-purpose时钟，不直接填native PUSH含Finish成本；缺阶段/退出阈值/成本则完整选择器不伪造输入，best=None/UNKNOWN。一个真实前态/单预测不构成选择收益；基准仅0.6请求恰好接触，不能推广固定最佳。
- 7项新专项CPU通过；只通过owner API读公开前态/因果forecast，未读offline actual标签、未新forward。证据`evidence/2026-11-12/recorded-v9-source-consumption-v1/真实B来源消费与坐标更正.md`及数值CSV。下一缺同query0.2/0.4效果、匹配阶段成本/误差/ready；新模型推理/物理不因本次消费自动授权。


### 最新实质交付｜2026-11-12 09:19：按新计划完成三候选数值选择器；真实排序仍无依据

- 已读《各小组下一步研究计划》，按其明确采用mission-v9/full4为共同研究参考，不再等待用户转交或“是否共同采纳”；保持owner原manifest/contract字节，未获物理准入。
- 在旧域/状态API之外新增`discrete_selection.py`：真正遍历0.2/0.4/0.6，计算退出后纵向支撑搭接/机器人分离必要余量与秒制准备＋PUSH含Finish＋后继准备cost；可返回完整三点模型内最佳、已评价子集最佳或UNKNOWN，未知不补0，目标不冒终态，预测ready不冒实际ready，永不释放动作。
- 有独立SHA固定的效果文件数值入口`select_from_bundle`，旧`native_domain_v0.py`及AINav已pin API字节不改。内部归一化布局不是另发技能ABI；WM有源字段仍需显式映射，不能猜center=front或借历史future。
- 9个明确合成数值案例/27候选行的修正结果：分别能因cost/支撑/退出共同后果选择0.2/0.6/0.4，子集保留非全局语义，缺效果/仅目标/缺秒数返回UNKNOWN。25项新专项通过；这些不是机器人排序或科学收益。初次runner误改来源角色的bug/原结果完整保留，修复打包并加回归，结论只用numeric-cases-v2。
- R2实际决策价值仍UNKNOWN：本轮真实决策前输入/因果查询0，所查同版本有源名义数值0；三点enum不认证效果，历史0.6不填当前预测。公开能力声明表和synthetic结果表分开，不伪造native三次查询。
- R3一次有界源码复审：native PUSH entry不仅catalogue固定.58，consumer也直接拒绝非.58，故不能只改JSON开放；底层moving_exit flag存在也不等于v0已有第二个可优化合格模式。当前仍三点枚举，不重开SLP/SQP新算法主张，不重复大审计/扩样本追胜。
- 主报告`evidence/2026-11-12/native-v9-discrete-selection-v1/NATIVE_V9_DISCRETE_SELECTION_AND_RESEARCH_DECISION_20261112_CN.md`；因docs≤5约束将计划拟议报告同名放evidence，未新增第六docs。无GPU/物理/真实API/WM/Actor/训练/渲染/远端/子agent/commit/push，旧A/B负结果、180条No-Go和closed roots保持。


### 阶段更新｜2026-11-12 01:22：已消费WM现有技能v0，真实域收缩为三个离散推距

- 新到WM合同/manifest已只读消费并独立pin，采用范围仅本组CPU参数域参考，不代表共同部署/物理准入；不再以“尚未收到manifest”作为当前缺口。
- 原生暴露推距只有0.2/0.4/0.6m；入口standoff固定0.58m，无独立base准备/退让/EXIT参数。解析连续(d,p,r)不lower为真实权限，底层0.8不越权，连续敏感度不编造。
- 新增只读`execution_preparation/native_domain_v0.py`及10项标准库专项测试通过，生成固定对象的三个参数模板，不伪造观察/原生请求；版本/权限失配拒绝，缺后果保持UNKNOWN/best=None。
- 当前缺口转为本次公开观察下逐候选的终态/耗时/next_ready/接续余量和依据。owner predict按交付仍NOT_READY；本轮未调用predict或初始化其历史档案验证，不读历史效果/选0.6旧成功作预测。
- 三点域的合理强基线应为同信息/约束的完整枚举，连续SQP/局部投影仅保留解析测试，不能转称原生方法收益。额外自由度需共同executor明确修订，不由本组擅改控制/JSON；不等新Sim2Real。
- 证据`evidence/2026-11-12/native-domain-v0-consumption/现有技能域消费与研究范围收缩.md`和`consumption.json`/`tests.txt`。0新增远端/GPU/物理/API/WM/训练/渲染；先前180条CPU No-Go和旧A/B负结果保持。


### 最新阶段交付｜2026-11-12 00:31：接续约束CPU原型与五法对照闭合；当前新算法主张No-Go

- 按11月12日新指导，研究优先级转为操作前箱位—准备—退出联合决策；现有技能优先，不等Sim2Real、不改控制/训练。本轮只在本机既有环境做解析CPU，不连接远端、不调用GPU/物理/Actor/WM/API/渲染/子agent。
- 实现独立`execution_preparation/continuation_cpu/`：解析共同物体/机器人退出后果、阶段余量/精确敏感度、问题/模式/有效邻域绑定、余项收紧、局部联合LP与恢复、完整复核incumbent。复用既有PHE tightening；缺界/跨模式/邻域失效返回UNKNOWN，空内域不判全局无解。
- 15项针对性测试通过，18个解析例×2数值种子×5方法=180条原始结果闭合。共同起点/信息/约束/预算（≤96完整评价/3wall s），含joint SQP、交替SQP、均匀黑箱搜索、保守局部投影、无余项线性反馈；不是18个机器人场景或任务成功率。
- 模型可行次数依次36/36、32/36、36/36、36/36、36/36。候选完整评价中位58次、joint SQP28.5次；候选总wall3.966s、joint0.089s，cost近数值参考。**候选未胜过强基线，当前是标准保守SLP应用，不作为IROS新算法贡献。** 广义Benders/多原生模式未实现，不用stub冒完成。
- 保守候选4603次局部预测可行查询无完整模型反例；无余项线性反馈4367次中1488次近似误判，但所有方法最终incumbent均完整复核通过，不能把局部误判当实际不安全动作/独立统计。三种修复结构由解析必要条件与见证核对，不是错误码→固定位移规则。
- 解析d/p/r域只是求解单元测试假设，不是原生权限。所核本地入口尚未接收统一执行包manifest；当前p/r lowering、逐方案机器人/对象后果及前瞻误差producer仍NOT_READY/UNKNOWN，不推断他组/远端完全无文件，不用旧成功峰值校准。机器人任务骨架/接口需求已冻结为临时消费需求，未另发“最终技能ABI”。
- 证据`evidence/2026-11-12/continuation-cpu-v1/最小优化问题与算法差异.md`、`per-instance.csv`、`raw-results.jsonl`、`protocol.json`/源SHA、`repair-structure.json`与`result-validation.json`。首次事后验证误用无numpy的system Python已保留错误，改用原项目环境验证，未装包/重跑比较。
- 11月5日A成功/B未完成的物理负结果、strict=False、旧16/16及closed roots继续保留。无新物理资格或自动队列；首轮有界包已交付，不扩合成规模/调参追优势。


### 最新闭合结果｜2026-11-05 23:29：A成功、B未完成，不是整体收益

- 一次A→B已经结束，无重试/新队列。A完整任务成功151.72sim，B在81.72sim停止，错误为原`No current public capability`。完整launcher wall为531.444/312.871s；B提前失败的sim/wall/API少不能算效率收益。两个新main＋各自1附属原标定world6.505sim如实记录，不复用旧16/16。
- 局部干预确实消费：干预前612条stow状态逐JSON一致，B选direct同compact，实际运动12.565→11.945s（少0.620s/4.93%）、原4s终态两臂通过，优化wall0.146710s。只是H-only，不是完整F7，不是动态安全/论文主贡献已证。
- 后续实际语义意图不同：A `PUSH-B-0.6`、B `PUSH-B-0.2`，随后都CLIMB:B。B PUSH/NAV/CLIMB:B成功后，原公开B→HIGH gap[0.025,0.775]m拒绝下一CLIMB，UNKNOWN-XY同0.6m任务NAV也不适用于当前0.2m支撑，原provider停。已用本次公开belief＋冻结原函数CPU复算，0物理/0API；不能将失败唯一归因于shortcut或擅自改LLM路线/阈值追成功。
- 两臂原生连续视频已取回，192×128/10fps，A1518/B818帧，真实相机即时编码、无重建/补帧，ffprobe及原报告/视频SHA一致。原strict=False保留，不把B短回合的累计越限数当更安全。
- 证据`evidence/2026-11-05/phe-old-pass-runtime-v2/actual-pair/实际A-B结果与下一步.md`及`actual-pair-comparison-v3.json`。新秘密入口只stdin→env，未落盘；任务子进程已结束，用户应撤销/轮换聊天曝光凭据，勿复述。
- 下一步CPU主线：明确真实上游准备自由度与高层给定接续条件，逐准备匹配操作后果/公开可用修复域；缺前瞻界仍unknown。原拓扑veto/两路径shortcut不是创新；本对未证明F7或整体导航收益。不补跑、不用缓存LLM路线重放；新物理另立协议/预算。


### 当前实际执行｜2026-11-05 23:09：一次A→B主对照已启动

- 用户提供本实验凭据后，通过关闭终端回显的stdin→远端内存→子进程env传递；未写密钥文件/源码/argv，未独立付费探针。原key已在聊天曝光，应由用户在实验结束后撤销/轮换，勿在后续摘要复述。
- 23:06重新核release v3、全部main freeze inputs、runtime/pair入口SHA及原三个锁；全部相符/可用，两个main此前无claim。23:08:23 detached一次A→B启动，supervisor PID1516820，whole-pair上限14500wall，各臂原7200wall/420sim/12API/65536tokens不变，无重试。
- 23:09实况：A已有pair/own-wrapper/attempt claim，正在原push阶段（physical约11s）；B尚未启动。没有任务或优化收益结论。严重A错误按冻结runner停B，不重开/补seed。
- 唯一干预仍是H-only原卸载捕获边界的同compact路径优化；不是完整F7上游base/arm/support。原strict=False边界保留；原生连续相机直接编码开启，不从日志重建。
- 本地执行记录`evidence/2026-11-05/phe-old-pass-runtime-v2/actual-pair/launch.json`；远端own release的`control/stdin-launch.json`和`actual-pair-launcher.log`。下一只读跟踪本次精确作业，收实际report、PHE触发、原生视频和全成本；不重跑已有zero/CPU，不写他组账本。


## 理论补强：误差管、连续路径覆盖与有限候选联合优化｜2026-10-21

**完成的是推导和CPU代码，不是新物理成绩。** 针对用户“理论太弱，需要公式充实”，在原IDEA第16节补充明确假设/证明：将相对平移/姿态、关节跟踪、路径采样间隙及未表示几何误差统一成管界；按该误差同时扩大yz候选与x需求，给出连续被表示点轨迹的方向分离充分条件；最后在同一最终输出处拥有支撑/储备见证的有限候选中最小化名义全成本。不再只证明“多退几毫米”。

**复用与边界：**已有rigid_pose_error_bound/robust_request不重复发明，新preparation_theory.py仅补采样覆盖/误差组合及有限集合选择。标准扰动界/Lipschitz/枚举最优不是自动原创；没有可靠前瞻误差、全域Jacobian/路径界或最终输出支撑见证时unknown，不能当真实动态安全/成功或超过参考论文。T6未接在线规划，旧物理与视频成绩不改标。

**软件验证：**23项新测试＋7项旧误差管回归通过，包含终点通过/中段侵入的解析反例、误差扩大yz成员、64个合成支撑表穷举一致性、非单调支撑及较小搜索点见证不能借给较大最终输出。全部只是合成代数/模型反例，本轮0FK/SDK/actor/物理/训练；没有读保留后果或调阈值。原父预算实际16/16、无新任务启动。

**下一步（未完成）：**先确认可计算全域界与真实接口的适用域，补原生最终候选支撑/储备见证和名义成本来源；有了独立上界与新协议后再评价误拒/准备失败/任务全成本。现阶段仅称“条件性鲁棒准备理论框架与软件验证”，不能称新任务收益、动态安全证书或论文创新性成立。证据`evidence/2026-10-21/conditional-preparation-theory-v1/`。

---

## 原生录像已完成并核验，实验已停止｜2026-10-21

用户要求的单次摄像机演示已正常结束，rc0；实际任务NAV→PUSH→收臂→共同NAV目标完成。原片已同步：`../artifacts/go2-piper/native-recording-demo-20261021-v1/run/native-run-original-speed.mp4`，SHA `6c90641db0dcf480176e3ce905a1df2051feaf91ca6af782b43f37f7c27f4526`。这是本次Isaac实时render的原生画面，不是日志重建或不同reset拼接；960×640、H.264、10fps、625帧，625帧均非黑，容器62.50s、实际最后状态62.38sim秒（差异为恒定帧率首尾显示时长）。35s帧从该MP4提取并目视确认狗/臂/箱可见，原始帧时序与raw SHA通过。

阶段：0～23s接近/停稳/机械臂准备；23～40.58s实际PUSH；40.58～49.5s退出/收臂；49.5～62.38s返程NAV与停稳。物理运行墙钟553.475s，原生render开销约9.925s；本次摄像机条件不同且重复已曝光120601/P3，只作用户演示，不补原研究批第六格、不计独立方法增益。

原研究批按用户要求停于5已执行/1未运行，当前无该批在途case；录像监督器1325691和子过程已结束，下载器942367已完成；不再自动启动任何任务。预算原2＋旧8＋本研究5＋录像1=实际16，总净预约16，原未跑slot的释放/转移记录保留。新源f7b24d94…5f257d及本次SDK/原片证据见`evidence/2026-10-21/native-video-requested-v1/final/`。

---

## 用户要求已执行：当前回合收尾停批，单次原生录像已实际录制｜2026-10-21

**旧批次已停：**用户明确“跑完这次停下来，然后跑一个带录像配置的”。只暂停原续接scheduler1324683，未向实际timeout/Isaac进程发信号，保留原1795s超时。当前120603/P2自然完成后读取真实退出状态0及原生终态，最后仅结束调度器并逐条收尾。原六格现为STOPPED_USER_AFTER_ACTIVE、5/6启动/闭合、active空，最后120603/P3未运行；原结果/失败分母不改，不把录像演示补成第六个研究配对。

**单次录像源：**新source SHA `f7b24d94679b7fa6ff4d5bcffb443a55b2ce9ee73b3c64326d324deab95f257d`、protocol SHA393d37c7…0d4ef，远端 `/mnt/yuanyue/data/go2-piper/native-recording-demo-20261021-v1`。用户指令绑定1次新源SDK0env≤180s＋仅1次原生录像演示；本次SDK47.848721s实际PASS、0env/actor/physics，四角色/原CFG与新viewer配置核验通过（有私有FK，SDK不是录像成功）。无重开旧SDK。

**已开始真实录制，不是计划：**supervisor1325691，物理timeout1326146。15:51:41快照已记录175帧，原生帧时间0～17.4sim秒，960×640、10fps，直接读取当前运行`env.render(rgb_array)`串流MP4，不做MjData/log状态重建、不拼接reset、不加速。按帧验证render未改关节/root状态或控制时钟；原始画面无事后重建。控制器/prospective/support/安全门保持原字节或AST，新增仅viewer/实时录制与记录开销。

**用途与预算：**录像使用已曝光成功起点120601/P3，明确是用户要求的可视演示，不是新独立验证或新增方法成功样本。旧六格reservation原文件不改，追加unused-slot-release-for-native-video.json释放原未跑120603/P3的1个slot，再新预约demo1；账本原2＋旧8＋旧批5＋demo1共16，净预约2+8+6−1+1=16，没有扩额。8项新CPU测试验证源/控制不变、原生帧采样、render状态守恒、单SDK和slot转移；均非额外物理回合。

**日志/PID/收尾：**原停批依据在旧root `user-stop-{after-active,physical-exit,terminal}.json`、`user-stop-drain.log`；新root `video-supervisor.log`、`sdk.log`、`physical.log`、`physical-launch.json`。原物理应用持family pose_app.lock，录像调度持新root video-dispatch.lock。只读下载器942367最长2h在结束/失败后同步到本地同名artifact目录并写video-ready.json，原片在`run/native-run-original-speed.mp4`、逐帧来源在`run/native-video-frames.jsonl`。旧只读报告器933014已结束，未停止任何物理实验。

**下一步：**让唯一录像回合完成后就停，不自动启动第二次；完成后核验容器/帧数/可见性/连续时序并交付原片。录制若失败如实保留，不自动补跑、不重建替代。当前只有正在录制证据，不能先称完整视频或任务成功。证据`evidence/2026-10-21/native-video-requested-v1/`。

---

## 原剩余三格已显式续接：不重复SDK／不重跑已完成格｜2026-10-21

**实际阻塞已处理：**原队列在前三次全部闭合后因GPU占用停止（STOPPED_GPU_BUSY_UNSPENT_RESERVED），不是技术/安全失败；停止账本原SHA `8403603a8425e0b8e2c7056e93ab4233749029135749fc7bc40c1bbd481d13af`逐字归档。用户最新“行了，继续推进我们的”触发显式续接，GPU空闲后只执行原not_run三项，原scope/source/顺序/预算不变。

**已实现与验证：**新外部续接监督器仅接受精确三格闭合且资源停止、active空、前三格claim/raw SHA/原生评价一致、后三格无claim/output、原SDK PASS/approval/reservation/source/外部权重齐全。拒技术/安全停止、孤立claim、错序、旧文件漂移或重复调用；仍持原dispatch.lock和family pose_app.lock，使用原source内run_one/argv/make_permit/评价函数。11新续接＋4新只读报告测试和既有34项共49项CPU测试通过；fixture调度不是实际物理。

**真实执行：**15:25:48启动续接supervisor1324683；15:27:58快照累计4/6启动、3闭合，120602/P2在途，timeout1324688/child1324689，控制记录到13.44sim秒。旧三次原条目完全相同；本次新物理启动1（首个未跑格），SDK新增0、预约新增0、训练0。父实际消耗旧2＋旧8＋当前4=14/16，总预约仍16；原剩余两格尚未运行。冻结source仍149ac2b4…21054b。

**来源/锁/日志：**远端root `/mnt/yuanyue/data/go2-piper/native-pose-singlefactor-six-20261021-r2`；`continue_unstarted.py`在source外，sha f696a682…7f36ee3；`continuation-launch.json`、`continuation-unstarted.log`、`continuations/explicit-unstarted-v1/{authorization-and-owner.json,state.json,stopped-ledger.original.json}`。运行锁仍root `dispatch.lock`与原family `pose_app.lock`；新claim使用原allocation `native-pose-singlefactor-six-20261021-v1/physical_claims/`，未重置reservation/SDK。每个case仍用原seed*-P*.log和*-launch.json。旧approved_queue_state是已结束历史，最新以physical_ledger及continuation state为准，不重启旧queue。

**只读收尾：**新reporter933014最长2h跟随续接，输出本地r2 root `comparison-continuation-1/`的全6格任务/机制/成本JSON、Markdown及HTML，并一次性更新本组进展/计划。旧comparison和mechanism-final是原3/6资源停止快照，保留不覆盖。原reporter906943/机制后处理908977已完成，不再续用旧终态触发器。

**下一步：**让唯一续接按原门收尾，发生新的技术/严重安全或资源停止则保留余项不自动重试；完整后看三个配对的输入匹配、实际选择/消费、成功/失败与全成本，模型余量不替代任务收益。不恢复模式A、不读取5311/5312、不改其他组用途/账本。证据`evidence/2026-10-21/native-pose-six-continuation-v1/`。

---

## 新六格首配对：已证动作改变，尚无任务成功增益｜2026-10-21

**新完成事实：**seed120601的P2/P3两次真实Isaac任务均闭合成功；实际初态与决策前规划packet SHA相同。P2几何请求5.548672mm→原生重算选择15mm；P3请求13.043253mm→选择20mm，原支撑输出均0。两边控制器目标消费已由同query/step控制记录核实。因此不是仅分数变化，本配对确实出现额外5mm准备退让。

**收益与代价分开：**该配对成功差0；sim62.36→62.38s（+0.02s）、wall489.340→498.512s（+9.172s）。共同final_actual固定yz有限云的box-local-x方向余量13.900474→19.032124mm（+5.131650mm）。该余量不是全身欧氏净空、真实接触净空、跟踪误差界或动态安全证书；两条成功不能推出更稳健或普遍成功率提高。此前8格零动作差异和负结果保留。

**实际在途范围：**14:12:29+08:00快照新3/6启动、2闭合，seed120602/P3在途；完整六格主效应仍None/不可估计，不把后续unknown补0。唯一远端queue1321718/physical supervisor1321982继续原协议，不重启、不改冻结source149ac2b4…21054b、不新增物理或训练。此时父实际启动旧10＋新3=13/16，预约仍16上限。

**新产物：**只读`native_pose_followup/analyze_mechanism.py`，对全部注册行分开记录动作/控制器消费/全成本/有限模型余量；报告保留in_flight/not_run而非挑首个成功当整批。9项新报告测试＋25项已有followup测试共34项通过，均为软件，不新增FK/演员/物理样本。首配对报告`evidence/2026-10-21/native-pose-six-first-pair-v1/report/实际技能机制与效果.md`及HTML/JSON；输入raw SHA已留证。

**收尾：**现有只读watcher906943不变；另只读机制后处理PID908977最长4h等它生成最终comparison后，在本地r2 root的`mechanism-final/`生成全批成本/动作/余量报告，不启动或停止实验。问题页、旧source/raw/ledger及他组用途不动。

**下一步：**原剩余格按已有授权执行，完整或具体中止后核输入匹配、是否形成动作差异、原生失败与全任务成本。当前只能写“已出现真实机制响应”，不能写“已证明导航收益”；不要因尚无收益换seed/弱化支撑/继续扩批。

---

## 用户已批准运行：r2 SDK通过，新六格实际启动｜2026-10-21

**授权/来源：**用户针对精确请求回复“运行”。已为source `149ac2b4c25138b035efc68fccb948c544bdab4e842426d080b75ee27821054b`、protocol `1b1b241ae8fe9e0bcf910c1a0a40d1847da315120531ccfc189ff6f0d9ba5b48`绑定一次SDK0env≤180s＋通过后原余额6次；approval SHA `aef5d1450d8fe40cd48339388c5a4fbff718862043ae67312f330c3855f1ab40`。下方“待批准/未启动”现在是历史；本轮不再等待同一授权。

**实际完成：**SDK 1/1已运行26.534801s，rc0、最终gate_passed=true；229项原源inventory、实际CFG、P2/P3×planning/final_actual四角色、共同最终验证与状态恢复通过。SDK env/actor_loads/physics_steps均0，但有私有几何FK；合成far-box/参考adapter不代表新场景动态成功或实际参考freshness认证。冻结源未修改。

**实际在途：**2026-10-21T13:52:30+08:00快照，新1/6启动、0已闭合，seed120601/P2真实初态已落盘，控制记录到step678、13.56sim秒；无任务成绩可报告。三新初态/六格顺序不变，普通失败保留、技术/严重失败停后续，无重试/换seed/自动扩批。旧2＋旧8＋新已启动1=实际11/16；新6次reservation已创建，原剩余额全部预约，总上限仍16，没有增加物理总量。

**PID/锁/日志：**远端root `/mnt/yuanyue/data/go2-piper/native-pose-singlefactor-six-20261021-r2`；queue1321718、physical supervisor1321982、首case timeout1321987/child1321988（均以root launch/ledger为准，不据本文快照重启）。锁为root `approved_queue.lock`/`dispatch.lock`及原family `pose_app.lock`；reservation/claims位于原family `pose_allocations/native-pose-singlefactor-six-20261021-v1/`。日志root `approved_queue.log`、`sdk.log`、`sdk_supervisor.log`、`physical_supervisor.log`、`seed*-P*.log`；`*-launch.json`记录实际PID/命令，物理完成后ledger绑定原始SHA。旧账本/source/raw不改。

**只读收尾已安排：**本地watcher PID906943，最长4h，仅同步已闭合case并生成`../artifacts/go2-piper/native-pose-singlefactor-six-20261021-r2/comparison/comparison.json`和`研究效果对比.md`，一次性更新本组进展/计划，不动问题页、不启动App、不重试任务。watcher源码有新增2项测试，全部followup25项＋queue6项软件测试通过；模拟runner不是物理实验。

**下一步：**让唯一队列按原条件收尾；有最终或具体中止才评价。比较共同目标全链结果、真实query匹配、准备动作/控制器消费和全成本；输入缺失或不等不归因公式，unknown不填0。无动作差异不自动扩此姿态项。证据`evidence/2026-10-21/native-pose-six-approved-run-v1/`；这不是已完成六格或已证明正增益。

---

## 新六格实际技能协议已组装并stage，尚未启动｜2026-10-21

**本轮完成：**新增`native_pose_followup/`组装器、场景配置/被动动作见证、六格只读评价器及23项CPU软件测试（全过）；12项既有影响条件回归也通过。本轮没有FK/积分/SDK/演员forward/物理回合。测试中的六次调度为临时目录内的合成runner，不是机器人实验。

**精确候选：**source SHA `149ac2b4c25138b035efc68fccb948c544bdab4e842426d080b75ee27821054b`，protocol SHA `1b1b241ae8fe9e0bcf910c1a0a40d1847da315120531ccfc189ff6f0d9ba5b48`；本地`../artifacts/go2-piper/native-pose-singlefactor-six-20261021-r2`，远端`/mnt/yuanyue/data/go2-piper/native-pose-singlefactor-six-20261021-r2`均已stage并核SHA。v1草稿9e5fb7…952a9e1因case-id来源前缀与原始见证哈希记账完善而由r2取代，原包保留且未批准/未启动，不覆盖它补结果。

**冻结的开发对照：**seed120601/120602/120603，箱体默认世界x偏移分别0/−14/−28mm，每个初态P2全路径平移对P3全路径姿态参考，共6次；顺序P2,P3 / P3,P2 / P2,P3。偏移在configure后、gym.make前写配置，原生±30mm平面/±0.04rad yaw扰动、推箱目标随真实reset更新逻辑均保留。不是运行中移动物体，也不等于上轮固定query的局部x触发窗口；实际场景/触发仍未验证，不保证方法获益。

**控制与评价边界：**原控制器/Router/actor/PD/支撑搜索/最终实测门逐字或AST保持，仅main的初态/原始记录及prospective_entry被动见证变化；不改安全门。每次正式回合内记录真实初态、共同query、原支撑输出/实际选择，终态ledger绑定report/control/初态/geometry SHA。无须先额外采样筛新seed；所有注册失败、拒绝和未触发留分母。只读评价把全链结果与输入配对可归因性分开，缺数据为unknown，不把六格未运行写成0/6成功。

**远端真实状态/预算：**旧8格COMPLETED_REGISTERED_EIGHT且active=null，ledger SHA81c3129e…e91485a；原old2 ledger SHA831cc68c…842997未动，已有预约仅8次。新r2目录仅source和NOT-APPROVED请求，实际缺approval且准入明确拒绝；没有新allocation/claim/App/PID/运行锁/日志。这里只核本组，不宣布其他组无作业。待运行日志路径会为root/sdk.log、root/seed*-P*.log与root/*-launch.json，实际尚不存在。

**唯一待用户确认：**是否为该精确r2源批准1次SDK0env≤180s，通过后显式分配原剩余6次物理额度（3初态×2方法；父物理总上限仍16）。此次没有自动写approval或预约。技术/严重安全失败停后续，普通失败保留、不重试/换seed/扩批；SDK失败也不免费重启。证据见`evidence/2026-10-21/native-pose-six-preparation-v1/`。

---

## 实际技能研究增量：原生动作影响条件与解释器｜2026-10-21

**完成：**新增`native_influence.py`及只读报告器，将公式是否改变入口退让与已执行源55190212…83fd0a1的`prospective_entry`精确AST分支绑定。记原支撑输出为d₀、几何请求为m：m≤d₀直接复用baseline；m>d₀须调用原支撑搜索，并非简单max(d₀,m)。因而同一输入下mₐ,mᵦ≤d₀可证明入口退让相同；超过d₀仅是触发原生重算，不证明可执行、动态安全或任务收益。缺输入/域外/重算结局未知不填成功。

**新证据的范围：**将该分支命题应用于已曝光且已闭合8格的同query记录，8/8查询四种请求均复用原支撑输出；这解释已观察零动作差异，不是新增物理样本或泛化证据，也不推断未执行分支的结局。历史成功/失败、原支持约束和预算保持。

**验证：**12项新CPU软件测试通过（其中遍历511个非空合成支撑通过集合，共1533次baseline复用分支检查）；18项既有姿态/真实私有几何回归＋5项报告回归通过。后者实际进行了23634次CPU mj_forward，不能说0FK；没有SDK/App、演员forward、积分或新物理回合。

**新增的可检验设计条件：**固定机器人/路径/姿态参考、盒朝向与原支撑结果，只让盒沿自身局部x方向靠近δ，则所选有限点云最大x增加δ。由有符号最大值而非已截零请求解析得到“平移方法仍复用支撑、姿态方法需要重算”的δ窗口。两条已曝光P0查询的窗口分别约(9.745,17.210]mm与(12.117,19.611]mm。这只是固定query下的场景设计代数，不是已采到的新状态；实际从不同箱位启动会改变机器人轨迹，必须在真实准备时刻重验，不把窗口或中点当安全/成功证据，也不按旧成败挑选新seed。

**下一步而非完成：**下一物理比较收敛为P2全路径平移对P3全路径姿态参考的单因素对照，不再重复四臂8格。先闭合合法新初态在真实准备时刻的共同query/原生重算结果与预算；按决策前机制分层保留负对照，所有注册失败、未触发与拒绝仍留分母，不换seed追正结果。当前没有已验收新初态，也没有新协议授权，剩余6次不自动占用；若新增项仍不改变动作，就停止扩这条姿态退让线，不删支撑约束造效果。

**产物：**`evidence/2026-10-21/native-entry-influence-v1/研究结论与下一轮接口.md`、`analysis.json`及三份软件测试记录；原始source/raw未改。不恢复模式A，不维护问题页，不改变其他组代码/账本。

---

## 最新决定：撤回模式A，恢复实际技能研究主线｜2026-10-21

用户明确要求“退回我们之前利用实际技能去研究的版本，删除模式A的方式”。本节覆盖下方历史在途快照和模式A联合研究建议；不是回滚整个Git仓库，也不是抹去原结果。

- **研究主线：**沿用真实Go2＋Piper技能/控制器执行的任务与状态条件Reach研究，基于实际Isaac NAV→PUSH→stow→NAV链研究几何、姿态、路径与技能接管条件；论文目标仍是对整体导航的可复核增益及受控消融。不得将这个局部链夸为已实现完整穿障碍导航或实机验证。
- **撤回内容：**本组不再开发/接入模式A理想化执行平台，也不以oracle未来诊断或代理技能实验作为当前推进路线。两个未验证接口草稿已从research活动源码删除，仅在仓库外保留撤回快照及SHA；没有模式A实验成绩可保留或转用。世界模型组独立方案不由本组删除或改写。
- **最新已完成事实：**55190212ff9b6cafcd9536a0c6397fc1132b1d9505cde2a6c838b5d9883fd0a1源的新8格已全部闭合；P0–P3各1/2成功，seed120501均push_timeout、120502均成功。准备选择未改变、姿态项被原支撑需求覆盖；本批未证明新增姿态项增益。旧失败、原始日志与曝光身份不改，不重复运行。
- **预算/范围：**原旧2次＋新8次共10/16物理消耗，剩余6次未分配，本次切换不启动SDK/训练/物理、不重启或终止作业，不扩大预算。原始source、actor、PD、观测/动作契约和安全门保留；不另训PUSH或重复WM，不读5311/5312后果。
- **下一步（未完成）：**以既有实际技能源码和已曝光开发轨迹为起点，核清现有Reach公式进入哪个真实控制/接管决策、候选能否被实际执行器消费；优先形成一个可执行的单因素方法/原技能对照方案。先闭合源码、输入、共同安全门、任务目标、评价与新实验预算，再运行新的物理实验；不得为了获得效果删原支撑约束、改失败标签或换seed追正结果。

撤回记录：`evidence/2026-10-21/mode-a-withdrawal-v1.json`。本节是路线修订与现有结果确认，不是新方法已实现/已验证声明。

---

## 最新接续：授权已生效、SDK通过/新8格在途；整篇IROS定位完成调研｜2026-10-21

**先纠正旧“待授权”：**用户明确“继续，没有遇到重大决策都默认同意”，本组按原已提出范围绑定55190212…83fd0a1源：1次≤180s新SDK＋门通过后原14余额中的8次，总物理仍16，余6未自动分配。2026-10-21 01:39:42批准文件SHA `e160e413…e51630`已落盘；原request-NOT-APPROVED文件只作历史。日常实现/修复/已登记预算内工作不再逐项请示，重大方向/安全/实机/显著扩预算仍确认。

**已发生：**新SDK1/1真实耗25.903457s、rc0、完整8-role/CFG/真实私有几何检查＋最终JSON gate PASS，SDK总消耗变为3。fixture是合成far-box/target adapter，不是实际动态成功或真实target时序证据。现有物理supervisor1312174已串行启动；快照`2026-10-21T02:38:03.253172+08:00`为starts6/8，已闭合4格seed120501/P0–P3均push_timeout（71.48sim），120502/P1在途；这不是完整注册主效应，更不是正增益。原旧ledger仍2/16、14not_run/hash831cc68c…842997，只新增独占8次reservation；父预约上限原2+新8=10/16、余6未分配。

**在途/源/锁/日志：**远端root `/mnt/yuanyue/data/go2-piper/pose-entry-gated-release-20261020-v1`，source SHA55190212…83fd0a1未改；只读资源队列PID1311909、物理supervisor1312174。root `approved_queue_state.json`/`physical_ledger.json`及各`seed*-launch.json`才是最新PID/状态来源，不按本段旧快照重启。root `approved_queue.lock`、`dispatch.lock`与原family `pose_app.lock`按各自阶段持有；8次reservation/claims在原family `pose_allocations/pose-entry-global-goal-20261020-p1/`。日志为root `approved_queue.log`、`physical_supervisor.log`、`seed*-P*.log`；普通推箱超时保留失败，技术/严重安全停后续，不补跑。

**晨间效果对比已实际安排，不保证正结果：**本地只读watcher r2 PID872156跟随上述唯一队列，原r1仅因增强报告因果解释而停止，物理/SDK/远端队列未被停止或重启。r2只同步已完成case，最终或安全中止后写`comparison/研究效果对比.html/.md`与JSON，并一次性置顶本组进展/计划，不动问题页。[固定报告入口](</home/yuanyue/re-nav -piper-manipulation-reachability/artifacts/go2-piper/pose-entry-gated-release-20261020-v1/研究效果对比入口.html>)已存在，最终文件生成后自动展示；原control/query/report保留。报告比较全部8格、同初态有无姿态参考、完整耗时/96s失败惩罚、几何项是否超出原support-only及控制目标实际消费、已记录查询输入是否相同；若准备选择相同，不把偶然完成差异归因公式。watcher最长5h只读等待，超时给partial、不杀实验，不恢复旧自动化。

**本轮独立调研结论（建议，不是改实验指令）：**三组方向足以构成一个统一IROS选题，但现有新颖性/实证还不足投稿。最接近工作已包括OmniNav、MMDirector预测可达性世界模型、NWM与操作可行NAMO；“WM+Reachability”本身不新。当前WM拟4/6kg、摩擦.4、推.5m不能与v317原1kg/.15/.6m旧成功直接拼表；新视觉WM独立训练/选择收益、同WM上Reach增量、完整路线接口和实物部署证据仍需补齐。Sim2Real旧PUSH8/8和CLIMB3/3开发完整链保留，不宣称从未跑通。整篇框架/文献/证据缺口见原论文草稿第13节与`evidence/2026-10-21/iros-paper-positioning-v1/assessment.json`；只推荐一个统一规划器：WM预测、Reach评价、Sim2Real执行，不各选一次。

**下一步：**现有8格先按原安全/预算完成并读取自动完整对比，不用这里的局部结果冒WM+Reach整体导航证据。与用户对齐第13节共同主张后，优先统一任务/动作域/物性/执行器与预测-评价接口；未来主消融应固定WM比较有无Reach，并保留控制器参考姿态/强反馈规则等强对照。没有因本次调研新开训练、物理或预算，不修改他组数据身份。最终报告/新主记录若比本段更新，以其实际终态为准。

---

## 最新：新SDK准入/8次分配调度/评价器代码已闭合，source已stage，实际执行待授权｜2026-10-20 22:55

**本轮实际完成：**在前轮姿态输入＋共同最终复核基础上，新增真正source-bound release，不再是无条件禁止运行的CPU-only快照。已实现SDK检查器（实际probe定义/CFG前缀、原源清单/私有几何、P0–P3规划/共同实测8角色检查、报告先落盘再native close）；其action-manager输入仍为明确合成adapter，不能声称已验证真实target生产时戳/实际跟踪。实际probe/SDK脚本均要求精确源码授权＋单次ticket，在任何Isaac导入前消费；无授权直接入口不能绕过supervisor开App。

**预算/调度实现：**旧`physical_ledger.json`和14not_run只读/hash锁定，新8次另写`pose_allocations/<allocation_id>/reservation.json`及独占claims；包括尚未消费的预约也计入父16 cap。授权必须显式1次新SDK≤180s＋8-of14重分配/0额外物理；旧原16批准不自动变成新批准。启动前校源/权重/GPU，记录supervisor/timeout/child/PGroup/source/log；SDK175+5/物理1795+5墙钟、原96sim/16sreturn/48sPUSH/单GPU串行保留。每case claim先于App，不自动重试/替代/重置余额；任意缺报告/源错/未处理异常/严重安全停后续。仅在新协议下，有完整原full-cloud+同query FK guard/最后control步一致的`entry_final_preview_refused`才作为失败保留后继续；旧E1 runtime_error/停派绝不更名。

**评价与CPU验证：**新8格评价器保留not_run/unknown，完整前不算主效应/成功点率；success仍需共同world goal原稳定/收臂门＋共同实际复核，最终拒绝是失败不是安全成功。29项新授权/锁/预算/票据复用/缺证/停止/评价/SDK结构软件测试＋5项旧durable regression共34通过，全部在临时合成目录/子进程，不是实际App/FK/实验。新增测试曾有一处引号SyntaxError（测试未执行即停），原日志保留，修复后全部通过；无运行结果被洗掉。本轮0新App/SDK/物理/FK/actor/训练。

**精确source/未启动事实：**最终release SHA `55190212ff9b6cafcd9536a0c6397fc1132b1d9505cde2a6c838b5d9883fd0a1`，protocol SHA `e0e083fffe67c28d10dd0d800fbf699d3de68b73e710e2dbbcc3204e808830a9`；本地`../artifacts/go2-piper/pose-entry-gated-release-20261020-v1/source`，远端`/mnt/yuanyue/data/go2-piper/pose-entry-gated-release-20261020-v1/source`只stage。22:53:24远端4入口（probe、SDK checker、supervisor sdk/physical）实际plain-Python均在App前拒绝；无approval、无sdk_result、新physical_ledger/预约/claims均不存在。只写了`execution-request-NOT-APPROVED.json`，不是执行授权。无本轮在途PID/活动锁/运行日志；原family ledger SHA仍`831cc68c…842997`、2次物理/14not_run、SDK2/2，未新占8次。远端source成员SHA已核对；原有CPU-only v1–v3及全部历史保留。

**证据/下一步：**`evidence/2026-10-20/pose-entry-release-admission-v1/`含源码manifest/protocol、未批请求、34项测试、远端拒绝与原账本SHA、8格全not_run评价。下一可执行动作已明确：用户批准此精确源的**1次新SDK≤180s＋门通过后将原14余额中8次绑定新2seed×4臂**，总物理不增加/原2＋新8最多10/16，余6不自动分配；拿到该授权才创建approval/启动SDK。门失败停止，不自动第4次SDK；通过后仍需源/资源准入再按原序派发。真实新角色消费/非零退让/支撑/READY/共同目标尚未检验，没有新增导航增益或完整穿障碍任务结果。只维护原5份docs/进展计划，不改问题页/他组数据用途。

---

## 最新：姿态规划＋统一实测复核已完成CPU隔离实现；执行准入仍关闭｜2026-10-20 22:14

**本轮已完成：**新代码`research/task_conditioned_reachability/pose_conditioned_entry/`已实际组装，不再只有离线公式shadow。基于已执行r2 manifest `169e0d15…6f4b518`复制到新目录；原controller/actor/PD/足锚/历史/clock、安全/支撑helper均不改，AST差异仅`prospective_entry`与`main`。新`planning`角色按端点/全路径×原平移/已有参考姿态P0–P3输出标量；每臂均建同样两云/四标量观察，不能宣传虚假算时节省。新`final_actual`角色始终使用原完整41×64云＋原fixed-yz算法，完全不读规划臂的参考姿态，并拒绝带nominal_translation/forecast margin的“实测”调用。

**CPU实际结果/范围：**18项软件测试最终通过；真实私有Piper几何的8个role-query（不是8episode）上，已曝光18.42s输入的P0/P2规划0，P1/P3规划5.085926mm；已曝光21.90s同一实测输入的四臂均1.387167mm，与当前私有几何上的冻结原helper逐项精确相同。私有qpos/qvel/ctrl/time恢复，source-hand模型与原preview误差0；这些都不是新Isaac环境或真实caller运行。直接使用旧记录云时仍是5.085884/1.387125mm，不改原记录。首轮CPU断言要求跨次计算1e-10m一致而因4.285916e-8m差异失败，日志保留；仅改单位测试数值比较（同日志代数仍13位、最终rule仍与原helper精确相同），原5mm margin/40mm cap/0.2mm source-hand gate完全不动。本轮所有版本显式私有mj_forward合计91910次，不能说0FK；0新App/SDK、0物理启动/积分、0actor/训练。

**共同复核/失败语义：**新主调用的最终门显式`evaluation_role=final_actual`。仅在新提案里把原“最终仍需退让”分支记为`entry_final_preview_refused`，仍在PUSH激活之前break并保留失败、原reason与所需量，不发下一命令或物理步；这只是被测新协议的CPU分支验证。原E1 runtime_error、旧全批停派、E0成功和14not_run一律不重写。错误时新selector保留捕获的完整原始输入/云，不丢拒绝见证。参考只声明查询前读到的既有last-issued controller target，其生产时戳/跟踪界仍unknown，不冒真正future pose或新freshness证书。

**版本/执行隔离：**最终CPU snapshot SHA `014e8474f1c25b19e8a2ae4f8515fc3472b2bbb1cb7a2acbc684264b1d0417ab`，本地`../artifacts/go2-piper/pose-conditioned-entry-CPU-20261020-v3/source`，已只stage到远端`/mnt/yuanyue/data/go2-piper/pose-conditioned-entry-CPU-20261020-v3/source`。实际本地及远端直接调用probe均在任何Isaac导入/App前被PermissionError拒绝；无approval，无SDK checker/physical launcher。它是CPU闭包快照，**不是可执行SDK/物理release**；旧snapshot v1/v2和失败测试均保留。无本轮在途PID/锁；没有启动/重启/杀任何原实验。

**预算与证据：**原family `reachability-native-entry-global-goal-20261020-v1`只读核仍starts2、active=null、14not_run/原技术停派；旧ledger SHA `831cc68c…842997`、SDK两次claim保留，无重新分配。新CPU源approved SDK/physical预算均0。轻量源manifest/protocol/patch、CPU summary/测试/拒绝执行证据见`evidence/2026-10-20/pose-conditioned-entry-CPU-v1/`，3.4MB原CPU云在artifacts对应`queries/entry_geometry.jsonl`。旧完整原始数据/保留身份和归档问题页不动，docs仍5份。

**下一步仅计划（本组可直接做的代码，不等main）：**补齐新源的实际SDK装配/CFG准入检查器，以及原14余额中8次的显式分配账本/串行launcher，保留父预算总16与旧ledger/14unknown，不能挪用旧16次supervisor。完成CPU授权/预算/停止条件回归后才冻结真正release并向用户绑定1次≤180s新SDK＋8次重分配的请求；本轮不先发App。新P0–P3物理结果、非零退让实际消费和完整障碍导航收益仍未验证；不能把CPU接口正确写成成功率增益。

---

## 补充：用户运行视频请求——已交付日志重建回放，非Isaac原录屏｜2026-10-20

原E0/E1运行未启用相机录像，已查本地/远端该source目录无原视频。按用户请求用原始control中的root＋18关节、仅已观测箱中心生成并排**离线运动学回放**：左E0完整61.42sim，右E1到21.90sim后明确END/最终preview拒绝，不延长物理结果。3倍速、21.5秒、1280×600/20fps/H.264；[本地回放视频](</home/yuanyue/re-nav -piper-manipulation-reachability/artifacts/go2-piper/reachability-native-entry-global-goal-20261020-v1/replays/logged-state-visualization-v3/rendered/e0-e1-logged-state-reconstruction-3x.mp4>)。箱朝向历史未记录，透明箱为轴对齐示意；首次实际观测前不补箱位姿。不是Isaac相机、不重跑动力学、不重算成功结论。

渲染使用远端独立MuJoCo环境＋Mesa llvmpipe CPU，未占用其他组GPU；4个同query手端模型核对误差均0。新增5项采样因果/无物理步和actor导入测试通过。原软件渲染v1光源API错误、v2几何组隐藏的QA失败和源均保留；最终v3已目视确认机器人和终态，430帧完整解码。包括QA在内产生2244次私有运动学更新，**不能写0FK**；0新SDK/App、0新物理启动/积分、0actor/训练，原SDK2/2和物理2/16/剩余14及停派状态不变。

原始/最终视频、逐帧source map和renderer日志留在family `replays/logged-state-visualization-v{1,2,3}/`，本地artifacts已镜像v2/v3；可交付仅v3。轻量元数据、SHA、失败/测试与预览在`evidence/2026-10-20/native-pilot-log-video-v1/`；视频不入Git。下一研究仍是新隔离包姿态条件接口/CPU闭包，不因视频请求重启原批次或授权新SDK/物理。问题页与其他组用途账本未改。

---

## 最新：先导2/16闭合后安全停派；E0共同goal成功，E1姿态预览拒绝｜2026-10-20 20:35

**真实结果已复核：**原调度器已20:11:17因第二格`runtime_error`停止，不是仍在途/16次全跑完。seed120401/E0于61.42sim完成共同world goal，最终xy误差31.708734mm、heading误差.041421866rad、原连续稳定.5s/全部exit gates/retracted_ready及0reset均核对通过；墙钟469.588308s。E1于21.90sim、墙钟164.708054s，原`measured_final_support_verification`仍需退让，抛`Forecast support reserve insufficient at measured final pose`，未激活PUSH。保留E1实际失败/原runtime_error，不记碰撞或力矩事故，也不改成成功。全16格保留：已启动2、已观察成功1/失败1、14未启动；仅这一seed的E0/E1观察差为−1，不估注册四seed主效应/总体成功率。

**具体诊断而非“再加余量”：**两次控制记录前1096行（step0–1095）所有已记录值完全相同，两次query输入/2624点云也相同，不证明未记录世界/隐藏状态一致。18.42sim初预测E0–E3请求均0；21.90sim实测云上E1请求1.387125mm，原5mm格点通过＋5mm reserve返回10mm（support-only仍0），故原最终门拒绝。E2/E3在同云上的离线标量同为1.387125mm，但它们没有物理运行/终态，不能填失败或成功。根源是翻译式forecast没有覆盖实际姿态变化：匹配云轴向位移最大[8.431004,1.461851,8.136313]mm，姿态转角.016761206rad；仅用记录的刚体变换重构误差7.30e-12m、0新FK。相位40/corner2点由forecast z122.310634mm（原120mm带外）进入实测z114.472209mm（115mm带内）；因此仅扩大world-x退让扫掠侧向集合不修复这次姿态输入缺项。

**本轮独立可复核产物：**新增离线终态核验/原始hash保护/前缀与云诊断、条件姿态管充分界与证明、仅用同query已有`stance_orientation_target`的姿态感知shadow；未改/重启冻结r2运行源。同query参考姿态shadow预测5.085884mm而非原0；首个可选原格点10mm、若原wrench可行则原reserve后15mm，但未评价该support/轨迹/终态，不写“修复已成功”。观测后反推epsilon不是在线界，未改原5mm门槛。12项新增软件测试通过（含已曝光反例回归），5项已有评价回归另列；0新App/physical/actor/FK/训练。本轮图先缺matplotlib，改用已有Pillow，未安装依赖；原失败记录保留。论文第12节含真实负结果、Entry-3/4公式/证明和新协议提案，图`stopped-pilot-pose-membership.png`只画记录云与标量重放。

**预算/源/PID/锁/原始证据：**SDK累计2/2，物理2/16、14余额未重分配，无自动第三次SDK/重试/替代seed授权。family仍`/mnt/yuanyue/data/go2-piper/reachability-native-entry-global-goal-20261020-v1`，运行source为`revisions/sdk-report-r2/source`、manifest `169e0d15b0ec0b23ff5b73f8d31745007834433a091388270e0f43e7c6f4b518`。20:29:04只读快照确认supervisor1308041、E0 timeout/child1308045/1308046、E1 timeout/child1308416/1308417均结束；r2/dispatch.lock真实未held，ledger active=null，未杀/重启作业。原日志在family `seed120401-E{0,1}.log`、r2 `physical_supervisor.log`；原report/control/cloud、claims/launch/ledger均保留并镜像到本地artifacts。轻量证据及原始SHA索引在`evidence/2026-10-20/native-pilot-stopped-pose-diagnosis-v1/`，正式派生用`stopped-pilot-diagnosis-final-v3.json`；v1/v2“无完整pair”措辞更正为已有单seed pair、尚无完整四seed消融，旧派生保留但superseded。

**下一步仅计划：**先在全新隔离包接入同query参考姿态的预测，分离规划选择与所有变体共有的最终原full-cloud复核，CPU核源/接口；不得续跑旧失败batch。具体新2×2开发提案已登记：端点/全路径×仅平移/已有参考姿态，共2新seed×4臂=8次；请求将原14余额中8次显式重绑定，物理总额不加，另需1次≤180s新SDK。该提案未批准、source未冻结、未启动；先闭合实现再绑定精确源授权。新协议才可将明确的最终preview拒绝记为正常任务失败并继续别格，原E1 runtime_error及旧停派绝不重写。没有独立整体导航正收益结论，不靠更多拒绝或已读反例自证。

---

## 最新：追加SDK已通过；原16次消融已串行启动，首格在途｜2026-10-20 20:02

**完成与授权：**用户在明确“追加1次零环境SDK≤180s，不加物理额度”的说明后回复“继续”。已为r2写入匹配manifest的独立授权，原失败包/缺报告事实不改；不再是等待SDK授权。追加SDK supervisor1307807、timeout1307810、child1307811均已结束，23.292970s、rc0、最终`sdk_result.json:passed=true`及`sdk_terminal.json:gate_passed=true`均真实留盘。实际probe/CFG、229项冻结训练源、真实私有几何/E2与原helper匹配、E0–E3恢复检查完整；fixture是历史q＋明确合成远箱，所有退让请求0，只证明装配/几何门，不是任务覆盖或方法收益。

**当前消耗/结果：**SDK累计2/2次（原1次失败缺证＋本次1次PASS），无第三次授权；物理仍原16次、未扩额。物理supervisor **1308041** 已20:00:40启动；快照 `2026-10-20T20:01:55.452673+08:00` 为 **starts1/16、0终态、1在途、15未启动**，首格`seed120401-E0`／`reach-entry-pilot-v1-E0-seed120401`，timeout/进程组1308045、child1308046，真实control已到8.06sim/step403、`native_nav`。这不是0/16成功率；全部16注册格保留，配对效应仍NOT_ESTIMABLE。后续原序列由现有supervisor执行，不重复启动它，不在在途时改源/换seed/调阈值。

**source/锁/日志：**远端family `/mnt/yuanyue/data/go2-piper/reachability-native-entry-global-goal-20261020-v1`，当前source为`revisions/sdk-report-r2/source`，manifest SHA `169e0d15b0ec0b23ff5b73f8d31745007834433a091388270e0f43e7c6f4b518`。family `physical_ledger.json`统一记原16次；`claims/`和`runs/seed120401-E0/`保留原始证据。当前真实内核排他锁在r2 `dispatch.lock`（已非阻塞探测确认held），不是旧root留档锁。调度日志r2 `physical_supervisor.log`；首格`seed120401-E0.log`与`seed120401-E0-launch.json`在family。SDK完整日志/云仍在r2 `sdk.log`、`sdk-app/entry_geometry.jsonl`；本地镜像在`../artifacts/go2-piper/`对应目录。轻量授权、PASS、启动和在途评价快照见`evidence/2026-10-20/native-pilot-sdk-r2-physical-dispatch-v1/`。

**实际接线已观测（20:05:55，仍非终态）：**首格已进`push_v212`、37.92sim/step1896；18.42与21.90sim两个同query各记录2624点，E0按协议请求0，原source-hand guard最大误差4.049208e-7m，小于原0.2mm门。证明新增观察层已在真实物理episode消费，不是仅SDK fixture；不代表PUSH/返程/整链完成或退让增益。独立快照`first-physical-query-observed-NONTERMINAL.json`保留。

**下一步仅计划：**让现有作业按原安全和预算收尾，原96sim/1800wall、单GPU串行、普通接触失败留分母，技术/严重失败停后续、不补跑/重试/扩批。完成后读同query实际请求→原support实际消费→最终READY及共同world goal的实际终态，报告固定16格/unknown和配对开发先导结果，不能用fixture PASS或旧相对目标历史宣称新整体导航增益。此次未修改运行代码、旧数据角色或归档问题页；原有未提交改动保持。

---

## 最新：先导预算已批准；SDK未留最终报告，物理0/16，r2修复待补1次App｜2026-10-20 18:40

**授权/版本：**用户已明确“批准，继续”：独立1次SDK0env≤180s、技术门通过后最多16次新Isaac启动（4新初态×E0–E3，原96s sim/1800s wall）。基于`9109f8221cec1afe7d1e7879d6f31023814c3ec8`新增隔离组装/实际观察/批准protocol/预算supervisor/评价器；旧共享预算与数据角色不动，不是重新申请原16次。最新主稿第11节。

**本轮实际完成：**
- 新seed120401–120404、共同world goal(−.25,0,0yaw)、四臂循环顺序在结局前冻结。隔离复制原v317，原controller AST保持；仅方法观察/标量需求与全变体共有goal/provenance接入，不改其他组源/actor/PD/队列/历史/时钟。E2真实私有几何CPU检查与原helper一致，所有方法共建/记录2624点；初始patch锚点/test预期两个CPU问题已修，原失败日志保留，未因此多消耗SDK。
- 唯一SDK确已在远端启动：supervisor1307300、timeout1307304、子1307305；均结束，墙钟27.814s。底层rc0但`sdk_result.json`未生成，`sdk_terminal.json:gate_passed=false`。检查器把唯一报告写在native App.close之后，SDK关闭实现会shutdown/release framework，结构上可能跳过后续落盘。四个2624点fixture云找回不等于最后断言/PASS，未补造通过。
- **SDK1/1已消耗；物理0/16、全部16次保留，没有演员forward/训练或新Isaac环境启动。** 有CPU/SDK私有几何FK，不能说本轮0FK；这些fixture不是4个episode。原失败source/claim/log/terminal未覆盖，不在旧目录补SDK PASS。
- r2修复已实现并stage：fsync/atomic pass/fail与checkpoint先于close、BaseException留证；CPU hard-exit0不会洗掉body fail。revision需匹配manifest显式授权；后续physical claim/ledger固定共享原family，不因修复目录重置16。probe与实际几何算法byte一致，仅SDK持久化/授权调度/meta变化。r2无approval文件，plain-Python已实际拒绝其自动启动，0新App。
- 本轮14个独立software tests（组装/真实私有几何4、持久化/授权5、评价5）通过，不冒机器人样本。评价器独立核实际共同world goal事件/最终pose/native门/无reset/物理覆盖；旧relative goal或SDK fixture不能计成功。当前16格全not_run、配对效应不可估计，不写0/16成功。

**源/PID/锁/日志与证据：**远端`/mnt/yuanyue/data/go2-piper/reachability-native-entry-global-goal-20261020-v1`，原manifest `dfd30848b1da07adffc2932269dc5ad31127d277ec408d75803c76346cd84e2e`；`source/`、`approval.json`、`sdk.claim.json`、`sdk_launch.json`、`sdk.log`、`sdk_terminal.json`、`sdk-app/entry_geometry.jsonl`保留。修复stage在`revisions/sdk-report-r2/source`，没有运行；原`dispatch.lock`文件留档、无本轮活动PID/内核锁，不声明其他组全局无作业。本地raw在`../artifacts/go2-piper/reachability-native-entry-global-goal-20261020-v1/`；轻量证据在`evidence/2026-10-20/native-entry-global-goal-pilot-approved-v1/`及`native-pilot-approved-run-repair-increment-v1.json`，CPU失败/修复、拒绝未授权revision、未运行评价全部保留。

**下一步与唯一资源问题：**实现、source/观察/评价已推进；当前阻塞在SDK最终PASS缺证且1次App预算用完。修复责任在本组，已完成CPU回归；需用户仅补充**1次SDK0env≤180s**验证r2，原16次physical仍有效/未增加。未获追加前不重启App；获批且匹配r2技术门通过、原source/权重/GPU准入齐后，才执行原16次注册case。技术/严重失败停后续、普通原生接触失败留分母，不重试/换seed/补跑/扩批。论文整体导航增益尚无本轮新物理结论；旧历史、失败、曝光身份与问题页均保持。

---

## 最新：已绑定实际Isaac整链／原退让模块形式化与回顾证据｜2026-10-20 17:35

**目标/版本：**继续为论文“理论对整体导航的增益＋受控消融”章节推进，主稿第10节。基于`6028bc4d6f8501c0a9f818e94a08f311aadba830`；本轮不再把通用MuJoCo SE2 shadow假当实际执行包，已选定技能组原Isaac v317及直接父版v316作来源/机制基础。原实现归技能源码，本组本轮做形式化、评价/新充分界和对照设计，不声称新造/重跑controller。

**已完成/结果：**
- 验原plan和候选源码、16份历史report/index、物性/actuator/native terms与96s命令；全部8个已用case纳入。原局部NAV→PUSH→stow→NAV完整任务7/8→8/8，唯一改善3703；v316的30.6s invalid_hand_contact失败原样保留。3703 tip需求19.333mm→原20mm格点＋5mm reserve请求25mm。共同成功7条平均慢.094286s；96s失败惩罚次指标差−4.4875s仅事后描述，不宣称普遍提速或独立因果收益。
- 两版为geometry/support处理bundle且已有针对失败的开发调试，不是新独立单因素消融；原返程goal由当时stow状态生成，3705两版绝对目标约差12.8mm，因此也不是共同预注册global-goal的整体导航确认性结果。已有v317/v319选择价值零增益结论保留，不挑版本赢家冒选择收益。
- 绑定真实v317/3701 READY step1180/23.6s、root z=.279354900及18轴命名q/dq/命令等到原control行，不裁剪实际q、不猜腿序。该READY在原入口准备之后，只作真实机器人输入绑定，不回推未执行动作。3703所选共同物理/命令值决策942前无差异，r1测首次值差944；row0双方未记录action/phase单列unknown，v1原诊断保留。只读主前缀3167行＋增量覆盖修正1986行，无整轨重跑。
- 远端仅SHA核NAV TorchScript/PUSH actor/原冻结12腿hook三份权重、probe及两路点JSON，全部匹配；0SDK/actor forward/物理/FK。实际configure pitch1.0、两路点SHA9c6…，不能偷换成旧Ry(.8)或其它16路点包；完整新source/SDK准入仍未完成。
- 新数学代码`tip_envelope_standoff.py`：既有有限tip前平面退让公式＋swept侧向带充分界，覆盖给定有限云在[d_request,40mm]最终刚体平移下的tip间隔，不覆盖连续残差/跟踪、运动、全身或任务。超cap仅无充分请求/unknown。抽象漏点反例不是Piper实际事故/可达性或新导航收益。22项新增reader/覆盖/几何/native shadow测试通过，旧核心/物理/静态map不重跑。

**具体输入缺口与实现边界：**`native_tip_ablation_shadow.py`已映射实际机器人部分；仍缺同查询box位姿、完整未门控41×64 tip云、箱系投影、caller translation参数、source-hand FK量，所有新对照not_ready/execution=false。旧preview audit取后续PUSH箱位置/stance yaw作事后核对，不能补为原query输入；本轮不复跑/不默认初态。原caller在线可读这些量，下一由本组在新隔离包补观察层与同caller接口，不要求main再派单，也不代改其它组原件/ledger。

**下一方案（未执行、未分配）：**`native_entry_ablation_draft_v2.json`取代旧未运行MuJoCo提案：原Isaac同caller/同support处理、E0 support-only／E1末端／E2全有限云／E3仅侧向集合改进。为直接测整体导航，提出全变体共同预注册world goal(−.25,0,0yaw)，仅改变共有return-target参数；原安全、到达阈值、96s回合、16s返程与1800s墙钟保持。这是新任务协议，不能重评分旧8条记录。资源提案1次SDK0env≤180s、随后至多16新Isaac starts（4新初态×4变体），独立预算未分配/没有启动，不借旧共享余额；先完成隔离观察/共同goal/source技术门，最终论文独立场景确认性验证另锁、不自动扩批。

**证据/作业：**`evidence/2026-10-20/executed-v316-v317-navigation-binding-v1/`、prefix r1、`historical-navigation-goal-scope-v1.json`、`v317-frozen-preprocessing-geometry-binding-v1.json`、`executed-v317-remote-metadata-v1/`（两个只读SHA命令terminal0，0App）和`historical-native-entry-mapped-readiness-v2.json`；图`executed-navigation-history-development-v1.png`。本轮本地只读与SSH元数据进程均已结束，无本轮物理PID/新锁；旧screen/supervisor锁原件未动、不声明他组全局作业状态。日志`executed-v316-v317-navigation-binding-v1-run.txt`及远端metadata各terminal/stderr保留。原历史/失败/曝光身份与本轮初版诊断均保留，问题页不更新。

---

## 最新：论文导航增益章节／原A*静态shadow消融已接通｜2026-10-20 16:40

**目标/版本：**用户明确最终交付为论文中“理论为整体导航带来何种增益，并通过消融归因”的一章；方法主稿`docs/IDEA_PAPER_CN.md`第9节、目标同步`docs/PROJECT_PLAN_CN.md`。本轮基于`65e0e75f3eec2ca5013c32359d16991033688442`新增状态研究、消融、原NAV shadow接入与图；不另训策略/世界模型或造controller。整体原导航目标完成是主指标，静态筛选不冒该收益。

**实际完成：**
- `.28/.38`新状态各75候选×同13方向、同90%限位/两seed；`.33`原75条query按SHA复用不重跑。新增1950posequery/3788初值、39路径/819相位样点、静态CPU11.706s；0物理/actor/训练。`.28`任务39/75解、端点与全21样点同8/75通过关节/35mm；`.33/.38`任务0、P3各排75。height是条件，未交付NAV高度行动或实际支撑状态。
- 同原静态比例cost消融：S0/S1选b039，模型净空−38.511mm；S2端点门改b017，55.290mm；S3路径门集合/首选不变；S4余量偏好仅多.046mm，S5同选择。**本批路径项未显示增益，不能追正例或冒物理收益。**31条IK成功路径未达指定模型净空，不是31次真实碰撞。
- 进一步用原`OraclePlanner._path_between`实际返回的A*grid中心路径长度（1m归一），25个xy只算25次，在yaw/状态间复用；15xy可达/10阻塞，每状态45共同NAV候选。`.28`纯route cost/＋taskIK选b021（grid路长0m、模型−30.090mm），＋端点改b015（.200m、58.613mm），＋路径/margin/P3仍b015。原canonical `SkillAction(NAV,[x,y,yaw])`类型identity已核，不是复制类；未调用NavigateSkill/runtime或导入actor。约.0092s仅缓存IK/path上的路由/选择shadow，不是在线完整规划耗时。
- `navigation_goal_bridge.py`拒绝把静态alignment/psi cost冒J_nav、拒绝跨state/height混选；缺route/source为not_ready、所有proposal执行权限false/物理success=null。原NAV到达容差不是IK容差，未来必须重读实际到达fresh状态。5项新height/cache测试＋10项bridge/静态不冒物理测试通过；旧核心、旧map和物理未重跑。

**证据/本轮作业终态：**`evidence/2026-10-20/piper-state-height-static-v1/`、`piper-state-height-static-ablations-posthoc-v1.json`、`original-planner-navigation-shadow-v1/`与`navigation-chapter-static-development-v1.png`。两项单次本地研究均exit0，PID已结束，无本轮在途锁；run日志分别为同目录外`piper-state-height-static-v1-run.txt`、`original-planner-navigation-shadow-v1-run.txt`。所有原query/失败/曝光身份保留，不声明他组远端作业全局状态；问题页不更新。

**未完成与下一步（计划，不冒已执行）：**
1. 论文核心N0同候选原route-cost、N1加任务IK、N2加端点、N3加过程约束的**真实整体导航**消融尚未运行。P3计算效率/余量偏好另隔离；原fixed-approach planner只作外部参照，不能混成同候选N0。不能把本轮0.20m局部绕行称整链净收益。
2. 下一最高优先是绑定**一份兼容冻结NAV→操作执行包**及真实查询/关节/足位/到达误差、原native/fallback/整体成功合同与真实运行route-cost；本轮旧pose-mode参考和合成静态初态不冒最新actor/真实handoff。Reach负责只读绑定和选择/评价，原技能owner的执行代码保留；只做新增接线所需检查，不重开无尽控制独审。需要确认的唯一来源问题是“哪份冻结Go2＋Piper整链包作本章基线”，不是等待main新派单。
3. 已有具体最小先导草案`navigation_chapter_ablation_draft_v1.json`：4初态×4核心变体=至多16新物理启动，远端go2-root-yuanyue、独立source/锁/日志、原安全不变；**新预算未分配/未启动**，不得借旧共享余额。用户分配独立资源、来源/技术门齐后再锁真协议；先导检验接线/覆盖，不以4case报泛化，负结果不自动扩批。

---

## 任务条件公式第三轮：任务姿态无解与Piper腕高必要界｜2026-10-20 16:10

**版本/范围：**基于`7eaab5b932b6de2db4265c91b366dedbfa3da8ff`新增源码锁定task协议、同query方向对照/名义路径接口、P3解析界和证据；运行protocol SHA `e4bf7d8f80031588d814f176842508a2f52678ffef59d2a9a314647d18e3c624`。这是独立组数学研究，不是默认position模式、冻结v212/最新actor运行，不改原控制/安全/数据用途。

- **单次真实模型数值结果：**源码给定接触前目标(.47,0,.10)m、Ry(.8)、body z=.33；75个base位姿每个同13方向/同90%参考限位/两seed，共975query/1879初值、5.795s静态CPU。任务方向0/75找到解，其他方向合计76；任务150尝试均触joint2参考边界。未构造任务路径，端点/P1对照**不可评价**，不能说路径通过或改善成功。原miss为unknown，原summary不改；未重跑扩seed/方向/阈值。
- **新增数学产物P3：**从实际Piper链推导`M_z=腕高下界−含2mm/1°容差的目标腕高上界`。上臂竖直投影在joint2区间内解析求极值，前臂/微小偏移用保守长度界，保留88.260μm非轴向native偏移。`M_z>0`排除指定固定机身/参考关节域的pose；否则inconclusive。证明与结构适用条件见`docs/IDEA_PAPER_CN.md`第8节。
- **模型用途已具体化，但不夸大：**90%参考域75/75有+13.397284mm缺口，因此本任务在该固定状态/参考域内不成立，xy/yaw重试不能救；原native hard域75/75为−31.236883mm，0个可排除，不能宣称硬机构不可达/授权放宽限位。该事后解析推导不新增FK/IK，证明的是模型域必要排除，不是独立泛化、论文新颖性、已测加速或实际物理收益。
- **实现/测试：**`research/task_conditioned_reachability/{piper_task_geometry.py,run_piper_task_study.py,task_height_bound.py}`；原checker+USD碰撞已接入，但任务0路径不能冒充实际净空对照。8项task/frame/phase/状态恢复＋6项解析代数/结构测试通过，公共采样轴修改后27项原核心API回归通过；0物理/actor/GPU/训练。本轮本地单次作业exit0，无本轮在途作业/锁；未检查或声明他组远端全局作业状态。
- **原始证据：**`evidence/2026-10-20/piper-source-task-static-v1/`；完整query SHA `cd6d96d1a05eca416fe378a65c9ec4819ff89bc0fb50e24c9b38598c1eddd045`。只读残差`piper-source-task-readonly-diagnosis-v1.json`、P3`piper-task-height-necessary-bound-posthoc-v1.json`、测试日志与增量清单保留。旧map失败/旧原始数据/已曝光身份不改，问题页不更新。

**后续有界正控也已完成：**另锁12个90%域内合法关节构型（joint2低/中/高×joint3低/高×joint5低/高，其余中点），原FK生成12个已知可达pose；P3在90%与native hard两域均0误排、状态/time恢复，0 IK/物理，静态CPU.207s。证据`evidence/2026-10-20/piper-height-bound-positive-controls-v1.json`；只是模型正控，不是任务正例或独立泛化验证。

**下一步仅计划：**显式比较body高.28/.33/.38m（不是偷偷放旧joint2或方向）。同75候选/同方向，至多2925posequery/5850初值/4725路径样点/180s本地CPU，0物理/actor/训练；12次FK正控已完成，不列在下一待办。此高度网格由当前发现启发，标开发，非独立泛化；有任务路径后才评同query/35mm的A1/P1/P2，真实支撑/外载/延迟/物理成功仍未验证。未执行该下一协议。

---

## 当前工作方式：各窗口独立，main仅讨论方向｜2026-10-20T13:05:01.167467+08:00

**用户最新指令：结束不同窗口的协作模式；各组不再需要更新《问题与待确认事项.md》，进展和计划可以持续更新；main只与用户把控方向，不再具体指挥各组。** 本节覆盖下方历史主从／跨窗口派单／等待main回复及审批／强制问题页同步规则。

- 各组在各自窗口依用户授权独立开展工作，自行维护本组进展与计划；不通过main中转任务、催办或审批常规实现。此次规则更新本身不启动作业，也不自动恢复旧定时任务。
- 《当前进展.md》《下一步计划.md》可持续更新；《问题与待确认事项.md》退出日常维护，旧内容仅作历史档案，不再要求跨组登记、回复、关闭或等待回执。
- main职责仅为与用户讨论研究问题、总体方向、优先级及取舍；可在用户要求时阅读现有进展作方向性总结，不主动派发、续派、轮询各组，不担任逐项执行门或自动技术审核协调者。
- 需要用户决定的事项由相关组在自己的窗口直接与用户沟通；不再要求先向main提交问题单。
- 不改变安全、资源、数据身份、仓库归属及真实验收条件；原冻结运行包和已消耗授权保留，不因撤销组织审批流程而绕过已有技术安全门。已暂停的协作Goal不自动恢复，未完成事项不改记成功。


---

## 真实Piper静态图／拟合失败与方向条件诊断｜2026-10-20 15:26

**已完成：**真实仓库XML＋五USD SHA/profile/工具与mount/六关节限位绑定，复用原pose-IK；预定125+64位置×12方向共2268query/4388尝试，175解fresh FK核对，静态CPU14.14s。新增11测试通过、4非默认FK正控4/4；0物理/actor/GPU/训练。源码`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/research/task_conditioned_reachability/piper_kinematics.py`、`build_piper_workspace.py`、`workspace_fit.py`，非硬件标定/实际支撑或全任务执行。

**负结果不掩盖：**原ψ>=.25在拟合125点正例0（最高2/12），不产全方向双椭球参数，不调阈值/扩seed/网格重跑。ALL12事后方向切片仅0/1可满维拟合，64点TP/FP/FN/TN=18/28/0/18与24/16/0/24；其余10拒绝。此为有界solver标签/简单协方差近似误差，不是真实失败/原OmniNav方法失败或本组改进收益。图/拟合失败/诊断与校验：`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-20/piper-numeric-baseline-development-v1.json`。

下一实际任务是预先固定目标/工具允许方向与当前状态，再比较任务条件ψ_a与宽方向比例，并接同query可靠路径瓶颈；不从本轮成功最多方向挑任务/用独立IK点拼连续路径。所有189点/诊断现已曝光，后续改方法另锁验证；本轮未读reserved、未改原问题页或他组ledger/代码，旧已验证/失败结果保持。原数学核心27测试不因新增map误称已证明物理收益。

---

## 公式研究首轮：数学原型/反例限定结果｜2026-10-20 15:04

**已实际推进，不再只有idea：**`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/research/task_conditioned_reachability/model.py`实现原OmniNav局部双椭球cost、P1路径瓶颈/候选max、A1端点、P2硬筛与余量偏好、静态同frame外载力矩代数、缺量上下界/unknown；`run_demo.py`与27项新单元测试可独立运行，无SDK/模型训练/FK/物理依赖。穷举6561个人工小数组核有限max-min等价，不冒机器人样本。代码与限定scope见`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/research/task_conditioned_reachability/README.md`。

**重要更正：**已从原始HTML核准arXiv2609.08159v1实际题名/Section VI-A/双椭球式33–42；上轮题名与四项travel/−log可达代价写错，已在idea-paper明确撤回。当前是原式局部表达式实现，未做Piper实际IK图/双椭球拟合，不称整篇复现。

**本轮结果：**人工内部净空/静态外载反例中A0/A1选内部违规near，A2选全名义样点通过offset；无载荷时A2回选near，缺载荷模型则unknown。另读取已曝光/已审原Piper路径2870：endpoint6.960861mm对内部4.011407mm、原要求5mm，单约束归一ρ从+0.392172变−0.197719；不重算原planner/FK、不冒native碰撞或完整endpoint可行（其它swing gate本已失败）。**没有新物理完成率/安全增益/创新性证明。**

证据`/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-20/task-conditioned-math-prototype-v1.json`与`math-prototype-validation-v1.json`、测试log；首draft语法/权重/phase表示修正范围保留，最终27test PASS。本轮0物理/训练/校准/推理/SDK/FK，不读reserved原始后果、不更新问题页或他组账本。下一必须接Piper实际数值图和同query可靠名义路径/最少载荷项，再锁定真实配对验证，不继续扩大toy或独审工作代研究。

---

## 协作结束／当前交接状态｜2026-10-20T12:58:14.869138+08:00

**用户要求更新三个方向进展并结束协作模式。两个协作子agent已关闭，当前Goal由实际工具确认为paused，未标记完成；不自动恢复旧聊天、heartbeat、实验或训练。** 下方旧执行指令均为历史，不构成重新启动授权。各组下一研究方向须与用户先沟通；本次仅同步文档，不新增控制修改或实验。

- **已独立核验：**v022r2忠实CPU重放复现666有序候选、11联合chunk及原mask/返回。完整support-leg path与full-swing gap/margin交集形成两类分别足以致空的约束；不是唯一物理根因或统计独立性。证据：`/home/yuanyue/main/work/agent_team_runtime/stage2_joint_gate_20261018/verification/actual_review_fcf13d30_02/review_receipt.json`。
- DEV003筛得10个名义准备有效点，预定first-valid635仅名义证书，不能装载历史635冒实时筛选，也不等于准备执行成功。
- 原v023误阻后续RR／伪测量epoch等问题已在后续限定来源契约下修复并审查，旧拒绝回执保留；不再以旧v023拒绝冒充最新状态。
- REV037接受DEV044限定性能窗/闭合；REV038/039接受局部值复用正常API域；REV040核真实CPU590对＋144谓词；REV041闭合SDK root接线；REV042接受最新e880/ae4a/真实SDK精确技术准入。各层scope不同，不把CPU/SDK符号审当动态假设成功。
- **未完成：**DEV051已有terminal/closure与完整状态视频，但独立终态审查未交付；准备／settle／fresh／原RR及原CLIMB-NAV完整结论仍缺。原完整Goal不能据诊断或困难完成；也未证明授权域内不存在可行修订。
- H0候选/研究入口新核验刚派后已按用户“先沟通”撤回，未作为已完成成果。Reachability组历史独立方向保留，不因承担临时核验角色而被改成仅验收组。既有本地commit f83b8c5…保留，最新外部review不等于全已提交；本次无push。

### 后续边界（待用户讨论，不自动执行）

如用户恢复该项工作，先窄核DEV051终态与真实准备触发证据，再根据新的研究问题确定所需候选可执行性证据；不重复已闭合重放/SDK套件、不自行发起控制实验。

未决：DEV051末状态与准备路径未完成独审；H0入口契约未确认。旧成功、开发证据、独立测试的角色必须分开，不能降低原安全成功门来制造通过。

---

更新日期：2026-10-19。以下为不同协议的结果，不能合并为同一成功率。完整逐实验文档可在本分支 Git 历史中检索相应版本名；机器 JSON 证据在仓库根 `evidence/`，原始大报告在仓库外 `../artifacts/go2-piper/`。

## REV017–021 独立增量核验归档（2026-10-19，仅本地里程碑）

本轮小型独立checker/CPU反例、接受/拒绝/终态receipt与canonical SHA索引归入 `research/stage2_incremental_verification_20261019/`；结构化归档记录见 `evidence/2026-10-19/rev021-stage2-verification-local-milestone.json`。归档不是可直接RUN的source，不含环境/权重/原完整日志、录像或大报告；历史硬编码checker仅原字节快照，不能直接在归档目录执行。

- REV017的r2g拒绝原件保留（UNKNOWN通知/采集状态）；REV018保留r2“SDK配置通过但source有PGID缺陷”与最终r3“quiet修复＋真实新r3 SDK同digest接受”的不同层次，不冒继承执行、不放宽gate。
- REV019正式旧首箱baseline在授权预算内未完成，wall2336.441560s、子timeout rc124，**1次尝试/0成功/0retry且保留成功率分母**。实际记录到step15500/310sim/climb_exit，不等精确最终tick；raw缺失不等0物理，未知尾段/原控制故障类别不把任务失败变成可删失样本。
- REV020仅已记录95事件与v13前95及310点7共同字段一致，不代表完整连续状态、后缀或NAV成功。已无据把当前超时认定为接线/物性根因，排查转运行时预算/吞吐，具体瓶颈未定；不靠旧后缀给本次补成功。

旧8101/4kg/.4/model199+.50开发baseline不充抵当前Goal；原cfg .60与实际PUSH事件>=.50、失败数据身份和成功/安全门保留。REV021只做一个显式路径本地归档commit，无push/新agent/SDK/物理/旧套件复跑。预算变更待用户答复，无新RUN；旧主窗口/自动化停用状态不因此恢复。

## v021原2s/真实恢复已达，188.22s候选域拒绝；floor因果未证（2026-10-18 11:44）

**已独立接真实终态，不再在途：**source `sim2real-user-test-v021-pre-recovery-priority-a`／manifest `cd6c9ea0f5cd65d9367760b04558aa201e59cd4da4e8cd08f2c0bbd4db7ef342`已**11:06:53.814 closed**。原report SHA`4fb41f339da42130e99542bc4ba9aec1242cfdc977a525c8b6d1ef92b44de3c9`／closure／producer汇总相同：FAILED/unsupported_domain/原support候选空/fromCLIMB/error=null/full_task_success=false，**188.22sim／9411区间／2308.129wall**。[实际priority/恢复/后段候选拒绝评价](</home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-v021-actual-recovery-late-candidate-refusal-evaluation-v1.json>) SHA`0d08dd3c6eb2db23d547a0151c1867311a2c45bdcd2f62452131d0338c1c75d7`。2308s虽接近core2340，实际reason不是预算；最后完整raw188.22s仍CLIMB且unsupported=null，随后同step拒绝下一步，不能用末raw盖掉真实FAILED report。

**原计时与恢复已真正执行：**原priority PRE**64.26s** eligible/同源fresh，原2s离散timer在PRE**66.24s**记录2.0000000000000013、1次完整路径实际规划accepted并交权，首恢复模式物理区间POST66.26s；原计时定义不改，不将两PRE戳跨度1.98s当另一套timer或把elapsed当2s。已发日志99个skip-completed-control仅表示ordinary未评估，**不是99次反事实计划被阻止**。原stalled-detail64.24过旧，在corrected第一priority记录中明确null，不回填新64.26；初derived选择与同SHA原始prefix保留，不修改原物理源／用途。

**本源实际恢复与原完整接回valid=true：**69.92 POST实际完成原1s，calf/allnonfoot normal0N、四足30.190/65.482/38.136/79.530N、body误差5.556mm/角误差.021317rad、原完成gates全true。69.92 fresh native原完整floor-aware handoff通过，reference/velocity/所有clock/state与真实PD/actuator/obs-history事务保持。priority/recovery均不是只有used=true或static plan。已有固定prefix中的**128.00 PRE/128.02 POST**同source-step6400样本可核双前足G高度.223864/.223946m及normal54.748/23.393N；是实际高位／载荷见证，**toe-box命名接触对仍未独立绑定**，不等全四足登箱/CLIMB完成，不重提首次126.08或全轨迹来凑相同证明。

**后段失败的准确类型：**最终原flags空／native effort witness=null／max recorded arm ratio.965215<原.98；本次未发生v020那类原effort终止，但单例不证明普遍消除／priority唯一因果。188.22s最后physical的q/dq/root/PD/issued18/box与refusal-before-physics相同，physics_advanced=false/actor_command_issued=false；report为**本步支撑计划／caller域拒绝，执行success=false-valid=true，最终原生物理任务后果未观察**，不是碰撞/力矩失败。PUSH23.74/EXIT31.32/CLIMB31.34进入、本源恢复/后续腿动作保留，CLIMB/NAV未完成，旧v020原phys失败false-valid不变。

**不能仅凭异常字符串填floor因果：**保留原reason `Original support candidate set empty under new floor mask; keep issued supported reference`；末188.22记录1053原valid0→floor0、3645原valid0→floor0，另一个1候选原valid1→floor1。**这三次匿名调用不证明floor删光原有效解，也不能把单1检查合并成前两候选集合的有效解。** floor为首个阻断项／唯一原因、caller primary/fallback/partial/expanded身份和最终pose/swing聚合因果均先mask未知；不套旧v012解释、不删floor或改旧report。

**下一既定任务：**沿[main11:22](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#main-v021-closed-original-candidate-diagnostic-20261018>)由Sim2Real用现有186.70/188.22真实输入给简短`具体caller→原hard mask→floor mask→最终pose/swing/reference`表；缺原内部量可用原模型重算但标派生，不能当native。依据首个已证阻断项再选具体控制流修复／有物理依据的新准备步骤，不先扩候选/网格/seed或降gate。Reach已完成独立分类／14已发stage文件hash、原2s/恢复/接回事件、现成128s点、唯一raw末行与拒绝物理字段核对；不重算9411轨迹／原恢复51点统计、mask/FK诊断、旧CPU/SDK/物理。原1mm/35mm/5N/25mm/10mm/2s/3s/5Nm/.98/PD/物性/clock/history/成功和单GPU1env同锁/48+420sim/NAV120/core2340+60/outer2400保持；39历史启动已结算、账本／曝光角色不动，无新次数/用户决定，H0/H1/H2/鲁棒性/整链仍未证。

唯一增量：[WM-07](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-v021-real-recovery-candidate-refusal-no-floor-cause-20261018>)。

## v021等待优先级契约已绑定，真实dwell/反事实/交权缓存分层（2026-10-18 10:55，无终态主张）

**已接真实启动的v021单因子调度，不再等旧诊断／冻结：**source `sim2real-user-test-v021-pre-recovery-priority-a`／manifest `cd6c9ea0f5cd65d9367760b04558aa201e59cd4da4e8cd08f2c0bbd4db7ef342`，parent完整v020；start **10:28:24.252**、1启动0retry/原同链锁。实际SDK r1和17项当前source hash已核；10个核心原控制源字节同父，recovery adapter AST剔除唯一`current_scope_measurement=m`缓存字段后同父。只核新增priority/source/log契约，[优先级—真实dwell—抑制/交权评价](</home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-v021-priority-dwell-and-suppression-protocol-review-v1.json>) SHA`e5fadcdcc696e3c05fcd67967c570ab08b1e6100039c2c7e1fafac48e5851063`；不重做v020首tau机制/名义PD、21新CPU或旧套件/SDK/FK/物理，也不读增长中的raw/priority事件。

**新状态域与原门禁不混：**原recovery observer/planner每步先运行；首次原eligible＋同step/同源anchor才进入当前reference等待，未将2s置满。priority continuation是已声明的四足>=8N/known-ground/step-source/原safe/request-zero/u0/notlifted支持保持域（normal>1N），**不等原恢复eligible（>5N及calm等）仍持续true**；calm失效时原2s timer照旧归零，等待不能当已停稳／已规划。请求是每步`a.reference.clone()`，不是测量q／旧bank／冻结物理状态；原limiter可继续积分/减速既有reference_velocity，不能把“不评估ordinary”说成机器人停止。原recovery active或used后priority明确关闭并写release cache/event；是否真实参考/负载完成仍要实际原件。

**新日志标签的关键界限：**`ordinary_pose_replan_suppressed=true`仅指该步ordinary路径未评估／跳过，**不是实际请求数／被阻止计划数／本来必会发的反事实请求**。真实ordinary/recovery/handoff调用看同源原plan事件，不按控制tick的marker累计；elapsed hold也不能代原连续2s gate，断开的eligible不能相加。PRE cache step/time与POST积分行分相核对，不能要求两者step裸相等；release cache往后原样携带不是重复交权事件／当前fresh dwell。priority_active、dwell完成、planner调用、恢复真实load-transfer、native τ与原安全、后续任务是不同层。

**已报告在途观察与独立证据分开：**本组只消费冻结10:30的7.22s PUSH snapshot，不把它当当前阶段；[main10:51一次远端观察](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#main-v021-live-released-priority-20261018>)另报告113.02s/5651仍CLIMB、flags空/unsupported=null/无report，缓存**66.24s已released_to_original_recovery=true/active=false**。这是main原读数的时间作用域，不冒本组独立raw复核，旧66.24交权cache不是113.02当前eligible/dwell或物理恢复效果。已越过旧v02066.34失败时刻也不证明一般力矩问题解决、priority唯一因果或CLIMB/NAV通过；本项无本版终态／native结果标签。

**当前下一动作与固定：**按main10:22/10:51只接该唯一源实际冻结事件／真实report：eligible/priority开始→原2s/full-plan→恢复交权/真实负载→原τ安全/RL-RR/CLIMB-NAV。原v020真effort失败false-valid保留，新的失败按真实类型有效记录；尾部domain/history缺失不补假真。原完整v020 geometry/finite模型、5Nm/.98/PD/actor/物性/2s/full path/force/contact/35mm/5N/25mm/10mm/clock/history与单GPU1env/同锁/48+420=468sim/NAV120/core2340+60/outer2400保持，原无触发80sim／恢复12sim不延长。39=旧20+WM7+producer12含本源，非hardcap；不热改／重启／另发作业或为形式回签等待，无新用户或次数决定依赖。

唯一增量：[WM-07](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-v021-priority-dwell-counterfactual-and-release-review-20261018>)。

## v020完整候选原生力矩门禁真实失败（2026-10-18 10:12，非域拒绝／未知结果）

**真实终态优先于09:50在途快照：**完整v020 source `sim2real-user-test-v020-measured-gravity-support-a`／manifest `c2eaa124387eab6050182d2306c83bf0c40af5f5706080086f4cc2fb69bc42b9`已**09:54:42.724 closed**。原report SHA`6d2f4d98cc93c00cc1a214944c945cfea4aff6c5fbad566e2ddc2d2c09f9654a`与closure同值：**FAILED/phase=FAILED/reason=original_physical_termination/from CLIMB/error=null/full_task_success=false**，66.34sim／3317区间／779.927wall、0reset。不是旧v012/v013算法域拒绝或预算删失；**本源原生安全失败／任务success=false为已观察且valid=true，不能沿旧域拒绝模板记unknown**。[完整有限域绑定／原生arm-effort失败评价](</home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-v020-complete-domain-and-native-arm-effort-failure-v1.json>) SHA`e42e2a0e95eacec56e5be1a33ccd045e26aa0a832a349c16e0b668dffa5df7d9`。外部return0只表示收尾，未升级任务通过；机械损伤／碰撞机制仍未证实。

**原门禁真实见证：**最终original flags只有`arm_effort_safety`及`same_box_substep_effort`为true；first native substep witness在控制步3316的**66.32→66.34s**区间，native `joint5` applied **−5Nm／limit5Nm／ratio1.0**、q≈.118401rad、dq≈1.054982rad/s、written PD target0。源码`monitored_update`与v013父版AST相同，原ratio保护实际为**>=.98**，不是新设阈值或仅根据末帧重算；first witness未记录精确区间内子步时刻，不虚填66.335s。written target不是私有delay后实际target，不能仅由这些数唯一归因delay/新frame。两个flag不当两次物理失败，ratio1不宣称超过5Nm或发生硬件损伤。

**阶段与未测层：**本源PUSH23.74s／EXIT31.32s完成、CLIMB31.34s实际进入保持；原生力矩门禁在CLIMB失败，NAV未进。恢复日志只有62.96s同source实际无calf参考anchor，最后PRE66.32s recovery used/active/request均false，**新恢复规划0次／未发恢复参考／效果null-valid=false**，不能说新恢复路径失败，也不把旧v011–v013恢复/RL/RR局部成功搬进来。PRE cache此时FL载荷0、root速度.579m/s/角速1.278rad/s、body/arm动态诊断只是更早控制状态，不能与子步wrist证据拼成唯一因果或把模型command excess当actual hard-limit失败。

**完整新接口与时相缺失分开：**新manifest、producer采用、实际SDK r1及15项actual-source hash已核；初次COMPOSED两floor hook遗漏的0env失败保留，r1是真正新源闭合、不计物理retry。旧v016–v019零散接口待件关闭，不再要求重跑旧CPU。`protocol.measured_support_revision.replace_old_numeric_q_domain=true`与实际source明确覆盖继承的旧qxy1e−6说明；新有限模型是同step实际尺寸/完整姿态、upward top、μ=.15下竖直合力方向锥、实际**box**速度<=.025m/s/角速<=.1rad/s。不是robot稳定、动态摩擦/支撑wrench或actuator安全证明。producer现成汇总2129个模型记录true／无模型拒绝；owner已核最后fresh **66.32s/3316**仍全true。**66.34s/3317失败行history_updated=false且domain/frame缺失**，该缺失不是false，也不将66.32s真值挪成同step、不另调observe/FK补尾。终态仍是已证原生effort失败而非模型域失败。

**具体下一问题与范围：**沿[owner10:07既有诊断](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#owner-v020-native-arm-effort-closed-20261018>)交Sim2Real，用本源first torque witness及邻近真实issued reference/velocity/PD/q/dq/τ/延迟历史、ground/reselection事件定位首次饱和对应的请求/状态变化，给一个明确因子修订或具体能力域限制。当前单终帧不足唯一根因，不能为过关放宽5Nm/.98保护/PD或重跑相同v020碰运气。可用旧v013已曝光前缀做有限接线对照，但不伪称全私有history配对。原5N/25mm/10mm/1mm/35mm/安全/物性/成功/历史/clock与原单GPU1env同锁/48/468sim/NAV120/core2340+60/outer2400保持；具体修订后按现阶段授权新source，无新次数/用户决定依赖。此轮Reach仅1原尾行、单次75.9MB**纯字节hash**、15配置源码/原guard AST及已有producer/owner汇总，不全数扫描轨迹／复跑CPU/SDK/FK/模型/物理；38真实源均已结算、角色/各账本不改，H0/H1/H2/模型收益/完整任务仍未证。

唯一增量：[WM-07](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-v020-original-native-effort-failure-complete-binding-20261018>)。

## v018 feet-only端点与frame-current契约增量接收（2026-10-18 09:24，无新native资格结果）

**本轮只接v018新增sample／freshness契约：**`wm07-guidance-edge-scope-preparation-v018` index SHA`142dbe9331a67bf1eaae1f8d25196e959970ff955896052c133cea18e27305e5`，parent v017/物理v013不变。[feet-only端点与frame-current局部接收](</home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-v018-feet-only-qualification-and-freshness-review-v1.json>) SHA`b50987d0ec01dec9499c8b22f11fafd83b6910b178227494176d094dc977c2ce`核34索引文件／16父源码绑定、stage/recovery同源guidance以及原冻结ClimbCompletion SHA；没有重跑27+5或旧12/20/22CPU、36函数/clock/sample字段AST全审计、SDK/FK/物理或v013大日志。32项producer新检查全为synthetic/纯consumer，初始fixture参数/active-cap断言失败与修正日志保留，不是新native动作/接触或真实3s站稳。

**已核端点字段消费，不盲旋整个sample：**`climb_handoff.sample`只将`feet_position`转完整B-canonical供原有限top几何判断；`platform_final_goal/guidance_body_target/robot_position`保持G，原remaining/tracking仍同frame相减；速度是绝对world速度的G分量（不减box，不当移动G位置导数），载荷是G-z=W-z normal N。原ClimbCompletion仍严格物理时间递增、gap>.020001重置、原至少3s/四足8N/body10mm/停止/.002目标余量/extension-hold-command及安全锁存，未改原资格器或把feet几何membership冒脚箱配对接触。

**新明确审计边界：**新增`planning_frame/measurement_frames`是**可审核元数据，原冻结资格器不读取／验证这两个键**；未来`complete=true`不能单凭它证明frame/version/step正确，真实caller仍须负责一致采样与物理时间。不要为此改冻结原资格器或追加原成功门槛；当前只核source路由，native稳定3s/新CLIMB结果null/valid=false。新`*_planning_G`日志键也不是旧`*_box_math`/`actual_*_box`的数值别名，按新source/frame解释，不回填旧闭合源。

**局部available只收紧：**floor native_free_support的`available` AST保持原contact.available与cache-step==当前step完整AND前缀，仅追加`frame_current`；后者要求bound frame同一对象且其source step=当前native step。原无效contact不能被新frame条件拼成available；这仅一处availability源码结论，非完整SDK时相/全管线有效性证明。其它guidance/edge保留B面查询与G .10m cap/G高度inset/插值区分，producer现成保护回执直接消费、不重做测试。

**下一原清单条目（未完成）：**按[main08:21](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#main-v017-geometry-validity-scope-20261018>)，Sim2Real继续PLATFORM/NAV真实support_z/模板height/有限footprint、PUSH_EXIT实箱edge flags，再有限力/摩擦支持域、初始化版本日志／phase报告／完整配置/SDK0env/冻结源。guidance/floor/stalled和feet-only sample已prepared，不再催同一条目；两旧guard仍保留、非launchable/未采用、无新实际源。原1mm/35mm/5N/25mm/10mm/3s、PD/限矩/物性/候选/成功/真实history-clock与单GPU1env同锁/48/468sim/NAV120/core2340+60/outer2400不变，几何纠正不要求旧错误flat全集子集，不发半包/新抽象或要求旧测试重做。37旧源/原失败/曝光用途/各账本/H0-H1-H2结论保持，无用户／新次数决定依赖。

唯一增量：[WM-07](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-v018-feet-qualifier-freshness-partial-review-20261018>)。

## v017三个实际目标构造caller的增量接收（2026-10-18 08:38，仍非完整候选）

**本轮只接producer新完成消费者，不重跑旧证明：**v017 `wm07-stage-classification-landing-preparation-v017` index SHA`a6ffca281914357d7321c83ffba78b7b844feaa2f20119d134773df5c36470aa`，parent准备v016／原物理v013版本不变。[实际目标caller局部接收](</home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-v017-target-consumer-route-review-v1.json>) SHA`6213cec36f9df15a887de9b7bb40aaebc323a0a83103ca40cb6a7753ed80a1f3`核26索引文件／10父绑定和3个实际构造点：`StageClimbAction.process_actions` refresh完整G xyz落点赋值、`PlatformFrontExtension.release`真实extension目标、`GroundEntryGuidance.reserve_second_front_landing`原两项短落点。不是只有helper文件，也不是整体stage／SDK或新物理已跑。

**局部权限与量义已核：**B-x/edge/delta都经完整点回G，不把标量写G-x；top sole .0245m沿实际top-normal、ground .024m沿独立world-ground，extension保持B-normal偏置/B-y、原<=.08m，短落点只有−.01/−.02m。短落点实际`accepted=backup[3]&inside`表达式与父版相同，原backup=false在此局部决策不能被新inside复活；这不要求或证明所有新真实几何valid为旧错误flat-valid子集。extension的原permission/dwell状态机仅消费已交源码保护，不重复CrawlClock/clock AST或float32序列测试。原22新CPU中初始fixture dtype失败日志保留，后改fixture而非阈值；本组未复跑22/12/20CPU／SDK/FK/物理，也不把CPU数当独立环境数。

**整体域未完成边界：**`reserve_second_front_landing`的single-front scope、Stage的hold/platform admission等外围caller仍未转换，目标点已接不等整个方法/全链完成。现有remaining表8整体area complete=false与真实prepared目标点可同时成立，不能将其读作未推进。guidance/floor-context/stalled/其它all-ground分类、CLIMB/PLATFORM/NAV终态、有限力/摩擦域及初始化起实际日志继续由Sim2Real完成；两旧guard保留、launchable/adopted=false，未有新动态prefix/任务结果。本轮没有要求先证明不存在的全管线状态子集或另建协议。

**下一既定动作：**按[main08:21](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#main-v017-geometry-validity-scope-20261018>)只接上述实际新条目/最终完整支持域和配置，按原物理余量/非几何hard条件/源码差异做最小增量核。几何纠正可双向变，旧v013物理失败/partial/RR及所有旧角色原样；新G参考变化是控制修订，不称logging-only，不中途切frame/清history。单GPU1env同锁/48/468sim/NAV120/core2340+60/outer2400、原1mm/35mm/5N/25mm/10mm/3s/PD/限矩/物性/候选/成功/clock不变。37旧源closed快照不重写，不发半包，不因旧36额度停工，无新用户／次数／方向决定依赖。

唯一增量：[WM-07](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-v017-three-target-callers-partial-review-20261018>)。

## v016局部源码与量义增量核验（2026-10-18 07:53，0新物理、非完整候选）

**本轮新交付为静态增量核验，不是新实验／完整接收：**依main07:21，消费`wm07-gravity-frame-OBB-integration-preparation-v016`部分源码index SHA`d2d06af212b848e6f5750dfde0cf0e8b7c8f0506a99b4c887e83d74828d00610`，parent v013 manifest `a7d6e179…d72151`。[局部内核保持／物理量语义评价](</home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-v016-partial-geometry-kernel-and-quantity-review-v1.json>) SHA`1b1b5d8752db174a85df69fce238aeba7f26a0a1d9fe56ad3eab6caf2397d887`。核17索引文件、4父源码差异及8剩余消费者父源SHA；未跑producer20CPU/v01512CPU、SDK/FK/模型或物理、未重读v013大日志。现有两旧guard仍保留、8消费者complete=false，launchable/adopted=false，不把文件或测试数当新源／动态通过。

**已核实际改动范围：**stage与独立recovery的两份clearance模块，分别只移除声明的4个adapter AST节点（base_box_gap与primitive_box_gap的import+输入query）后，**整模块AST与父版精确相同**。原SAT/精确圆柱支持半径／有符号保守gap／余量／其余函数未改；不是用旋转包围AABB替代真实OBB。G只yaw/translation、world速度不减box速度；接触空间向量与Jacobian空间行同yaw，广义关节重力补偿原样读取。不据该局部证明声称所有caller已接或非水平运行等价。

**现有清单应继承的具体量义：**`actual_top_height(xy,c)`的c是**沿真实顶面单位法向的距离m**、输出是G-z坐标；竖直增量是c/n_z，不是直接+c，也不是有限箱顶／landing/contact判断。`actual_ground_height`是本冻结world ground z=0在G中的高度`.1−box_world_z`，不是箱顶。OBB separating-axis gap为原保守轴向gap，不是任意点的精确欧氏距离或重力投影高度。`box_query_pose/box_canonical_points`输出的B-canonical**仍保留(1.35,0,.1)**，不是v015居中B；B-x边缘标量不得直接当G-x目标。按main既有W/G/B清单逐字段标这些含义，不另造第二协议／几何实现。

**invalid规则不偷换：**原非几何invalid必须保持invalid；**真实OBB修正相对旧错误flat几何的数值gap可以双向改变**，不能要求或宣称`valid_new`必为“所有旧flattened几何valid”的子集。现两模块无mask/search/score/阈值修改，但完整pipeline非几何invalid保持尚未由本局部交付证明，mask保持标签仍null/valid=false。新原控制支持域／真实prefix／CLIMB-NAV结果均未到，不给通过标签。

**下一已有工作（计划）：**[main07:21](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#main-v016-interface-coordination-20261018>)已定Sim2Real继续现v016清单：先选腿/ground-top分类与landing/extension，再CLIMB/PLATFORM/NAV端点、有限力/摩擦域与版本日志；完成实际caller初始化/支持域/配置才形成可启动源。Reach随后只对实际修改消费者增量核原物理余量/非几何invalid与真实W/G/B输入输出，不要求整套旧测试重做。保留原1mm/35mm/5N/25mm/10mm/3s、PD/限矩/搜索/物性/成功/历史/clock及原单GPU1env/同锁/48/468sim/NAV120/core2340+60/outer2400。不删旧guard、不启动半包、不把新frame当logging-only或中途换frame清history。原37源closed是producer已交快照，旧v013FAILED及RL/RR、旧数据用途/账本/H0-H1-H2结论不变；无新用户或次数决定请求。

唯一增量：[WM-07](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-v016-kernel-quantity-partial-source-review-20261018>)。

## v013真实partial→RR动作已证，POST平面域拒绝；居中坐标接收边界（2026-10-18 07:09）

**已完成独立消费：**source `sim2real-user-test-v013-expanded-floor-followup-a`／manifest `a7d6e1794f36940d9ac52206a734bccf01272542438ba573ca0e31abd2d72151`，原report SHA`8fb0951927f9545ccfad773ef1490edac8593841220495138b4aa53505986a89`与closure／两份producer分析同值。06:36:36已closed，**116.74sim／5837区间／1149.039wall**，`FAILED/unsupported_domain:Existing CLIMB planar-support domain; actual box tilt unsupported/from CLIMB/error=null/full_task_success=false`；原flags空／failure_latched=false／0reset。不是仍在途、wall耗尽或原生倾覆／碰撞。PUSH23.74s／EXIT31.32s／CLIMB31.34s进入、本源恢复和69.78s完整handoff保持。[真实partial／RR／POST域拒绝及坐标接收评价](</home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-v013-RR-partial-planar-domain-and-frame-evaluation-v1.json>) SHA`66f1d10862e4e1aff2adc56b41f4c1226f48af197072f0999e621d6e549541e0`，回顾性评价不倒签run前验收。

**本源真实partial与RR进展：**86.98s原plan事件`partial_applied=true/ready=false`，四足参考实际执行，原u=0/progress0/swing-ready=false，现成窗口四足各最小43.99/35.88/48.25/33.19N；88.50s原完整plan ready=true。RR **91.24s normal4.606N／COM33.453mm**、**92.04s native足z.034131m>=原.034000m且normal0**、**95.86s phase1/8.574N实际重载**。RL在本源仍成立，不拼v012；partial参考合法≠复活完整方案或提前授lift，clock失触位不替代native足高，也不补造精确settle事件。FL后续partial已执行，115.78s native FL脚点(.831304,.031744,.223861)m、normal8.272N/COM36.895mm只是**箱顶区域几何／载荷见证**，toe-box命名接触对仍null/valid=false；不据它写全脚登箱／CLIMB完成。

**终止层级与微小几何量：**最后支持域内POST为116.72s；116.74s完成物理积分后的箱姿态观测触发旧qxy绝对1e−6域，raw qy=−1.038638e−6。producer现成几何给真实top倾角.000135240度／角点高度跨度3.814微米、对固定world z=.2最大差2.211微米。原raw q／norm与单位化数学q分开，未回写物理／旧MathFrame；微小越界不是大角度倾覆，也不能以小误差证明任意tilt支持或直接调大阈值。**此次POST观测域拒绝不同于v012下一步前floor候选拒绝**。完整任务执行失败原样保持，RR已达层不抹掉；CLIMB/NAV未完成、最终原生任务后果未观察／mask无效，不改失败为成功。

**v015只读接口的具体接收差异：**已核现有helper源码／原索引4个SHA，不运行其12CPU或重新算几何。旧`MathFrame.position`为`inverse(raw_q)*(world−box_center)+(1.35,0,.1)`；v015 `point_to_box`是**单位化数学q下的居中box坐标，无这段平移**。因此旧canonical脚/COM不能直接送入helper居中box plane/distance；原canonical名义顶面z=.2、helper居中top z=.1是不同坐标，不是物理高度改变。接线必须显式frame_id／origin／rotation／native step/time，保留raw与derived表示、真实重力m/s²／normal N与friction、点/向量/平面offset转换；不能把box-local z当真实竖直或把无限top平面距离当完整OBB碰撞/接触证明。

**下一项（未完成）：**按[main06:51](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#main-v013-domain-geometry-next-20261018>)，Sim2Real将v015只读基础完整接入**保持重力竖直的规划坐标**及实际完整OBB/top/edges、独立ground、载荷/Jacobian方向与support/body/swing/landing/CLIMB/NAV边界。保留1mm/35mm/5N/25mm/10mm物理余量、原候选invalid/PD/限矩/物性/历史/clock与原成功；明示有限支持域／拒绝，不能只删旧guard或放宽四元数容差。现12CPU helper未集成／无可启动manifest；生产者交具体配置/接口后Reach增量核上述单位／坐标／原判据与后续实际原任务，不造另一几何实现、不重采/重跑v013。原48/468sim/NAV120/core2340+60/outer2400、单GPU1env同锁和阶段授权保持。此轮10源文件＋4helper hash、3选定RRnative、partial首尾/两plan事件/FL一点已核，不重算2348点／5837帧／8帧tilt窗／12CPU/FK/物理；37启动均closed保留分账，H0/H1/H2／世界模型收益未证。

唯一增量：[WM-07](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-v013-RR-postphysics-domain-centered-frame-20261018>)。

## v012原RL真实抬落已证，RR新floor拒绝；v013仅协议／启动映射（2026-10-18 06:24）

**v012实际结果已独立消费：**source `sim2real-user-test-v012-floor-aware-followup-a`／manifest `1e1f7fe005c60c1cbd4db196165144e352794c9f32a4e688ea85468d3f129227`，原report SHA`e9870206a6eaee0970cfda907be90094e79fd5e675192f24e659221c4413c451`，使用corrected analysis而非旧initial-clock-label。真实06:02:17已closed，86.98sim／4349区间／872.508wall，`FAILED/unsupported_domain:Original selected support/swing (including expanded fallback) rejected by new floor constraint; issued reference untouched/failed_from_phase=CLIMB/error=null/full_task_success=false`。这是真实整链执行未完成，**新规划域拒绝不是原生碰撞／摔倒或wall耗尽**。[实际RL层／后续floor拒绝评价](</home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-v012-RL-native-progress-floor-refusal-evaluation-v1.json>) SHA`df91a63a2db4f3bce4c4e104ff94b4cd27017ca159f04e71b16ec762e68d865b`。

**已达③RL真实动作层，不只是参考／锁存：**69.78s本源真实恢复＋原完整preserve-reference handoff成立，原hard-valid2350经floor后1311，ref/velocity/所有clock tensor/q/dq/root及actuator/obs-history规划事务保持。原RL在**72.56s normal4.710N<=5N／COM35.907mm**，**73.34s实足高.034319m超过原raised .034000m且normal0**，**76.96s原progress1且重载8.757N**；后续**85.46s native clock已到RR**，RL实际x.150897/z.023522m/载荷33.857N。clock73.00s lifted仅contact-loss锁存，当时足高.023537m尚未raised；不以它替代真实抬足。重载样本与到RR事实保留，不补造未记录的精确settle成功事件。PRE观测与POST端点分开，最大足高.054235m仅消费producer汇总，不重算全860点峰值／首次事件或重跑模型。

**最终拒绝与统计字段作用域：**86.98s RR普通候选hard-valid0；expanded最终选中1个原hard-valid完整解被floor postcheck拒绝，calf/nonfoot0，原flags空／CLIMB failure_latched=false，未发坏参考到下一物理步；已记录q/dq/root/actual PD与refusal-before-physics相同，不把这个局部保留记录说成所有controller metadata不变。**producer `new_followup_domain_refusals=[]`只汇总初次handoff事件，不代表整阶段没有floor拒绝**；本评价分别记initial-handoff拒绝0与later-selected-floor拒绝true。不能从一个selected expanded失败证明所有floor-safe/partial候选皆无解。原PUSH/EXIT／真实恢复／RL里程碑保持，RR卸载抬落、CLIMB/NAV未完成，最终原生物理结局因规划停止未观察，不拼接不同版本成成功回合。

**v013协议与实际start已接，未代写动态效果：**manifest `a7d6e1794f36940d9ac52206a734bccf01272542438ba573ca0e31abd2d72151`；source `sim2real-user-test-v013-expanded-floor-followup-a`已于**06:17:25.630**实际启动，以start原件覆盖旧“尚未启动”。[新域／partial层级映射](</home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-v013-expanded-partial-protocol-mapping-v1.json>) SHA`ece2f42aea416ae9cc5eb034cc1e1d9295a93c7f50449bbbdbd83ab0559aaaf2`只核实际源码／差异／start，不读增长control，不倒签run前验收。expanded原32768/seed913/范围/hard gate/score不变，同floor mask移到ready后／score前；ordinary replan允许原pose-feasible四足partial参考，但**swing_ready仍false，原support_ready/实际卸载门槛仍禁止抬腿**。初次恢复handoff文件byte-identical、仍要求完整swing＋原history事务，不能将ordinary partial合法提交错套为初次完整接回。

**计划与完成界限：**recorded RR screen完整expanded仍无解、原partial可行只是新模型静态结果，不是RR动态改善；本组未重跑screen／5CPU／SDK／旧统计／FK／物理。按[main06:21](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#main-v012-RL-milestone-v013-20261018>)，只消费当前唯一v013的真实partial参考提交／完整swing转变、RR原<=5N／实足高抬落与后段原结果。handoff后不套80s准备早停，原任务／安全／core给真实终态；没有原件则保持缺失，不发重复v012/v013或另一恢复器。原1mm/10um floor、5N/25mm/10mm/calm/PD/限矩/contact/35mm/物性/历史与单GPU1env同锁/core2340+60/outer2400不变。37启动=旧20+WM7+producer10含本在途源，非hardcap；旧v011未测RL身份不回填，旧数据／账本不改，H0/H1/H2／完整CLIMB-NAV／模型收益未成立。

唯一增量回执：[WM-07](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-v012-native-RL-v013-partial-boundaries-20261018>)。

## v011实际解除小腿支撑、四足接回；原卸载／整链未测（2026-10-18 05:38）

**已完成独立评价：**source `sim2real-user-test-v011-ground-support-recovery-a`／`wm07-ground-support-recovery-v011`，manifest `af7baf9c7f2ba0844f46d150f13ce4104b65fd7a4db2cbc211f81f313ca29fb4`，parent v010 `2c8148fa…5f95a0`。原report SHA`bf0a9ab791c254b8db0a63943bc2131e20d29424795b7d41a2d9d3066fc34140`／closure／producer汇总相等，真实05:18:49闭合：69.78sim／3489区间／691.826wall，`PREPARATION_EXPERIMENT_COMPLETE/actual_calf_ground_support_released_fourfeet_restored/task_phase_at_stop=CLIMB/full_task_success=false/error=null`。是预声明准备观察终点，不是wall耗尽／原生物理失败或CLIMB成功。[动作—实际负载—未测原卸载—任务删失评价](</home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-v011-actual-recovery-layered-evaluation-v1.json>) SHA`cbebac5d27323b920732a010848ab925e9a033447985067423d71feb69af4078`。run前非正式组接收的身份保留，此为回顾性结果评价，不倒签。

**①新动作与②实际载荷局部通过：**同source62.88s只记录实际无calf负载时的高度／姿态reference anchor，不回放q/clock/脚位/history；66.18s一次fresh-native完整规划／0拒绝，66.20s首次真实动作，180控制区间。原reference/velocity/clock/q/dq/root和actuator/obs历史规划前后相等（history SHA`dbb86a48…59b9d9df`）。这是新的requested控制原语，**不是仅改目标／全控制方程未变**；原limiter/PD/队列仍自然更新。新域ground载荷>5N与.025/.1等连续2s是显式接地恢复域，未回改旧v009 .001/.01/10s。原完整路径/IK/box/限位/载荷/力矩/摆腿加plane起始不加深／FR_calf单调解除／终点1mm通过，1mm新floor条件不是将原leg-box5mm降为1mm。

**真实完成而非nominal gap：**同POST66.18s calf normal85.368N／四足和128.251N，67.40s首记录所有非足normal<=1N；69.78s calf及所有非足normal0N、四足29.508/66.187/37.234/80.419N、合计213.348N。实际root z .217877→.241909m，body目标误差4.180mm／角误差.013461rad。已核现成样本**68.78–69.78s的51个布尔完成门禁全部true／间隔20ms**；只消费producer已有数值范围／峰值和180样本，不重算其全统计或提取control末51行。该1s控制采样的准备完成valid=true，不宣称所有5ms子步连续或独立鲁棒性／精确wrench。

**③④未测试，不能写原卸载失败：**活动期support_ready只收紧false、不授lift，不降原5N/25mm/10mm/calm；末RL37.234N是四足准备终态，不是已试原卸载仍失败。原RL卸载／真实抬落effect=null/valid=false，CLIMB未完成／NAV未进入／最终物理结局因隔离准备终点删失。PUSH23.74s／EXIT31.32s原成功和CLIMB31.34s真实进入保持。**旧stalled_support_preparation_cache停在66.16s**，其85N／旧.191m目标／COM/u不是69.78s当前状态；此次完成只取同POST实际witness，issued参考cache69.76s另相。新handoff必须fresh读实际非足／足载荷／根状态和原guidance，不复用旧cache宣称已卸载或仍接地。

**下一项（未完成）：**按[main05:21](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#main-ground-recovery-success-followup-20261018>)，Sim2Real把v012仅收紧floor mask接入原candidate tier前、补完整41点swing plane，并将同一新source自然恢复后的真实reference/velocity/anchor接回原preserve-reference全规划。当前7CPU helper不是已集成候选；不重跑单独v011准备／同一身份，不注入本源末态到新环境。保持原invalid不能复活、原候选不扩高度网格；全集为空记录具体拒绝并保持支持，不降plane／门槛。原10mm/25mm/<=5N/calm/PD/限矩/35mm/contact/物性/原成功条件与单GPU1env同锁/core2340+60/outer2400不变。后续四层分别记：恢复完成、plane-aware计划采纳／拒绝、实际原卸载抬落、CLIMB/NAV整链；新实际终点运行前声明。此轮Reach0物理／FK／模型／拟合，无他组源／角色／账本改写；35真实启动按旧20+WM7+producer8保留，不作hardcap／跨版成功率，H0/H1/H2／部署均未证。

唯一增量回执：[WM-07](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-v011-actual-load-transfer-layers-20261018>)。

## v010原生命名地面接触已证，诊断结束不等任务成功（2026-10-18 04:53）

**独立评价已完成：**source `sim2real-user-test-v010-contact-identity-a`／candidate `wm07-contact-identity-diagnostic-v010`，manifest `2c8148faf40c846efe5203bd3d6d0ab4d296246f5d60e68f648a706e025f95a0`（parent v009 `b622830c…e0ad41`）。原report SHA`bfea9f981ed88aa8fd0ed322bb316b12441445e7e73fee107529a4914c12f0d4`与closure／producer汇总同值；真实04:26闭合，65.46sim／3273区间／679.293wall，**DIAGNOSTIC_COMPLETE**，按运行前声明的身份观察2s主动收尾。`full_task_success=false/task_phase_at_stop=CLIMB/error=null`，旧phase=PUSH不覆盖实际阶段。这不是2340预算截断、原生物理失败或任务成功。[独立绑定／诊断终点／任务删失评价](</home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-v010-ground-identity-diagnostic-evaluation-v1.json>) SHA`e9a6e5b1ca1888b487d8e09dfd7600f6865ab430652cdea3d11cdf27d514d59b`。运行前未有本组形式接收的sidecar事实保留，此次为回顾性结果评价、不倒签验收。

**关键新有效标签：**真实FR_calf body与26个peer路径／顺序接合；在**63.46–65.46s／101控制采样点**，唯一载荷对端是实际地面`/World/ground/terrain/GroundPlane/CollisionPlane`，pair-normal账目残差0N、其余已过滤peer法向0，真实raw patch点z约0。因此本源本窗小腿—地面额外法向支持`true/valid=true`，原生点可用；**不再缺对端／点**。原v009缺对端标签保持原样，不用v010回填。2s包含接触建立，法向均**75.152N**、终端**85.106N**不可混用；微米级负separation不能单独写成硬碰撞损伤或唯一控制根因。

**阶段／效果分开：**PUSH23.74s原完成、EXIT31.32s原READY、首CLIMB物理31.34s均保留；65.46s仍未完成CLIMB／NAV未进入。诊断observed为有效目标结果，原任务最终物理success/failure均null/valid=false，删失原因为预声明诊断早停而非wall。准备事件／planner尝试／拒绝均0、最大dwell.16s；身份观察不是准备／恢复动作效果、卸载／抬落／完整链通过。

**测量语义与核验范围：**本SDK `net_forces_w/force_matrix_w`为**normal-only**，friction另列；此前v009“净向上力”在解释层明确为法向，旧字节／flag／用途不变。新源normal/friction rawpatch独立clone共享count/start缓冲，点为原生patch而非平均点，未从mean点×合力声称精确wrench。末POST65.46s四足normal128.313N＋calf85.106N＝213.419N仅为负载线索，PRE65.44s RL49.791N／COM17.094mm／u0另层，不跨时相加。每20ms控制边界取最后5ms子步，不是每子步全时连续或力积分／完整动态安全。已核7个索引文件大小／hash、真实binding、两窗首尾2点、报告相等与7个原控制/抬腿源码同父版；只消费生产者101点统计、原尾行一条，不重算2s窗／旧17CPU／SDK／plane15CPU／FK／全轨迹。新增tensor view不保证逐tick bit-identical。

**下一项（未完成）：**按[main04:51](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#main-ground-support-confirmed-20261018>)，Sim2Real将v011纯CPU plane几何准备接为**有已接地起态域、进入／退出／拒绝条件的支撑姿态／负载转移原语**，并交原完整box/限位/限矩/支撑/摆腿路径、连续issued reference/velocity/clock/history和实际载荷见证。不能以从第一点正gap作永远拒绝，也不能clip初始接触或默许更深接触；新域／解除方向与数值须运行前明示。评价依次分新动作合法请求/规划/执行、实际小腿载荷解除与足支撑接回、原<=5N允许RL真实抬落、CLIMB/NAV/整链。plane helper／静态gap或法向下降不等后层通过。原10mm／25mm／calm/35mm/contact/PD/限矩/物性/成功条件及单GPU1env同锁/core2340+60/outer2400保持。v011尚非完整可启动恢复候选，本组不另实现第二控制、不补采已齐身份或等待旧次数批准；0新增物理／模型／拟合／他组账本改写，跨线34保留开发分账、H0/H1/H2未证明。

唯一回执：[WM-07](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-v010-ground-identity-diagnostic-masks-20261018>)。

## v009持续非足净力的有效标签与诊断终点分层（2026-10-18 04:07）

**已完成：**消费producer03:34交付的v009两窗／持续性统计，绑定原source `sim2real-user-test-v009-stalled-support-replan-a`、manifest `b622830c…e0ad41`、原report `08374f96…ed0244`及closed control `b4c48246…c026ac`，不重扫9028／全control、不重算两窗／FK。8项原索引文件大小／SHA与4项额外引用已核，只查两窗各首尾4样本及旧终态cache同一性。[独立消费与后续诊断标签口径](</home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-v009-native-support-window-consumption-v1.json>) SHA`b27776f4d4821a9e8d7a8692d3fc336c0f578a5f950eceb5e731c889e489d4d4`。不是新source预验收／启动或正式测试。

**新增有效标签与保留mask：**原生缓存FR_calf向上>1N持续**控制采样**区间63.44–243.98s／9028样本已可消费；不能继续称持续性未交。末窗501样本均约85.206N，RL均49.749N、仍未原<=5N卸载，新准备动作／planner尝试／拒绝均0。只有body净力，**对端／点／外部支撑接触对／精确wrench／唯一因果仍null/valid=false**；不因数值接近重力就命名ground或排除self。缓存norm>1N筛选使缺body项不等于零，20ms记录不等子步恒定。

**独立口径核对：**首窗626样本中calf存在573，四足均值应取同573样本**130.0495N**加calf83.4288N＝213.4783N；不能将全626样本四足137.0075N与calf均值相加。末窗同501样本合计213.5117N与planner重力213.5146N接近，仅负载线索而非精确力／力矩平衡；足box-math／非足world同precontrol相位仍分开。窗起点已有原计时，不重置计时来构造新最大值；分支越界样本可重叠，不把88/182/37相加冒196总数。

**当前接续：**按[main03:51](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#main-v009-no-action-contact-support-20261018>)，Sim2Real核真实FR_calf候选对端／点的SDK/场景绑定，并做真实支撑姿态／载荷转移；原两窗和尾报已完成，不催重做。若必须实例化才可取身份，已允许固定v009控制／物性／安全的必要观察诊断新source并按预声明终点早停；若已有字段足够，直接并入恢复，不强加独立探针。**诊断目标达到／可用性结论仅诊断结果，不是CLIMB成功或失败**；原物理结局未观察到即删失，真实原生失败不屏蔽。producer需声明实际新source/parent/SHA、观测更新相位、对端可用性／点语义和诊断终点，新增sensor若改变lazy更新／历史须披露，不假称逐tick等价。新恢复的条件、请求、规划、参考、实际卸载／抬落和整链结局分层；对端不符／缺量／完整路径不支持则拒绝新增恢复，不强抬腿。原10mm／25mm／<=5N／calm／native安全与core2340+60/outer2400保持，不采用仅放宽calm。Reach没有新候选可绑定，不代签实施已完成；0物理／模型／拟合／他组账本改写。

唯一增量回执：[WM-07](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-v009-native-window-labels-diagnostic-endpoint-20261018>)。原03:32终态评价、0动作与资源删失保持，不回填其当时“尚缺持续性”的时间快照。

## v009真实收尾：core wall截断，新准备动作零尝试（2026-10-18 03:32）

**已完成的独立消费：**source `sim2real-user-test-v009-stalled-support-replan-a`／candidate `wm07-stalled-support-replan-v009`，manifest `b622830c4765e57c6d800f0cc4de2373b5df0d24ca71cc51bb7519e2dbe0ad41`。已核实际集成源码／配置与原抬腿模块未变，并消费03:24真实闭合的report及closure；这不是v008的operator缺native尾报，也不再称在途。[协议／固定前缀评价](</home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-v009-preparation-protocol-fixed-prefix-evaluation-v1.json>) SHA`c6c19cf220b4401a8d8c1bff88e58bdb1af6a23ebe76fd08413f7919f6da19b4`，仅回顾104.22s已发布快照、不倒签预验收；[真实收尾分层评价](</home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-producer-v009-core-budget-no-action-evaluation-v1.json>) SHA`493b6e3b535bc32a1162512ea51706f49c9bfa43a848738f88e8f13abb2f292b`。后者覆盖终态，前者的“未见终态”只保留原快照作用域。

**真实未完成，不改成物理失败或成功：**原report `FAILED/full_task_success=false/reason=wall_budget_exceeded/failed_from_phase=CLIMB/error=null`，原旧`phase=PUSH`不覆盖events；core执行**2340.135s**，共**12200区间／244.00s模拟**，2340core＋60收尾仍在原outer2400合同内。外部returncode0仅说明正常交付尾报，不等任务成功。PUSH **23.74s true-valid**、EXIT **31.32s true-valid**、首CLIMB物理**31.34s**保持；终端仍CLIMB complete=false、failure_latched=false、flags空、unsupported=null，NAV观察窗未进入。整链执行未完成已知，预算截断后的最终原生物理完成／失败unknown；不凭通用FAILED虚填原生安全失败，也不抹掉已经进入的CLIMB。

**新动作未发生，不是“重规划失败”：**严格新动作域根速<.001m/s、角速<.01rad/s等连续10s；producer既有最终screen给最大**9.56s<10s**，calm不符196样本，最终当下条件全true但仅连续**2.06s**。**准备事件0／规划尝试0／新准备参考0／无实际planner拒绝**，仍余一次机会但源已闭合，不补跑找触发。原<=5N卸载抬腿、25mm COM条件和普通10mm重规划语义不变。未发新动作，卸载／抬落的新增控制效果无有效标签；不能把离散true片段拼成满足持续条件。

**native与因果界限：**最后完成区间244.00s，cache属于prephysics243.98s／step12199，两相位分开；native RL载荷约49.7848N、progress0／未抬、COM margin17.0984mm、u0。实际缓存能识别FR_calf净向上力约85.2076N，已不同于v008纯离线FK假设，但接触对端／点与持续性未由本组独立确认，不断唯一根因。只核最终一帧、现成汇总与24个小文件hash引用，不重复12200帧／全10s窗口统计、FK／CPU／模型／物理。

**下一项而非已完成：**依main03:21，Sim2Real用已有native日志给首次RL停滞与终端两个必要短窗的calm重置、FR_calf载荷持续性、四足载荷／根高度和原支撑规划假设，world-model集成，Reach消费用途／动作事件／删失口径。producer提出放宽到普通全支撑replan calm域.025/.1的离线谓词对照，假想74.20s可满足10s，**仅proposal／predicate replay，不是实际触发、规划、抬腿或改善，也未由本评价采用**。若非足承重持续，下一控制须显式处理支撑姿态／载荷转移，不能只调阈值找触发。当前不缺native接线／尾报，不再等旧quota或形式批准；不新建竞争版本／不重复启动。原开发身份、历史账本和5311/5312已见用途保持，Reach零新物理／拟合。唯一过程回执：[WM-07](</home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-v009-core-budget-no-action-20261018>)。

## v008已operator闭合：CLIMB已进入但观察窗未完成（2026-10-18 02:39）

**v008已按operator真实闭合，本组完成尾部／阶段分层评价（2026-10-18 02:39）：**已消费producer闭合`operator_reconciled_no_original_terminal_report`及同字节closure，不再等一个并不存在的native report或按旧快照称仍在运行。实际SSH返回**255**、约**2430.455s**，与2400+30外层限制相符，但**原native终止／信号原因与进程最终exit code未知**，不虚构124／137、精确native timeout或原生物理失败。[operator／原尾帧／观察截断评价](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-producer-v008-operator-closure-evaluation-v1.json)／[WM-07独立回执](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-v008-operator-closure-tail-unknown-20261018)。不为补造report重跑或把已收费源标免费。

**已证阶段不因缺native尾报而抹去：**同源原PUSH23.74s true/valid、PUSH_EXIT原READY31.32s true/valid、31.34s真实CLIMB entered保持。最后完整记录**255.18s／step12759**仍CLIMB，原complete=false、stable_s=0、failure_latched=false、unsupported=null、原flags空；NAV在观察窗内未进入。**整链执行未完成已知；CLIMB最终native完成／原生终止原因／最后帧之后物理状态unknown**，不改CLIMB not_entered或物理安全失败。原01:23固定前缀和当时inflight记录保留其时间作用域，不改原件。

**实际原放行门槛未满足，而非已证明唯一原因：**producer现成源映射／统计给62.92–255.18s持续selected RL、progress0／not_lifted，最后10s RL约49.67–49.81N，原**<=5N卸载才抬腿**未满足。Reach只核一条最终原帧的304维crawl原映射（FL/FR/RL/RR，非关节发出顺序）、RL onehot/progress/lifted及实际foot load接线；actor观测对应255.16s、postphysics负载对应255.18s，两个相位分开，不重做12759帧／501尾样本汇总或任何FK／CPU。native COM／u／valid内部量在旧源缺失，producer模型重算17.10mm/25mm裕量、旧目标误差10.149mm仅支持假设，不注入当native触发测量；不能凭128N四足合力唯一推断非足部接触或由静态误差断唯一根因。

**main02:21已采用v009方向，本组预先评价边界：**Sim2Real制作有实际状态限制、最多一次的全四足支撑准备重规划；这是新增控制入口，不改原普通replan／<=5N抬腿放行，也不装作旧条件一直满足。触发必须有native后腿地面／phase0未抬／四足>=8N／根速度角速／原安全valid/path/limits／native COM margin<25mm／u=0／RLload>5N／oldtargetXY>=10mm连续10s等实际支持；缺关键native字段或条件不符则拒绝／记录，不能强触发或用FK估计补量。保持原preserve-reference规划接口的真实reference/velocity/队列/history和完整规划可行性，不能跳clock或锁箱。**新参考／静态plan feasible不是实际卸载／抬腿／落脚或CLIMB／整链成功**，新源要逐一记录。已见v009证据是原型／CPU，不代签完整接线或物理通过，实际新源码／配置到齐才增量绑定。

**收尾与控制效果分开：**outer wall仍2400，新版可明确core2340+收尾60、统一remote monotonic，metadata如实记录core观察窗变短；这是终态捕获改进，不是机器人控制提升，不延长总wall或改sim/门槛。SDK关闭／断连若仍漏报照实unknown，operator closure永不冒充native report。旧20＋WM7＋producer5关联32是已计真实启动，0active为main02:21快照，不作hardcap／同版成功率。原阶段成功、所有负例／开发身份和正式train/dev/diag均保留；Reach未改他组账本／用途，0新物理／FK／actor/model／拟合或旧检查重跑。

以下01:23固定前缀和01:57“待终态”均是历史；新operator闭合没有补造native report或将边界里程碑升级为整链成功。


## v008固定边界：退出通过，CLIMB已实际进入（2026-10-18 01:57，无终态主张）

**v008已发生的边界里程碑已独立消费，未把前缀当终态（2026-10-18 01:57）：**producer于01:23发布的固定前缀bytes／SHA证明新source原PUSH **23.74s完成true/valid**，**31.32s原PUSH_EXIT／CLIMB准入完成true/valid**（原全部12项当下条件true、实际连续1.000000s），**31.34s第一次真实CLIMB物理控制、输入304维**。不只是激活controller，CLIMB已进入不能再写not_entered。[固定边界标签／终态分类](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-producer-v008-immutable-boundary-evaluation-v1.json)／[WM-07回执](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-v008-fixed-prefix-exit-CLIMB-entry-20261018)。这是同一实际动态箱的新连续运行，旧v007退出异常原样保留；本次不是原v007回填成功或完整同箱任务通过。

**观测界限精确：**本独立评价只消费已发布不可变前缀（01:21:42截到47.24s／step2362，37,654,987bytes，SHA`5105c113…1a374`），**不是当前全运行状态或终态**；不追读增长中的raw control、不重复377条退出审计／323旧参考数学／CPU／FK。main01:50另见234.18s仍CLIMB，是之后的在途观察，不被本固定47.24s材料伪装成独立重新核查。截至本组收尾尚未取得实际最终report/closure；预计wall截止约01:53:50**不等于已经拿到timeout原因回执**，不据时钟或旧inflight标志虚填当前成功／失败／继续运行。

**只绑定原门禁，不倒加准入条件：**原退出READY包含conversion6s、四足>=8N、根线角速度、姿态／yaw、actual臂腿速度、PD/reference到原goal误差、箱前足域、零请求和safety连续1s。本源actual q在真实native硬限位内、PD请求在reference soft内；actual q不全落nominal reference soft只是diagnostic，原准入没有该项，也没有“actual q距default误差小”的项，不能事后加条件把原READY改false。actual硬／nominal soft／PD request／measured q分层，不把参考soft边界当原USD硬限位。原PUSH226→退出210→CLIMB304、三处box身份与0reset见证一致。

| 已证明量 | 标签 | 尚未证明量 |
|---|---|---|
| PUSH原完成 | true/valid，23.74s | 不等后段成功 |
| PUSH_EXIT原实际准入 | true/valid，31.32s，实际1s | 不是CLIMB后平台NAV READY，也不保证动态攀爬 |
| CLIMB实际物理进入 | entered/valid，31.34s | 原CLIMB完成／终态仍null/invalid，不能从已进入推完成 |
| NAV／整链终态 | 固定前缀中未见NAV进入；最终entry／complete未知 | 不能据缺尾写native物理失败／not_entered最终结局或整链通过 |

**终态收口预先明确：**若先有原native成功／物理失败／域拒绝，沿实际原件；若wall2400先到，记**运行资源超时／观察截断**及真实最后完整区间，保留PUSH／EXIT已成功与CLIMB已进入，不改成CLIMB未进入或native物理0%成功。若无report，需producer实际进程／timeout/closure与固定最后前缀来界定；不能猜返回码／仿真步数。producer原runner负责停止／收集，Reach不延长wall、不提前kill、不重复启动。闭合后优先既有少量stage/crawlclock／足与箱位移点区分推进、阶段条件与吞吐限制，不为旧字段新采或盲重。

这是新边界能力的**部分观测评价**，不是CLIMB／NAV／整链、鲁棒性、H0/AB或世界模型收益。producer研发身份和采样当时未正式组间接收状态保持，不重编WM source；main01:22旧20＋WM7＋producer5关联32是启动snapshot而非hardcap／最终完成计数。本组0新物理／actor/model／FK／拟合／旧审计／他组ledger修改。

下方v007退出异常只属原v007，不用于本v008；本固定观测也不提前给CLIMB或整链最终成功／物理失败。


## producer v007首次原PUSH完成、退出仍运行异常（2026-10-18 01:09）

**producer v007的原PUSH完成已独立核实，整链仍未完成（2026-10-18 01:09）：**本组按main00:51任务直接消费Sim2Real真实用户研发源`sim2real-user-test-v007-supported-startup-pose-a`，不是因不在WM目录拒收／重采。原PUSH在**23.74s／step1187完成true/valid**：原completion callback contact_seen=true、实际停稳0.50000006s，箱相对初态x推进**0.599154592m**、线速3.4689e−5m/s；实际mode boundary从PUSH到PUSH_EXIT且before/after物理／队列快照一致。21.62s原合法接触见证8项均true。随后**30.26s／1513区间在PUSH_EXIT运行异常**`Supported brake reference outside original soft limits`；CLIMB/NAV未进入。[原源／阶段／unknown独立评价](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-18/wm07-producer-v007-PUSH-success-exit-error-evaluation-v2.json)／[WM-07回执](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-producer-v007-PUSH-success-exit-error-20261018)。

| 评价对象 | 已有真实支持 | 本组结论 |
|---|---|---|
| PUSH | 原完整callback／contact history／.5s实际停稳及真实箱状态；23.74s转换event | **完成true／valid**，后续异常不抹去这个阶段成功 |
| PUSH_EXIT | 23.74s逻辑进入，23.76s有实际EXIT阶段命令，30.26s引用原soft-limit检查抛错 | 运行已中断；**退出物理完成null／invalid**，已知是计算参考受限位检查拒绝，不偷换为原native接触失败或实际关节限位失败 |
| CLIMB准入／CLIMB／NAV准入／NAV | legal_climb_entry=false，未观察进入 | 未进入，各自completion null／invalid，不补0或成功 |
| 整条运行／动态后果 | 原report FAILED／rawFALSE，error具体；legacy phase=PUSH但event/failed_from_phase=PUSH_EXIT | **运行／整链未完成是已知事实**；未来物理整链／后段结果unknown，与阶段PUSH成功分开 |

本源0中途reset，实际source/初态/边界/终态同一个动态box已对齐；PUSH完成行safety_ok=true，既有实际substep峰值0.965215<原.98，空flags字典不单独当“全程每门禁已逐帧核验”。本组检查6个必要状态，其中4个是直接标签依据（首合法接触、PUSH完成、首EXIT、末态），另2个是退出开始／末段邻帧，**没有重跑1513帧／全部slew／323条参考重建／8CPU／任何FK或物理**。

**身份与计账不倒签：**原runtime role字段与producer sidecar的`user_directed_development_debug_not_group_accepted_not_independent_test`一起保留，采样当时formal group binding/owner reception=false不改成true；这是事后实际阶段评价，不是当时正式验收。producer本源1次，producer已closed4／WM已closed7／旧20的main00:51关联计数31保留，各版本不混率；本组没有迁移角色／更名WM source／写他组ledger或发布拟合许可。此前v004/v005/v006和WM0007负例不被此单例覆盖，未在本次冒称已独立评价所有旧源。

**当前工程关键路径是退出与合法CLIMB接管，而不是继续PUSH高度扫描：**main00:51已采用Sim2Real现有v008离散制动参考方向。保留v007成功PUSH启动／完整关节准备／接触前缀、原软限位／速率／加速度／35mm／力矩和真实历史；先核实际q与PD请求／补偿／延迟和原准入goal兼容性，不能只消除Python异常便称READY。producer323参考重建和324步新helper数学／8CPU是既有组件证据，**未集成／未物理测试不叫退出已修好**；若goal也需改，完整披露为退出协议修订而非单因素数学小改。新源须从真实原reset自然再过PUSH，前缀如果再失败也保留，不注入旧成功末态或挑成功前缀计后段。用户stage及研发直测权限沿同链锁／单GPUenv和原单次时限执行，不再为WM编号／形式签署重跑或逐次问名额；H0双候选和模型决策贡献仍未建立。

以下旧v003 partial／2mm声明与所有负例为历史，不是当前阻塞；本单例阶段成功不回填旧失败／正式验收或独立模型结果。


## v003完整POSE语义部分绑定与合成参考边界（2026-10-17 22:38，非物理结果）

**完整分阶段POSE v003已完成8类实际语义增量，剩1个精确参考上界说明（2026-10-17 22:38）：**已接main22:25采用范围、producer22:26真实新配置sidecar；manifest`277d091e…7e04d`、stage/Cartesian flags=true、0env/step/actor配置核验已到，**不缺配置、不重复9CPU/14静态支持**。本组核4个parent/child路径及原native安全／softq偏好字节保持，完成ALIGN_HIGH／DESCEND／低位originalgate／POSE路由／原始reset／cache和后续face腿释放字段映射。[部分binding](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/wm07-staged-POSE-v003-partial-binding-v1.json)／[原WM-07实际差异](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-staged-v003-clamp-contract-gap-20261017)；当前`final_acceptance=false`，不能作owner最终launch receipt。

**必须按完整POSE解释：**初始路径增加ALIGN_HIGH（boxlocal退让x/y、高于final .30m，实际xyz35/60/35mm及armdq<.25持续.10s），再DESCEND、原低位retreatgate／face。初始也提前采用entry pitch1.5、orientation taskscale.1（此前1.0/.5）；配置数值虽来自原模式，早期有效目标与优先级确实变化，不能只称xyz消融／有效权重不变。14个静态目标位置支持、54.41mm最小模型间距只是已探索开发支持，不证明在线IK、整姿态或动态连续安全；解不能注入实际执行。

**具体剩余差异，不是物理失败：**[纯CPU合成源函数例](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/wm07-staged-v003-reference-contract-counterexample-v1.json)在原高位合法容差内输入actual local z=.32m、x/y到位、dq0持续.10s，进入DESCEND后`(actual_z−.10dt).clamp(final,final+.30)`输出约.30m，比actual低约20mm，故不能无条件宣称“相对actual最多2mm”。这是upperclip优先与实际到位容差的**参考保证表述／控制协议边界**，不是观测到新物理失败、不证明unsafe运动。**同轮作用域更正：**xy丢失前后参考同为.30m，反例**不证明**xy丢失额外下降／新20mm参考跳变；先前把pause与actual-relative lead一并说成冲突过宽，[更正记录](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/wm07-staged-v003-reference-bound-scope-clarification-v1.json)及原记录均保留。

**唯一问题／责任方与独立已完成工作：**Sim2Real控制owner明确高位actual>high时采用clip优先的真实保证，或隔离修复为严格actual-relative lead；main可明确原采用范围。按实际所选语义给精确parent/diff/newSHA或真实范围确认及此边界最小验证，不重做全部配置／9测试／14FK，不要求新次数。本组不擅改控制、不凭同一9通过替全局2mm保证签名；其余8类源／POSE/handoff/原门槛映射已实际完成，不泛称整个包未交或停止所有独立工作。新候选物理结果仍unknown，source0006负例和旧26累计／全部数据身份保持。

以下0006实际失败仍是最新已消费物理结果；本节只是精确源函数语义与合成边界，不新增真实任务样本／不重标原失败。


## WM-07 source0006：软偏好实际启用，原接触失败（2026-10-17 22:16）

**净空偏好v002实跑0006已独立评价（2026-10-17 22:16）：**550控制区间／11.00s、0中途reset，原flag只有`invalid_hand_contact=true`、`actual_surface_clearance=false`、error=null。**PUSH／整链false valid、PUSH entered，CLIMB/NAV及准入未进入**。retreat/face/initial complete/motion_ready仍false，legblend0；无0005净空flag不等于PUSH修好。[新源／实际active／原接触分支评价](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/wm07-source0006-soft-preference-contact-evaluation-v1.json)／[WM-07回复](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-wm07-source0006-enabled-preference-failure-20261017)。

**“初始偏好未启用”已不是当前解释：**已核原source/control SHA与owner现成550帧汇总，actual-q偏好550/550 active；9.74s/step487起64帧positive residual，最大3.857715mm，末值0.877778mm。Reach独立解码首／末两条cache证实active，**不重做550帧汇总或旧测试**。55mm软目标／行权重10与35mm原终止是不同量；active或正residual不是安全／实际到位／完成保证。原v002有限增量真实signer是main，本组保持`is_Reach_signature=false`，不冒充本人对该版控制签署。

| 0006原接触检查 | 真实末帧与原门槛 | 评价 |
|---|---|---|
| 高度带 | abs(box-local z)=0.100302242m，原上界0.0901m | 高10.202242mm，false |
| 抵抗力大小／方向 | 合力18.647024N、近竖向；抵抗轴约−0.000002663N | 原>1N及>80%两项均false |
| 其他原检查 | 有限、tip距11.304521mm<70mm、front/lateral | true；原norm>1激活下invalidflag与witness一致 |

这些三分支**只属于0006**，不回填0004／0005或旧0003。0006实际10个路径点／q/dq/PD/cache及见证owner已交齐，末tip约[.491737,.021347,.210388]m，shield前target约[.410199,.005706,.100000]m，尚未实际到原退让点；未录5ms接触／delayqueue仍未知，参考不当执行／已到位。计至本closure新phase6closed＝2operationalunknown＋4跨版本原生PUSH失败，旧20保留、关联26，不合并同版成功率／H0/模型收益或新hardcap。Reach0物理／FK／actor/model／拟合／阈值或他组账本修改。

**main22:04已采用下一具体路径假设，不再诊断相同mask／采相同witness：**由Sim2Real给实际到位驱动的“可支持高度层箱前退让／侧向对齐→守住退让位置受限下降→原face advance”新阶段控制候选。只改变初始路径／推进规则，保持v002已启用偏好及其原参数、原35mm/接触/力矩/碰撞、名义最终目标、权重PD/限速/物性/初始化和PUSH48s及后链。候选须事前明确中间目标支持域、实际位置／低速度／持续量／拒绝及阶段事件；不能按时钟或target已写切换，不能强设不可达高点。Reach在真实新manifest到齐做精确阶段语义增量；owner唯一集成／采集沿现有stage授权，不等main次数。仅避上沿却卡阶段／超时仍未完成，不无改动重放v002或换seed追成功。

以下旧“v002物理结果unknown／待main或Reach增量”是当时快照，当前source0006已实际运行并负结果闭合，旧签署仍按真实main署名保存。


## WM-07 Cartesian首案原生净空失败（2026-10-17 21:36，不是改善成绩）

**Cartesian首案0005原生净空失败已独立消费（2026-10-17 21:36）：**新控制769控制区间／15.38s、原flag仅`actual_surface_clearance=true`，`invalid_hand_contact=false`、error=null、report0中途reset。**PUSH entered／false valid、整链false valid，CLIMB/NAV及准入未进入**；不是初始化unknown，也不是PUSH已经修好。[原源／阶段／净空定义／引用评价](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/wm07-source0005-clearance-evaluation-v1.json)／[WM-07回复](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-wm07-source0005-clearance-failure-20261017)。retreat到位false、height/face持续量0、motion_ready=false、legblend0；避开0004接触flag却尚未retreat完成便触发另一安全门禁，不能拿终止时间变长作效率或控制改善。

**非活动接触检查不能当失败分支：**末帧hand force=0、contact point缺失，原invalid_hand_contact=false；witness里finite/height等false只是无有效接触时的诊断量，不是本次非法接触终止或0004同分支。target约[.41019,.00570,.10000]m是shield前计算参考，实际tip约[.44368,.13601,.24963]m；参考高度合法不证明实际到位／原生净空安全，after-shieldref也不是含重力／平滑／延迟后的真实施加目标。

**已有几何诊断只作原代理模型重建引用，本组未重算：**owner已交末两帧、原guard／asset及joint selector映射的静态6姿态proxy核对；本组只核原source SHA、实际q／PD请求／cache逐项接合和35mm不等式。原actual_surface_clearance用当前实际6臂q，在源MuJoCo几何proxy里对link1…6与base_link求最小表面距，**不是Isaac真实网格碰撞flag或全机器人净空**。

| 同源原代理静态重建 | 15.36s／step768 | 15.38s／step769 | 范围 |
|---|---:|---:|---|
| actual q最小距 | 35.587471mm | 34.832496mm | 终态link5-base_link，低于原35mm门槛约0.167504mm；正净空不足安全余量≠已经硬碰撞 |
| shield后／重力前reference端点 | 57.881005mm | 60.133658mm | reference端点不等实际已达／整个轨迹安全 |
| 写入PD请求端点 | 76.552249mm | 76.552339mm | 请求不是私有delay buffer后的实际target |

这些是**owner现成静态模型计算**的source/状态接线核对，不是Reach新实测或物理回放；本组0FK／0mj_step／0新环境／0actor／0旧测试重跑。参考/PD代理端点安全而实际proxy越界说明需要具体路径／制动／跟踪／坐标接线诊断，**不能唯一归因为delay、IK或任何一层**；缺执行器队列／子步信息就mask。原35mm门槛、权重PD、原PUSH目标与安全不降。

**当前接续已具体化：**owner已有末两帧／原几何证据交付齐，Sim2Real负责给保持35mm等原判据的一个最小控制修订／域限制说明；Reach绑定真实新语义delta，owner阶段授权下唯一新source回归。不重跑同Cartesian配置或换seed追成功，不继续以“等binding／净空报告未到”停留。该版负结果固定，0004与0005不同控制版本不拼成同版成功率。至此已消费phase5closed（2运行unknown＋3不同源原生PUSH失败），旧20／关联累计25保持，不作hardcap或H0/AB/模型收益结论。

以下旧“本候选物理结果unknown／尚待绑定”已被0005真实终态与本评价替代；旧源码接收／原失败记录不改成成功。


## WM-07初始Cartesian新原语领域增量接收（2026-10-17 21:17，无物理成绩）

**main21:05采用的初始Cartesian控制候选已完成本组精确领域增量（2026-10-17 21:17）：**[真实binding](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/wm07-cartesian-entry-control-binding-v1.json)／[WM-07签署](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-cartesian-entry-control-binding-20261017)，candidate`wm07-cartesian-retreat-entry-v001`、manifest`1fe52e70…84adb55`、parent`23a9f363…60d31d`；`final_acceptance=true`、`new_control_revision=true`、`logging_only=false`／`unchanged_control=false`。这是**新初始原语及其到位语义**接收，不搬r5日志签署、不称路径小修。owner21:12接收及producer原adoption已到，可按新控制gate直接登记新source／资源接收运行，不再等本组／main／producer重复批准；Reach没有代写实际运行或物理通过。

**4路径实际增量与字段：**初始joint waypoint不再覆盖原Cartesian IK，target仍箱局部`x=−(L/2+.06),y=0,z=0`，不是降低高度。原几何到位x<.05/y<.08/z<.045m且实际armdq<.25rad/s连续.10s锁存才完成新retreat；`safe_approach_index`由该锁存推进，不代表原2个关节waypoint真实到达。retreat≠face_ready≠腿释放，后续原face advance≤.03m/ .10m/s／height<.035／原实测face或合法接触.10s、motion_ready与legblend仍参与。新初始原语改变原pitch/rate/residual分支何时生效，不声称新旧参考逐tick相同或只改一个标量；只支持2点ordinary heightgate模式，混用拒绝。

**未变和评价边界：**原contact/安全/PUSH48s成功谓词、actor226→19／真实18历史、权重PD/IKgain/名义height、物性和后段CLIMB/NAV合同保持；核必要delta及原判据逐字一致，复用producer8CPU／真实零环境config及owner清单回执，不从头重跑旧测试／364远端清单。`push_approach_controller_cache`在正常及raw-only终态记录target/index/retreat/face/motion_ready/legblend，target是shield前参考；after-shieldarmreference还非含重力补偿／平滑的actualPD，真实目标用`actual_pd_target`，S0cache不当控制已执行。目标存在或retreat到位不等于PUSH/整链成功，原nativeflag和48s／后续原条件才定结局。

**物理结果仍null/invalid：**新Cartesian IK可能受盾／跟踪／时间约束失败或超时，不称接触已修好／鲁棒性／AB/H0或模型收益。source0004仅已曝开发参考，原0003机制缺失和0004两原失败分支保持；新初态／关键前缀测量支持才称匹配，不能同seed便叫严格对照。Reach0新物理／forward／拟合／阈值、无他组源码／账本修改。下一是owner按现有阶段授权真实新source后，直接评价actualtip/target/height/force/invalidflag、原PUSH完成与后段进入，不再欠领域binding。

下文旧“只可在高度／释放时机二选一”是main20:45当时假设，21:05已有源码／实测支持第三解释与具体新原语；旧0004失败和双分支不变。


## WM-07 source0004：原非法接触双分支核实（2026-10-17 20:56）

**source0004原生子谓词已独立消费（2026-10-17 20:56）：**r5缓存witness单次日志诊断已closed，不再欠owner原witness／实际tip时序。本组核原report/closure/receipt/原contact函数及末帧：step532、10.64s，只有原`invalid_hand_contact=true`，witness available／native一致；原8项contact检查中恰有**高度带与抵抗力占比两项失败**。[原源／子谓词／阶段评价](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/wm07-source0004-contact-branch-evaluation-v1.json)／[WM-07回复](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-wm07-source0004-contact-branches-20261017)。PUSH entered／false valid、整链false valid、CLIMB/NAV及准入未进入；不是初始化unknown，也不能据此说动态箱不可爬。

| 原子条件 | 实际witness与原门槛 | 本组独立核对 |
|---|---|---|
| 合法高度 | 箱局部接触z=0.10083999485m，原上界0.0901m | 超出10.739995mm，false |
| 抵抗前向力占比 | 抵抗力1.65230262N／合力3.27280140N=50.485881%，原要求>80% | false；抵抗力>1N本身true |
| finite／near-tip／front／lateral | tip距6.163984mm<70mm，前面x差0.64882mm<20mm，横向域及有限值均通过 | 其他6项true；原native激活force_norm>1N，不替换新触发阈值 |

**定位层级与缺失：**已确认两个**原判据失败分支**，不是唯一控制根因。接触world z约0.200841m、实际tip z约0.206172m与顶前缘／较强竖向力相符，但不能证明目标本身太高还是跟踪未完成即底盘前进。owner已交533点实际tip（t0＋532控制后，20ms），本组只核来源／SHA，不重复提取／FK／全轨迹审计。真实IK目标、waypoint index、底盘释放事件、5ms tip子步本来未记录，mask保持；不是还没找到／要求重发的文件，不把policy pose-request或事后理想轨迹冒充实际指令。t0仅初始tip，native buffer不当已求值判据。

**source与计账边界：**这两项witness结论仅对0004；0003原分支仍缺实测，不能回填。0003／0004为既有控制的日志开发重复，不当两个新独立组或完整私有队列匹配实验。当前已消费phase4closed＝2运行接线异常／动态unknown＋2已知PUSH物理失败，旧20保留、关联累计24；计数不构成阶段停止。原rawFALSE／flags／旧结果角色不改，本组0新物理／模型／阈值／重复测试。

**当前唯一控制接续已由main20:45明确：**Sim2Real用现有源码声明参考与实际tip时序先辨“目标高度”还是“前进释放时机”，选择其中一个最小控制修订；不同时改高度／速度／增益，不放宽原接触或安全门槛，不重采相同witness。owner只集成／唯一采集；Reach绑定实际源码delta及原失败／PUSH48s完成／后段进入评价。若既有数据确无法区分，生产者只列区分两机制的最小真实内部量，明确新日志假设，不要求完整重建旧日志。当前不再等待次数、owner重发原包或本组原flags评价。

下方0003“缺witness”仅指原0003，没有被0004新测量回填；0004的原分支／tip交付已完成，不重复采相同日志。


## WM-07首次实际PUSH：532步／10.64s原生非法手接触失败（2026-10-17 20:37）

**连续开发阶段3份closed源已独立评价（2026-10-17 20:37）：**已从构造错误推进到**真实PUSH原生物理失败**，不能沿前几例统一写初始化unknown。[三源身份／原终态／分段mask证据](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/wm07-phase-0001-0003-evaluation-v1.json)／[WM-07独立回复](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-wm07-phase-0001-0003-actual-outcomes-20261017)。只消费已closed0001／0002／0003，核phase实际登记与manifest/receipt/report；远端原report与closure哈希一致，首次/终态只解码2条control记录，不重复532帧历史审计或任何测试／物理。

| phase source／candidate | 本次真实进展与结局 | Reach评价 |
|---|---|---|
| 0001／r2 | ObservationManager因wrapper mandatory`kw`签名初始化拒绝 | 运行初始化错误；环境完整创建／物理步数unknown；5段未进入，整链动态unknown |
| 0002／r3 | 已创建1环境，真实policy210／box16／CLIMB304／NAV210；首PUSH226检查报错，loop steps0 | **环境创建已知true**，不再maskunknown；未证actor forward/命令下发，5段未进入，整链动态unknown；steps0不等于初始化绝对0物理 |
| 0003／r4 | 真正PUSH226→19→实际PD18，532控制区间，10.64s原flag仅`invalid_hand_contact=true`，error=null | **PUSH entered／completion=false valid、整链false valid、已知原生物理失败**；CLIMB/NAV及准入未进入，不归因其动态箱承重失败 |

**完整分母：**这3次实际启动＝2运行前技能异常＋1已证原生PUSH失败，0已证任务成功／2未知动态结果；只有1/3原生任务结局可见，不包装为3次物理失败或无说明的0%成功。0003report0中途reset、初态／首步／终态同箱、首实际actor与18轴维数已核，但不伪称全532行队列／子步独立审计。原phase至本三例closure为3收费closed，关联旧20累计23；旧ledger不改，阶段无旧36硬停止，后续已登记运行状态由owner实时记录。

**具体机制仍缺witness，不猜阈值：**0003最后原flags能确认非法手接触，但现有terminal/control缺hand force、contact_pos、tip及local/finite子谓词，不能由root/箱位姿唯一断定哪项失效。world-model owner已负责仅补缓存传感器witness的针对性日志／诊断，Reach不重复派发或造第二诊断。需给同一step／原flag／原缓存值与各子谓词不可变引用；不新增观测compute或改历史／阈值／权重，不从已知失败调阈值。若后续控制变化，明确parent/diff/newsource与Sim2Real领域核验；当前先取得实际分支，不能盲重同配置或换seed追成功。

**阶段授权与范围保持：**本组0新物理／模型forward／拟合／阈值／旧测试重跑，旧角色／失败／20累计不重写。owner按现有阶段authority单GPU单env同链1作业继续已具体诊断，单次468sim/2400wall及原安全／完成条件保持；本次不要求main逐次给次数，也不重开旧PUSH／GRU／AB正式试验。

以下旧“所有同箱尝试都是初始化unknown”不覆盖本phase0003；旧source仍保留当时unknown，不由新物理失败回填。


## WM-07原修复批两初始化异常已独立评价；开发转阶段授权（2026-10-17 20:16）

**main20:04交办的v2/v3已有两案已独立消费闭合（2026-10-17 20:16）：**source`wm07-same-box-3701-env0-v2`／candidate`wm07-same-box-composite-v003`在scene membership把整数0当实体key时KeyError；source`…-v3`／candidate`wm07-same-box-composite-v003-owner-r1`在观测config deepcopy沿bound callback进入live USD Stage时RuntimeError。两案均在策略循环前初始化失败，原rawFALSE与外部return0分存；每案5段not_entered，动态整链／原生物理失败／环境完整创建／真实physicssteps／simduration均null、valid=false，不填0或物理失败。[原report/closure/identity与10段mask独立评价](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/wm07-repair-v2-v3-initialization-evaluation-v1.json)／[WM-07回复](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-wm07-repair-v2-v3-consumed-20261017)。

**完整分母与历史保持：**本修复批2收费尝试、2运行初始化异常、0已证native成功／0已证native物理失败、2动态unknown；与已评价旧v1合计本问题3初始化异常／3未知动态，不当原生0%成功。已核两案start／close及唯一source/manifest，实际closure历史累计19→20、0预留；v3非物理原plan路径preflight拒绝和释放／重新预留保留，收费0，随后实际v3只计1次，不重复计作第三案。约30.099453／30.847807s为各report初始化至报错wall，不作成功耗时；原失败／claim／owner修复回执／旧标签角色不改。本组无新采集／forward／拟合／原轨迹读取／旧测试重跑。

**用户19:58阶段授权已实际采用到本组计划／评价边界：**旧“两次用完／36封顶／等main新给1次”仅历史约束，不是未来开发依赖。world-model仍唯一集成／采集owner，按[阶段authority](/home/yuanyue/main/work/wm07_development_phase_20261017/authority.json)可把已核r2接入隔离launcher／receipt，建立关联旧20账本的新阶段记账并用新source继续具体修复／构造验证，不用等待本组旧两案归档或作者逐次回签；每次真实尝试／失败与用量照记，禁止无新诊断盲目重复。同链最多1物理作业、单GPU／单env、每次468sim／2400wall及48/420/120原任务／安全约束仍保持，不扩硬件或把调试当独立验证；不重开已关闭正式PUSH先导。

**下一具体动作不再是额度提案：**owner已完成scene lookup和r2 callback-copy定向修复，本组不造第二修订或重做6项／真实IsaacUSD零环境copy。原r2支持的延迟构造路径仍需实际新source推进；纯路径／callback句柄／调度权限接线由集成负责人本人署名增量即可，不能把旧Reach签署搬给新SHA；真正影响评价／控制／单位／几何才核精确领域差异。Reach本轮已有结果评价已结束，与owner新阶段接收／执行并行，不构成其下一启动审批点；实际新closed source到达后沿现成语义继续消费。

以下19:12“须main新给1次／旧1或2次／36上限”的内容仅当时历史，未来开发已由用户19:58阶段授权覆盖；原失败／计数／正式实验身份不改。


## WM-07 v002实际一次尝试：初始化错误，动态结局unknown（2026-10-17 19:12）

**v002唯一实际尝试已闭合，本组已独立消费初始化异常（2026-10-17 19:12）：**source`wm07-same-box-3701-env0-v1`／candidate`wm07-same-box-composite-v002`的真实report为`runtime_initialization_error`，原raw`full_task_success=false`保留；堆栈为action-manager构造原PUSH几何shield时缺`reconfigurable_navigation.piper_robot_profile`。没有owner技能策略循环／初始状态／control轨迹，**PUSH、CLIMB准入、CLIMB、NAV准入、NAV五段均not_entered，动态整链结局null／invalid，不能填成物理失败或成功**。环境是否部分创建、真实物理步数／仿真时长无支持，均保持unknown，不虚报0；外部退出码0不改变初始化错误。[独立源／阶段／mask评价](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/wm07-v002-initialization-error-evaluation-v1.json)／[WM-07结果回复](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-wm07-v002-initialization-result-20261017)。

**账本与结论：**已核真实start／closure／owner receipt与先前final binding／manifest同源，该次1实际登记启动已经收费；共享**18/36、0预留，18未分配**，本slot closed。失败不是免费接收探针，不能删除claim／补跑／用旧receipt重启。本次只是**运行依赖闭合失败**，不提供箱滑移、承重、平面域拒绝、碰撞／力矩或世界模型结论；原生0已证成功／0已证物理失败／1未知动态结局，另报1/1运行初始化异常，不混成“原生0%成功”。本组未写账本／其他组用途、没有物理／forward／拟合或重复43测试。

**对前次绑定的限定披露：**18:58 final_acceptance是精确v002源／评价语义接线接受，不是完整延迟构造依赖／物理通过。本次在此前未实例化的`PiperBaseArmGeometryShield`构造路径暴露缺包；43CPU和0环境配置导入的通过保留，但不足以证明此延迟依赖完整。旧包／原异常／原绑定不改写为已修复或成功。

**无需串行等作者的小修接续与唯一预算问题：**按main19:08新规则，world-model owner为集成负责人，可在隔离child修订绑定原几何profile模块／资产／路径，保留parent＋diff＋newSHA，做0环境／0actor／0物理的延迟构造依赖核验并由本人真实签署路径小修增量；不得把旧Reach签名复制到新manifest。若实际几何／坐标／判据变动，才需要对应领域增量核验。本组支持owner已有同一建议：依赖修补通过后由main明确是否分配**最多1个新的实际启动、0重试／替补**，原1次已用；小修权限不补充额度，不自动执行。没有新增用户方向确认或另起竞争实验。

以下18:58最终源码binding不是环境构造／物理验收；本次真实结果和原异常保留，不用后续修复覆盖或包装成成功。


## WM-07冻结v002最终源码／评价接收（2026-10-17 18:58，未宣称物理通过）

**冻结v002最终源／评价接线已完成（2026-10-17 18:58）：**按main18:52唯一接收对象完成旧partial后的增量核查，实际`same_box_followup.py`、原PUSH事件／phase safety／合法退出、CLIMB304及真实18历史、同箱math-frame／实际组合mdp、首READY世界冻结目标、v005保护NAV／11门禁连续1s、source身份／失败阶段／初始化及预算输出均已绑定既有定义。[最终绑定](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/wm07-same-box-v002-final-binding-v1.json)／[WM-07真实回执](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-wm07-v002-final-binding-20261017)，`final_acceptance=true`、`not_valid_for_owner_launch_receipt=false`；仅针对`wm07-same-box-composite-v002` manifest`55fea1b8…64259b1`及producer`d7130eca…68a40c7`，source_id另为`wm07-same-box-3701-env0-v1`。旧v001撤回且0物理，其18:09 partial完整保留但不签新包。

**已解除的依赖：**完整followup／入口代码已交付，本组最终binding已交付，不再等重复发包、评价公式或方向批准。owner可直接使用本真实路径／SHA做自身实际部署／依赖／资源／角色接收，唯一live账本登记和receipt后执行已授权1次；Reach未代写owner已接受／登记／执行，未派发／收费。生产者43CPU、0环境配置导入是原回执消费，本组不重复测试或完整296远端清单。接线和静态源接受**不代表动态箱承重／整链物理通过**。

**实际结果分类已绑定：**原flag与safety失败保留为已知物理失败；原timeout、平面／足域等`unsupported_domain`能力拒绝、运行异常／初始化创建未知、连续性破坏分别记账，后段未进入为null。1e-6平面条件是算法支持域不是校准安全界，越域不得旋平／锁箱／加容差或重试。新NAV用真正firstREADY+.30m固定世界目标及35mm／11门禁持续1s，原caller缓存`platform_details.complete`含native80旧谓词，不作新复合整链完成。原生／保护后／总运动据实际world/issued-mode分别记，箱数学坐标legacy progress不冒充world量，终态区间submode若无支持则贡献mask但不抹已知失败。

**保留预算／身份：**main已定1次／0重试／替补／探针，seed3701单环境沿原reset规则、不承诺旧8env0数值重放；原已曝光角色`wm07_same_box_capability_dev`不进训练／独立验证／校准。PUSH48／后续420／总468／CLIMB完成起出口120／wall含初始化2400s／单GPU单环境保持。当前物理结果未由Reach读取或宣称，本组0物理／forward／拟合／阈值／账本或用途写入；旧WM-04和原失败／冻结分数不动。

下文旧v001的launch_ready=false／followup缺件仅当时快照；v001在0物理撤回，v002已完整交付与本组最终绑定，不把旧partial SHA当新回执。


## WM-07同箱合同的实际源码部分绑定（2026-10-17 18:15，无物理结果）

**已执行main17:40并行接线任务：本组现有评价定义完成实际源码的部分绑定（2026-10-17 18:15，非最终接收）：**按生产者`wm07-same-box-composite-v001` **18:09:19源码回执快照**，把`LiveClimbCompletion`、`actual_platform_domain`、`FirstReadyGoalLatch`、`composite_nav_gates`、`remaining_budget`映射到既有阶段／整链字段；额外绑定18:08新写的`ContinuousGoalHold`及实际loop／stage事件、同箱身份与边界记录。共8类原字段接线，[不可变源码快照／字段映射／待绑定清单](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/wm07-same-box-evaluation-binding-v1.json)／[WM-07原回复](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-wm07-actual-hooks-partial-binding-20261017)。没有重写标签体系或轨迹审计器，没有改生产者控制／候选表／账本，没有重复33项CPU回执或原14项测试。

**不能沿旧17:40摘要继续称“1s计时尚未实现”：**已核`continuous_runtime.ContinuousGoalHold.update`及coordinator调用点：11项实际必需门禁共同为真且真实连续1s，缺帧／缺字段／false打断，安全失败锁存，20ms下51状态才跨度1s；不靠HOLD命令、单帧all(gates)或拼两段半秒。**但计时实现≠实际caller已接好**，所核生产者仍`launch_ready=false`／无本筛查物理结果。`same_box_followup.py`及源原PUSH成功／phase safety、实际合法退出→CLIMB入口、全规划碰撞／地面高度调用、实际v005保护NAV caller与输出贡献日志均未在该回执完成。部分绑定`final_acceptance=false`、`dispatch_permission=false`，**不得拿本证据SHA当最终launch-approved Reach receipt**。

**已落实的新合同语义：**main17:19已采用这1次能力筛查，不再等是否采用。真实首READY位置沿当时箱局部前向+.30m，世界位置／朝向一次冻结；越实际足域拒绝，不缩短或保护后重定目标；35mm／1s实际到点停稳及原安全不降。raw-native80mm在本新复合合同仅诊断，原生／保护后／总运动分记，绝不倒改旧v005／v006／三源失败。总468s、PUSH48s、PUSH后420s、CLIMB完成起出口120s、wall2400s／单GPU单环境／seed3701-env0原初始化规则／1次0重试；不是旧8env抽样初态逐字相同承诺。原段更短限制仍需followup绑源，时钟不在READY重置。

**当前唯一具体交付依赖：**Sim2Real提供能逐项连接上述实际测量／事件／持续计时／贡献字段的`same_box_followup.py`及完整组合不可变source/call-site覆盖回执；world-model owner最后接收／唯一登记执行。现有调度loop已写但依赖该followup，不再笼统说整个入口代码不存在，也不对半成品签通过。初始化／队列／观测历史连续性与真实物理能力仍待完整合同和唯一实际结果支持；本轮0物理／forward／拟合／阈值，预算未由Reach登记或消费。

以下17:15关于“待main决定采用1次”的旧快照已被17:19采用与17:40接线安排替代；当前唯一关键路径是完整followup／caller，不是方向批准或Reach评价公式未交。


## WM-04三点消费收尾／WM-07评价定义（2026-10-17 17:15）

**旧WM-04三点实际已消费闭合（2026-10-17 17:15）：**按`4a5e824`固定协议核owner已交labels／共同v3完整source、report、READY step/time与S+50，未重抽control／重跑原测试。3/3实点可用：v001/3703为0.122929148m/s，v002/3701为0.137829363m/s，v002/3702为0.112030722m/s；保持当前值的绝对误差0.122306428／0.137280897／0.111392110m/s，均值**0.123659812m/s**。原输入／v2／原成功-失败-成功与所有mask保持。[独立消费证据](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/platform-bridge-velocity-consumption-v1.json)／[WM-04收尾](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-bridge-target-consumed-20261017)。这只是固定调用主动加速的描述和目标可读性，不证明模型需求、失败因果或选择收益，不能据最大失败点选阈值。按main16:16／16:19关闭原三点路径，不再提取字段／新增caller参考或拟合；此前“待路径”依赖解除。

**WM-07评价定义已按main16:16新任务交付（2026-10-17 17:15，无新物理）：**已在候选未齐备、未看任何新先导结果前，给出整链／分段原生完成、物理失败、异常、缺失、删失、未进入语义，以及匹配对上的始终A／B／事后上界和共同成功耗时公式。[结构化定义](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/wm07-evaluation-definition-v1.json)／[WM-07原主记录答复](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-wm07-evaluation-definition-20261017)。没有新建轨迹审计器或第二候选表，没有训练／校准／阈值选择；候选A／B、三个距离值、整链新成本均未填，不把+.60m同指令散布或v005／v006版本号当两个动作。

**当前真实能力依赖而非等待参数事实：**已消费生产者16:26／16:28答复和owner16:32同表整合：只有一个已验证+.60m目标；旧CLIMB静态箱并非PUSH动态箱；同事件双过渡也未交付。14项几何工具测试不等于全CLIMB碰撞／完成／出口或动态箱承重通过。Sim2Real负责完成同一实际移动箱的自然PUSH→CLIMB连续入口及支持域／成本合同；main按既定节点决定是否先采用owner／生产者已有的**固定+.60m同箱完整入口筛查、最多1启动、0重试／替补**。本组支持同一建议而不另开竞争试验；它是H0前置能力检查，不是双臂选择或H0通过。方向已批准，不要求用户重复确认；1次或6次都未因此自动授权／预留。

**评价关键边界：**某段已知原生失败→整链false／valid，后续未进入段为null／invalid，不能把失败洗成unknown；仅因日志／未来支持缺失才mask相应未知量。异常与物理结局分存，不以程序码覆盖已知结局；单段成功／READY不等于整链成功。保护／复合控制只在新明确版本合同下评价，原生／保护后／总运动分开，不追溯改旧失败。几何／环境运动、本体与已完成历史分命名空间，未来终态／READY／峰值不得回填输入。真实初态／asset／队列前缀不齐就不称配对，相同seed不证明匹配；所有实际尝试／失败／unknown／未运行仍留总分母。

以下“待S+50路径／尚无误差”等是旧快照，本次已消费闭合；新WM-07只有评价定义，没有新的候选／物理结果。


## 固定桥接末速度评价准备（2026-10-17 16:09，尚无后果误差成绩）

**main16:04已采用桥接末端速度核对，本组固定评价参照与精确时钟（2026-10-17 16:09，尚无后果数值评分）：**owner16:05已登记同三源S+50提取，本组不重复启动／编写第二套原轨迹提取；负责消费同一批源绑定后果点并核标签／mask／常量参考。已从共同输入v1的READY当前帧固定三个保持值与目标step/time，[评价协议](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/platform-bridge-velocity-evaluation-protocol-v1.json)绑定原input／共同v2、控制source SHA、单位／坐标／缺失和误差公式。[原WM-04接线](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-platform-bridge-velocity-reference-fixed-20261017)。

| 原来源 | 冻结READY world-v_x参考（m/s） | 唯一目标S+50／总时刻 | 实际后果／误差 |
|---|---:|---|---|
| v001/3703 | 0.0006227202247828245 | 14908／298.16s | 尚未由Reach消费，不填0 |
| v002/3701 | 0.0005484663415700197 | 15266／305.32s | 同上，原已知终态失败仍保留 |
| v002/3702 | 0.0006386118475347757 | 16808／336.16s | 尚未由Reach消费，不填0 |

协议按原20ms轴精确S+50，禁止S+51／插值／近邻／其他case或终态回填。记录`e=保持值−实际值`、`|e|`及真实变化，始终保留3行全分母；缺点／提前终止则mask，无有效点均值NA。只是免拟合描述性参考，**不宣称最强信息匹配参考、需要GRU或替代动作收益**；三源已曝光、原终态早已知，不伪称新独立冻结测试。三条原输入／共同表不改，本组0额外控制流读取、0物理／forward／拟合／角色或索引写入，17/36、0预留保持。

**当前唯一交付依赖：**world-model owner已登记的至多3个S+50原source点／缺失回执；只需其不可变输出路径／SHA，不缺物理、方向采用或重新发包。数据未到不计算误差、不另提取同一source；若原件确无该点，沿既定mask停止、不补采。前一三源事件接口已由owner16:05消费闭合，不再保留“等事件回执”作为当前待办。

以下三源接口及旧结果保持；前文历史“最强免拟合参考”应按本协议理解为当前值保持的描述参照，未证明其为最强信息匹配预测器。


## 已采用三源READY接口实际接合（2026-10-17 15:17，非新物理结果）

**main14:18已采用的三源READY接口已实际形成（2026-10-17 15:17）：**不是待方向批准。本组将v001/3703、v002/3701／3702的原报告／实际READY／边界事件／既有终态审计，按完整version＋report SHA＋READY step/time＋pre-admission phase接到owner唯一三行表，产出[共享接口v2](/home/yuanyue/re-nav/artifacts/go2-piper-world-model/platform-ready-interface-20261017-v1/three-source-interface-v2.json)与[Reach事件／原生结局回执](/home/yuanyue/re-nav -piper-manipulation-reachability/artifacts/go2-piper/2026-10-17/platform-ready-interface-v1/reach-event-labels-v1.json)。原输入v1／接口v1完整保留，没有另抽一套窗口、改模型输入或另建相互竞争的数据表。[交付证据](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/platform-ready-interface-delivery-v1.json)／[WM-04原主记录](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-platform-ready-native-receipt-delivery-20261017)。

| 原完整来源 | READY时刻／step | 原生终态 | 接合与删失 |
|---|---|---|---|
| v001/3703 | 297.16s／14858 | 原成功303.22s | READY／源／相位接合有效；终态已知、不删失 |
| v002/3701 | 304.32s／15216 | 原transition_effort失败306.16s | 已知物理失败不是删失；cached no_failure=true不覆盖终止；沿用原42已下发计数，保留details41及记账适配 |
| v002/3702 | 335.16s／16758 | 原成功341.12s | READY／源／相位接合有效；终态已知、不删失 |

**范围与缺失：**接口可接合不等于状态完整／风险头或模型收益。owner已有21状态／20已完成命令、最多.4s因果窗口不重抽；实际关节力矩、数值delay／观测buffer、5ms子步目标历史仍缺，原mask原样保留；210维嵌套NAV输入及当前未完成action明确排除。READY相位在私有reference已计算之后、当前asset PD下发／物理推进之前，不拿READY+.02s补当前。精确首个raw-native动作时刻本组未提取，保持时间mask，不能等同READY；已进入与最终结局另有原计数／终态支持。

**原任务语义更正／保持：**.30m reference前向目标、至少80mm实际raw-native进展、到点／真实停稳1s、原子步安全及总420s／CLIMB后平台120s均保留；80mm是进展下限，不是替换原任务目标。2成功／1失败只是Sim2Real既有事实，不包装成本组新物理结果或“READY已能分类”；每状态只有固定续行动作，无第二已验证候选，不算排序／oracle／停止收益。新增reader与12项合成守卫通过；本组新物理／forward／拟合／几何重算／全轨迹重放均0，原PUSH标签／角色／共享账本和索引不改，17/36、0预留，19余额不自动开放。

**下一最小量建议（沿用owner同一建议，尚未执行）：**原1s权限桥接末端`v_x(READY+1.00s)`，时域来自原桥接而非已知失败挑选；最强免拟合对照为保持当前实测v_x。若采用，最小预算新物理／模型forward／拟合0，只取既有三源各S+50一个后果点（不误用S+51／+1.02s），交付至多3行源绑定值／缺失及描述性常量误差；缺帧mask即止，不训练／校准／选阈值。潜在用途是为将来明确验证的桥接释放时序／准备选择提供状态响应证据；目前没有已验证替代动作，不声称已经能优化或提升任务回报。

以下13:48的“接管建议尚未采用”属于当时快照，main14:18已采用且上述接口现已完成。


## 历史2701原生结局核实但真实救回不可证（2026-10-17 13:48）

**历史2701限定核查已完成（2026-10-17 13:48，非待批准）：**已执行[main13:18决定](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#main-choice-pilot-close-and-historical-check-20261017)和owner既有指针，只核两个原批报告的env9／26共4个证据单元。env9快调用14.07999992s、env26快调用10.59999943s均为原生`invalid_hand_contact`失败；同env慢调用39.47999954／40.81999969s均原生`box_settled`成功，显式flag names、原per-env计数与来源SHA核一致。**原生结局反差已核实，但同reset救回和reset时可见偏好仍无法核实**：两臂均缺目标env的第一动作前实测状态／PD目标／已下发历史；fast仅有11.52–14.06s／8.04–10.58s失败前缀，slow无这两个env的逐步历史。`trace_env0`不代替env9／26，startup-physics相同静态物理参数不代替实测初态。按既定停止条件以缺失矩阵结束，不要求补日志／重跑。[最多两行完整证据](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/historical-2701-rescue-audit-v1.json)／[WM-04回复](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-historical-2701-rescue-audit-20261017)。

**证据与范围：**原32例分母仍为slow32成功／32完成、fast30成功／32完成（2非法手接触失败）；此次只解码4个原env，不当4个新组或完整32例重新评分。env26在接近路径尚未完成时失败（index1），env9在已完成接近时失败（index2），均为事后解释，不回填到reset输入、不从两已知失败选特征／阈值。新有限reader及8项合成守卫通过；原始报告只读从go2-root-yuanyue复制、哈希与owner原登记一致。本组本轮物理／forward／拟合／模型重评分／角色修改均0，共享17/36、0预留不变，唯一数据索引本轮未改。此证据路径关闭，不能据此训练选择器。

**下一项具体建议（尚未采用／执行）：**转向已发生的自然CLIMB→台上原生NAV接管，最多使用Sim2Real原同物理版本的3701／3702／3703三条已曝光开发记录，做`transition_ready → next_skill_complete`的全分母事件／结局接口试验。只绑定owner已有同版group-v2／终态适配，不重复几何残差或整轨迹源码审计。固定原80mm目标、停稳和原子步肩部力矩门禁；对照为原READY规则／总是按既定桥接释放，不引入新动作或阈值。最小预算新增物理0、forward0、拟合0、读取最多3旧episode；交付3行READY时刻／总时钟／可见字段mask／原生接管成功或失败／unknown表，区分“READY后失败”与未观测替代动作后果，缺字段就mask并停止、不补采。由Reach维护标签／事件、Sim2Real只提供现有group／source指针；这是新目标的接口诊断，不混入旧PUSH训练或独立测试。main需决定是否采用该有界试验，不自动动用19次余额。


## 已采用完整调用先导最终评价（2026-10-17 13:13，两实测开发组）

**快慢完整调用先导的Reach实际评价已完成（2026-10-17 13:13）：**owner已将最后slow5402正式登记closed；本组仅针对新增closed源生成`live-evaluation-v4.json`，原生成功39.59999847s，startup／source SHA及第二组首动作前typed状态可比性通过。全4槽／4启动／4closed：两臂各2成功、0原生失败、0unknown、0程序／记录异常。5401慢40.0000／快15.93999958s，快少24.06000042s；5402慢39.59999847／快16.15999985s，快少23.43999863s；**共同成功配对少用时间中位23.74999952s**。固定慢／快均2/2完成，平均39.79999924／16.04999971s；事后oracle等于固定快，额外完成0、相对固定快提速0。[完整来源／分母／阶段与物理诊断证据](/home/yuanyue/re-nav -piper-manipulation-reachability/GO2-PIPER-SIM2REAL/evidence/2026-10-17/existing-push-choice-final-evaluation-v1.json)；[WM-04原主记录](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md#reach-existing-choice-final-evaluation-20261017)。

**范围与停止：**两实测组是已曝光开发先导，不证明非劣／安全／稳定偏好或学习式选择收益；全部4份原20ms报告均有非零腾空／少于三足支撑采样，完整保留，不用原生终态成功抵消过程风险。共享17/36已收费、0预留，本组新增物理／模型forward／拟合均0；原13记录、train／dev／diagnostic角色及精确用途不变。无需等待最后一案、重派接续或增加同类测试／样本；已仅更新唯一索引本study的评价指针和历史，未改owner账本／split／manifest。

**下一阶段建议（不是已采用计划）：**已在原WM-04提交0新增物理／0拟合／0forward的旧2701批次“两条快臂失败及各自慢臂对应报告”来源／可比性审计，最多4份closed原记录；保留旧开发身份，只核原生失败、实际t0证据及决策时字段可见性，不选特征／阈值、不训练或重评模型。缺件就报具体缺项并停止，不重跑。main只需决定是否采用这一限定的历史救回案例核查；不自动花剩余19次预算。

以下逐次局部结果保留当时状态；关于本pilot的“最后running／仅一配对／尚无实源”等均已被上方最终评价替代，不是下一待办。

**新先导第三份native源已核、末案仍进行中（2026-10-17）**：fast5402原生成功16.15999985s，源码／报告／native flags／实测group核通过；评价快照17/36已收费、0预留，4真实启动、3closed原生成功，slow5402running为unknown。仅5401有同组双成功、配对快24.06000042s，5402不能在慢臂终态前算提速或宣称整批完成。新研究4次收费事件ID唯一，旧13canonical记录、原group和旧ledger原始字节前缀保持；不重复派发／重试，不调参或新模型forward。证据`evidence/2026-10-17/existing-push-choice-progress-evaluation-v2.json`。

**新先导首组实际可比双成功及条件效率（2026-10-17，先导尚未完成）**：5401的v209/model255慢调用40.0000s与v212/model255快调用15.93999958s均原生box_settled且无其他终态native失败，Reach已核两原source／evaluator／actor、startup实测group及第一动作前物理状态／PD目标／力矩／joint名一致；仅此共同成功组快调用少24.06000042s。未要求不同完整调用首动作后轨迹相同；原20ms物理风险诊断保留，不以“native成功”证明全程安全。该版全4槽、实际启动3、closed成功2，fast5402running为unknown、slow5402未运行，16/36已用、1预留；尚非两组完整先导，不证明非劣／稳定选择／模型增益。只在新closed源后更新，Reach0物理／forward／拟合。证据`evidence/2026-10-17/existing-push-choice-first-pair-evaluation-v1.json`。

**已采用新先导首个实际native标签核验（2026-10-17，仍为部分结果）**：owner新slow5401已closed，Reach用26测试通过的arm-scoped reader核原report／显式native flag names、model255／evaluator来源、1kg/.15/48s、startup实测group及第一动作前状态：原生box_settled40.0s且无其他终态native失败，物理标签与owner注册结局一致；首次观察approach34.42s、legal38.0s及2000连续20ms区间仅为阶段事实、不代表全程安全。评价快照全4槽／已启动2／已结束1；fast5401running为unknown，另2未运行，配对共同成功0、效率NA。不将单臂成功当整个先导结果，不重派／重试任何案。预算快照15/36、2预留，Reach0物理／forward／拟合，旧角色／标签／分数不变。证据`evidence/2026-10-17/existing-push-choice-first-native-evaluation-v1.json`。

**已采用快慢完整调用先导：原生事件／条件效率适配已实现（2026-10-17，尚无新native成绩）**：main12:29已采用v209/model255 21点与v212/model255 2点原reset前完整调用选择，原恢复B提案0物理关闭。Reach交付`native-arm-endpoints-v1r1`和26项合成守卫，直接绑定owner当前协议v2、`skill_choice_development`与共同canonical source，按原evaluator显式native flag names解码；48s、失败优先且time_out＋goal沿源码，物理结局与程序／后处理错误分存。可选阶段坏流仅mask阶段，有startup／native报告仍可做初态可比及任务终态；首动作后允许不同，不套旧二元反向偏好要求，共同成功耗时与全分母风险分开。当前仅metadata接线／合成测试，首案由owner在远端GPU1唯一执行，14/36已收费、3预留，尚不报告新成功／失败／效率。额外2接收已豁免、只预留4；本组0物理／forward／拟合，旧角色／标签不改。证据`evidence/2026-10-17/existing-push-choice-evaluator-preparation-v2.json`。

**新零预算选择价值实验：现有返程程序对无观测选择收益（2026-10-17）**：依main11:44从预测分数转到真实选择的要求，比较已实际执行的v317/v319全部4个共同开发起点（8历史回合）；核相同原目标及10,156个已记录状态／实际命令／历史前缀，query行55字段typed相同。原任务完成优先、双方完成才比耗时：固定v317=4/4，固定v319=3/4，事后oracle=4/4；三个v319成功分别慢3.72/3.84/3.58s，3703原生力矩失败不当提速。相对最佳固定程序的额外完成／当前观测提速均0，建议不为该程序对新增训练／物理。20项合成守卫通过；0新增物理／模型forward／拟合，原共享账本／角色／标签不变。已知粗结局后的开发筛查，不是新独立验证；只在原终点成功／耗时目标下成立，不等于否定原生18轴SDK目标或认证隐藏状态／动态晚切API。证据`evidence/2026-10-17/return-mode-choice-screen-v2.json`，具体下一试验建议`next-choice-experiment-recommendation-v1.json`；原reserved诊断保持闭合。

**两原保留案完整诊断链闭合（2026-10-17）**：采集、观察审计、严格receipt身份适配、两份独立全记录consumer、逐文件仅诊断发布及原冻结主／辅助评分均已完成。Reach独立typed核原／新主分数、本体分数、全部固定预测／原资格与时钟20,641个数值字段差0；只接入真实已发布辅助标签，不回填旧实验或改预测。5311为原生接触失败，主／辅助资格0／NA；5312成功且主10个重叠查询／1组，主覆盖1/2尝试。原固定GRU主1s14.3553mm弱于预声明匹配线性9.8856mm；净空0.4s3.6284 vs2.9361mm（16查询）、1s4.2350 vs1.9297mm（10查询），1s最大乐观误差11.6049 vs5.1792mm仅样本描述。全部固定成员／参考保留，候选未显示强参考外独立增益，但单组不能证明广泛劣势或安全／规划收益。两份标签合计300查询／572完整／28删失，所有非诊断用途禁止；13/36、0预留，两原案不再派发，不调参／拟合／校准／扩批。证据`evidence/2026-10-17/v212-diagnostic-complete-evaluation-audit-v1.json`；下文pending／旧分数为当时快照。

**5312真实全记录核对与精确仅诊断发布（2026-10-17）**：为解除“标签已到但旧快照仍缺”的等待，由Reach触发go2-root-yuanyue上原owner独立consumer＋身份adapter v3，从真实原流重新计算后全记录匹配，辅助值最大差0m；独立性来自owner独立数字实现，触发方明确为Reach，未将expectation充当alignment或伪称owner人工确认。第一次回执路径为服务器引用，保留v1、canonical路径另出v2，alignment字节相同；无源码／指标／模型／物理更改。5312精确release已登记，194查询／374完整／14删失，仅诊断可用；两份reserved总300查询／572完整／28删失，拟合／dev／校准／选择／阈值权限false。原5311和train/dev保持。当前剩原冻结辅助评分及主预测不变核验，不提前宣称完整辅助链闭合。证据`evidence/2026-10-17/v212-diagnostic-5312-release-verification-v1.json`。

**原5312闭合源与辅助标签导出（2026-10-17，待独立消费／发布）**：同冻结协议和身份附录下，真实19.34s／967个20ms区间、原生box_settled成功，独立PUSH并非NAV接管。实际194查询、374完整／14删失（0.4s190/4，1s184/10），原合法接触／历史／完整窗口资格0.4s16、1s10。owner原主位移score仅有5312的10查询／1实测组，5311为0／NA；即1/2尝试可评价，不作两有效组均值。固定GRU14.3553mm弱于预声明匹配线性9.8856mm，但单组不足以称广泛劣势；未改主比较或选seed。该旧score无未来辅助标签，不作净空结论。本组新标签全权限false，待独立consumer和精确release后才补原辅助评价，未拟合／重采。证据`evidence/2026-10-17/v212-diagnostic-5312-label-coverage-v1.json`。

**5311发布后冻结评分消费核验（2026-10-17）**：Reach只读核owner远端评分回执，确认原锁／协议、确切标签与release SHA一致。14个预登记固定主predictor均0合法接触后查询／MAE=null；同mask下净空26项、本体48项也均0／NA。96个完整1s实际辅助真值窗口中，4个无原0.4s历史，次级all-complete窗口因此为92；全部接触前，不能改作主指标或解释为模型风险识别。未重跑模型／拟合／改mask，5311源→标签→独立对齐→仅诊断发布→冻结消费链已闭合。共同账本新快照13/36、5312 started/group=null；其原始源／标签／评分仍未读取或放行。证据`evidence/2026-10-17/v212-diagnostic-5311-frozen-consumption-audit-v1.json`。

**2026-10-17原5311身份修复、真实标签与仅诊断发布**：按main 00:47决定另建identity-only适配，仅接受原5301非录制receipt的固定同组／report SHA关联，其他跨role仍拒绝。旧6源码／锁／模型／指标／标签数字核未改；补丁在已知5311物理后果后发生并附录披露。118项软件回归通过。原5311 closed流10.56s／528区间，原生invalid_hand_contact、成功false；实际导出106查询，0.4s完整102／删失4、1s完整96／删失10，共198有效／14删失。合法接触后主查询0，主MAE=NA；不表示模型预测失败，不按结果改主指标。owner远端独立consumer全记录通过、有效辅助值最大差0m，本组核绑定执行回执后完成精确文件仅诊断发布，拟合／dev／校准／选择／阈值权限仍false；5312无许可。Reach新增物理／训练／模型评分0，未读5312原始后果。实现证据`evidence/2026-10-17/v212-diagnostic-identity-repair-v1.json`，最终发布核验`evidence/2026-10-17/v212-diagnostic-5311-release-verification-v1.json`。

**owner保留接口冻结接入核验（2026-10-17，非保留评价）**：世界模型确认接入后，Reach用原协议函数验证最终用途协议，核对32个owner模块、6个配置及原Reach冻结代码SHA；未改变协议／实现，也未读取模型或保留后果。owner报告46项合成链和80项旧dev回归通过，Reach仅核回执，未重跑模型。共同账本核验快照12/36、5311 started/group=null、5312未启动；旧22:41资源阻塞预飞仅历史快照，不据此推断当前GPU。实际标签／发布仍空，待owner闭合源和实测group／source SHA／观测审计，不能在started阶段转换。证据`evidence/2026-10-17/v212-owner-diagnostic-integration-verification-v1.json`。

**diagnostic_reserved仅评价接口准备（非保留结果）**：新增独立版本转换器／协议守卫／发布器，原train/dev转换和标签字节不变。最终owner冻结协议及观测审计绑定显式ID、角色、实测group和源SHA；独立消费对齐后才允许精确文件的`allowed_for_diagnostic_evaluation`，拟合、development、校准和seed／候选／阈值选择权限始终false。异常前完整窗口可评价，未知后果null；缺日志／无查询保留分母，终态after不补未来、不跨reset，各预测头独立mask。36项新合成测试＋53项原v212检查＋10项窗口检查共99项通过；共享索引仅登记准备接口。未读取5311/5312后果、未造group或标签、未采物理／训练／模型补评；owner实际接入、闭合新源及真实独立对齐仍待完成。合同与哈希见`evidence/2026-10-16/v212-diagnostic-interface-preparation-v1.json`。

**2026-10-16标签语义落地（非新物理结果）**：main确定双口径异常标签与0.4/1s实际净空余量后，本组用来源匹配代码导出v272/3701成功、v268/3702原生失败、v272/3706运行异常三个真实历史样例。每例两个查询，共12个净空标签：6个完整有效、6个跨终止而截短；后者保留前缀但完整值为null。原生失败的PUSH标签为有效false，运行异常的未观测PUSH结局为null；后续未进入阶段不填0。10项mask与窗口检查通过，来源225项几何运行时文件与冻结清单匹配。完整样例及哈希在`evidence/2026-10-16/shared-label-examples-v1.json`，共享索引在main的`work/shared_push_v212_20261016/labels_index.json`。这些是历史语义对齐材料，世界模型尚未逐值确认；不是v212新域覆盖、预测增益或安全验收，新增物理采样0。

**v212 P0本体标签与简单参照**：本组只读复用世界模型P0三条训练用途序列，调用其原审计器及实际初态group指纹，将joint1…joint6按日志关节名重排后，以匹配几何离线重算20ms实际净空。491个0.1s查询对应982个0.4/1s目标：940完整、42在技能完成处删失；重算最低净空49.744／51.418／50.682mm，与原报告最大绝对差约1.5e-9m。完整接触后窗口中，当前净空常量参考的0.4/1s三组等权MAE为4.726／6.874mm，最大乐观误差19.085mm；没有训练或比较神经模型。P0全流程账本为4回合全部成功、其中一次无逐步记录基线；记录覆盖为3回合／3实测组，不能当4个独立组。新域全正例，不支持失败判别、误拒或安全校准；本轮未读保留组、新物理采样0。来源、规则及逐组摘要见`evidence/2026-10-16/v212-p0-label-coverage-v1.json`；共享合同、覆盖表及待同步的采集／划分事项已交main共享入口，双方逐值确认仍待完成。

**P0规则参考的阶段混合诊断**：在同三条训练用途轨迹、同一净空标签和≥0.4s历史条件下，本组按查询时已经观察到的接近完成／合法接触事件分段。1s完整窗口共449个，接近完成前325个、接近完成但未观察合法接触93个、接触后31个；未来发生接触不会反向改变查询阶段。当前净空常量参考的三组等权MAE依次为2.159／1.975／6.874mm，全部混合为2.421mm；0.4s则为0.855／1.162／4.726mm，全部混合1.299mm。准备／接触前窗口主导混合得分，因此模型比较须保留查询阶段及逐组结果，不能将总体低误差当接触后预测通过。当前491查询的净空必要条件全部通过，三回合全成功，没有风险分类／误拒反事实证据，也没有模型增益。分阶段代码与逐组结果见`evidence/2026-10-16/v212-p0-phase-reference-v1.json`，仅用P0训练组，新增物理回合0；未调整阈值或读取保留组。

**共同划分已接收绑定（非新物理结果）**：世界模型新建的共享manifest、账本和`wm-v212-split-v1`已由Reach逐项匹配P0标签、source／report／metadata／startup哈希及训练角色。原入口与记录5301仍同组，P0训练标签保持三条／491查询；共同账本快照为4个已启动、9个尚未启动预留，不将预留当已采集。原标签字节不改，以`evidence/2026-10-16/v212-p0-canonical-binding-v1.json`作为外部split绑定；未读取预留组轨迹，未放行训练。WM-01已补实际接收核对结果，WM-02世界模型消费对齐仍待完成，没有新增决策请求。

**P0标签双方对齐完成并限定发布（非预测收益）**：世界模型独立核对491查询、940有效／42删失及225项几何来源，实际重算标签最大差0m；历史12目标的异常／原生事件mask也通过。本组据证据将唯一索引中的P0三条train来源标为可训练，发布记录`evidence/2026-10-16/v212-p0-training-release-v1.json`绑定原标签哈希及P0归档`wm-v212-split-v1`快照。原标签字节不变；新增回合及历史样例不继承发布。此为数据接收阶段完成，不是模型拟合、泛化、安全校准或在线收益结果；新增物理回合0。

**新训练来源的终态监督边界**：共享registry登记已关闭train回合`p1-reset-5304`后，本组按实际关节构型增量导出189查询／378净空目标（366完整、12删失），该原任务成功、实际最低记录净空49.738mm。真实reset前terminal after为18.90s，故17.90s查询的1s净空窗口51个样本完整有效；owner before-only模型编码止于18.80s，无18.90s状态终点。应分别使用各监督头的mask或共同支持窗口，不能补帧或自动认为箱位移与净空窗口支持相同。标签为新来源待消费对齐状态，不继承P0发布；证据`evidence/2026-10-16/v212-p1-reset-5304-label-coverage-v1.json`，具体差异已交原WM-02。本轮无新物理采样、模型训练或保留组读取。

**分角色增量与开发规则参照**：5304的独立消费核对与终态适配已通过，本组据证据完成train限定发布。其余四train及两development已按owner白名单分开导出，新两批待消费核对；全记录现为8train／2development实测组，train1356查询／2604有效／108删失，dev325查询／622有效／28删失。固定净空常量参考在接触后1s完整窗口的组等权MAE为train7.414mm（83查询）与dev10.331mm（20查询）；0.4s为5.166／5.398mm。未训练或评价新神经模型，未用dev调门槛；全正例不能检验风险分类。两条预留诊断轨迹未读，Reach新增物理回合0。证据`evidence/2026-10-16/v212-role-increment-coverage-v1.json`及`v212-train8-development2-reference-v1.json`保留角色和来源，开发标签不允许拟合权重。

**首轮世界模型开发结果审计（来源组训练，非本组方法增益）**：世界模型组已在远端完成两版训练并冻结开发研究。本组只读核验24项下载文件、12份冻结权重、训练/评分源码及300项指标的回合→组汇总，没有重跑模型推理、训练或物理。两个开发组共20个“已观察合法接触且1s完整”窗口，箱体前向位移MAE如下；每类神经模型是3个训练seed的集成，训练seed不增加独立开发组数。

| 开发版本／模式 | GRU | 无历史MLP | 同信息全历史线性参考 |
|---|---:|---:|---:|
| 初版，自由展开1s | 27.62mm | 41.35mm | 24.80mm |
| 初版，0.4s真实反馈后展开至1s | 35.25mm | 42.11mm | 16.59mm |
| 反馈训练版，自由展开1s | 41.72mm | 39.73mm | 24.80mm |
| 反馈训练版，0.4s真实反馈后展开至1s | 28.40mm | 31.59mm | 16.59mm |

GRU比当前值／速度及较弱响应参考好，但两版均未胜过同信息全历史线性参考，尚无神经模型独有收益。反馈训练版收到反馈后优于其自身开环，但同反馈线性仍更好；这是开发迭代，不能当未见测试。还核查到该次冻结视图的净空监督只来自3个P0训练组，两个开发组净空目标数均为0；对应辅助MAE为null，不是0误差，不可与本组已算出的10.33mm开发净空常量参考比较胜负。后续新增标签发布不追溯改变这两次运行。证据`evidence/2026-10-16/v212-model-development-score-audit-v1.json`明确仅验证文件身份与分组算术，未独立复现网络预测；保留诊断组未读，无风险校准、安全或在线决策收益结论。

**冻结净空头远端补评：简单线性优于神经头（补充开发结果）**：新增四train与两dev标签经世界模型独立核对差值0后，本组落实角色发布，8train可拟合、2dev仅可评价。在远端复用世界模型原评价脚本，保持两版神经权重和原fitting视图不变；线性参照只使用同一原P0辅助拟合标签，新增dev标签仅作评分。两个开发组的合法接触后1s完整窗口共20个，结果如下：

| 未来最小净空余量预测 | 组等权MAE | 最大乐观误差 |
|---|---:|---:|
| 当前余量常量参考 | 10.331mm | 21.361mm |
| 全历史线性残差参考 | 4.841mm | 13.579mm |
| 初版GRU | 5.604mm | 17.370mm |
| 初版MLP | 5.861mm | 18.115mm |
| 反馈训练版GRU | 5.817mm | 15.924mm |
| 反馈训练版MLP | 6.244mm | 18.678mm |

0.4s的32个窗口也由线性最好：MAE3.545mm，当前常量5.398mm、初版GRU4.184mm。未来净空在此开发域有可预测变化，但神经头未胜过同信息线性；不能将小样本最大乐观误差当校准储备，也未测危险事件预防、完成效率或在线选择。两版头都仍仅用原3个P0组的辅助监督拟合，并非使用后来发布的全部8组重新训练。首次隔离cwd启动因相对权重路径失败且未产生分数，已保留；新目录仅修正cwd后退出0，全部预期来源／12份权重哈希前后不变。本组无新神经训练或物理回合，未读保留诊断。证据`evidence/2026-10-16/v212-frozen-margin-development-audit-v1.json`链接远端计划、原score、执行日志、两批发布及16项分组核对；旧箱位移评分未改变。

**逐查询案例：预测偏差与采样敏感性分开**：按main安排，本组在远端对原冻结净空补评的聚合函数作只读预测后记录，捕获416条支持内逐查询误差；16项原评分逐值一致，所有预期模型/输入哈希未变。随后仅用两个已暴露dev回合实际关节构型，重算20ms与100ms采样的未来最小余量。三个事后选择的查询案例为：

| 回合／查询 | 预测器 | 对20ms真值的乐观误差 | 100ms与20ms真值最小值差 | 对100ms真值的剩余误差 |
|---|---|---:|---:|---:|
| 5309／13.9s | 全历史线性 | 13.579mm | 0.933mm | 12.646mm |
| 5309／14.1s | 初版GRU | 17.370mm | 0.933mm | 16.437mm |
| 5310／15.2s | 全历史线性 | 4.727mm | 0.575mm | 4.152mm |

前两查询共享14.38s同一实际低谷，三查询只涉及两个物理回合。20个1s完整窗口的真实粗细采样差组等权平均0.819mm、最大2.784mm；这些案例的主要误差并非仅由100ms/20ms记录分辨率差解释。该分解只隔离了采样因素，不能据此确定剩余误差来自哪一表示／损失／控制机制。未来真值只用于事后诊断，不成为输入或部署基线。三个最低实际余量仍为正，不是安全终止案例；不提供风险分类或安全储备结论。证据`evidence/2026-10-16/v212-margin-error-cases-v1.json`链接原轨迹、步骤、时刻、预测与完整远端计划，图在共享索引`frozen_margin_error_cases`；没有新神经训练、物理采集或保留组读取。

**面向实机字段的源码依赖草案（非硬件结果）**：复用一条已有P0 train记录，核对六轴名与Isaac原18轴槽位[8,13,14,15,16,17]，按冻结几何确认当前指定arm/base距离不依赖共同root刚体位姿。两个实际姿态的平移／偏航静态检查误差低于1e-7m；这不表示动力学或未来后果不依赖底座状态。runtime profile安装z为0.07m，raw XML为0.06m。仅在内存中以raw值代替profile作诊断：初态计算净空76.554→66.586mm，记录最低净空姿态49.744→44.975mm，恢复名义后原值一致；没有修改冻结文件或执行新物理轨迹。该差值不是实物安装误差测量，只说明模型来源必须完整。草案`evidence/2026-10-16/clearance-hardware-input-draft-v1.json`逐项标注硬件单位／槽位／零位／正向／时间与标定尚缺真实证据，硬件命令和日志审阅均0。未提出新的即时确认请求，实际字段交付后沿既有WM-05对齐。

**旧净空线性参考的缩放协议身份已补齐（无重拟合／重评分）**：针对世界模型train-only箱CV新发现的嵌套缩放机制，本组仅在远端读取原冻结归一化统计，核对旧净空4.841mm参考的实际协议。它先用8train状态normalizer，再在有效P0辅助标签上作ridge特征归一化；0.4/1s分别179/173个拟合查询、各3个P0组，647列。原坐标有效尺度为两层尺度之积，并非对原字段只应用一次0.001下限。两个时域各有35个非恒定状态／历史列的有效尺度低于原坐标0.001；例如箱四元数极小变化列可为约1e-6。反之，箱CV已指出的当前Y角速度列，在这里原std约0.00238/0.00248rad/s，旧有效尺度与单层原尺度相同（仅舍入差），不能将箱CV的具体极端机制或修正幅度直接继承到净空。

这只是训练特征统计和方法身份审计，没有拟合任何新系数／模型、没有构造开发窗口或生成新预测排名；旧分数与权重未变。数值floor不是物理噪声界，35列的计数也不证明这些列导致了净空误差。证据`evidence/2026-10-16/v212-margin-scaling-provenance-v1.json`保留原输入、两版相同normalizer、实际特征统计及限制。未来若采用单层raw规范，应另立协议并固定数据／权重／alpha后再比较，不能把同为alpha=.01当作同一原坐标正则化强度。无新增即时确认请求。

**新来源切换入口只读审计**：sim2real v224 的已用 seed3701 在 `17.42 s` 发布 `transition_ready`，本组已将事件中的关节状态、PD 目标、力矩、门禁和观测历史与同一步的 872 行控制轨迹核对；运行到此即结束，没有执行 PUSH。另一控制版本 v234 的已用 seed3701 在 `10.54 s` 因 `base_contact` 于入口前终止，528 行轨迹与失败事件对齐，没有 READY；seed3702 未启动。两者都不能提供后续 PUSH 结局，也不能用于校准本组技能选择器或计算收益。来源 `EntryState.applied_position_target` 对应逐步轨迹的 `pd_target`，不等于 `applied_joint_command`。哈希与审计边界见 `evidence/2026-10-13/source-transition-v224-v234-trace-audit.json`。

**v238 同版本两起点**：已用 seed3701 在 `13.98 s` 达到持续 `0.5 s` 的 READY，位置误差 `5.40 mm`、基座速度 `2.05 mm/s`；700 行轨迹与事件中的状态、PD 目标和门禁相符，PUSH 尚未启动。seed3702 在最后完整控制样本 `4.82 s` 后因承重力分配约束异常退出，242 行轨迹中无 READY 或原生安全终止事件；它属于不完整的运行异常，仍计入两个已启动起点的分母。仅 seed3701 的固定 `4–11.4 s` 窗口，臂累计运动相对 v224 减少 `76.6%`，不能当作整段平稳或任务收益。v239 核对时仍等待 GPU，两起点均未运行。证据和来源哈希见 `evidence/2026-10-13/source-transition-v238-trace-audit.json`。当前仍无同一冻结过渡版本的 READY 后 PUSH 结局，不能校准或验证本组选择公式。

**后续过渡诊断（v239–v242）**：v239 缩短承重混合后，3702 仍于 `4.78 s` 后运行异常，3701 按首失败停止。v241 增加求解迭代后，3702 仍于 `4.82 s` 后异常；来源对精确失败输入作的外包线性约束检查也不可行，说明**该时刻请求的承重力矩**不满足四足单向/摩擦条件，不能推断所有控制或姿态不可达。v242 收紧接管前实测速度、角速度和四足载荷条件后，3701/3702 均运行到 `24 s`，无原生安全终止，却都没有触发接管或 READY，均计入口超时。本组逐条核对四份原报告与50Hz轨迹，分类和哈希见 `evidence/2026-10-14/source-transition-v239-v242-boundary.json`。更保守的过渡避免了这两例的立即异常，但尚未交付可用的接管状态，更未检验本组公式。

**v243 分母纠正**：来源组将 NAV 手端请求对齐 PUSH 准备位后，已用 3701/3702 的原报告和各 `1201` 行轨迹均在 `24 s` 入口超时，READY `0/2`、原生安全终止 `0/2`、报告缺失 `0/2`。旧监督摘要把 3701 错列为未运行；来源对账文件和本组逐轨审计均确认其完整终态，不修改原报告。证据见 `evidence/2026-10-14/source-transition-v243-reconciliation.json`。v244 核对时仍等待 GPU；尚无 PUSH 后续结局或本组选择公式干预结果。

**v244 同版本结果**：加入捕获瞬间的制动力矩可行性检查后，已用 3702 在 `10.38 s` 达到入口 READY（XY 误差 `6.30 mm`、基座速度 `1.31 mm/s`），但 PUSH 尚未启动；已用 3701 在 `6.70 s` 因承重力矩分配残差异常退出。两份报告及 520/336 行控制轨迹已核对，同版本分母为 1 次 READY 探针、1 次运行异常、0 次 PUSH 结局。v238 的 3701 READY 属于另一过渡控制版本，不能与本轮合并成 `2/2`。哈希与限制见 `evidence/2026-10-14/source-transition-v244-mixed-entry.json`；v245 核对时等待 GPU，尚无物理结果。

**v245 首批入口诊断**：在捕获时增加竖直速度和偏航角速度限制后，已用 3701/3702/3703 分别于 `11.28/10.38/9.52 s` 达到 READY，3704 于 `24 s` 入口超时且末态一个后足仅约 `1.20 N`。四份原报告与50Hz轨迹逐条对齐，首失败筛查分母是 READY `3/4`、超时 `1/4`、原生安全终止与缺失均 `0/4`；3705–3708 在这轮筛查未运行。3701 的 `565` 帧原速入口录像与非录像报告/轨迹逐值一致，但停于 PUSH 首动作前；v248 对3704的另版补救仍超时。哈希和视频路径见 `evidence/2026-10-14/source-transition-v245-entry-cohort.json`。这表明入口可达到多个已用起点，尚不能说明 PUSH 后续安全或本组选择公式收益。

**v245 八起点补齐及后续控制对照**：独立补跑3705–3708后，同一 v245 版本的八个已用起点为 READY `5/8`、入口超时 `3/8`、报告缺失0；3704/3705/3706均超时。3707虽达到READY，控制日志有一次全关节力矩比 `0.99215`，不能称全程零限幅。来源组 v249 的足载准备适配器使同初态3704于 `15.50 s` 达到READY，前三条既有成功轨迹与v245控制日志逐字节相同；但3705仍超时，v249只运行5个起点（READY `4/5`），不能拼成全八成功。v250尝试迟到停车，在3705超时、3706于入口前力分配异常，已被来源组拒绝。各原报告/轨迹及来源审计哈希见 `evidence/2026-10-14/source-transition-v245-eight-v249-v250.json`。这些都是来源组过渡控制变化，仍无本组判据干预或PUSH后续结局。

**首次连续 NAV→PUSH 箱任务完成，尚无 NAV 返回**：来源组 v251 的两个已启动入口诊断为3706于 `18.10 s` READY、3705于 `24 s` 超时，均未运行 PUSH。v252 早期快照只有四份 READY 报告；其后续完整结果见下一段。v253 在**一个已用开发起点3701**连续运行：`11.28 s` READY，下一控制样本开始 PUSH，`28.70 s` 原生 `box_settled=true` 且无同时安全终止；PUSH 阶段 `17.42 s`，箱体前进约 `0.617 m`。本组核对1436个控制样本、入口实测状态、激活时序及报告终态；全程最低记录净空 `48.56 mm`、力矩比≥0.98的样本0，但仍有42个少于三足支撑样本，其中腿部接管后的105样本有35个。箱停稳时机身仍约 `0.0996 m/s`、`0.4026 rad/s`，尚未达到返回NAV准入，**未执行 PUSH→NAV**。这是来源组控制器的单例结果，尚非完整 NAV→PUSH→NAV、独立鲁棒性验收或本组可达性公式的配对收益。来源报告、轨迹和审计哈希见 `evidence/2026-10-14/source-transition-v251-v253-first-push.json`。

**同版筛查补齐与出口失败**：v252 八个已用起点的入口探针现为 READY `8/8`、报告缺失0，均在 PUSH 首动作前结束；3707仍有一次力矩比≥0.98采样。v253 实际 NAV→PUSH 首失败筛查只启动3701–3703：3701/3702分别于 `28.70/28.82 s` 箱停稳；3703在 `9.52 s` READY 并激活PUSH后，于最后完整样本 `16.22 s` 之后因承重力矩分配残差异常退出，**没有原生安全终态**。其余五点按首失败规则未运行，不能写成 `2/8` 或 `8/8` 完成率。v255在已用3701的同一物理回合于 `28.70 s` 记录箱停稳并请求出口捕获，但始终未进入出口稳定保持，`36.44 s` 原生 `invalid_hand_contact` 终止，仍未返回NAV。v253/3701原速录像1436帧、50Hz，录像回放的报告与控制轨迹哈希均和非录像回合一致；本组未独立目视判读画面。完整分母、来源哈希及限制见 `evidence/2026-10-14/source-transition-v252-v255-followup.json`。所有变化均属来源组控制器，不是本组公式的效率或安全收益。

**伸臂停车单例通过，整链仍未通过**：v258在已用3701箱停稳后尝试 NAV 零速度制动，`31.18 s` 触发原生臂力矩安全终止。来源组 v259 改为四足承重制动，同一已用起点在 `28.70 s` 箱停稳后，于 `30.44 s` 捕获制动保持、`31.02 s` 满足出口稳定门禁连续0.5秒；本组将1552行轨迹与出口实测状态逐项核对，原生安全终止0，退出段117个采样均无少于三足支撑或腾空。但这仍是**伸臂停车**，未收臂、未运行 NAV 接管；出口门禁不能替代原 NAV 入口门禁。另一来源候选 v260 在3703于 `9.52 s` 开始承重准备，`14.02 s` 才正式 READY 并激活 PUSH；旧力分配运行异常没有重现，却在 `26.66 s` 原生无效手接触终止，仅此一点运行，其他七点未运行。来源 v261 收臂物理诊断核对时仍在运行，不预报结果。报告、轨迹与来源审计哈希见 `evidence/2026-10-14/source-transition-v258-v260-exit-and-support.json`。这些是来源组控制器变化，尚无本组公式的配对增量效果。

**收臂通过，实际 NAV 返回超时**：来源 v261 在已用3701同一物理回合维持箱停稳与伸臂停车前缀，`38.32 s` 收臂并满足出口门禁连续0.5秒；本组核对1917行原报告/轨迹，原生安全终止0。原速录像1917帧的来源审计称报告与控制轨迹一致，但录像不含返回NAV。v264沿完全相同的前1917个控制样本，在 `38.38 s` 激活冻结NAV并尝试后退250mm；`54.32 s` 原16秒返回预算到期，距目标仍约355mm，末态一足竖直载荷0N，无原生安全终止，**整链成功0/1**。本组对v261/v264前缀的共同物理字段逐步比较，差异0；失败发生在新增返回阶段。来源 v263 的同版PUSH筛查快照仅有3703/3701两个已用起点箱停稳，余六点尚未完成，不合成八点成功率；v265返回控制诊断核对时仍在运行。审计边界和哈希见 `evidence/2026-10-14/source-transition-v261-v264-stow-nav-return.json`。收臂与返回均是来源组控制器结果，尚未检验本组接管判据的效率或安全收益。

**同版推箱扩展和 NAV 返回仍未整链通过**：来源 v263 首失败筛查现已运行五个已用起点，3701–3704均原生箱停稳，3705于 `36.78 s` 因实际表面净空 `33.62 mm` 低于原 `35 mm` 门槛安全终止；其余3706–3708未运行。逐份报告与轨迹核对为停稳 `4/5`、原生安全终止 `1/5`，**不是 `4/8` 完成率**。v267 对3705增加只读几何屏蔽日志，1840个共同物理控制样本与v263逐项一致，仍在相同净空处终止；已记录屏蔽动作并不能证明物理净空保证。来源 v265 的后退速度请求增加后，返回 NAV 仍于 `54.32 s` 超时，终点误差约333mm且一足零载；v266交还冻结NAV全身输出并保留有界接续后，终点误差降至约91mm、四足末态均有载，却也在同一16秒预算超时，三版返回均无整链成功。本组核对v264–v266相同的1917样本收臂前缀，终点差异只能归于后续来源控制变化，不能归于本组公式。v268规划净空预留筛查核对时尚无完整物理报告。分母、哈希和限制见 `evidence/2026-10-14/source-transition-v263-v267-cohort-and-return.json`。

**来源控制器首次整链单例**：v268 的另版 PUSH 首失败筛查实际只启动已用3705/3701/3702：前两点分别在 `40.16/32.42 s` 箱停稳，3702在 `31.14 s` 原生 `invalid_hand_contact` 终止；其余五点未运行，三份报告和逐步轨迹均已审计。v270 在已用3701的**一个连续物理回合**于 `11.28 s` READY并激活PUSH、`28.70 s` 箱停稳、`38.32 s` 收臂准备完成、`38.38 s` 激活返回NAV、`47.96 s` 到目标并停稳0.5秒；无二次reset、无原生安全终止。末态目标误差 `32.50 mm`、实际返回移动 `224.06 mm`、四足均有载；2399行轨迹的最后状态与报告完全相同。与v269前2261行逐行一致，变化发生在后续返回控制。全程仍有2个腾空、45个少于三足支撑的20ms采样，不能称独立安全验收。v270原速录像2399帧/50Hz，录像回放的报告和轨迹哈希与非录像回合一致；本组尚未独立目视判读画面。v268和v270不是同版，不能拼接成功率；v270仅 `1/1` 已用起点，尚无八起点整链或未见种子结果，更没有本组公式的配对收益。原哈希、分母及录像路径见 `evidence/2026-10-14/source-transition-v268-v270-chain.json`。

**来源入口分支两点回归**：v268 的3702失败首次无效接触位于箱体系高度 `100.62 mm`，超过原 `90.10 mm` 合法上界，不能归因为净空终止；来源组 v271 仅在需要后移的准备分支启用额外规划预留。它在两个已用关键起点3702/3705分别于 `28.82/40.16 s` 完成箱任务，原生安全终止0；本组审计1442/2009行报告与轨迹，并将23项共同物理/控制字段逐样本对照其对应成功旧版v263/v268，均无差异。含初始化仍分别有2次腾空、28/33个少于三足支撑采样。该 `2/2` 是**PUSH阶段已用失败点回归**，没有出口、收臂或NAV返回，不能与v270另一版的返回成功拼成同版整链率，也不是本组公式收益。来源已启动v272合并版本的八起点整链筛查，本次快照尚无整组终态；下一次以原报告为准。证据及哈希见 `evidence/2026-10-14/source-transition-v271-branch-regression.json`。

**同版整链首失败筛查**：v272把来源组入口分支与返回控制合并，远端监督器已按首失败规则结束。本组从远端复制六个已启动起点的原报告与50Hz轨迹并逐份核对事件、入口/出口/收臂快照和最终目标：3701–3705五点均在无二次reset、无原生终止的同一物理回合完成 NAV→PUSH→箱停稳→收臂→NAV到点停稳，结束于 `46.52–58.06 s`，终点误差 `32.17–32.52 mm`。3706在 `21.98 s` READY并激活PUSH，最后完整控制样本 `36.78 s` 后发生承重力分配残差运行异常，没有箱停稳或原生安全终态；3707/3708因首失败规则未运行。因此已启动分母为**整链 `5/6`、运行异常 `1/6`、缺报告0**，不是 `5/8`。五个成功回合仍各有1–2个腾空及28–45个少于三足支撑采样，未通过独立安全验收。六个入口快照全部满足来源 READY 门禁，入口净空均约 `76.55 mm`、力矩比约 `0.615`；这些瞬时值未区分后续异常。3706入口最低足载较低，但在本批已看结局上挑阈值会事后拟合，不能声称本组公式可预防异常。本组尚未运行有/无公式的同初态配对。完整分母、哈希与逐起点时刻见 `evidence/2026-10-14/source-transition-v272-full-chain-screen.json`。

| 问题 | 已核验观察 | 结论边界 |
| --- | --- | --- |
| Isaac 重置态单技能 PUSH | 来源 `aa/model199` 两组 `30/32`、`32/32` | 不是 NAV 接管、MuJoCo 或实机接触验收；原配置关闭本体自碰 |
| 开启本体自碰 | 已用 seed3701 的 32 环境降至 `2/32` | 原参考策略不具备当前本体自碰安全资格 |
| 独立 NAV→PUSH 基线 | 24 回合：17 次箱体停稳、3 次 NAV 超时、3 次 PUSH 底座触地、1 次无效手接触 | 固定场景即时交接基线；PUSH 内部接近动作尚需约 8–9 秒 |

**入口可观测性复核（2026-10-12）**：上述 24 回合中只有 21 回合进入 PUSH；它们的 `handoff.settle_elapsed_s` 全为 0、`readiness` 全为 `null`，记录时 PUSH 控制器 `motion_ready` 与 `safe_approach_complete` 全为假。故这个快照是 NAV 结束、PUSH 内部接近动作尚未完成的状态，不能当作“准备过渡完成后的 $s^+$”。21 个入口都有 4 只脚法向力超过 2 N，但后来仍有 4 次安全终止；入口最低足端法向力、后腿载荷占比、平面速度、软关节限位余量和腿部目标跟踪误差在 17 次停稳与 4 次安全终止之间均有重叠，现无单变量阈值可直接区分。17 次停稳的首个 `motion_ready` 在 PUSH 开始后 `8.02–8.94 s`；3 次底座接触在此前终止，另一次无效手接触在 `motion_ready` 后 `0.08 s` 终止。`motion_ready` 也不是安全接触证明。审计原始报告的结构化范围见 `evidence/2026-10-12/nav-push-entry-observability-audit.json`。这些是同批描述统计，不能用同批失败拟合门槛后宣称安全提升。

同控制/策略哈希、不同种子的 5801–5824 基线再核对：24 回合中 8 次 NAV 超时、13 次停稳、3 次 PUSH 安全终止；3 次安全终止全部早于 `motion_ready`，其中 2 次甚至早于 `safe_approach_complete`。两批合计 48 回合、37 次进入 PUSH、30 次停稳、7 次安全终止；7 次安全终止中 **6 次发生在 `motion_ready` 之前**。因此只在过渡结束后设置入口门禁，无法避免主要的已观测准备阶段故障；需要分别检验准备阶段安全与完成后的接触资格。5701 批 17 次停稳在 `motion_ready` 后还需实测 `2.52–3.02 s`，停稳距 12 秒时限只剩 `0.30–1.20 s`。这些是已看成功回合的耗时分布，不能充作未见状态的完成时间上界；两批均无接管门禁干预，不能推出改善率。

现有五步支撑预警在 5701–5724 回顾重放中覆盖 4/4 次安全终止，也触发 2/17 次最终停稳；规则先于 5801–5824 新种子收集冻结，在该批覆盖 3/3 次安全终止、0/13 次最终停稳。七次安全终止的预警提前量为 `0.44–1.38 s`，但它是**后一步才能响应的状态告警**，不是可达性或安全控制证明。seed5802 的两种已试固定足端脉冲均仍在 `5.56 s` 底座接触；没有已验证的触发后安全动作。规则、来源和限制见 `evidence/2026-10-12/nav-push-entry-observability-audit.json`。

同一预警规则进一步对 5101–5124、5201–5224 两批旧基线做**回顾性**重放，结合上述两批的完整 96 次 NAV 起点，结果是 56 次停稳、23 次 NAV 超时、1 次 PUSH 预算耗尽、16 次安全终止；16 次安全终止均曾预警，56 次停稳中有 4 次也曾预警，安全终止的最短提前量为 `0.40 s`。旧两批在选定此规则之后才被本次检查，不能冒充独立预注册验证；四批均为同一场景，无控制干预。若简单地把预警当作硬退出，会至少影响 4 个已知可停稳回合，且退出本身是否安全尚未验证。带原始报告哈希清单摘要、脚本哈希和逐批分母的可重复审计见 `evidence/2026-10-12/pre-ready-support-warning-four-cohorts.json`。

按控制器事件分段，16 次安全终止中有 15 次预警早于 `safe_approach_complete`，4 次最终停稳但被预警的回合中也有 3 次如此。故预警主要描述**准备阶段的状态风险**，不能作为过渡完成后的接触许可；最短 `0.40 s` 的窗口也要求任何退出动作有实际响应测试。

2026-10-13 在远端 GPU0 运行已看 seed5802 的预警后锁臂隔离试验：触发前 `256` 步的共同物理/控制字段与冻结基线逐值一致，`5.12 s` 预警、`5.14 s` 首次执行锁臂，共 `22` 步；**仍在与基线相同的 `5.56 s` 触发原生 `base_contact`**，准备阶段未完成。故“只停止臂接近”在该状态下未救回支撑；不能推广到其他状态或动作。原自动审计首先因旧基线多一个只读 `recovery_decision_state` 字段而拒绝，后续只修正此记录字段的对齐，未修改物理报告或运行协议。修正审计、源哈希和完整终止原因在 `evidence/2026-10-13/warning-arm-hold-seed5802-pair.json`，原始大报告及运行时协议副本在仓库外 `../artifacts/go2-piper/2026-10-13/warning-arm-hold-known-state/`。协议中第二个误报成功 seed5703 的试验以首例安全失败为停止条件，**不运行**。

对四批 `20` 个预警回合（随后安全终止 `16`、停稳 `4`）再做只读状态重放：预警时机身高度、过去 `0.2 s` 的机身竖直速度、后足与前足法向载荷的两类范围**全部重叠**。例如停稳/安全终止的后足合力范围分别为 `13.36–15.38 N`/`5.46–18.22 N`，竖直速度范围分别为 `−0.0249–0.0150`/`−0.0386–0.0147 m/s`。故这些单项均不能靠一个阈值在已看回合中完美区分，尚无经过独立验证的联合门槛；这些状态量也没有给出安全恢复动作。逐例、原报告哈希清单和脚本见 `evidence/2026-10-13/warning-state-overlap-four-cohorts.json`。

对完成后的最简时间门槛做了独立于控制动作的回顾性审计：5701 批 17 个停稳回合从首次 `motion_ready` 到停稳为 `2.52–3.02 s`。把其中最大值 `3.02 s` 固定为剩余时间要求，在四批 96 次起点中，56 次最终停稳有 55 次放行、1 次错拒（seed5821，实际只需 `2.58 s`）；唯一准备完成后的安全终止仍被放行（seed5723，`0.08 s` 后无效手接触）；1 次预算耗尽被拒（seed5110），另外 15 次安全终止在准备完成前，门槛没有机会评估。故常数耗时门槛不采用，**没有由此产生的效率或安全提升**。审计脚本 `scripts/audit_piper_post_ready_time_budget.py` 和完整源报告哈希在 `evidence/2026-10-12/post-ready-time-budget-four-cohorts.json`。四批同场景，均为事后检查。
| v105 原起点 PUSH | 已用 seed3701，`24 s` 为 `4/8`；原 `12 s` 前观察为 `0/8`；最低控制步净空 `19.214 mm`，力矩限额比 `1.0` | 延长窗口诊断，不是原 12 秒配置重跑或安全候选 |
| v106/v107 提前近距减速 | 同批 `24 s` 降为 `1/8`、`0/8` | 简单提前减速损失推进；两版排除 |
| v108–v110 入口姿态 | v108 有限静态搜索未通过联合筛选；v109/v110 关节 4 脱限但仍为 `4/8` | 单关节移动没有让 env4 入口门禁通过 |
| v111 受载姿态 | env0/1/5 各 8 个固定机身静态起点，均无满足全部约束的候选 | 有限搜索失败不是全动作不可达证明 |
| v112/v113 逐控制步补录 | 成功 env2 与超时 env1 均触及关节 2 限幅；env1 有 232 个有载停线步正向命令为零 | 受载、基座间距和任务余量必须一起分析，尚未识别单独致因 |
| v114/v115 接触腿部渐变 | 同批 `24 s` 为 `3/8`、`1/8`，v115 新增两次无效手接触 | 延长渐变不是已验证修复；两版排除 |

2026-10-10 静态公式实现状态：静力平衡统一为 $\hat\tau=g-J_p^\mathsf{T}F$（$F$ 是箱体作用于手端的外力）。本地当前 MuJoCo 模型在默认姿态下，假设箱体沿负局部 X 对手端施加 `20 N` 反力时，关节 2 静态负载比约 `0.144`（零力约 `0.040`，模型限额 `20 Nm`）。这只验证模型 API 和计算可运行，**不是 v105 接触状态、动态负载预测或任务改善**。旧 seed647 快照的来源脚本哈希与当前版本不符，搜索器正确拒绝重放，没有产出可比较候选。

同日完成 v105 已看状态的远端 CPU 静态筛查，协议与哈希在 `evidence/2026-10-10/loaded-pose-offset-screen-v4-summary.json`，原始 JSON 在仓库外 `../artifacts/go2-piper/2026-10-10/loaded-pose-offset-screen/`。基座二维偏移网格为 `-4/0/+4 cm`，每点两起点：env1/2 首次合法接触分别有 `14/18`、`17/18` 个数值可行起点，评分均选零偏移；失败 env0/5 有载终态分别为 `0/18`、`6/18`，env5 仍选零偏移。env5 某非零偏移的静态关节 2 比值可从 `0.948` 降至 `0.893`，但其总评分更差。这个有限对照**没有给出效率或安全收益**，也不证明任何状态不可达。成功 env2 终态已经脱离接触，因此只用了首次接触帧。Isaac 原始首次接触帧有四足受力，而同姿态 MuJoCo 冻结重建未稳定识别足端接触；本次不把该跨仿真支撑量用于准入。

补充的 v5 回顾性筛查把源状态提前 20 个控制步，仍使用随后首次合法接触的点、姿态和反力作静态目标。env1 的 `17/18`、env2 的 `15/18` 个起点数值可行，两例评分仍选零偏移。`(+4,-4) cm` 的最低可行关节 2 静态负载比分别是 `0.907`、`0.889`，低于所选零偏移的 `0.955`、`0.940`，但总评分更差。后来接触信息在当时不可用，基座偏移也没有经过 NAV、准备过渡和动态接触验证，因此 **v5 不能作为可部署方法或改进证据**。

v10 改用源状态的 MuJoCo 手部与箱体最近点生成前表面目标，不再用未来接触帧；反力固定假设为 `15 N`，这是查看已看轨迹后的探索值，尚非在线测量。失败 env1 与成功 env2 各 `11/18` 个起点数值可行。原静态评分在 env1 选前移 `4 cm`，但控制器到 `0.43 m` 停线的余量从 `0.134 m` 减为 `0.094 m`；env1 后续确实因靠近该停线而难以推进。加上“不降低源状态停线余量”的几何筛选，两例均选零偏移。此条件是公式候选的安全筛查，**未验证能改善动态安全或任务效率**；MuJoCo 足端支撑仍未校准，真实状态估计也尚未实现。原始报告与脚本、模型哈希见同一证据摘要。

接触后又审计了一个简化推进预算：用过去 `20` 控制步的箱体/基座位移比，估计在剩余停线余量内能否走完到原控制停止阈值的距离；要求连续 `20` 个有效窗口低于需求才报警。失败 env1 在步 `745` 报警，首次停线为 `764`；但最终成功的 env2 也在步 `741` 报警，最大连续报警 `39` 步。故该比率**不能充当中止或不可达门禁**。底盘停住后还会因缺少基座位移而失去观测。公式、窗口和报告哈希见 `evidence/2026-10-10/push-progress-budget-audit.json`，原始 JSON 在仓库外 `../artifacts/go2-piper/2026-10-10/`。

同两条逐步轨迹的时间拆分更直接：失败 env1 的安全准备/合法接触分别在 `12.02/13.76 s`；成功 env2 为 `11.84/13.52 s`，箱体达到原控制停止阈值在 `16.56 s`，停稳在 `17.14 s`。两例首次合法接触都晚于原 `12 s` 任务时限。若保持成功轨迹接触后至停稳的观察耗时 `3.62 s`，接触需在 `8.38 s` 前发生，比当前早约 `5.14 s`。成功轨迹安全准备阶段中，阶段索引 17、15、19 分别耗时 `1.70/1.28/1.20 s`，这些是实测运动与等待时长，不能直接删去。上述均为**回顾性时间账**，不表示安全准备能直接缩短；见 `evidence/2026-10-10/push-phase-timing-audit.json`。因此下一步优先研究 NAV/准备过渡的可执行耗时，不能只优化接触后 PUSH。

已追溯上述冻结评估实际加载的安全准备资产：评估 `plan.json` 的 `approach_sha256` 对应远端 `train/mujoco/deploy/piper_push_safe_approach.json`，共有 **21 个路点**；几何根目录和来源组当前文件的 **16 点**版本哈希不同，不能用它解释评估轨迹的索引 21。索引 16–20 是追加的五个路点，在成功/失败轨迹分别耗时 `4.44/4.46 s`。全路径满足位置容差 `0.04 rad` 但速度仍高于 `0.12 rad/s` 的控制步累计为 `3.70/3.92 s`；追加五点中仅 `0.64/0.66 s`，剩余大部分时间是真实行程。索引 15–20 的报告最小净空约 `21.9/21.8 mm`。因此**单独放宽路点速度门槛不是有依据的安全加速方案**，这些累计步数也不能视为可直接节省的时间。哈希、分段和只读审计工具见 `evidence/2026-10-10/safe-approach-timing-audit.json`。下一候选应从有几何约束的完整路径与 NAV 姿态过渡中寻找，并先完成静态连续路径、支撑及执行器检查，才在远端做同初态 Isaac 配对。

原静态桥接表在较晚的 `17.44–19.50 s` 状态否决过直接跳过索引 18：索引 17→19 的插值边箱体净空为 `-18.85 mm`，低于 `+10 mm` 门槛；当时隔离脚本在 Isaac 启动前拒绝试验。**这个否决对较晚状态仍成立**。新一轮只针对 v112/v113 的准备阶段重建 374 个实测基座、腿部和箱体状态，每 `0.02 rad` 检查同一跨边，得到最低本体保护/箱体净空 `39.1/27.5 mm`，且末端路点不变，因此它成为**条件化的接触前静态候选**。跨边最大单关节行程 `1.177 rad`，小于原两段的 `0.590+0.974 rad`，但这不是实测节时。箱体向机身移动 `15 mm` 时最低箱体净空 `14.2 mm`，移动 `20 mm` 时仅 `9.94 mm`、不再达标；不能将这个候选无条件复用到箱体已移动的状态。脚本、哈希及已准备但未启动的远端隔离试验见 `evidence/2026-10-10/approach-shortcut-screen.json`；这个短边尚无动态配对或时间收益结果。历史更早结束的短路径试验（v17/v20，协议和控制版本不同）均为 `0/8`，分别出现无效手接触或几乎无推进；不能与 v105 作严格配对，也不应原样重试。

索引 18 在已看 v112/v113 轨迹中分别占 `42/41` 个 `0.02 s` 控制步，即 `0.84/0.82 s`。直接跨到 19 会改变相邻阶段耗时，因而该数值既不是严格可节省上界，也不是实测候选收益；但它远小于回顾性 `5.14 s` 提前接触目标。该小批优先检验条件化短边是否在动态支撑、合法接触、净空和力矩下可执行，不能单凭删一个路点就宣称解决原 `12 s` 任务。候选运行后使用 `scripts/audit_piper_approach_shortcut_pair.py` 核对冻结命令、完整分母及同 env 指标；该 `24 s` 诊断仍不替代原时限重跑。

在同两条已看轨迹上，用冻结 MuJoCo 运行时完整筛查单独跳过索引 15、16、19：分别覆盖 `201/333/241` 个记录状态，最低本体保护净空 `27.7/30.1/25.0 mm`，最低箱体净空 `196.4/159.0/91.1 mm`，均通过 `20/10 mm` 静态门槛。索引 15 的已看阶段耗时 `1.28/1.30 s`，其远端隔离副本已经准备并复核，**尚未启动**。但按两段与直达边的关节最大位移之差，索引 15 仅减少 `0.297 rad`，索引 18 减少 `0.387 rad`；原阶段耗时不能直接当成可节省时间，也不能据此把索引 15 排在索引 18 前。这些是各自单独跨边的已看状态结果，不能组合推断多路点跳跃安全，也不能推断动态节时、支撑或未见状态安全。原始报告哈希与远端路径见 `evidence/2026-10-10/approach-shortcut-screen.json`。

进一步对准备前段做完整记录状态筛查：单独跳过索引 2–14 的相邻跨边均通过静态几何门槛。更有时间潜力的长边 `1→14`、`1→15`、`1→16` 分别覆盖 `619/748/781` 个记录状态，最低本体保护净空 `76.6/30.1/27.7 mm`，箱体净空 `311.3/213.5/195.6 mm`，均通过静态门槛。`1→14` 替代的原阶段耗时 `4.74/4.86 s`；直达边自身耗时当时未知，因此这些数字**不是节时结果**。即使直达边耗时为零，单靠此边也不足以达到回顾性约 `5.14 s` 的提前接触目标。静态余量更大的 `1→14` 后来完成独立 Isaac 诊断，结果见下文；`1→15/16` 未开展动态配对。来源哈希、独立筛查报告和完整限制见 `evidence/2026-10-10/approach-long-edge-screen.json`。

`1→14` 首次远端诊断已启动，但来源组随后同时启动两张 GPU 的 v118 评估。本组在第 400 步后主动中止以避免并发争用：退出码 `-9`、无报告，不能据此判断候选成功或失败。新隔离目录已准备，待 GPU 释放后重跑；证据索引保存旧退出文件与新计划的哈希。

GPU 释放后的 `1→14` 重跑完成同种子、同评估器、同物理的 `8/8` 配对。原 24 秒基线和候选均 `4/8` 停稳、`4/8` 超时，无其他原生终止；成功环境由 `{2,3,6,7}` 变为 `{2,3,5,7}`，env6 从成功变超时。连续记录的 env2 安全准备完成从 `11.84` 提前到 `8.16 s`，首次合法接触从 `13.52` 提前到 `9.86 s`，停稳从 `17.14` 提前到 `13.54 s`；约 `3.68 s` 的准备节时与预先拟合的 `3.70 s` 接近，但这是已看单批而非模型泛化证明。所有停稳都晚于 `12 s`，原 12 秒配置尚未重跑。全批次最低控制步几何净空从 `19.21` 降为 `16.80 mm`，两者均低于 `35 mm` 目标；最大力矩限额比均为 `1.0`。原配对报告只连续记录 env2 支撑，按足端竖直力 `>2 N` 计少于三足的步数为 `44/857` 与 `46/677`；下文另补 env6，仍不能当作全批次支撑安全结论。冻结评估器不提供全环境支撑和无效箱体接触逐步计数，审计只核对可用接触计数及终止标志。此候选证明前段路径可显著提速，但**任务成功率与原时限未改善，且净空和 env6 结果退步，不予晋级安全候选**。报告、计划、退出状态保存在仓库外 `../artifacts/go2-piper/sim2sim-current-20261008-a/reachability-approach-edge-v1/`，哈希见证据索引。

为定位 env6 退步，只把连续轨迹记录对象改为 env6 后分别重放基线与长边候选；两次 `8/8` 终态与原报告逐值一致。env6 首次合法接触 `14.20→10.96 s`，箱体前进 `0.2 m` 也提早 `2.50 s`，但达到 `0.3 m` 反而晚 `0.74 s`。从首次合法接触起的相同 `150` 控制步（`3 s`）内，合法接触步 `150→123`，箱体前进 `0.517→0.291 m`，横向漂移从 `-10.7` 增至 `-38.9 mm`，最低控制步净空 `38.7→24.8 mm`；关节 2 饱和步数 `82→85`。两次首次接触时四足都有 `>2 N` 受力记录，候选机身瞬时速度更低，不能把退步简单归因于瞬时切换或支撑丢失。候选横向手端误差在推进 `0.2 m` 时已由基线约 `-59 mm` 变为 `+65 mm`，在 `0.3 m` 时约 `+131 mm`；接触保持下降和横向偏差增长都与推进减速同时出现，**不是已证明的唯一因果机制或在线阈值**。原始 env6 轨迹、计划和退出状态保存在同一仓库外产物根目录，哈希及时间里程碑见证据索引。

另用两条已看轨迹的原路径阶段 2–20 拟合描述性时间模型 $\hat t=0.254\,\mathrm s+0.974\,\mathrm{s/rad}\,\|\Delta q\|_\infty$，原阶段留一最大绝对误差 `0.30 s`。它预测 `1→14` 直达阶段约 `1.42 s`，相对原对应阶段预计节省 `3.70/3.84 s`；`1→15/16` 预计分别节省 `4.59/4.75 s` 和 `4.83/5.01 s`。这些是**动态试验前的预测**，原阶段留一误差不能推广为新边的置信界；预测也未包含支撑或后续控制变化。模型脚本、输出哈希见同一证据 JSON，后续必须用 Isaac 配对报告检验。

为检验较短前段边，在相同两条已看轨迹上分别筛查 `1→10` 与 `1→12`：最低本体保护净空均约 `76.6 mm`，箱体净空分别 `421.7/345.0 mm`，均通过静态门槛。描述性时间模型预测 `1→10` 可在两例中节省 `2.67/2.79 s`；这仍是未校准的新边预测。只对 `1→10` 做了同种子、同评估器和物理参数的远端 `24 s` Isaac 配对，完整 `8/8`：基线 `4/8` 停稳、`4/8` 超时；候选 `5/8` 停稳、`2/8` 超时、`1/8` 无效手接触终止。env0/1 由超时变停稳，env3 由停稳变无效手接触；env6 仍停稳。env2 准备完成和首次合法接触均提前 `2.74 s`，停稳 `17.14→14.48 s`。所有停稳仍晚于 `12 s`，原 `12 s` 配置未重跑。全批最低控制步净空 `19.21→17.71 mm`，最大力矩限额比均 `1.0`；连续支撑仅记录 env2，低于三足的步数为 `44/857→45/724`，不足以证明全批安全。**虽然该已看批次的 24 秒停稳数增加，新的无效接触和净空退步使 `1→10` 不具备安全晋级资格。**`1→12` 未启动动态试验；后续先定位 env3 接触风险，再设计独立安全条件。配对审计与四份静态/时间报告哈希见 `evidence/2026-10-10/approach-conservative-edge-pair.json`，原始 Isaac 报告留在仓库外 `../artifacts/go2-piper/`。

针对 `1→10` 的 env3 无效接触，分别把冻结基线和候选的连续记录对象改为 env3 重放；两份报告的八个终态各自与原报告逐值一致。env3 安全准备完成 `11.88→9.14 s`，首次合法手箱接触 `13.52→10.78 s`。箱体前进约 `0.45 m` 时，候选手端高度 `27.0 mm`，基线 `35.2 mm`；相同末尾 `150` 控制步内，候选关节 2 饱和 `101` 步，基线 `78` 步，候选最低手端高度 `24.5 mm`，基线 `34.9 mm`。候选最后一帧**物理步前**仍记录合法接触，下一物理步触发无效手接触终止；当前逐步轨迹不能直接看到终止物理步的首次无效接触点。因此手端降低和负载限幅是并行风险线索，**没有建立唯一因果或可在线使用的高度阈值**。配对审计脚本与两份重放报告哈希见 `evidence/2026-10-10/approach-conservative-edge-pair.json`。后续若设计安全条件，应在独立初态和原时限下验证它对无效接触的约束及对成功率的影响。

等箱体推进量的四组已看轨迹对照进一步否定单变量门禁：成功的 `1→14` env2 在箱体推进 `0.2 m` 时手端比自身基线低约 `9.0 mm`，与失败的 `1→10` env3 同阶段低约 `8.5 mm` 重叠；成功轨迹也普遍出现关节 2 限幅。冻结 PUSH 的 `invalid_hand_contact` 判据是接触力大于 `1 N` 且不满足合法前表面接触，其中一项要求接触点与手端距离小于 `70 mm`。env3 候选最后合法物理步前，这一**接触点余量** $m_{\rm tip}=0.07\,\mathrm m-\|p_{\rm contact}-p_{\rm hand}\|$ 为 `+1.84 mm`；`0.02 s` 后的终态为 `−20.98 mm`，力约 `20.23 N`，足以解释无效接触分类。前一步到终态的接触点高度从 `91.3` 跳到 `114.3 mm`，手端高度几乎不变；不能据此推断接触点跳变的物理原因。其他已看成功轨迹的合法接触最小余量也并非无穷大，env3 基线最低 `15.52 mm`。因此，接触点余量比手端绝对高度更贴近**现有终止定义**，但本例到终止仅有一个 `0.02 s` 控制步，尚未验证能够预警和恢复，更不能按此样本拟合在线阈值。完整比较、冻结源码哈希和时间戳见 `evidence/2026-10-11/loaded-progress-pair-audit.json`。

2026-10-12 来源组独立验证了静态路径覆盖的边界：针对八个实际准备终态分别生成的路径在其独立静态审计中 `8/8` 通过；v147 已用种子、原起点 `140 s` 动态诊断只有 `6/8` 首次合法接触，连续健康接触 `0/8`、完整 PUSH `0/8`。env4/7 终止于无效手接触，终态接触点距手端 `99.09/89.28 mm`，超过 `70 mm` 谓词；另六例受载关节 2 均触限且净空下降。这说明本组状态条件化路径余量公式只解决“路径在实际准备状态下的必要几何/入口筛选”，还没有解决接触建立、负载安全和持续推进。来源组控制、起点准备与时限不同，**不得把 `8/8` 静态覆盖或 `6/8` 首次接触并入本组成功率或声称安全收益**。其小型摘要、分类器审计与退出状态的哈希见 `evidence/2026-10-12/source-path-bank-dynamic-boundary.json`；原始大报告仍留来源组远端。

来源组进一步做了明确的接触模式隔离：v148 保留 v147 的准备、按状态路径及安全终止，只在**实际合法接触后**启用原生锁臂。八个环境首次合法接触时间逐值相同，六个合法接触环境的持续健康保持由 `0/6→6/6`、维持 `10.46–12.46 s`，记录接触后最大力矩比均 `<0.760`，最低净空 `≥62.06 mm`；env4/7 非法首次接触仍在，完整任务仍 `0/8`。这说明持续压入/追踪模式对先前的受载退步有影响，但锁臂阶段没有证明推进或完整任务收益。对 reachability 应把“合法建立接触”“保持承重接触”和“受限负载下完成位移”分开计数，不以任何前两阶段成功替代后者。来源状态/摘要哈希及八环境对照见 `evidence/2026-10-12/source-contact-lock-stage-pair.json`，与本组冻结策略和 `24 s` 任务不可合并。

2026-10-12 来源组把准备和合法接触保持推进到已用种子的 `8/8`（v153），但该阶段箱体最大位移仅约 `0.18 mm`，完整 PUSH 仍 `0/8`。对 v153 的实际稳定接触姿态，来源 v155 用匹配质量/质心、执行器限额和实测接触点做假设法向反力 `0–30 N` 静态平衡：`20 N` 时 `7/8` 的关节 2 超过原硬限额，`8/8` 未达90%设计余量。对样本网格内负载比作线性插值，本组得最小90%力预算约 `9.90 N`，最小硬限额力预算约 `15.91 N`；只是这些静态姿态和反力假设的**描述性模型预算**，没有测得真实推力，更不证明机体无法推箱。来源组没有因此提高执行器限额或把静态负结果当全局不可达，正在探索承力姿态。脚本、源哈希及八环境明细见 `evidence/2026-10-12/source-loaded-contact-force-budget.json`。

同一来源组后续以 v153 实际接触姿态和匹配模型设计 v156/v157 承力端点：八例均通过端点的全机器人静态几何/承重筛查，并在假设 `20 N` 法向反力下达到90%力矩余量。与原接触保持姿态的 `0/8` 相比，这给公式 $F_{0.9}$ 一个**模型内候选**；本组在同一离散网格内插值得到最紧环境预算约 `9.90→20.38 N`。端点是针对已看样本用相近约束搜索选出的，改善属于设计内结果，**不是独立试验，也没有证明从原姿态到端点的连续路径或真实受载推箱**。来源组 v158 正检查每例连续路径，完整碰撞、真实接触迁移、动力学及原时限仍需验证。配对来源哈希、逐环境力矩比和预算见 `evidence/2026-10-12/source-loaded-endpoint-model-comparison.json`。

来源组 v159/v161 又检查从原实测接触保持状态到 v157 承力端点的有限连续接触路径：虽八个端点各自通过假设20N静态筛查，沿途41节点、假设5N的路径条件各只有 `5/8` 通过，同样的 env0/1/3 未找到合格序列；未通过者未在物理仿真中直接跳到端点。这个**端点与路径的落差**说明提高 $F_{0.9}$ 的端点设计尚未变成可执行收益；有限节点搜索失败也不是全域不可达证明。来源组正检查解除接触再重接触的替代转换，该模式必须重新通过合法接触门禁。结果和端点身份哈希见 `evidence/2026-10-12/source-loaded-endpoint-path-gap.json`。

来源组 v175 随后在已用 seed3701 的八环境、`130 s` 窗口完成**真实解除接触与退开**阶段，8/8 尝试且8/8阶段通过，无原生安全终止，`120.42–120.82 s` 首次确认手部合力≤1N并连续解除合法接触；初始120秒 env0 与 v153 轨迹逐值相同。退开阶段最低记录净空 `59.32 mm`、最大力矩比 `0.7583`，但完整推箱仍 `0/8`。因此“保持接触→观测解除接触→允许姿态转移→重新验证合法接触”的模式划分已有**退开物理阶段**支持，尚未验证中间姿态转移、重新接触及承力推进。静态规划的 `60 mm` 净空预留在实际退开中出现约 `59.32 mm`，不能当作动态下界；原 `55 mm` 保持门禁仍在。阶段摘要、退出状态和原报告哈希补入 `evidence/2026-10-12/source-loaded-endpoint-path-gap.json`。

来源组 v177 修复 v176 的位姿接口错误后，沿 v175 前缀在同一已用种子八环境运行 `145 s` 真实机身转移诊断，8/8 完整终态、前130秒 env0 轨迹一致。机身转移仅 env6 `1/8` 完成并保持至少2秒；另七例控制器停止路径推进后超时，原生安全终止0，完整 PUSH `0/8`。八例控制采样均至少三足承重，记录腾空0；最大足位漂移 `8.99 mm`、最大世界系手端位置误差 `2.51 mm`、最大力矩比 `0.711`。最低控制步几何净空 `54.42 mm`，略低于保留的 `55 mm` 门槛，不能宣称全程满足55mm保证；来源审计仍记原生安全终止0。结果说明真实机身调整只在一个已看初态完成，不能与退开 `8/8` 或静态端点 `8/8` 拼成全批连续接管成功；真实重新接触、承力推进、原12秒和独立种子尚未验证。报告及阶段审计哈希见 `evidence/2026-10-12/source-loaded-endpoint-path-gap.json`。

v178 在 env0 首次控制器停止时做同一规划世界手端姿态的运动学复算：实际机身 X 比规划位置多前移 `9.76 mm`，只替换这段机身平移会使几何净空从 `62.11` 降至 `54.34 mm`；只替换姿态则为 `62.34 mm`，实测为 `54.94 mm`。因此该状态的机身位置跟踪误差足以使原55mm净空门禁触发，提示规划净空须按**实际机身位姿**重算或留出跟踪误差预留。这仅是一例反事实运动学诊断，不是误差到净空的全局界或物理修正收益。来源 v179 已在远端测试位置跟踪修正，尚无有效终态；不与其并发运行。来源摘要哈希见 `evidence/2026-10-12/source-loaded-endpoint-path-gap.json`。

历史试验还否证过若干单项修补：单纯调接近 IK 权重、延长等待、提前减速、力反馈目标及一轮腿部 PPO 微调都未在原时限和安全门槛下形成候选。保留这些负结果的目的，是避免重复同一参数扫描；不能据此断言所有联合控制都无解。

来源组的新完整技能基线 v204 在更轻的 `1 kg/0.15` 箱体上、`226→19` 接口和 `48 s` 窗口，已用八初态 `6/8` 停稳、`2/8` 超时；六例完成时间 `41.36–46.42 s`。本组复核其本地小型结果与计划哈希，并记录了 `14` 个腾空、`169` 个少于三足支撑的 20ms 控制采样；因此它不是独立安全验收，更不是原 `12 s`/`5 kg` 任务的 reachability 收益。它提供了下一轮**固定底层技能后**比较接管判据的可用任务域，须以相同起点、负载、权重、完整过渡和原生终止做新配对。见 `evidence/2026-10-13/source-v204-complete-push-baseline.json`。

该 v204 原报告哈希已在远端复核。仅对成功 env0 的 20ms 逐步轨迹，首次完成安全接近约 `36.48 s`，`motion_ready` 约 `38.76 s`，首次手接触约 `39.36 s`，停稳 `41.36 s`；实测可接触后到完成约 `2.60 s`。若同一尾段耗时不变，要在 `12 s` 内完成，须把可接触时刻提前到约 `9.40 s`，比当前早 `29.36 s`。这只是**单例的条件算术**，不是尾段耗时下界或全批性能预测；它说明现有新技能的主要时限缺口在接近阶段，单纯放行/等待判据无法证明填平该缺口。本组可先在固定 48 秒域测接管判据的选择错误与等待成本，再单列原12秒任务。

v205 两条独立续训分支体现了底层策略选择风险：固定最终权重在相同已用八初态严格评估分别为 `0/8` 与 `7/8`。`7/8` 权重与 v204 的控制源码哈希、任务参数和初态相同，六个共同成功环境均更快，完成时间降至 `39.64–44.08 s`，env6 另在 `42.68 s` 完成；但少于三足支撑采样 `169→214`，最低实际净空 `50.14→47.08 mm`。这些数值只描述**选定权重的同种子比较**，不是未见状态的安全或本组公式收益；要做 reachability 试验须先固定其中一个底层权重，不能用两条续训分支的最好结果合成单一策略。完整来源、哈希及逐环境时刻见 `evidence/2026-10-13/source-v205-used-seed-comparison.json`。

来源组 v209 的入口退让缩短对照提供一个更直接的阶段证据：相同 seed8051 权重、已用 seed3701 八初态、1 kg/0.15 和48秒任务下，v207 `7/8`、v209 `8/8` 停稳，原未接触的 env4 在 v209 完成。最终准备点和实测入口门槛未变；箱面前中间目标由后方120mm移至60mm，相应推进段由90mm改为30mm。源码差异还使入口阶段姿态插值按较短推进段归一化。v209 的最小实际净空约46.47mm、最大力矩比0.9762，但全批少于三足支撑采样由209增至239，腾空采样均为14。完整同初态、源码与报告身份见 `evidence/2026-10-13/source-v209-used3701-pair.json`。

扩展到另一批已用 seed2701 的32初态，8051/8052两份固定权重均从 v207 的 `26/32` 到 v209 的 `32/32`，原六个接触准备或推进超时例全部停稳，报告无缺失和原生安全终止。完成时间分别 `37.88–44.20 s` / `38.38–44.48 s`，最低控制步净空约 `40.17/46.92 mm`；少于三足支撑采样各自 `746→898` / `747→885`。8052权重的已用 seed3701 小批也为 `7/8→8/8`，支撑不足 `215→246`。这显示缩短中间入口在**已看开发状态**改善完整任务完成数，同时支撑记录退步；不能推断未见状态鲁棒性、原12秒达标或本组 reachability 公式收益。来源报告身份、唯一终态和口径见 `evidence/2026-10-13/source-v209-used2701-expansion.json`。

v210 冻结8052后的两组未用32回合（仍为1kg/0.15、48秒）分别 `31/32`、`32/32`；唯一失败是第0.32秒、接近路点1时的臂力矩门禁，发生在后置接管决策点之前。来源组的两点直达接近 v212 在已用 seed2701 的32环境中为 `30/32`，两次无效手接触分别出现在接近完成前和 `motion_ready` 后。两类风险不能用同一个后置门禁包办；尚无本组公式的放行/等待干预结果。v210的31/32也不能写成零安全失败，v212缩短路径不属于本组主要创新。原报告哈希和预物理失败阶段见 `evidence/2026-10-13/source-v210-v212-stage-exposure.json`。

来源组现以 `push-direct-approach-v212` 作为跨组 Isaac 仿真参考版，并交付472项完整来源/资产清单、双checkpoint及原速录像；本组已核对计划、权重、视频哈希。录像是已用 seed3701 的成功 env0，共16.00秒、400帧，与匹配八环境非录像批终态及物理摘要一致。该版本在已用 seed3701 为 `8/8`，已用 seed2701 为 `30/32`、两次无效接触；仅用于本组固定技能选择研究，**不是已验证的任意NAV末态接管或安全实机技能**。详细接收契约与来源限制见 `evidence/2026-10-13/source-v212-approved-handoff.json`。

接触前高度外推只读审计：在手部原点到箱体前表面的间隙首次降至 `40 mm` 的控制步末，按当前两步速度算 $\hat z=z+g v_z/v_{\rm close}$。已看 6201–6208 条件样本的右侧布局仅有 5 条（1 次无效接触、4 次停稳），其外推高度约 `97.5 mm` 对 `46.8–79.6 mm`，只是提出假设的线索。另批 6401–6416 的完整右侧布局 10 条经原报告哈希复核后，以现有接触点高度限 `90.1 mm` 作**未校准参考线**，无效接触 `4/6` 在参考线以上、`2/6` 漏报，停稳 `0/4` 在参考线以上。漏报为 seed6403 `88.0 mm` 和 seed6415 `83.1 mm`；其中高度外推的是**手部原点**，原终止条件检查的是**真实接触点**，两者不能等同。间隙事件到首次有载接触的实际间隔为 `0.085–0.450 s`，远大于简单常速外推的确定性保证。此批次先前已做其他分析，不能称预注册独立验证；没有干预、效率或安全收益。复算脚本和完整分母在 `scripts/audit_piper_precontact_height_projection.py`、`evidence/2026-10-13/precontact-height-projection-secondary-cohort.json`。

当前最可信的机制分解是两类：env4 在合法手箱接触之前卡于接近高度/面向门禁；env0/1/5 在合法接触后仍可能因负载、手臂/机身相对姿态和近距停止线而超时。成功轨迹同样可能触及关节 2 限幅，因此任何单一阈值都不能从已看数据中作为完整可达性判据。

本组已有 `mujoco/reconfigurable_navigation/reachability/` 中的条件化限时回推和安全量检查。它只对提供的模型、观察划分及外部界成立；当前没有跨状态、动作、延迟和接触的联合校准，真实 NAV→PUSH 判定仍为 `abstain`。今后的核心交付以[公式方案](IDEA_PAPER_CN.md)的可测效率/安全改进为准，不要求先完成全域概率证书。

## 2026-11-05｜PHE首次真实冻结模型计算实验（非动态任务结果）

用户授权使用其他组场景/参数启动实验后，在go2-root-yuanyue新root完成A03真实MJB/原生源码三项独立CPU scope：1046私有FK、1004静态力LP、263263原geometry distance；0物理步/WM/Actor/API/Renderer。原父16/16账本未动，其他组模型/源码/账本未修改，未读保留结果。

实际Piper手端/COM Jacobian对数值微分最大误差1.3469e−10/7.0139e−11m/rad；三名义配置均有固定足锚点的重力静力见证，不等于真实接触或动态支撑。原Finish逆路点的参考代价5.603392/4.577544/4.151696s与简单收臂距离排序相反；私有模型中新路径有更低参考cost，但尚非在线模式/任务收益。原Finish默认时间参数与实际WM-v9 ProtectedStow不同，不将这些数字借给后续A/B。原始reports/输入SHA/协议/exit0在`evidence/2026-11-05/phe-a03-native-model-v1/`。

用户随后指定以老已通过方案做有无Reach对照。已选WM-v9/full-4（原7a6、source ae1c724d…、seed62271），旧任务通过但strict=False/单seed/原越限问题保留；AINav-v6老full-4为备选，不拿当前失败五箱冒成功。新fork A逐字节原541文件，B一处ProtectedStow挂点＋本组模块；12项source/模拟owner测试通过，未做完整host zero、未派A/B主回合。现阶段拟检验H-only同compact参考路径优化，非完整F7联合准备。草案和源差在`evidence/2026-11-05/phe-old-pass-ablation-plan-v1/`，效果仍unknown。

## 2026-11-05｜老成功WM-v9新A/B自身原生zero通过；主回合仍0

A/B原模型/任务/控制/硬门相同，除运行标识外协议逐项相同，原7a6权重SHA相同。各臂2744唯一原测试用例<strong>累计</strong>有实际通过证据：原2727项4个测试支持导入错误及更早发现错误均保留，补原版本测试文件上下文后51受影响用例实测通过，不是一次全量clean pass。

两臂各自新真实原生zero PASS：实际RGBD1帧、模型零步forecast1次、world0秒/物理步0/aux world0/API0，未借旧zero。原相机帧实时编码、ffprobe各1帧/128×192，无日志或状态重建；这些是零步材料，不是任务视频/研究episode。新A/B main根已冻结；截至19:09 actual main attempts0，无主回合报告，效果unknown。

当前缺本实验进程安全DeepSeek入口，未读其他进程env/扫key目录/复制他组凭据或进行API探针。source-scope资格显式是未变组件字节证明＋限定新方法源差＋own CPU/zero，不伪造新旧数据replay通过；原物理/模型/SDK/锁/终点门不放宽。首轮为H-only衔接路径对照，不是全F7；old baseline strict=False/单seed已曝光/旧越限保持。证据`evidence/2026-11-05/phe-old-pass-runtime-v2/`及其`当前准入与下一启动.md`。


## 2026-11-13 12:30｜AINav绝对摆放目标域CPU研究（非物理）

最新主线暂停研究WM，采用AINav既有目标路径。新增无WM目标需求评价模块，实际消费原catalogue/initial_stroke_facts/PlacementContract；14 current-source文件pin，8项公开蓝图目录全部保留，2项名义推程必要条件满足（0.78/0.74m），不计作成功样本。固定edge的原几何/完整枚举/顺序/联合仿射结果一致，当前目录单点；近邻目标在机械区间内仍不在目录。最终11新CPU测试通过，原先9不累加；无WM/Runtime/Actor/world/GPU/API/训练/物理，未重跑owner/旧实验。证据`evidence/2026-11-13/ainav-target-domain-v1/accepted-result.json`与主报告。完整host尚待AINav正式选定，不声称部署资格、动态安全或导航增益。


## 2026-11-13 13:05｜所选AINav完整v6的源绑定需求反像（CPU）

已消费正式release/原manifest与12必要原源，纠正当前五箱通路不在所选完整基线的版本边界。两个公开目标的数值箱位反像约[1.61,2.41)/[8.51,9.31)m；无当前独立观测界时UNKNOWN。联合基座入口/推程反像闭式交集已实现，7新数学边界测试通过、原pure judge/scalar4显式函数例一致，原12N支撑阈值保持；无WM/Runtime/Actor/world/API/物理，未重跑旧/owner套件。不是新成功样本、动态保证或方法增益。证据`evidence/2026-11-13/selected-ainav-v6-demand-v1/accepted-result.json`。


## 2026-11-13 13:17｜所选v6历史索引的新增阶段成本分析（非新物理）

只读消费Data已校验同源索引与AINav正式release，未重审原journal/GT或重演。原8意图/13原生窗口中5准备共53.620s、8interaction106.610s；两PUSH后继准备13.380/13.615s，native-start→后继准备末45.735/46.010s。query与独立Finish/Actor端点仍None，matched alternatives=0，不声称因果排名/方法省时。最终9新专项通过，开发8不累加，初SyntaxError日志保留；原输入SHA不变、fence空，0新模型/API/物理/样本。账本删项不是控制消融或收益。证据`evidence/2026-11-13/selected-v6-phase-cost-v1/accepted-result.json`。


## 2026-11-13 13:35｜原owner真实zero冷读PASS与新日志消费兼容

接收Data13:31原cold结果：passed=true，program0e0c4e01…匹配本机freeze，真实Runtime/Actor/CUDA/传感器原8字段，任务命令0/辅助约6.505sim/zero37.508wall。不是Reach重跑、PUSH成功或新研究样本；主运行此快照未见回执。新Data index缺历史manifest的实际兼容缺口已修，2新测试＋9受影响回归同11过，不累加新样本。尚无main journal，不称端到端部署过；新入口保留原bridge/reader SHA与source/closure UNKNOWN。用户已无成本限制自主安排，旧失败/安全门/在途freeze有限窗口保持。证据new-journal-cost-consumer-v1及autonomous-execution-authority-v1。


## 2026-11-13 14:19｜首新端真实API0地面PUSH/stow结果已消费

Data正式release8acfef17…：zero/main各1通过并closed，17137任务步/85.685sim，原9流检查过/收束0错，非完整导航/方法收益/新TEST。Reach实际消费3844行新journal（未重审大数组/重放）：原semantic query及两physical query SHA精确匹配，query35.190→原PUSH复合终点85.685=50.495s；NAV18.135、NN前11.355、NN后至compact16.995、验证4.000、两个间隙各.005。NN确认之后20.995s仍属退出/stow，不重复加。两个实际judge摘要及原最终placement合同重建匹配；实测XY7.364mm、dock约−.004295mm，不作误差保证/拟合。后继未执行，C_next/ready未知。下一fresh两请求PUSH→CLIMB工程协议已发布交owner，尚无采用/起跑回执；不作方法A/B。证据first-real-ground-result-analysis-v1/accepted-result.json，原owner scope不复开。


## 2026-11-13 14:47｜交接时最新实际结果/代码边界

Data14:38发布原PUSH→stow→准备NAV→20cm CLIMB实际PASS/cold/closed，21758步/108.790sim、1088帧、4option/8receipt，后继准备13.380s、stow→CLIMB终点23.105s，P1共同17137命令逐字同。Reach仅核正式release/子文件SHA和owner报告，尚未独立消费P2，不记为本组重算或方法A/B。scope全部closed、无任务待启动。新stow_path_choice.py只有130行未测核心，ast.parse过但未做单测/源hook/在线/物理；不记优化方法成功或论文贡献。完整交接prompt与WIP快照见evidence/2026-11-13/context-handoff-v1。
