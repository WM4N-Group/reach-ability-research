# 原WM实际anchor的target8计算已接；语义关联与现场因果流仍需source接入

## 2026-11-16 12:25 增量：af09/v2已closed；当前原关联成功不等WM anchor资格

新palette的该root原NAV在15.090s succeeded，fresh原192×128 query仍有cuboid_a关联，原entry judge READY；随后PUSH构造读取Runtime.staircase缺失而失败，尚无PUSH owner安装/命令/terminal。故不再称本scope在途；同时不能将其当source53/完整方法/96×64 anchor资格。query public geometry仍unknown，不从private judge base pose或closed图片补online reference/target8。entry谓词端点12.850s已观测，native-owner READY/成功成本未知；完整原件与770行链直接核过，见`operations/V4_PALETTE_V2_ENTRY_READY_CONSTRUCTOR_FAILURE_INTAKE_20261116.json`。原fixed prefix/producer/default开关及source53proposal不改，旧root不重开，原ABI应由AINav在新源修复、Data新程序资格。


## 2026-11-16 11:54 增量：source53已接本proposal的共同map；af09新asset仅静态delta资格

AINav source53 `530dfeae69873d854481669bc4c84bf6e3fd0dd2`已将固定增强map `802d3651187052d46c4006717d21fd27f21a2fde61ecc7e93a857197dd894cb6`接入默认OFF的`shared_appearance_public.build_shared_appearance_declaration`，driver可选`shared_appearance=`使observe_public/intent_catalogue消费同一typed context。下方“未源采用”历史应拆分为：**源码软件接收已完成；当前物理程序与五方法运行均未采用**。27 anchors原几何/不确定度/顺序与12 subject关系不变；不改本组原proposal bytes/producer默认开关或原视觉门。

Data af09/v2 `aecec6eb…`实际新asset `a8911921…`的398项nonRGBA一致/三RGBA行变化已获静态子交付，release `8bcc837e…`/6成员已独立核；本组未读MJB/帧或运行producer。当前在途af09保持原样，不能热换为53或为新map重跑；此子证据不等实际渲染分色、fresh关联、WM bootstrap/forward或完整任务资格。未来新五方法在原cold组件0步绑定同asset/map，才把`common.public_map()`作为本association的公开先验；仍需所有已有现场因果输入和原gate。见`operations/V4_PALETTE_V2_STATIC_ASSET_AND_SOURCE53_INTAKE_20261116.json`。


2026-11-16。此增量是V4原WM必要输入的实现，不是新预测器、后继cost、native资格或优化收益。

## 修掉的实际缺口

此前query port只收外部target8数值；现在`v4_anchor_target8.AnchorTarget8Provider`实际复用原`propose_visual_candidates`/`describe_visible_goal`/`front_plane`/`geometry_vector`，从**原Buffer已resize的96×64当前anchor RGBD＋相机标定**计算8维可见前平面描述。不是192×128 onboard原图，也不是1280×720第三视角或另时刻VLM off-grid图。

两份原几何完整文件和一段原geometry_vector顶层函数逐byte保管于`inference_source/original_behavior7a6_geometry/`，manifest记录原路径/whole-file SHA/行范围/保管SHA；loader硬pin实际代码，不导入原trainer、native、Torch或WM。原visual import仅用private namespace解析，算法不改/不覆盖已有ambient visual_box_proposals；相同原函数可供多个producer复用，不新增“每process只准一个方法”门。

## 可直接接原query port，不另起执行器

```python
from research.task_conditioned_reachability.execution_preparation.v4_anchor_target8 import AnchorTarget8Provider
from research.task_conditioned_reachability.execution_preparation.v4_causal_wm_query import CausalWMQueryPort

# model/buffer由新程序按原方法恢复一次；这里不恢复模型、不重建world。
targets = AnchorTarget8Provider(
    geometry_source_root=code_root / 'inference_source/original_behavior7a6_geometry',
    association_provider=current_public_association_on_WM_anchor,
)
query_provider = CausalWMQueryPort(
    original_behavior_buffer,
    role='CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY',
    target_provider=targets,
)
# 原10Hz真实packet -> query_provider.on_visual(packet)
# 原accepted200Hz位置参考/真实owner -> query_provider.on_issued(...)
# 当前原public IntentBatch -> OriginalBehaviorWMAdapter.evaluate(batch)
```

Source的`current_public_association_on_WM_anchor(observation, options, anchor)`只需交实际合法公共语义候选在**同一WM anchor**上的`frame_local_ref`（或None），不需要代写几何、WM或研究cost。返回格式：

