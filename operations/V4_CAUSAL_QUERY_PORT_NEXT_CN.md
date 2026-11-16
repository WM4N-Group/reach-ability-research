# 原WM因果query producer已接成直接接口；现场callback资格尚未完成

2026-11-16（北京时间）。沿原V4五组/current100次API cap/20cm技能与三箱参数策略，未改用户平台、Actor或原门。

## 本轮新增实现

- `v4_causal_wm_query.py`把原**BehaviorQueryBuffer、filter_full_native、resize_packet**三段精确源码接入原7a6 loader/adapter。`inference_source/original_behavior7a6_query`按完整顶层定义原行逐byte提取，manifest含原whole-file SHA/行号与提取SHA；不导入原trainer或native-control模块，不改过滤/插值算法。
- `build_original_buffer`生产模式只收真实strict-restore7a6模型标记，连接原normalization和原source函数；`CausalWMQueryPort`可直接作为`OriginalBehaviorWMAdapter`的query_provider。source接原observer packet→`on_visual`，原accepted200Hz位置参考/实际owner→`on_issued`，provider按当前原public45D构造query，候选不能覆盖observed owner。
- target8必须由source的**WM实际anchor图/时间**提供并逐SHA匹配，不能拿fresh off-grid VLM图或旧left alias代填；无descriptor保None。生产只收原public IntentBatch/Observation，不允许private ExecutionBatch进入。原3真实10Hz图/连续200Hz窗口与尾部、previous-action一致性、当前body clock和image-age检查均保留。
- fixture模式强制输出`EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT`，不能因给“CURRENT”标签升级成live。原raw adapter仍先核source_role再做预测；closed-audit不能作为live provider。默认生产拒随机/FakeModel、FakeBuffer或错源。

## 验证的真实身份

- 本机新增10项源码/port/时钟/fixture隔离单元检查通过；合计**110项纯软件回归（72新增＋38旧）**。
- 另在46308私有现有环境做一次**明确SOFTWARE_FIXTURE**的原函数CPU smoke：调用原resize/Buffer/filter三函数，3个synthetic帧/43个synthetic位置参考跨40间隔＋3tail，原输入存档/clock均过，错误anchor与fixture→live升级均拒绝，临时数组已删除。用的是显式FixtureModel，不加载真实权重，不做真实WM预测/训练，不是实测轨迹或新的native资格。源函数全局SKILLS依赖在此完整接通，不能仅凭AST可编译就称producer已通。
- smoke原件仅小摘要`operations/V4_ORIGINAL_QUERY_PORT_CPU_SMOKE_20261116.json`；**此前真实7a6 CPU restore仍仅1次，未来预测forward0、真实当前V4 query0、Actor/world/API/fit0**，未为这个smoke再恢复模型。

## 新原件权限与source到件

- AINav新PUBLIC_EFFECTS/DECLARED_MAP/acceptance按本地owner文件manifest逐SHA接收为**开发快照，非immutable runtime/native freeze**。当前共27条公共语义声明：17 NAV/6 PUSH/4 CLIMB、24 anchors；完整cost与实际exit均None、prep/exit variants空。不能把source新文件到件当完整cost provider，Reach继续负责估计/模型，不要求Data代写评价器或“None补0”。快照见`protocols/2026-11-16/V4-public-source-intake-v1/`。
- 旧OBS正式包明确`whole_artifact_model_input_allowed=false`。本轮只读核了公开metadata/记录格式，**没有将其frames/history送入WM**；不能因为现WM获推理授权就改旧数据用途。未拿原closed OBS/A/B做新的WM prediction，也未把原audit当新TRAIN/CAL/VAL。
- source acceptance另要求E实际成功及A—D完整直接live原片，Data可在fresh容量/新authority下并行；不是当前E已经成功或允许Reach另建world/抢卡。当前40cm/static-deck/caller/完整terminal资格仍在AINav侧收敛，没有更改用户场景。

## 下一实际动作

