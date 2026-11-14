# 原像素component成员与当前公开框：不借private catalogue做对象pose

2026-11-14。P1本轮将此前“bbox有深度但没有mask”的缺口推进到**原appearance-component成员可复现＋当前public框精确对应**。不是新分割器、控制域、训练、物理运行或后继预测器。

## 1. 实际执行原算法，不另写HSV／连通域

`public_component_support.derive_original_component_support`直接调用原`visual_box_proposals.py`（SHA837e95ec…）及原`_hsv/_components/single_visible_hypothesis`。`_hsv/_components`只是原纯像素计算函数名，不读取任何private data。

- 所有原threshold/default/HUE_FAMILIES固定，原源文件和函数不patch，不按15ms赢家调参。实际NumPy1.26.4计算，RGB/depth/K/T前后逐byte未变。
- 原proposer输出不含mask，本实现再次调用同一原helper取得每个原component的YX像素集合；按原排序核family/bbox/pixel_count/valid_depth_count逐项一致，不以bbox填充、merge或largest代替component。
- 原`single_visible_hypothesis`对同family多片段/多实例和缺深度的拒绝保留；不能因为公开框“看起来像目标”而绕过原拒绝。
- 为每component给出像素成员/摘要和一个固定的实际有效成员ray。**它是集合中真实采样pixel，不把coordinate-wise visible median冒充物体中心或必然在某实体面上的点。**

`join_current_public_components`只按同一采集钟、图像身份、当前一对一bbox对应公开target_ref；不同/多对应/缺失都UNKNOWN，不解析label含义、不把颜色当box ID、角色、mass或成功先验，不读query-private/association/catalogue。

## 2. 两种RGB SHA不能混用

原proposer的RGB_sha256是decoded uint8 RGB像素bytes；原Observation.rgb.sha256是encoded PNG文件bytes。二者是不同域，不能拿相等/不等错判帧对应。

本实现分别保存并检查encoded file pin、decoded raw-pixel pin、原calibration pin及acquisition time。纯函数不能凭provenance字符串证明来源真实性；实际caller仍须建立同一真实packet/file关系。索引是frame-local，**不是跨frame／episode的实体tracking能力**。

## 3. 真实公开历史数据到哪一层

Data6921b24c…历史seen-DEV/audit-only包内，仅原84.430决策前可用的9query、15个公开框：

| 每支原query时刻 | 公开框面积 | 原component像素数 |
|---|---|---|
| 35.190 | 1120 / 4165 | 495 / 3191 |
| 53.330 | 5822 / 684 | 4010 / 340 |
| 84.430 | 6048 | 4088 |

15个公开框均精确对应当前原component；在本数据中不再需要猜mask。但这是**appearance-mask membership和公开框对应**，不等于完整物理object identity／点归属、中心/姿态、registered reference-relative pose或误差保证。新sidecar未修改原objects.geometry，那里仍unknown；没有把visible surface median/extent塞进center/size字段。

9条query的RGB/depth/calibration/time在三arm间形成3组完全相同的纯函数输入，仅运行3次原proposer并复用这3组确定性CPU结果，然后独立join各自当前public refs。这是相同输入的计算复用，**不是跨episode复用实体ID或三个独立科研样本**。未来READY三帧排除，数据未转ONLINE_PUBLIC、未fit/预测cost或选择阈值。

公开depth NPY同时与NumPy `allow_pickle=False`读法逐值核过（NaN明确相等），只涉及公开depth，**不**重审原command/torque NPZ、全部journal/hidden state。审计进程禁止network/child/Torch/MuJoCo/ONNX及executor-private文件，实际没有新capture/render/Actor/物理。

证据：`/home/yuanyue/main/work/ainav/manifests/public_component_membership_20261114_v1/ACTUAL_ORIGINAL_PIXEL_COMPONENTS_AND_PUBLIC_JOIN_AUDIT_ONLY_v1.json`。

## 4. 本机CPU依赖与测试边界

默认Python仍没有NumPy。仅在本组**不进版本库**的缓存
`/home/yuanyue/.cache/ainav-cpu-deps/numpy-1.26.4-cp312-20261114-v1/site-packages`
准备官方固定wheel，SHA675d61ff…；没有pip/apt/系统或他组环境修改、没有永久PYTHONPATH。运行时隔离`-I -B`显式加该路径，单线程CPU，图像解码用系统PIL10.2.0。

这是本机Python3.12.3/NumPy1.26.4/PIL10.2.0的原纯视觉算法计算，**不是Data的Python3.11.16/PIL11.3.0原生环境或远端frozenCPU资格**。没有完整Host/Runtime/Renderer/Actor构造、训练/WM模型或GPU调用。默认解释器无该依赖时新增测试明确skip，缓存中的资格执行是10项全过、0skip，不混报。

新10项component边界检查覆盖空洞bbox≠mask、实际成员ray、原多fragment/缺depth拒绝、多公开框对应、encoded/raw SHA、clock、输入不变/default不调及geometry不变。都是CPU定向fixture，不是额外科研seed。

## 5. 同时修正一个已识别的原调用接缝遗漏

检查原`CourseBindingResolver.observe`发现**physical_tick必须严格大于_last_physical_tick**。此前再观察软件端口未覆盖此约束；旧开发helper会先capture，再被原resolver拒绝。它不是Data失败或guard问题，旧测试/源/负例完整保留。

开发版`public_reobservation`现在封存resolver身份，并在任何capture前检查这个原条件；成功后确认resolver消费当前tick。不以step/HOLD/wait/reset或修改_last_physical_tick绕过。同tick已有完整query时直接拒绝，0capture/0issued/不消耗实际调用预算；不会反复采集到出现赢家。正常已fresh路径本来不请求它。

同一个physics-clock的“此前sensor packet”只有在resolver尚未消费该tick时才可作第一次query；这仍不增加时间状态信息。**不能把它误说成resolver允许同tick重复query。**

已有再观察suite复验11项通过，其中新增1条真实原resolver约束回归，另10项是既有回归，不是新增11项。原标量条件从冻结source提取执行，像素/数值publisher/传感/geometry仍明确software ports；未冒完整resolver/native构造资格。测试runner曾误拦原Host在临时软件目录写虚拟catalog的动作，已仅允许该临时目录的write-only fixture记录，仍禁止private输入读取；错误日志保留，无生产门放宽。

证据：`REOBSERVER_ORIGINAL_SAME_TICK_GATE_CORRECTION_v1.json`与`LOCAL_COMPONENT10_AND_REOBSERVER11_QUALIFICATION_v1.json`（本组同manifest目录）。

## 6. 下一最小能力缺口

本轮缩小了第一层缺口：可公开复现component成员，并与当前公开框精确对应；**没有解决**物理对象完整几何、注册任务reference相对状态及可信误差。下一应在公开语义/图像/标定/声明几何之间建立可核的reference约束，歧义和误差来源不足仍UNKNOWN；不能把已发布label的身份、声明size或相邻boolean自动当作完整当前pose。

继续复用Reach现有`visible_point`，传成员ray的明确`pixel_uv`/optical Z/原K/T及同钟来源，不另造投影/selector。即使未来有相对几何，完整后继cost/失败评价仍缺合格模型，不能用当前历史后果或UUID拟合、用field更名恢复WM/训练，或复跑closed三点。原12N/4s/stop/FIFO/完整v6、旧.2平台NAV→PUSH缺口和evaluation_ready=false/TEST0保持。
