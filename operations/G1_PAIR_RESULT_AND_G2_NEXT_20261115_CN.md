# G1有限问题完成：同设备两条件真实闭合，前驱差异在首次PREPARE公开表征中没有完全归并（2026-11-15 01:42）

## 结论及准确退出

**left/right均在新46308同GPU1真实REQUESTED_API0_PASS并closed；实际不同的原生NAV前缀经同PUSH/stow后，在首次CLIMB PREPARE留下了不同45D/decoded RGBD与名义component测量。** 本次“是否被归并/是否只剩时间或UUID差”的有限问题已经回答，不再重跑这两支或扫mask/代表点。

这给出一个有真实caller/原生执行/公开非碰撞证据的**候选条件源**，可转G2数据准入设计；不是稳健/统计可辨、完整hidden-state、8独立条件族、critic可学性、候选优劣或优化收益证明。旧NEW_DATA_PROTOCOL里的qualified_entry_condition_family仍false，**旧8组4/2/2草案未改写为已通过**。G1当前有限测量完成，G2资料及总G1—G6研究验收没有因此完成。

## 实际链和成本

|条件|主episode sim|首次PREPARE|PREPARE→READY|PREPARE→请求成功终点|zero+main含aux sim|ledger wall|
|---|---:|---:|---:|---:|---:|---:|
|native_NAV_prefix_left|121.085|97.285|13.460|23.800|134.095|866.559200|
|native_NAV_prefix_right|109.865|86.580|13.485|23.285|122.875|754.196207|

- 两支各3个真实语义意图NAV/PUSH/CLIMB成功；left有5 native options/10 literal receipts，right4 options/8 receipts。原whole-far-bank任务成功未宣称。成功v2两scope合计256.970sim/1620.755407ledger wall，scope highwater各177091729/162614737bytes，跨独立scope合计339706466bytes；同scope的phase highwater不重复相加。
- left在前驱NAV后还执行一次PUSH entry NAV，right直接接PUSH，是此次原门实际消费的分支差异，不是两支同时故意删步骤。其后都走CLIMB准备NAV，成功终点均需原READY/stop。不同语义前缀goal的episode差11.220sim不能当某个优化器收益；本研究各condition只用original准备，没有同condition三候选counterfactual。
- left准备局部13.460、right13.485，完整后继23.800/23.285仅描述不同condition的同一original动作后果；**不套Stage-B同condition候选ranking/H1或双100ms结论**，不以此选action或调threshold。
- Data逐六字段原控制footprint报告首issued差tick7339/time36.695、延迟/torque tick7343，两支六字段bitwise同前缀7338步。本组消费其封存比较，不重算原command NPZ，不扩大为全部隐状态相同。

## 后果前固定信息测量（全部两条件保分母）

准确输入是actual Host intent-observation，按原journal CLIMB/preparation首bound事件/semantic SHA定位：left97.285sim/query4，right86.580sim/query3，均age0。已与Data正式组合release逐条物理Observation/钟对齐。不同query号源于左支多一次前置准备，不能硬用相同文件编号或_ready后帧。

|公开block|单位|不同通道数|max abs(right-left)|L2(right-left)|
|---|---|---:|---:|---:|
|q|rad|18|0.0434556007385|0.0635134154606|
|dq|rad/s|18|1.08017338789e-05|1.8635157605e-05|
|gravity|1|3|0.000250364348176|0.000250428703102|
|angular_velocity|rad/s|3|2.23578535952e-06|2.51513313791e-06|
|linear_velocity|m/s|3|1.78522307692e-06|1.81069934404e-06|

45D不是exact collision，尤其q最大差0.0434556rad；这不是误差校准或重复性证明，dq/角速度/线速度的微小差也不事后叫material。两者都是同一original candidate，前2action offset同0、采集age同0，路径/UUID/绝对钟/前缀标签/pending字符串没有参与差异判定。不同时间的静止关节状态可不同，不用世界pose/GT补输入。

原RGB decoded数值不同、depth按equal_nan逐数值比较不同；K与T_base_optical完全相同。非PNG编码/元数据hash差充测量变化。原未改proposer+component helper各对两个实际公开帧运行一次，沿唯一已发布cuboid-2 bbox对应原component，无largest/nearest/颜色猜身份/private关联：left4016/right4004像素，depth全有效、拒绝0。名义可见点median right-left XYZ为[+2.164,-7.361,+0.301]mm，L2=7.678mm。它不是object center/reference-relative pose或真实tracking误差；**bound仍None**，该样本人口原native matcher过滤条件保持。

## 来源/用途/失败账

原reader复用Journal.verify/Observation.create，并核Data cold实际result/journal SHA；comparison核exact公开query/image/depth/calibration bytes、原proposer837e95ec…与helper0b66cbf4…前后不变。禁torch/mujoco/网络/子进程/private catalog/association，forbidden=[]；没有新capture/渲染/世界/Actor/fit或读取GT/command NPZ。完整45D/逐通道差和帧数组仅远端/本地ignored小audit报告，Git只存代码和本摘要/scalar结果，不转TRAIN/ONLINE。

正式组合release v2 SHA77748185ec39a8bb4cc8a51945ba3e8ad5716ece4a0680e329957cd470276268，已逐声明metadata成员SHA核过；v1→v2只修说明文本的frame编号padding，原child/query/clock/Observation/结果未变，不计新实验。Data旧46174 administrative UNKNOWN的zero1/main1/最后费用及未知尾部、新端v1 zero FAILED_NO_RETRY/15.156688wall/usage_known=false全部另保，不因v2双PASS删账。

## 正在转G2：下一问题已给有限代码依据，不停在“2case都完成”

当前只有两个已曝光DEV条件，不能将帧/arm/新UUID/相同seed重复reset变为独立组，也不能喂旧8组训练器。本轮下一具体源gate：**另两个原full-v6已登记ground NAV引用center、upper-entry能否增加可用公开condition，达到至少4组最小分组原型的源基数？** 只提议两条新reference前缀，各一次，后面仍同PUSH/CLIMB original；原G1left/right不重跑。

精确请求/原constructor source pin、限额、拒绝与停止在`protocols/2026-11-15/G2-registered-source-cardinality-gate/`。这是新问题/新owned版本的待接线方案，不是G1两main余额或scope已分配，不把任意连续goal/API字段冒动态资格；AINav负责真实caller引用/参数，Data仍唯一owner/new freeze/自身zero/原lease/安全门。本次新增源gate数据仍DEV、不转fit。

源不足即物理前No-Go；两条结束仍不足condition组就报G2不可准入，不继续扩seed/offset凑8或派12/24main。若四condition源及组可用，再另定未来新用途cohort/统计与停止规则；最小2TRAIN/1CAL/1VAL只是有明显局限的四组原型设计选项，不是当前8组协议通过或部署证书，当前新TRAIN数据0/fit0。随后G3真实critic/常量均值基线/未见组→G4三策略→G5多决策/未见布局→G6可复现正负结论。

独立备选已完成G3指标代码与31软件检查，不继续刷夹具。长期目标未完成；原12N/4s/identity/immutable/guard/QP/FIFO/stop、Actor冻结/WM暂停/真机未开、dirty/closed/P0负弱结果/TEST0/主要贡献未证保持。