```text
WM_anchor_RGB_bytes_sha256: sha256(anchor.rgb.tobytes())
WM_anchor_time_s: anchor.time_s
WM_anchor_calibration_sha256: original visual_calibration_sha(anchor.K, anchor.T)
frame_local_ref_by_option_sha256:
  exact option.sha256: {frame_local_ref: current original visual ref, declared_standoff_m: original bounded diagnostic quantity} | None
```

- ref是该96×64图上重算出的frame-local ref，不能转抄192×128/raw、fresh off-grid VLM或旧OBS left alias；图像hash、time与calibration逐值核。`declared_standoff_m`只作原可见plane proof的诊断参数，**不是新增native standoff可控自由度**；geometry_vector仍原公式。
- 没有关联、缺深度、同色多片/实例歧义、原plane拒绝：结果None＋UNKNOWN，不能挑最大块/填有效zeros/用旧初始位姿补。可见平面也不是箱体完整中心、世界pose、质量、native target绑定或支撑成功。
- **NAV公共路标不会被本模块凭空关联为可见箱面。** 若source没有合法对应视觉目标，保None，A/B仍可能无合格raw结果；不得用“已写target8类/打开WM”冒方法成立。
- 原BehaviorM底层确实接受mask0（原训练geometry_vector(None)返回显式masked8），但当前V4方法选择继续对mask0/缺target弃权；**本次没有利用这一事实放宽方法域或用合法零掩码掩盖未知**。如未来要定义nonvisual-waypoint/masked-target推理，是另一个显式事前方法域决定，不在本增量偷偷改。
- producer给callback只读来源的像素/标定副本，前后hash守恒；fixture producer/输出不能被生产query port升格live。query port传递同候选的visible proof hash；原raw WM输出记录同时保实际target8/action11/预测duration，方便核真实输入，不把raw native-event响应改成成功Finish/READY/整链成本。

## 验证与真实完成度

- 13项新增metadata/source/来源隔离检查，连10个原query＋41个原V4方法共64项软件回归。真实原source NumPy一次CPU smoke（0.4467wall）在46308：显式synthetic96×64单前平面得到`[1,0,0,2,2,0,1,1]`；缺关联/无深度/同色歧义仍None，错anchor拒绝、原数组未改、private module不覆盖ambient module。**不是传感器样本/模型forward/任务输入**，无Torch/native/API/child导入，数组仅RAM，不装环境。
- 小报告`operations/V4_ORIGINAL_TARGET8_GEOMETRY_CPU_SMOKE_20261116.json`，SHA **d0ac33cca53d5c65d627f22d6bebdec4181df802996aed0603d194d37320ff84**；原件留`/mnt/yuanyue/reach-runs/V4-anchor-target8-original-functions-CPU-20261116-v1/ORIGINAL_GEOMETRY_CPU_SMOKE.json`。当前真实原7a6 restore仍1，现场query/forward仍0；未拿OBS/bulk/组件zero单帧补3帧/40步history，数据用途不变。
- AINav新eafc8c5b…/23-source的destination binder/选中task factory已读：保持public destination和原native option hash；这是软件接缝，不是本模块可读取private witness source-height/pose的许可，也不是完整driver/observer资格。原component zero是04f/19-source、已closed，不借给新23-source或重跑。
- 最新总计划0e9f872b…仅新增J组具体权重许可/版本核定说明；不热换当前7a6/五组，不扩bulk用途。平台.20→.60与static deck/owner/真实terminal、完整cost provider/准备退出域仍未闭合。用户布局决定未回，不擅改三箱/平台/原门，也不把本输入实现当准备路径优化器完成。

## 2026-11-16 02:43：真capture已过，但首次WM决策有bootstrap依赖；不把capture编码成原HOLD

Data新**25-source/475-member**程序f1991adb…已真实完成SupportedCapture448条命令/2.240任务sim＋同world/FIFO原execution装配，scope已closed；release1254bb36…/result00768cd9…。Reach只读核16发布metadata＋20 sealed远端成员SHA与452行原journal全链，不decode NPZ或调用模型；精确小记录在`operations/V4_ACTUAL_CAPTURE_EXECUTION_INTAKE_20261116.json`，SHA **5b7810c39650ff66d2968ba9272e0770e6aacf1f5706924bf2c44d7c91b49c7f**。原23 onboard帧不是WM用途输入许可（whole_artifact_model_input_allowed=false），不从中造history/forward。原19-source cold zero仍单独closed；这两个component均非五组main，也不能借给新27-source full driver。

**首次A/B不能仅凭“有448条命令/23图”就宣称可开始。** SupportedCapture是实际ground owner，但当前V4尚未核定其到原6类observed-family的合法编码，不能自动归入HOLD/NAV/RECOVER，也不等原FarBankStop。现A/B第一select就要求实际WM预测；若一开始只发capture、随后直接进该select，仍缺合法的已发模型技能上下文。此处是源码输入依赖，不是已观察到A/B native失败；不能偷改首次A/B为VLM-only，或改成HOLD伪造过去。

