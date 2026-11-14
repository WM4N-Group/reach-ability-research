# full-2左支实际闭合及同left前缀跨layout公开测量（2026-11-15 03:17）

## 实际执行，不冒方法/全任务收益

full-2 left程序6ee69a5f…在原门下exact3 NAV→PUSH/stow→CLIMB真实REQUESTED_API0_PASS，02:52:45 CAS closed，Data cold全过。episode118.99999999996426sim；actual first PREPARE95.605/query4，原READY边界108.980，PREPARE→READY13.375、至请求成功终点23.395sim。zero+main含各aux总132.010sim，最终ledger836.637653wall，scope highwater174466192bytes。采用closed ledger，不用较早result/raw stdout进行中wall；不同scene/目标与旧full-4的121.085s不作优化快慢对照，whole-far-bank成功仍未声明。

原full-2公开目标PUSH(2.3,-1.9,0)与原NAV left_y=-1.75/CLIMB .2保持；这次是完整原registered case变化，不是纯lane单因素因果。两scope main上限原样，left已消费不重跑。

## 已消费三格中的新一格：full4-left vsfull2-left

继承事前四格协议，本次只测完成的同left前缀两layout。first PREPARE仍通过原journal/Observation semantic SHA定位，不套同query编号/绝对时钟；full-4 left97.285、full-2 left95.605均age0。Data正式left原件release SHA **3b5e9a9fd20971faa45fca7e53a0385118270bb607f67944fd04a7a49429b2c5**已逐声明成员SHA核过；证据/公开数据不入模型。

| 45D block | 单位 | max abs(full2−full4) | L2(full2−full4) |
|---|---|---:|---:|
|q|rad|0.184519648552|0.274952328894|
|dq|rad/s|2.89403396891e-05|5.91277979549e-05|
|gravity|1|0.000806393945822|0.000868430204313|
|angular_velocity|rad/s|6.9416473707e-06|8.56245976008e-06|
|linear_velocity|m/s|4.36039590568e-06|4.78717337344e-06|

- 本对照45D五块均不同，q max0.184519649rad；decoded RGB/depth数值不同，K/T相同。路径/ID/时钟/PNG编码差未参与判定。
- 原component支持：full-4 left4016、full-2 left4461像素，均有效depth/唯一公开alias join。coordinatewise可见点median nominal差full2−full4=[+11.130,+124.861,−10.342]mm，L2=**125.781mm**；不是WORLD运动、object center/reference pose、误差/追踪精度或置信界。该变化可能混合case/ego状态/可见面，不能归因单一几何参数；bound仍None，native-filter条件人口保持。
- 这只是同prefix的一个跨layout DEV pair、可观察非碰撞正证据，不是稳健可辨/独立性/分类或time predictor验证，未得到candidate三动作counterfactual或在线收益。没有按新数据挑mask/代表点/阈值。

## 不重复G1计算，数据留远端

`operations/measure_full2_left_crosslayout.py`复用已冻结且SHA固定的full-4组件结果，逐原query/RGB/depth/calibration及算法pin核合；**旧proposer重跑0次、新full-2帧原proposer仅1次**。原proposer837e95ec…/helper0b66cbf4…不改，输入/source bytes前后相同。raw数组逐值比较在46308完成，NaN按既有语义；禁止private catalog/association、torch/mujoco/网络/子进程，forbidden=[]。无新采集/renderer/Actor/世界/物理/fit，未重审command NPZ或用GT。

原45D/逐通道差/原像素只远端及本地ignored小audit文件，不入Git/不转TRAIN；云端仅代码、本标量摘要和来源pins。首次公开读取仍用既有read_G1_public_boundary.py，没有加新Data logger/消费回执门。

## 未完成格与接续

本次已消费full-4 left/right+full-2 left三格，full-2 right尚无本组已消费终态；其自身zero/cold已通过，02:54:49唯一main已派发，不重发/不提前填结果。四格齐后复用冻结三格计算，只对新right帧作一次原组件运算，再完成full-2内部pair与匹配right跨layout比较；direct READY/失败/拒绝/缺测保全部分母。

正在G2 source/信息资格，原门PASS和输入差异不等完整训练族。full-2若完整有效也仅第二任务scene，第三个相关source scene/新用途/whole-scene映射/样本功效与停止规则仍未齐，TRAIN行0/fit0。calibration/validation不能按同scene的prefix/arm/新ID/reset伪拆；不能让G1/G2 DEV变fit。未来真正新cohort才G3 critic及常量/均值基线，再G4—G6；本批不以“全部跑完”收工，也不以缺第三scene阻当前最小gate。

旧失联UNKNOWN与已耗zero/main、新v1 XML失败/未知usage账不洗掉，旧端停止追踪；Data唯一物理owner，Actor冻结/12N/4s/identity/immutable/guard/QP/FIFO/stop、旧audit/GT不fit/WM-DINO-真机不恢复、TEST0/主要贡献未证保持。source/cardinality/分组研究不是原AINav工程成功的改名贡献。
