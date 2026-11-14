# 公开RGBD：可见深度射线，不冒对象中心／reference-relative pose

2026-11-14。本轮实现 `public_rgbd_geometry.py`，继续P1合法相对几何方向。**不新增控制域、技能、native许可、训练/fit或物理实验**；冻结Stage-B及原三候选不改。

## 1. 当前实际接口能给什么

原公开记录有RGB、optical depth、camera K、T_base_optical及采集时钟，public对象有bbox/匿名target_ref。原`visual_box_proposals.py`本来就用`x+.5,y+.5`和optical Z回投，再乘T到相机父base frame；本模块保相同约定，不把Z当单位射线的欧氏距离。

原pixel-only proposer使用颜色连通域mask计算**visible_surface_median_base_xyz_m**，明确不是全物体中心/尺寸/世界pose。当前publisher公开的却是bbox与geometry unknown，**没有这个逐像素mask**。原private-native几何匹配器还会读取真实object/catalogue，它不能被拿来补公共planner状态。

因此本轮只交付可核的最小几何层：

- `backproject_pixel((x,y), depth_z_m, K, T, image_hw)`：验证zero-skew K、proper rigid T、pixel/range/type，输出该像素中心的**nominal observed ray intersection**，帧为提供的相机父base frame，不是world。
- `summarize_bbox_rays(depth_rows,bbox,K,T)`：按半开bbox筛像素中心，只统计区域内的有效深度射线、名义sample AABB及首个有效ray示例。**框内可能有背景/其他面**，不作object mask、不选择最大/最近对象、不把AABB当完整object extent。
- `read_recorded_depth_npy(path,expected_sha256,expected_hw)`：只支持本批实际NPY1.0、C-order `<f4`、HxWx1，显式SHA、尺寸/payload/头长度限制；无NumPy/pickle/eval。对象/结构dtype、Fortran、异端格式、错误shape/SHA、截断/尾随数据均拒绝。它是有界公开深度归档工具，不是通用数组加载平台。

所有输出固定保留：
`object_center_base_xyz_m=None`、`registered_reference_relative_pose=None`、`world_pose=None`、`validated_metric_error_bound_m=None`、native admission/prediction=false。

**误差边界没有被编造：** 目前没有合格的depth/calibration/membership误差界。名义投影数值和sample extrema不是概率/置信界、tracking slack或完整NAV+arrival保证；软件round-trip容差也不是物理测量界。校准/深度/目标/时钟必须由既有真实来源绑定，纯函数不能证明来源或数据用途许可。

## 2. 已有真实公开记录上的回顾检查

复用Data6921b24c…历史包及已核索引，不修改原路径/字节，也不打开任何`query-private/association.json`或catalogue。

- 只处理原84.430决策可用的前三次query×三支，共**9个depth grid／15个public bbox区域**；三个未来READY帧明确排除。
- 逐depth SHA/shape、RGB SHA、calibration与query acquisition clock绑定后，实际读取**公开depth NPY**并执行射线算术。**不是原command/torque NPZ重审，也不是运行原NumPy视觉proposer/重建mask/调用private matcher。**
- 每支三次query的有效区域像素分别为`1120+4165`、`5822+684`、`6048`。这些像素均在原深度有效区间，并不证明全部属于目标。
- 结果仅为历史字段/几何接口可用性回顾，整包仍HISTORICAL_SEEN_DEV_AUDIT_ONLY。没有转换为ONLINE_PUBLIC、拟合、预测成绩、新场景或物理样本。

证据：`/home/yuanyue/main/work/ainav/manifests/public_rgbd_visible_rays_20261114_v1/ACTUAL_PUBLIC_DEPTH_NOMINAL_RAYS_NO_OBJECT_POSE_v1.json`。

## 3. CPU资格

新10项本机隔离CPU过：半像素/optical-Z、实际mount形式round-trip、半开bbox、无有效深度UNKNOWN、proper rotation/type/range拒绝、原source公式、归档SHA/shape/order/dtype/执行表达式拒绝。禁NumPy/PIL/Torch/MuJoCo/ONNX/network/child为空；未做远端/Renderer/Actor/物理资格，未改变系统环境。当前本机没有NumPy（PIL存在但本实现未使用），原完整视觉proposer并未执行；不能把本纯算术结果冒为它的重算。

`/home/yuanyue/main/work/ainav/manifests/public_rgbd_visible_rays_20261114_v1/LOCAL10_PUBLIC_RAY_AND_SAFE_DEPTH_CPU_v1.json`。

## 4. 已定位的最小语义缺口与下一步

**bbox+depth足以得到名义ray，不足以认证注册reference-relative pose。** 下一工作不是再拍/调δ，而是依次落实：

1. **公开point/component membership**：优先复用原pixel-only proposer，不能以bbox所有像素替代mask。若需要暴露visible samples/descriptor，应是独立的可见表面语义，不是物体中心。
2. **当前帧的public对应关系**：把可见component和已公开target_ref以可审计的一对一证据连接；缺失/多component/多对应保持UNKNOWN，不能用private catalogue、颜色→角色、largest或nearest兜底。
3. **reference与误差来源**：只有合法图像/注册几何对应、时钟及误差资格明确后，才能讨论相对reference位姿；单个可见面并不确定全物体中心、yaw或机器人world pose。

当前`objects[].geometry`只接受center_xyz_m/size_xyz_m及对应uncertainty；把visible-ray AABB/median塞进去会偷换成全物体几何，因此**没有填这个字段**。如下一版确需提供visible-surface特征，先明确最小字段/输入版本与consumer解释，不热改closed包，不经Data另造平台。

即使未来具备相对几何，也仍不是完整接管/stop成本或成功概率；既有Reach预测缺口保UNKNOWN/default/弃权。旧数据只用于回顾/问题定界，不fit或按赢家调参数。原12N/4s/stop/guards/FIFO和任务成功区不动，旧.2平台NAV→PUSH缺口不因本投影宣称修复。

## 14:02与Reach现有API直接对齐（避免再发展一套规划几何）

Reach并行交付了`public_depth_geometry.visible_point`。它接收**已标定的连续pixel_uv**，不会暗加半像素；本组核的是当前原proposal从整数数组索引到该坐标的约定`(x+.5,y+.5)`。两者没有相互替换语义：正常方法侧直接复用Reach API，AINav这份小算术保留作原source对齐／有界公开归档及bbox区域诊断，不另建selector/evaluator。

3项直接接缝检查通过，并用已固定的original第三query首个有效region ray做一次历史数值对齐，body坐标差<1e-14m（软件算术比较，**不是物理误差界**）。直接把数组索引当pixel_uv是另一种输入约定，会得到不同名义点；这不代表Reach通用函数错误，也不代表已独立证明真实sensor pixel-center alignment。两侧仍保object/reference pose与测量误差UNKNOWN，历史输入保持AUDIT_ONLY。

证据：`EXISTING_REACH_PROJECTOR_SOURCE_CONVENTION_INTEROP_v1.json`与`Reach-interop3.*`，均在本组上述manifest目录；没有改Reach源。

## 14:21原component层补充

已在本组独立缓存用NumPy1.26.4实际执行原pixel-only proposer/helper，15个历史公开框可精确对应到原appearance component成员（例如84.430框6048 pixel、原component4088 pixel）。此前“仅bbox没有mask”的输入缺口在开发计算层缩小，尚不等于完整物理object membership/center/reference pose或误差资格。默认解释器/原source不改，仍不调用private matcher。详见`PUBLIC_COMPONENT_SUPPORT_CN.md`；本节早先“未执行原NumPy proposer”保为当时历史边界，不能借本轮资格回填旧记录。
