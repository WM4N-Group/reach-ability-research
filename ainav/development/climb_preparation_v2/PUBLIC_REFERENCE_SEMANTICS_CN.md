# 当前公开component → 已发布语义别名 → 声明CLIMB reference

2026-11-14。本轮只推进原public接口的**语义连接**，不宣称从视觉独立识别实体，更不估计reference-relative pose。

## 最小实现

`public_reference_semantics.link_public_CLIMB_reference`使用现有Observation.value、当前component sidecar和原requested reference，不新增Data schema或控制字段：

- 只支持当前原Host的`cuboid-N:upper-entry`声明，必须在public declared_map里有唯一原“Declared skill reference…CLIMB destination…”条目。
- 物体别名只接受原publisher已经明确给出的`cuboid-N; dimensions ...`前缀；不是按颜色、UUID内容、bbox距离或“包含某字符串”猜身份。该label原本由原publisher发布，本函数**不独立证明其物理对应正确**。
- 必须存在唯一对应的当前public target_ref及原component；精确核同一acquisition time/encoded RGB。component sidecar仅补齐已存在的encoded/raw RGB/calibration stamps，原数值derive函数AST不变。
- 初始蓝图/retired/fixed surface不替代CLIMB skill reference；多alias/multi-anchor/multi-support保持UNKNOWN，不挑最大/最近。
- `adjacent-boundary=True/False`和声明dimensions均不授予READY、支撑或成功，原native判断仍执行。

输出只包含当前成员ray与**声明**的reference坐标；物理object identity/point ownership、object world pose、robot world pose、reference-relative pose与测量误差均不认证/None。

## 一个必须显式拆开的“0”

原static map中`uncertainty_xyz_m=[0,0,0]`属于**声明蓝图/reference坐标**。它不等于当前物体位置、相机测量、tracking或NAV+arrival误差为0。新输出字段专名为`declared_reference_uncertainty_xyz_m`，而`measured_relative_pose_error_bound_m`仍None。不能因JSON里有0就制造安全/预测保证。

## 历史实际检查与资格

直接复用上轮已核的9条原component记录及其父记录中已存在的encoded/raw RGB、calibration、clock字段，不再执行原proposer或打开新传感帧。9条在其原query钟可语义连接到cuboid-2的声明upper-entry；包括adjacent-boundary=False的早期query，**故语义连接不等READY**。未使用初始蓝图当当前pose，未来READY第四帧没有倒灌，历史role保持audit-only，不调用在线模型/fit/物理。

7项新定向stdlib CPU、既有component10项带stamp回归分别本机隔离0fail/error/skip；不是17项新测试/两个物理端。没有native/remote资格或新后继预测器。

证据：
`/home/yuanyue/main/work/ainav/manifests/public_reference_semantics_20261114_v1/ACTUAL9_PUBLIC_ALIAS_TO_DECLARED_REFERENCE_NOT_POSE_v1.json`
与`LOCAL7_PUBLIC_REFERENCE_SEMANTICS_AND_COMPONENT10_REGRESSION_v1.json`。

下一缺口仍为**相机父body帧的可见几何如何约束物理对象/reference相对状态及可信误差**。声明world reference不能在缺合法robot localization/registration时直接与body ray相减；也不能因已发布alias就把visible median替代全物体中心。当前只能标输入/语义接口完成、几何/后继评价未资格，不宣传在线优化，不据此新开物理或重跑closed三点。