AINav/Data新V4 caller可直接绑定上述两个callbacks与当前descriptor provider，source自己的必要zero/main核实际IO，不再等待本组另造schema或收件签字。Reach继续在相同public capability/效果边界实现共享完整名义cost，不从原WM terminal elapsed/logit伪造成功Finish/READY；PUSH绝对→公开relative action、CLIMB语义destination→原native SOURCE要有显式原binding。现场query/优化/native消费成立前不报有效五组对照。

收尾已核最新00:03计划34c169d5abfc7edc112ac0febd6e372052021d478c847e77c60050791fdd430b：新增独立V-JEPA候选研究不阻V4，当前7a6/五组不热换、不冒第六arm，旧用途不转新训练；Reach职责继续。

## 2026-11-16 07:50：共同NAV观察准备从泛提案收敛为一个固定公开目标和可消费代码（尚未采用/派发）

此前只建议“共同公开NAV prefix”，没有固定目标或可调用选择/回执逻辑。本轮给出单一、default-OFF的 `v4_common_nav_prelude.CommonNavObservationPrelude`，以及 `protocols/2026-11-16/V4-common-public-NAV-observation-prelude-v1/PROPOSAL.json`（SHA **7a28c1c2606d67e3ff44c8d4f2fb7f742de6fe3635dcc3a4b61d0366c462eacb**）。固定使用**现有五组公共目录** `v4-ground-nav-007` = NAV(.22,0,ground)，每arm最多一次，A—E完全相同、不挑view、不重试。该点取自早已公开的目录；我们已经见过DEV组件，**不冒结果前盲定或未见选择**，不读取私有实际approach/存在性路线、不改目标/布局/物体/Actor。

这只是一次共同工程观察准备：从capture后真NAV实际owner取得新的模型窗口，避免A/B必须先预测才能选择第一个modelled owner的启动依赖。它不是第一条A/B方法选择、不是VLM-only兜底，也不是本次优化贡献；VLM/WM/新selector在prefix中0调用，全部原执行/sensing/4s/收臂/wall/sim成本计各arm task0账本。只接受原同intent参数绑定NAV的`succeeded`原回执；admitted/started/READY、预测、布尔不当成功。失败/预算到期/拒绝都unavailable，不替换目标/重试。成功后要求新原public acquisition，但**不自行宣告WM ready**：原3帧/完整200Hz/实际owner/同96×64 anchor语义/真实forward仍必须齐，target8 None/mask0不放宽、不用closed v2帧。

### 源owner的最小接点（本组没有修改AINav/Data）

1. task0仍装真正arm method为host.planner、原legacy H/新treatment身份不变，E仍精确原RuleBaseline。辅助policy**没有`.enabled`治疗因子字段**，原factor gate不能误将它当B/D。
2. source ActualCoordinator可在首个方法query前，仅一次用该auxiliary policy走**原**IntentExecutionCoordinator→judge→factory→executor。原NAV complete receipt回到helper后，清理该intent，再把coordinator.model交回同一个已构造的真实arm method；不要替换host.planner/E类或让辅助prefix推进AINav树/规则placement。helper的`require_fresh_method_observation`核新观测后才开始真实method。
3. 原capture_grid实际packet、accepted200Hz reference及实际native owner仍须接原query port。PREPARE/PUSH意图不覆盖真正issued NAV，SupportedCapture仍不冒HOLD。first A/B select仍必须真WM预测，缺输入则明确method unavailable，不能绕成API0/首次VLM-only。C/D仍保原VLM/tree/replanning且不暗加WM；E不调用模型。

新增15项明确SOFTWARE测试本地/46308两端过，包括**真实原IntentExecutionCoordinator纯语义接口**的auxiliary→回执→fresh acquisition→同一arm-method交回测试；没有Runtime/Actor/physics/真实WM/API。不是15次NAV或native资格，旧74项本轮不刷。helper default OFF、源没有接，**当前main config只记录proposal，不改变现有执行协议或表示已排队**；AINav/Data可按现有流程技术集成，新准确程序自身资格，不加Reach签字/收件门。

