# G1新端完整两条件与旧attempt行政收束｜承接2026-11-14 23:45总计划

本文件是新用户切机决定的接续解释，不改写原两条件问题、历史后果前协议或旧ledger。原冻结协议中的“总两条件各一次”分别作用于其scope；新的46308独立同设备cohort按最新计划明确允许left/right各一次。它不是恢复旧left，也不是仅凭换ID获得无限retry。

## 必须纠正的事实

旧46174 left已经实际own-zero/cold并于23:05:10 CAS派发main，zero1/main1均已消耗。旧程序5472a8bb…，原zero主任务0步/1 RGBD、aux6.505sim/42.510914ledger wall；失联前main最后已知usage93.635sim（含aux）/681.323241wall/142731645bytes。**这些是最后观测，不是最终成功成本或完整费用**。本地名为final-ledger.json的文件可能仍只含zero closed行，不能据其文件名说main未派发或已closed。

Data发布的最终任务结果为UNKNOWN_UNREACHABLE，不是native失败/成功，也不是旧进程已退出或旧锁已释放证明。保留原件、消耗及未知费用。最新用户明确“旧服务器已断，不用再纠结”：不再恢复/轮询/SSH旧端，不等旧端fresh CAS/锁释放回执作新端前置；由Data以本地原件行政停止追踪，不伪造物理终止。Reach本轮旧端连接0，不接管authority。

## 新端可以继续，不重复搬迁

- 46308新cohort完整left/right各一次，沿既定原NAV前缀→同PUSH/stow→CLIMB original、full-4/seed4301/原Actor与门；保持同设备配对，不把old-left与new-right拼成一对。
- 新left显式保old未知attempt谱系、全部已知花费和未知尾部；不删除/重命名旧root、launcher、ledger。新端若已有合法在途或closed同任务，直接接续消费，不能再开第二批。
- AINav已验证148成员原SDK/四Actor字节现存在`/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle`，Data pins一致；不再等旧端取资产/新下载，不向本地或Git搬权重。此处消费其源校验报告，不重跑它的148成员或冒Reach独立native资格。
- Data已报告`/mnt/yuanyue/data-team/env-native-v1`为Python3.11.16且7依赖metadata匹配。Reach此前probe的3.11.13是另一既存候选，不应再写成新端没有合格版本/必须重装；仍需owner绑定实际加载路径/环境字节及Host/Actor/GL/采样、UUID/canonical/lease/新freeze/各scope own-zero。
- Data唯一物理owner；旧authority不可fresh核不再阻新root，新的authority须引用用户切机决定，不称旧CAS迁移成功。不要求AINav/Reach再交消费receipt或等全感知/critic完善。Reach代码/小协议已在本地/GitHub/46308，新机大产物留远端。

## Reach正在做、下一项、可独立做的备选项

| 项 | 目标/动作 | 验收与接续 |
|---|---|---|
| 正在做 | G1：按既有后果前规则消费新端同设备两条件真实原流；处理首次CLIMB PREPARE、direct READY、失败/缺测与完整花费 | 两支均有实际终态或明确未知/失败分母；45D按单位块差、decoded RGBD、原component名义信息，结论是可辨/归并/证据不足，不冒候选收益；不等待旧端 |
| 下一项（条件可用） | G2：新用途cohort按祖先/条件组拆TRAIN/CALIBRATION/EVALUATION，登记实际信息变量、样本规模依据及有限停止规则；未来新数据授权已给，不重问 | G1 DEV两条件不自动转训练；新数据真实准入后G3实际训练critic/常量成功及mean-time基线、未见分组评价，再G4同域固定/greedy/successor三策略、G5两类布局/每链至少3有效决策机会、G6可复现结论 |
| 下一项（归并/不可辨） | G1失败分支：一次有当前实际caller代码依据的新条件源设计与最小验证，不重复left/right/seed/偏移直到可用 | 在新问题前固定变量/信息/对照/限额；当前无法定位合法可辨变量就准确报缺口，不以raw浮点差/UUID或GT升格条件族 |
| 无需外组的备选 | G3评价设计：明确classifier false-negative/positive失败语义、uncalibrated score/条件成功时长与UNKNOWN/回退覆盖的分母；先以既有模型接口设计，不调旧数据阈值/生成fixture权重 | 各指标只在真实future新用途组数据足够时报告；没有数据就无数值成绩，不用多一层schema/训练空跑充进展 |

数据不足不是总目标结束；也不能为了“持续运行”强派。旧public/隔离GT仍audit-only，小高层模型训练只用未来新预登记数据；原actor/WM/DINO/真机未恢复。全部dirty/closed/12N/4s/identity/immutable/guard/QP/FIFO/stop和TEST0/主要贡献未证保持。原三支/几何诊断不再重跑。
