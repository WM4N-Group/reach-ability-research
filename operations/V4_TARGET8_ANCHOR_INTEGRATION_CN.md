# 原WM实际anchor的target8计算已接；语义关联与现场因果流仍需source接入

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
