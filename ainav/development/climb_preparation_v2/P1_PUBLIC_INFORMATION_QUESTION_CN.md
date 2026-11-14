# P0收束后下一问题：合法公开时间信息是否足以支持后继接管评价？

2026-11-14，按12:50长期计划的P0/P1推进。此处是开发问题与否证规则，**不派新scope，不复扫±4cm，不开放训练/fit/私有GT，不改变技能或门**。

## 1. Pilot结论已闭合

完整正式发布4de5ca66…/35成员已逐SHA消费，三支真实closed：original与plus成功，minus stop_deadline；不是“minus尚待执行”。运行原Reach `evaluate_serialized/describe_mechanism`，完整保失败分母，得到`STRICT_BUT_SUBTHRESHOLD_REVERSAL_RETAIN_RAW`：局部15ms、完整惩罚785ms，双100ms为false。失败成功成本None，21.920s仅失败端消耗；缺原failed receipt不补造。

Data六字段数组冷审确认三支至tick16886一致，原实际issued首分叉plus17603/minus17571；delayed/torque与q/dq随后分叉。说明不止目标改名，但不扩大为base/contact/Actor全部隐藏态相等。数组/完整journal本机未重审。所有原预算/失败/旧根、角色及原片保持。

minus诊断中的`machine.native_machine.preparation.metrics`属于**ClimbEntry对象字段**，不是已绑定到失败时刻的stop稳定gate全状态；没有这些metrics各自更新时钟/stop内部状态，不能用其较小速度/tilt断言“stop本应成功”或给Actor/contact归因。full READY不等完整成功这一边界仍在。

## 2. 只选择一个下一主要问题

**问题：在不增加控制域、不读私有未来结果的条件下，现有发布器的异时公开proprioception序列，相比单帧，能提供哪些可验证的接续运动信息；它仍缺什么才能支持前瞻成本/失败判别？**

变量是**输入的时间覆盖**，不是偏移量、seed、关节轨迹、成功容差或额外等待动作。候选池、native binder、任务/终点/控制权不变。研究终点不是“多一帧就成功”，而是给出信息来源可核、UNKNOWN明确的输入能力边界；真正预测/改善任务要另有已资格评价能力，不能凭窗口长度宣称。

## 3. 已实现的最小独立工作

`public_observation_window.summarize_public_window(observations)`直接接收现有`Observation.value`或其value字典，不新增Data日志合同/loader：

- 固定原45D：q18/dq18、projected_gravity_b3、root_ang_vel_b3、root_lin_vel_b3。速度在body frame，范数仅当前运动描述；不积分出世界pose，不假设gravity归一化或自行换成yaw/tilt。
- public proprio用原packet acquisition clock，不把query时间当新样本。原age上限.100001s保留；同camera clock重新发布不增加时间覆盖，同clock物理proprio变化拒绝。
- 只有不同acquisition clock才形成时间窗口；稀疏样本即便横跨4秒，也不证明原1s稳定＋3s verify连续通过。
- 明确拒绝generic schema虽允许但当前publisher并未接入的`localization`，以及foot force、controller latch/phase、GT pose或failure cost字段；这些不能作为自动fallback。
- 当前world XY/yaw、足载荷、native latch/hold、未来完成成本与成功概率保持None；函数不选择、不发命令、不训练、不能证明数据来源真实性或用途授权。

源级核查：`FullCourse.observe_public`调用原publisher时没有`current_public_proprio` override；原OnboardObserver的45D与camera packet是同次无step capture。该结论针对所选实际source，不是所有同名模块。9项本机隔离CPU通过，正向仅软件schema，不冒实际传感/远端/物理资格。

## 4. 同条件对照与停止规则

- **单帧对照**：同一合法公开窗口的最后一帧；**历史输入**：相同窗口内已有不同acquisition clock的原数据。两者共用同一候选、输入权限、评价预算、UNKNOWN/原default逻辑；不能只给历史方法额外私有字段或真实未来cost。
- 第一检查只比较合法字段/单位、真实时间覆盖、可解析的当前运动量和未解决信息项；不是预测准确率、优化收益或H1新样本。
- 没有合格动态评价器时，两者都不得输出完整cost/probability：仍原default或弃权。始终默认只能说明接口/信息检查完成，**方法待评价能力**，不能宣传部署优化。
- 发现GT/未来泄漏、时钟padding/回退、同clock矛盾即拒绝；缺记录就UNKNOWN。不为补记录重跑旧root，不换seed/δ追差异。
- 若时间历史仍不能辨别原stop相关状态，保留这项能力缺口，比较下一最小解析/观测能力或提出具体模型及数据用途授权；不私下拟合旧audit。这里未证明全部RGBD公开信息在理论上不可辨识，视觉定位/状态估计尚未实现/资格，不能把本小接口的缺口扩大为“不可能”。

## 5. 实际记录与最小解除动作

现有原Host已经写`main/query-observations/frame-*/observation.json`与calibration；本机正式35成员发布没有这些逐帧公开文件。若需回顾核上述字段的实际可用性，只消费owner已存在的这些文件及原SHA/clock，不要求Data生成新研究报告或新日志，不登录其服务器取代owner。旧数据只作回顾/可用性检查，不进入在线评价器、阈值选择、训练或fit。

开发的纯输入检查、稳定binder和Reach接缝已可继续使用；当前外部缺口是实际public记录可用性与经合法前瞻输入资格验证的后继评价能力，不再是“等三分支跑完”。在后者未解决前，**没有值得立即派发的新物理方法对比**；这不阻止P1接口、合法再观察/解析能力与基线继续开发。

## 13:18补充：公开原件已到，不再以缺文件阻塞

Data正式补交release6921b24c…/63成员、12条原query。实际检查确认全部publication==acquisition/45D完整；原84.430决策只可用前三帧，第四帧严格晚于决策。决策前最大间隔31.100s，不是连续历史。原coordinator正常已做fresh capture，故“只需额外刷新一张照片解决时效”对当前正常路径不成立，不据此安排新物理。

有界再观察的执行接缝已在开发版落地，默认off、原成功retired边界、每host一次、异常不重试/不step，10项原Host方法链＋Reach请求CPU接缝过（sensor/geometry明确软件port，非物理资格）。详见同目录`PUBLIC_REOBSERVATION_CN.md`。下一重点为合法相对几何/候选条件评价，不把同状态不同动作的后果差误判为理论不可预测；历史包不进入ONLINE_PUBLIC或fit。

## 13:54补充：下一相对几何层已有实现，但没有“升级”成对象pose

公开RGBD射线模块和有界深度归档reader已实现；实际解析/投影9条因果可用历史query的depth（非command NPZ），10项定向CPU过。原bbox没有逐像素component mask，当前schema的object center/size字段不能承载可见ray AABB；目标/参考pose和测量误差界仍None。下一最小缺口已定位为公开component membership、当前帧一对一对应及合格误差来源，而不是Data未采集或简单多拍。详见同目录`PUBLIC_RGBD_GEOMETRY_CN.md`，不派新物理或fit旧后果。

## 14:21后续开发

原pixel-only component成员及公开框对应已实际CPU复现，不再只拿bbox所有pixel当mask；同tick再观察的原resolver严格约束也已在capture前补齐。下一几何缺口继续收缩到物理对象/reference约束及可信误差，不因15个精确public对应就发布object pose或训练预测器。详见`PUBLIC_COMPONENT_SUPPORT_CN.md`，当前不申请新物理/重跑或fit授权。