新增`CausalWMQueryPort.on_unmodelled_issued(tick,time_s,native_owner_id=...,owner_kind='SupportedCapture')`供**实际accepted-step**调用：只撤销模型窗口/旧observed_skill，不动world/FIFO/原recorder/已落盘query。unsupported期间的grid帧不进模型窗口；同一已排除owner ID不能改名HOLD/NAV/RECOVER。真正新控制owner按原on_issued输入之后，必须积累3张**新**真实10Hz帧和完整原200Hz区间，仍由原build核history、clock、previous-action等；未齐抛`WMContextUnavailable`，不作native failed或成功代价0。8个新增metadata专项（连此前64共72）不使用本次真实capture流作模型输入，未再次运行原Torch/NumPy smoke或恢复权重。

### 对AINav新live_driver的最短接法（仍由source owner改其代码）

1. **grid而非任意planning图：** 原`NavPilot.capture_grid`只在`tick%20==0`且未重复时调用observer/append_visual。就在同一packet的原记录后交`port.on_visual(packet)`；不要将`observe_public()`额外off-grid拍摄写进10Hz窗口，也不为WM另建renderer/world。
2. **accepted而非意图：** 原`CourseGuardsAndWriter._write_command`在实际step后记录`issued`，并设置`_last_issued=issued[0].copy()`。port输入的native18 position就是这个实际accepted的`issued[0]`，**不是delayed FIFO/PD应用后的ref、VLM候选或将来动作**。同原physical_tick/time；实际SupportedCapture时用on_unmodelled_issued，其他已真正发出动作的原6类owner用on_issued。
3. **实际native动作族与稳定owner：** CLIMB意图的PREPARE可能真正执行NAV，必须编码NAV而非CLIMB；owner ID来自实际原controller/session（含必要exit子owner），不取尚未执行的意图hash。原native身份与same-params检查不改。
4. **仍需同anchor公共语义关联：** 新driver的192×128当前alias不能直接抄成96×64 WM anchor ref。用同原packet/变换来源证明建立公共semantic/landmark与该anchor frame-local ref的一对一关系；缺失保持None，不能传private body pose来补。非视觉NAV路标不凭空有箱面；A/B raw适用域必须真实可用。

### 首次合法上下文的共同前缀：仅提议，未执行/未改协议

建议AINav/研究在**五组共同初态协议**中事前固定一个必要的公开原NAV观察准备（从共同27目录选择；具体目标/次数由其在结果前冻结），五组都先取得真实NAV原回执，并计入从task t0开始的全部时间/费用/完整原片；A/B接真实NAV已发history，C/D仍保原AINav所有能力，E仍零VLM/WM/优化。准备动作不是方法决策或正确完整路线，不能据其结果调五组策略/选赢家，也不能只给A/B独占prefix。

**这只是用于消除bootstrap依赖的共享方案，不是本组新派发/新权限或已采纳的条件。** 本轮未硬编码/执行某条NAV、未改五组协议或场景、未让Data运行新scope、未借448条closed capture做WM输入；若未来采纳，要在新full program精确freeze/必要own-zero/lease里验证，不重开任何closed组件。若不采用共同prefix，必须显式解决其他合法的原模型观测编码/启动方案，不能暗中丢掉A/B的WM要求。平台.20→.60/static deck/动态箱NAV与完整后继cost仍独立未解决。

## 2026-11-16 10:46：补足一个具体same-anchor关联producer，但只限未来共同新外观/共同公开先验

source47新增实际writer→本组CausalWMQueryPort桥接代码，端口/Raw adapter SHA与本组一致；仍未native采用，不等首query/WM已通。source50又明确：原native compiler三箱全brown，而review palette未被原资产消费；新appearance_entry是**未来三行RGBA-only共同资产修订候选**，不是重着色旧root或旧brown run已具新色。Native端192×128两个warm component的诊断不等WM96×64结果，更不能把64px阈值调小/选最大块。本组补的是这个新条件下缺失的**公开先验→当前WM anchor appearance hypothesis**，不是新detector或Native ID证书。

### 已实现的具体代码与边界

