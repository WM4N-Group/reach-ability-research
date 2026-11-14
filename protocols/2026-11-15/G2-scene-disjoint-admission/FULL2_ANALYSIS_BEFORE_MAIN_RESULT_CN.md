# full-2 gate分析接续：沿既定G1规则，不新增阈值/采样门（2026-11-15）

## 当前真实caller已选full-2，不再混用备选center任务

已只读核Data新owned `g2-full2-46308-20261115-v1/prepare_prefix.py`：在真实`build_plan`调用AINav `registered_layout_conditions.build_condition(LayoutCondition('full-2',prefix_side,'original'),enabled=True)`，消费它的original_native_protocol/runtime_config/request，并核实际case_id full-2、与固定条件逐字段相同、仅actor_device overlay/seed4301。不是改full-4标签，未创建新planner/controller/日志接口。

`inputs/g2-question/FIXED_TWO_CONDITIONS.json`SHA64c92421…明确新full2 left/right各三请求：NAV x=-0.07999999999999996，Y分别-1.75/-2.05；PUSH(2.3,-1.9,0)；CLIMB upper-entry destination .2，准备original，两main上限/每条件一次。该source/helper同时能表达本组原center/upper-entry备选，但**本次Data实际采用的是full-2 left/right**，不要求两gate并行或在途换回center。未改他组源/在途程序/旧包。

本文件是对既定信息评价/分母规则的跨layout明确化，不是派发门、额外consumer receipt、新日志合同或完整训练协议。Data可沿新冻结程序自身zero/lease/原门继续，不等待本文件/报告。

## 一个限定问题、四格DEV对照

问题：原登记full-2在相同冻结技能下能否走到首次CLIMB PREPARE，且得到与full-4/同prefix不同的合法task相关公开输入？这是source/信息资格，不是纯几何因果或在线优化收益。

- 四格：已闭合full-4 left/right（旧DEV，后果已曝光）与新full-2 left/right；每格原唯一main，无重试/补帧/换seed。full-2是整个原登记geometry case/公开目标的变化，不把它当仅换一个连续lane数值的单因素试验。
- 每格独立从首次CLIMB PREPARE原judgment/binding/event→actual Host Observation SHA定位；不硬套query编号、不以绝对clock/nearest对帧。没有PREPARE就按direct READY/拒绝/前段失败/缺记录分类，保持全两条件分母。
- 复用现有`read_G1_public_boundary.py`/`compare_G1_public_boundaries.py`，读取当期公开45D、decoded RGB/depth、K/T及原component；不新增sensor/feature槽、HOLD/采集或状态回放，不读GT/private关联/command NPZ。
- 先报full-2内部left/right按原单位的exact差/每通道差及block统计；再固定同prefix的full-2 vsfull-4两项跨layout比较。检查decoded数组shape/dtype/数值/NaN缺测语义；若尺寸不同，明确不可逐像素等同比较，不resize/补0。图片/深度数值变化不单独证明task-related信息，原component有唯一关联/深度才给名义点差。
- K/T是否相同只按实际原件报告；名义component坐标在各自camera-parent body frame，不能不带heading/pose就叫WORLD motion或reference-relative error。所有误差/稳定界未知仍None，不沿用旧几何p95或新差值当门。

## 首先证实真的加载了新case，不用显示ID认证

消费Data实际original_protocol、runtime_config、constructor/source pin和zero/main numeric-model记录，确认完整registered full-2及lane目标、仅允许overlay、同Actor/已明确库配置和成功门。zero与main须同本scope程序/模型身份；不要求模型数值hash等于旧full-4，因为geometry确实变化，也不能凭hash不同单独证明每个物理参数或独立可辨性。数值hash只是原owner资格证据的一部分，不由Reach另建MjModel/MjData/GT审计。

已知left zero出现OWN_ZERO_PASS/主world clock0、numeric93869e1a…（full-4为7b9ed33e…），这仅是本程序初始化/采样资格，**不是full-2前缀/请求链已通过**。此时尚未读取任何full-2 first-PREPARE后果或模型训练行。后续按原Data原件/实际终态更新，不追旧机或重发launcher。

## 成本/失败与角色

各格分别报实际NAV意图、原PUSH准备/执行/stow、CLIMB PREPARE→READY和成功终点；Actor首次activation没有原事件就None，不从dispatch时间编造。不同layout/目标的episode不能当优化收益；准备与成功cost不重复加。失败端elapsed与成功cost分开，启动/资源失败与native失败分开，usage_known=false不能按sim0报完整已知费用0。

同scope phase输出highwater取max，独立scope才相加；主任务sim与各自own-zero/aux/ledger wall分列。引用G1旧失联/v1失败谱系，不用成功sourcegate替换全项目费用/分母。

全部仍DEV/audit，不转TRAIN/CAL/TEST。full-2若动态/公开信息有效，只有第二个已观测任务scene，不能直接完成TRAIN/CALIBRATION/VALIDATION三个互斥scene split；第三个相关scene及新用途cohort/样本功效/停止规则仍要明确，现8组草案/12/24main不自动排队。两支结束即按新结论接续G2→G3或有限source/信息缺口，不重复这四格到成功。Data唯一物理owner，原12N/4s/identity/immutable/guard/QP/FIFO/stop、Actor冻结/WM暂停/真机未开放、TEST0/主要贡献未证不变。
