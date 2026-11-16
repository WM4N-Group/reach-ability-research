# 旧46174 left：恢复后只读取得原result/最终账本，不是新运行

依据2026-11-16 14:08主计划e56951c2明确授权，仅为原失联left的具体缺失result/ledger，使用已有密钥一次只读访问46174；不恢复计算/旧launcher/旧world，不动旧H、锁、源、进程或账本。不复制环境、模型、SDK、原大数组；仅取约101KB小元数据。

旧scope data-native-prefix-left-PUSH-CLIMB-20261114-v1，原program5472a8bb…、authorization c9787048…与失联前已知H及原结果/账本三方一致。原main result 9a879643…，原最终账本5825aa3d…；main行closed=true且report_sha精确匹配。原result报告REQUESTED_API0_PASS/所请求NAV→PUSH→20cm CLIMB三项语义成功（含准备共5个native option完成），whole_task_success_claimed=false。原main任务24217步/121.085sim，记录1211机载帧；本回合未读取raw/journal做完整冷审，因此只是原件级恢复核验，不能升级为Data重新全流通过/新V4或E20成功。

原zero/main账本行均closed=true，但账本顶层stopped=false、旧H仍CAS_DISPATCHED_MAIN/active=true，H SHA仍为失联前e3baa660…；这些历史管理元数据不回写、不当当前执行权威/lease，也不因此续派旧right。旧PID3970779在恢复核验时不存在。

保留两种成本原口径：main result wall909.799338533s；最终main ledger wall909.890570222s，zero42.510913883s，账本zero+main合计952.401484105wall/134.095sim（含两次aux13.010sim）。main最终ledger高水位177089038bytes，result记176989422bytes，差99616bytes恰为原result文件大小；仅报告此算术一致性，不凭此猜所有wall差原因。未知货币成本不补0，不作为某算法成功成本或新端项目总费。

保留2026-11-15失联时UNKNOWN/已知usage下界原件a312c3e5…不改，另附本恢复证据。旧zero1/main1仍只各1次，不新增物理分母、独立TEST或批量库存；新46308 left/right与旧left的同祖先/重复条件血缘保持，不据新增读回结果回改配对/选择赢家/用途。当前唯一计算端仍46308，E20静态geom lookup硬阻塞不因这份历史结果解除。今后无具体新增缺失项不再轮询旧端。