- 新`v4_declared_palette_association.DeclaredPaletteAnchorAssociation`，默认OFF。仅在Data新准确程序明确选定新appearance revision、新MJB SHA以及原appearance compiler的`common_appearance_revision`证明后才可enable；核revision/contract/MJB一致、geom_rgba仅三box行、nonRGBA摘要/engine/topology不变等**metadata**。本类不读MjModel、不证明文件真实或实际render；Data仍须核实际compiler proof与真正载入模型绑定、必要新render/native资格，不能手填SHA当批准。旧0b3547…brown MJB与无proof均拒。
- **不让A/B独占语义/几何答案：** proposal给`PROPOSED_COMMON_PUBLIC_MAP.json`及`PROPOSED_COMMON_CONDITIONING_RELATIONS.json`；必须由source在所有五组**同一public observation**发布后才可enable。A/B只有私下constructor字典而当前Observation仍旧map时明确拒绝。公开内容是已有review hex的scene-specific A/warm、B/green、C/violet先验，以及原2.4m箱长/固定.58声明算术对应的12个box approach/top NAV subject关系；保“INITIAL不是live pose”，generic8个NAV不当箱面。未来五组必须冻结同一新asset/先验；不能把旧brown条件与新色当同环境比较或归因B/D。
- 仅在原96×64实际anchor上调用**原propose_visual_candidates**；所有同family兄弟（包括深度不合格者）照数，唯一且depth valid才给frame-local hypothesis，不挑最大/合并/降64门。当前frame缺失/两碎片/背景同family/clock/K/RGB不符均UNKNOWN或拒绝；不取off-grid query bbox/旧alias/private current pose/物理ID，也不把颜色映射mass/成功率。
- NAV subject只是**声明条件对象**，不是“waypoint就是平面”或“箱当前就在initial/goal”；对其选中的当前visible component仍经原`describe_visible_goal`/front_plane/geometry_vector，原plane拒绝优先于先验。`.58`只为原几何proof诊断参数，不更改Native approach/目标或产生准备自由度。target8 mask0弃权保持，PUSH absolute→relative和CLIMB approach action11仍未支持，不因有subject就补出来。
- 输出明确`SHARED_DECLARED_APPEARANCE_HYPOTHESIS_NOT_NATIVE_IDENTITY`、`semantic_identity_verified=false`与声明subject/证据ref；由现Raw adapter原有target8-evidence字段进入VLM payload。**单一颜色component仍可能是背景/错误对象，假设不是物理ID验证**；不能据此直接派发PUSH或覆盖原current RGBD gate。8维数值只是真当前visible plane，原模型输入/权重未改，新palette上的预测准确性也未建立。原安全/identity/immutable/12N/4s/FF/QP/FIFO/CLIMB stop全部保。

### Source/owner未来如何接（本轮没有替其改代码/运行）

1. source/Data显式采用并资格新的RGBA-only资产，公开同一增强map给A—E；核实际new-model proof，不沿旧default brown native_entry盲重跑。新MJB/appearance是新的共同环境条件，不消耗/修改旧closed root。
2. 构造真实arm/driver后，在task0、空WM history/forward0时，用**同一个FactorJournal**构造本association；`selected_asset_evidence=asset_result['common_appearance_revision']`，active revision/MJB来自真实已选asset。把它作为`AnchorTarget8Provider(geometry_source_root=.../inference_source/original_behavior7a6_geometry, association_provider=...)`，在首次query前给同一个CausalWMQueryPort.target_provider；source47流桥仍负责真grid/accepted owner。不得以本组件替换真arm planner或Native binder。
3. 已固定共同NAV prefix(.22,0)proposal逐byte不改，仍未源采用；真实modelled-owner/3新grid/完整200Hz history仍必须先齐，不能拿SupportedCapture冒HOLD/NAV。source新外观也可能仍碎片/遮挡/plane拒绝，第一A/B必须确有合格真实WM预测才算身份；不降为VLM-only、不用closed帧或假有效zero target8。

新增**20项**metadata/公开映射/错asset-proof/独占先验拒绝/fixture隔离专项，连受影响原anchor13项=**33项纯软件本地/46308两端过**；初次fixture缺观察时钟已修fixture，未松原clock。没有再跑原74/15/11套件，没有模型restore/forward、真实图像/NPZ/Native编译/render/Actor/physics/API/fit；原single-visible、plane/geometry三源字节未变。额外修复parent拒绝fixture association被装进production，并给当前call的可选证据ref/明确hypothesis范围，不通过旧class属性拿stale证据。

proposal `protocols/2026-11-16/V4-declared-palette-WM-association-proposal-v1/PROPOSAL.json` SHA **b9e586c44e9984390eb979f34f4880398705258a54e5c2e78918729634495544**；3份source公共文件仅字节保管，增强map/relations为**尚未采用**的共同公开先验建议。当前main config只登记候选，不启用，不把producer字段数/测试当完整WM或优化器；完整public nominal effects/cost/准备退出域与.40m/static deck/后续owner/真实task资格仍未完成。formal41 release4d8029de…18小成员SHA已补核，与既有2c56de1c…/765行结论相同，未重提journal/帧或训练。总计划be3aa7e5…不变，全部dirty/closed/用途和原模型/CAL/VAL保留。
