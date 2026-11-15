# full-2 gate闭合：1通过、1原PUSH卸载中止；四格终态齐，首次PREPARE仅3/4可测（2026-11-15 12:07）

## 原件结论，不再误写right在途

full-2 left三语义请求链PASS，主119.000sim，first CLIMB PREPARE95.605；right于主64.170sim发生原RuntimeError `reconciled_reference_FF_intersection_empty`，03:24:00 CAS `CLOSED_ACTUAL_MAIN_FAILURE_NO_RETRY`。traceback定位原PUSH brake/unload→reconciled_unload/select_axis，不是XML启动故障或CLIMB执行失败；right该程序zero1/main1已耗，绝不重发/换seed补到成功，不放宽FF/12N/4s/stop/QP/FIFO门。

right原cold记录：selected engineering intents2、bound native options2、literal receipts3；只有NAV started/succeeded与PUSH started，没有PUSH terminal failed receipt，**不补造**。原九流cold true是数据完整性，不是任务成功。实际first-PREPARE reader复用原Journal.verify/Observation.create核result/journal SHA，返回`PREPARE_NOT_REACHED_OR_BOUNDARY_NOT_RECORDED`、first_PREPARE=None；结合完整原journal/实际只选2请求可判此处为未到达CLIMB，不用早期PUSH query/零向量/旧right或READY后帧补值。

## 完整分母与已知成本

|量|full-2 left|full-2 right|
|---|---:|---:|
|实际请求链结果|PASS|PUSH卸载原FF异常|
|主任务sim|119.000|64.170（失败终止耗时）|
|CLIMB首次PREPARE|95.605|None，未到达|
|PREPARE→READY|13.375|None|
|PREPARE→成功终点|23.395|None，失败耗时不得代填|
|zero+main含aux总sim|132.010|77.180|
|active ledger wall|836.637653|450.701685|
|scope输出highwater bytes|174466192|116112415|

full-2原分母2：请求链通过1/2、PUSH卸载中止1/2，首次CLIMB PREPARE覆盖1/2。full-4/full-2×left/right四格**终态4/4已知、first-PREPARE测量3/4可得**，不是“四个状态已测完”，也不能只报可测子集的CLIMB通过率而掩掉未到达。

本cohort总209.190sim/1287.339338 active-ledger wall/highwater290578607bytes；ledger是实际phase收费，不冒从freeze到发布的全部日历耗时。旧46174行政UNKNOWN/已耗zero/main/未知尾费，新v1 XML故障15.156688wall/usage未知，G1及其他scope全部另保，不把此cohort当全项目最终费用。

完整组合release SHA **9be124b38bb2e29de554f3d4afac28c08f5eef711c3decfb14ee61902778cbff**声明metadata已逐SHA核，left/right原cold/CAS/ledger等原件pin在JSON；raw first-boundary失败报告只留ignored证据/远端，不入Git或训练。没有对不存在的right边界运行proposer/跨layout差，也没有重算原command NPZ/私有catalog或另开world。

## 这次负结果对现有模型/优化器的实际含义

现有critic的输入/预测时点是**已经到达CLIMB PREPARE**。right在该时点之前就中止，没有该模型输入，不能伪造成一行CLIMB失败标签，也不能把它从全episode/源gate分母删除。现有post-PUSH准备选择/收臂路径优化的收益范围也不能回溯解决这个未到达决策的失败。

因此继续现有条件critic路线时必须同时报告“到达决策的覆盖”与“到达后的条件成功/时间”，**不把后者冒全链风险或完整导航成功率**。若后续要学习/选择更早的NAV前驱以规避这类失败，需另明确模型decision event、合法动作域与任务horizon及未来新用途数据协议，不能偷用失败之后的观测作执行前输入或在当前profile里悄悄换标签。本次只给范围诊断，不更换原任务/安全门、不fit旧DEV；标准条件分母关系不是新算法贡献。

full-2已观察一个可用公开边界（left与full-4同prefix的q/视觉/nominal点不同），但不能声称整个left/right族可靠、四个condition都可供训练。G2 gate已结束，不重跑这些格或用left代替失败right；源动态缺口和model人口限制如实保留。

## 真实接续：full-1新scope，不是full-2失败重试

Data已经按原先发布的第三registered-source方案建立独立full-1-left程序3b5e9d4d…，保原case的lane−1.8、C质量1kg/底摩擦.3与geometry差，不冒同材料/geometry-only；旧full-2 helper仍拒full-1，未热改/放宽旧程序。自身真实zero/cold PASS，numeric92f86189…；**2026-11-15 11:52:50**才实际CAS唯一main（03:36是freeze/zero，不是整夜在跑），本组尚未接收其终态，不预告成功/重发launcher。这个新问题是第三case资格，不是修复/覆盖full-2right或清旧attempt。

正在做[G2]：闭合full-2负结果/不可测格，接续full-1真实终态和first-PREPARE；有则用既有公开reader一次增量测量，无则保缺失/原生失败分母，不凑第三scene。下一：合格第三source/新TRAIN用途、whole-scene/祖先split、样本/功效/停止规则冻结后才G3真fit及简单基线，继而G4三策略、G5多决策未见任务、G6复现结论。**即使full-1 PASS也不自动训练或12/24main排队**。

独立备选：用现有源事件界定conditional critic与更早前驱可靠性问题，不追加schema/测试平台或重刷已过34fixture；不要求Data代做模型/特征/研究评价。小高层未来新数据用途已授权不重问，现训练行/fit0；旧DEV/audit/GT不fit，Actor/WM/DINO/真机不恢复，Data唯一物理owner/原保护门/dirty/closed/TEST0与主要贡献未证保持。全程旧端连接0。