当前source41 packageec62709d…逐成员SHA只读核过，parallel metadata guard候选属五组共同底座，不算B/D新贡献或实际吞吐改善；旧v1/v2仍closed。完整几何effects/cost/准备退出域、.40m/static deck/后续source链与真task终点资格仍未解决；这个小前缀不冒优化器或五组完成。

## 2026-11-16 09:22：新41源已到真正NAV succeeded，但fresh关联丢失；不是PUSH READY/WM-ready

Data新程序 **edb78627482c639a1edb78e28683108dc976bce882f32c135b874f54c09e38fc**（source2ab8b8ae…/41＋准确新freeze）已09:07关闭，不再依据旧README称“仅构建/在途”。直接原result **2c56de1c69e1f6915b985052b345a88081c5923d81fef5599bb17157335c039e**、ledger及Data关闭CAS proof核同；10份本地/远端原小metadata逐SHA核过，原journal **765行**完整hash-chain独立通过。此时只读消费的是原结果＋closed proof，尚未消费完整formal release/NPZ cold；没有把包裹未齐变运行门，也不冒独立流/动力学重算。

- 真capture：448命令/2.240sim完成；PUSH语义query当时原public observations接受一个cuboid_a当前关联。
- 真issued owner仍是地面**NAV准备**：2.245 started，**15.090原succeeded**；唯一admitted option即该NAV（nominal goal约.22,0），2570条后续命令、294次原NAV Actor forward，合计3018命令。该段first query→NAV成功约12.850s，但**不是PUSH READY准备成本**。
- 在同15.090的**新**原public observation，objects=[]；原judge按“Current original RGBD association unavailable; no old alias/static-pose substitute”拒绝PUSH。未派发PUSH interaction/CLIMB/动态箱NAV，没有这些技能的failed/succeeded receipt。PUSH_READY、所请求交互成功成本/CLIMB标签仍None，不能把NAV succeeded当后继已可用，也不能缓存2.240的旧alias/蓝图pose绕过门。
- 本次不是wall-censor：原resource_wall_censored=false，generic `COMPONENT_PREFLIGHT_FAILED_CLOSED_NO_RETRY`保留；2611.899700074wall、15.090task＋6.505aux sim、12,858,924bytes、known/close0。源码parallel guard属共同工程底座，不用与旧短截断不同长度run的比值冒匹配提速或B/D收益；Data guard14658次/947.257s与capture331.180/执行loop2178.076的区间重叠，不能相加；loop非纯Actor时间。

**对本组固定前缀的准确含义：** 新原NAV到了与proposal相同的nominal .22区域，说明在一个已曝光的、不同的API0工程probe里，NAV成功后合法fresh关联仍可能缺失；**不是本helper已执行/已证失败，不证明WM96×64没有任何可见目标，不证明整个任务不可行或C/E失败**。固定proposal与helper目标/参数/次数逐byte不改、仍default OFF/未采用；本次结果只作parent proposal的审计child说明，不为了追可见性换点或重跑。前缀只能解决modelled-owner/history的必要启动条件，绝不自签same-anchor语义或WM ready。其后的后继模型/退出域必须把合法fresh观测/关联可用性列为缺失条件；仅到几何点或省参考路程不构成完整可执行后继。当前这个条件的预测模型仍未实现，不能把此case查表灌进在线cost。

本组小摘要 `operations/V4_PARALLEL41_FRESH_ASSOCIATION_REJECTION_INTAKE_20261116.json` SHA **73d0d0e93e71a9b986d338c832eee8387daaf0720c67ccbdfeab1e6eba9a9db3**。没有读取RGBD帧/NPZ/MJB/权重，没有做模型调用/fit、像素/阈值扫描或重跑软件测试；没有获得本包新的WM/J训练用途。仅依据public metadata，不能断言“物体物理不可见”，当前只证原accepted association为空。source45新C/D胶水保持未实际方法资格，不把41结果倒贴45；五main/真实WM forward0，旧closed/失败/费用/dirty/布局授权全保。
