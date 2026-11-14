# 状态／受载条件路径瓶颈：最小数学原型

这是本组公式研究代码，不是控制器、物理资格器或世界模型。最初`model.py/run_demo.py/test_model.py`数学核心仅用Python标准库；可选Piper静态图后端需要已有隔离环境中的NumPy/MuJoCo，不加载actor、不连接远端、不读保留组原始数据。

## 已实现

- `model.py`：OmniNav v1 **Eq33–42的代价表达式**（双椭球target/shell、朝向与底盘softplus），参数显式传入。三个主权重归一到和1。**不含**IK图采样/椭球拟合、PSO或整套导航；默认没有真实Piper数值图，不能称OmniNav复现。
- `path_score`：端点A1或完整离散路径A2的最小归一有符号余量，以及最坏sample/constraint。
- `candidate_score`：固定路径集合上取max。缺字段保留上下界；有已知负项可拒绝该路径，但其他未知路径不擅自删除。空路径集/模型域不支持为unknown，不宣称机器人无解。
- `select_exact_candidate`：同一base-cost/candidate集合下执行P2硬筛＋余量偏好；未定最优的unknown候选存在时保守返回unknown，不冒全局最优。严格物理门禁须另按原实现计算，边界0这里只代表声明的非严格代数条件。
- `quasi_static_torque`：同frame/point的静态平衡 `tau=tau_g-J^T w_external`。w是**环境施于机器人**的力/矩，非机器人对物体的反作用力。只是代数，不提供Piper惯性/Jacobian、动态执行器/延迟或接触模型。

## 运行（从仓库根）

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s research/task_conditioned_reachability -p 'test_model.py' -v

PYTHONDONTWRITEBYTECODE=1 python3 research/task_conditioned_reachability/run_demo.py \
  --output /tmp/reach-math-fresh-result.json
```

输出已存在会拒绝，不覆盖历史。可选 `--recorded-receipt ABS_PATH` 只接受代码固定SHA的既有capture32独审回执，读取原candidate2870的3个已审标量，不执行新FK/IK或planner；无该文件时直接省略该外部例子，不生成“原件”。依赖路径和SHA写入输出。

测试包含27个单元测试，其中有限等价性质枚举`3^8=6561`个人工小数组，**不是27次机器人实验或6561个统计独立样本**。

## 当前输出怎样解释

- 两个刻意构造的反例里，A0和A1选endpoint可行、内部碰撞/静态受载超限的toy路径；A2改选另一条全样点通过的路径。
- 同样构造去掉载荷后A2回选原低cost路径，体现条件化而非一律保守；缺受载模型时A2返回unknown，不拿空值当零风险。
- 此处椭球/路径/尺度/权重是人工例子，**不是Piper拟合、真实成功率、安全校准或方法创新证明**。
- 可选既有Go2/Piper CLIMB路径例：candidate2870的endpoint leg-box gap6.961mm，但路径中间最小4.011mm，原要求5mm。只是**单个原约束**的endpoint-vs-path反例；该候选其他swing gate本来也失败，不能说整个endpoint方案通过或新方法改善了动态结果。

## 缺失数据与数学范围

每个已知signed g按正scale归一；正/零为本有限名义模型通过。缺失项的下界为−infinity，上界由已有项给出；整路径/候选取min/max传播。输出中的±infinity用显式字符串表示，不是补0。

P1只在给定有限路径、采样点、已知约束内等价于“存在一条全样点/全约束通过的路径”。未建模接触、真实噪声/动态、点间碰撞及未知wrench必须独立处理。不能用未来实测量填查询时输入；若载荷/接触域不适用，应标unknown。

## 下一实质研究缺口

真正的Piper固定基座IK方向图与双椭球拟合、同query的实际候选轨迹/可靠载荷项尚未接入；物理A0/A1/A2公平对照尚未运行。先落实这些，保留原控制/安全/数据角色，再检验实际完成/失败、覆盖率与全成本。不要继续扩大toy例子数量替代验证。

## 第二轮：真实仓库Piper运动学数值图（静态模型，不是实机标定）

新增 `piper_kinematics.py` 直接编译原Go2/Piper XML并应用原USD来源profile，核五份USD SHA；用最小私有MjData适配器接**原** `PiperPositionReachabilityOracle`，不构造加载actor的LocomotionRuntime。读取完整base→Piper→end_effector链和六关节实际限位，不用ARX资产或legacy link6+15cm工具代理。`mj_step/mj_step1/mj_step2`在本进程被guard拒绝，只做`mj_forward`/原FK-IK，私有qpos/qvel/ctrl及time保持可核。不是实际控制队列/history的证明。

`piper_map_protocol_v1.json`在运行前固定：base_link下x=[−.10,.70]、y=[−.35,.35]、z=[.05,.65]m，5×5×5拟合开发网格与4×4×4独立位置的cell-center验证网格；每点tool-x沿±xyz六轴×两roll，共12个指定方向（非均匀全SO3）。每query固定default/midpoint两初值、至多80次迭代/初值、2mm/1°数值容差，先找到合法解就结束；不跨点warm-start。最大2268个pose query/4536个IK尝试/300秒本地CPU，0物理/actor/GPU。**该容差只定义静态数值求解，不改任何原控制/安全门。**

所有找到的解重新用原FK核目标残差；未找到标bounded_solver_not_found，不能算严格不可达。ψ是这12方向、这两初值的成功比例，不是精确方向空间体积。固定ψ≥.25筛拟合正点；64个验证点不参与拟合或挑阈值/尺度。拟合规则只有一次：正点均值/协方差外包椭球＋同心sample-empty内腔；不满维/空集/无内腔即拒绝，不改超参找成功。这个简易拟合器是**本组明确的A0近似选择**，不是宣称逐字复现原OmniNav拟合算法或保守可达域。

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s research/task_conditioned_reachability -p 'test_piper_workspace.py' -v

# 需已有隔离环境中的mujoco/numpy；不安装系统依赖。约300秒CPU硬上界。
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python3 research/task_conditioned_reachability/build_piper_workspace.py \
  --protocol research/task_conditioned_reachability/piper_map_protocol_v1.json \
  --output-dir /tmp/piper-static-new-study
```

11项**新增**测试覆盖资产/mount/原限位、已知FK目标IK闭合与恢复、远目标非全局不可达证明、禁物理step、12方向、fit/validation分离、嵌套椭球与退化拒绝。训练/验证的混淆表只针对本求解器采样率标签，不能写成任务成功/危险概率或独立机器人试验。粗图/壳层会误接收或误拒绝，必须原样报告，不看验证后重调。同一机器人完整self/environment collision、支撑、力矩/外载/延迟与任务路径尚未包含；A0拟合参数不授任何实际动作。

### v1实际结果与不应隐藏的拟合失败

本轮完成125+64位置、每点12方向、2268个pose query/4388个固定初值尝试，约14.14秒静态CPU；175个query找到并由新FK核误差的解。拟合网格最高仅2/12，预定ψ>=.25正点为0，所以原全方向双椭球**按原协议拒绝**；`summary.status`的INCOMPLETE_OR_REJECTED_FIXED_PROTOCOL指整体map+fit未通过，map的189行本身完整，不是超时/缺帧。没有改阈值、网格或seed再跑一遍。

`analyze_piper_workspace.py`只读这份完整图，保留ALL12方向结果，作**事后开发诊断**而非接收原失败：两个tool-x朝前切片（实际quaternion在输出中明确）各有27/34个拟合正点，能作条件壳层；对64位置相同方向label，分别TP/FP/FN/TN=18/28/0/18、24/16/0/24。假接收是相对于**这套有界IK成功标签**，不是真实物理失败/全局不可达。其余10方向因无点/少点/非满维而拒绝，没有只挑最佳方向展示。

这说明：目前的粗方向图＋简单协方差壳层还不能当可执行域，且不能据这种简单拟合器误差宣称超越OmniNav。下一任务方向必须由任务/工具坐标预先固定，不按拟合成功数选方向。所有本轮位置/结果已曝光，不再称未来未见测试；若修改拟合方法或方向采样，需要另预定新验证，而不反复调这个64点表。

四个固定、非默认、已知FK目标的额外正控4/4被原两seed IK找到，核基本链/pose接线；这不消除其他点的局部求解漏解。source/protocol/完整图/拟合拒绝/ALL12诊断均保留，不将失败改为成功。Piper数值图与静态正控都不是新任务/安全验收。

## 第三轮：任务方向与路径接口／姿态条件高度必要界

`piper_task_protocol_v1.json`先锁源码定义的pose模式PUSH接触前目标(.47,0,.10)m、世界手端Ry(.8)、机身高度.33m。不是position默认模式/冻结v212。每75候选同13方向（原12＋精确任务方向）、同原90%参考限位及两初值。`piper_task_geometry.py`仅AST核源并做frame变换，不导入控制器/Isaac；`piper_kinematics.py`可选原USD collision profile。成功的任务query才以单条21相位quintic名义关节路径复用原body/front-leg净空检查器，端点/全采样用相同35mm与硬关节余量；`PhaseSample`显式区别相位与`Sample.time_s`，不是物理时程。未知候选不凭空补路径或从全局排序消失。

**实际运行仅一次：**975查询/1879初值、5.795s静态CPU。任务0/75找到，路径0，端点/路径对照不可评价。另两个方向45/31找到，均不代替任务方向。原数据/summary/source SHA保留在`evidence/2026-10-20/piper-source-task-static-v1/`，不改旧图阈值或加seed重跑。`analyze_piper_task_study.py`仅对已曝光结果读残差：150个任务尝试均触及joint2参考边界，非不可达证明。

**新数学结果：**`task_height_bound.py`从冻结资产特殊链结构推导腕高必要条件，证明见`docs/IDEA_PAPER_CN.md`第8节：`M_z = wrist_height_lower - required_wrist_height_upper > 0`排除给定固定body/限位域的目标容差集合；不大于0为inconclusive。保留微小非轴向offset和旋转容差，不把投影几何约等式当精确链。90%参考域解析缺口13.397284mm覆盖75/75；原native hard域缺口−31.236883mm，不能排除。它说明目前该pose任务/固定机身/参考域不兼容，**不是native硬机构无法完成PUSH，也没有允许放宽关节/降低机身直接执行**。P3为本轮事后开发推导，0新FK/IK；未测计算加速、路径/物理收益或独立泛化，没有声称这种必要界本身首创。

```bash
# 使用已有隔离环境；每个正式study输出目录只能新建一次。
PYTHONDONTWRITEBYTECODE=1 ../.envs/go2-arx5-nav/bin/python \
  research/task_conditioned_reachability/run_piper_task_study.py \
  --output-dir /tmp/piper-task-distinct-protocol-output
# 上述命令是接口说明，不代表允许重复该已闭合v1研究。
# 只读解析复核不启动FK/IK/物理；不得覆盖已归档证据：
PYTHONDONTWRITEBYTECODE=1 ../.envs/go2-arx5-nav/bin/python \
  research/task_conditioned_reachability/task_height_bound.py \
  evidence/2026-10-20/piper-source-task-static-v1 --output /tmp/piper-height-bound-review.json
```

8项task/phase/frame/native碰撞恢复新测试＋6项解析链/offset恒等式/一维极值/旋转容差新测试通过；修改公共采样轴后27项原数学核心回归通过。新高度对照预算仅是计划，未执行；需要独立模型正控与真实物理对照，不能从“拒绝更多”宣称完成更好。

**后续有界正控也已完成：**另锁12个90%域内合法关节构型（joint2低/中/高×joint3低/高×joint5低/高，其余中点），原FK生成12个已知可达pose；P3在90%与native hard两域均0误排、状态/time恢复，0 IK/物理，静态CPU.207s。证据`evidence/2026-10-20/piper-height-bound-positive-controls-v1.json`；只是模型正控，不是任务正例或独立泛化验证。

## 第四轮：以整篇论文的“理论导航增益章节”为目标

当前章节主稿为`docs/IDEA_PAPER_CN.md`第9节，目标是原导航链整体完成的增益，而非独立几何/IK成绩。`piper_state_height_protocol_v1.json`先锁新高度.28/.38，**.33控制组原SHA复用，不重跑**。新1950pose query/3788初值、39条路径/819样点、11.706s静态CPU；0物理/actor。每个高度是独立状态条件，不是已交付NAV高度动作，不能跨高度优化后称实际导航改善。

`.28m`：39/75任务IK找到，8/75端点与全路径关节/35mm通过；`.33/.38`：任务0/75、P3各排75。`analyze_state_height_ablations.py`只读完整结果，S0/S1选b039（模型最小距离−38.511mm），端点几何门S2改选b017（55.290mm），S3路径门仍同8候选/同首选，**没有额外增益**；S4余量偏好换b027仅多.046mm，不作物理收益。P3调用数剪枝是反事实计数，本轮实际saved=0，无实测speedup。数据/图全部是曝光开发，不是独立泛化或真实碰撞/导航成功。

`navigation_goal_bridge.py`只接**原planner实际route-cost＋同观测状态的SE2候选**，输出shadow proposal并构造原`SkillAction(NAV,[x,y,yaw])`类型。不调runtime、不新造控制器、不授权执行；缺原route-cost/source即not_ready，禁止将静态alignment/psi成本冒J_nav，拒绝跨height/旧state混选，模型solver miss保留unknown。对应10个unit fixture不算机器人回合。

`navigation_chapter_ablation_draft_v1.json`定义N0同候选原导航cost、N1任务IK、N2端点、N3路径四个匹配变体；可选margin和P3计算效率独立消融。真实主指标是原整体导航目标完成，原所有安全门/actor/技能/预算保持、拒绝/异常留分母。兼容冻结整链source/真实查询与成功/实际route cost/独立物理预算尚未绑定，16新start先导未分配未启动，不动旧共享余额。原fixed-approach planner仅外部参照，不能假扮同候选N0。

新代码`run_piper_state_height_study.py`与5项height/cache状态测试完成，另10项shadow/消融不冒物理测试完成；不重跑旧物理、map或无差别核心测试。`plot_navigation_chapter_static.py`使用既有Pillow渲染原JSON，输出`evidence/2026-10-20/navigation-chapter-static-development-v1.png`，明确标STATIC/0导航rollout；不安装新依赖。

进一步实际接入原planner：`original_planner_route_shadow_protocol_v1.json`/`check_original_planner_shadow.py`调用原`OraclePlanner._path_between`，25个unique xy执行25次A*，原默认grid与Capability footprint、原箱几何，无目标exclude。15 xy可达/10阻塞，每状态45个共同SE2导航候选。`.28m`：纯原grid路径长度N0/N1选b021（0m，最小模型距离−30.090mm），N2端点门换b015（.200m，58.613mm），N3/margin/P3仍同选择。约.0092s只是缓存IK/path上的路由/选择shadow，**不是实时IK+规划总耗时或实际行走**；grid中心路径无精确端点/转向/动态证书。所有physical outcomes=null，execution_authorized=false，原canonical SkillAction类型identity通过，未导入actor/runtime。真实NAV到达误差/状态新鲜度、冻结包、真实snapshot和物理预算仍需绑定。

## 第五轮：实际Isaac完整链来源、已有退让公式与清洁消融设计

`bind_executed_navigation_baseline.py`只读v316/v317原plan、16份report/原guard/物性/actuator和有限control前缀，不启动旧probe。原8已用case整链7/8→8/8，唯一改善3703；common-success7条平均慢.094286s。两版是几何＋support处理修订bundle、已看开发且旧返程目标按stow状态生成（3705绝对goal不同），**不是独立/固定全局goal/纯单因素收益**。`historical_prefix_values.py`增量将row0双方未记录action/phase列为unknown，测得所选共同值在决策942前无差异、首个值差944；保留v1原件、不宣称完整物理世界相同。

实际v317不是通用MuJoCo OraclePlanner/SkillAction：native hook是`prospective_entry/required_standoff/prospective_support(minimum_shift_m)`，原loaded stance/final recheck/READY执行；source configure pitch1.0、冻结两路点JSON9c6…，NAV/PUSH actor/原12腿hook共三份权重已在远端仅SHA核验，0SDK/actor。实际v317/3701 READY step1180/23.6s root z=.279354900、18轴名字/实测q与原control行对应，未把q裁到命令边界，未填未来box。

`tip_envelope_standoff.py`形式化既有有限tip云前平面退让，新增swept yz band的充分范围。它只证明提供的finite cloud在固定姿态最终平移下的tip几何，不覆盖残差内部/实际tracking、全身/运动/支撑/任务。超40mm仅无充分请求/unknown，不证明机器人不可行；抽象漏点反例未证明native Piper可达，不冒真实v317事故。

`native_tip_ablation_shadow.py`把实际机器人部分映射到新schema，但同查询box pose、uncensored41x64云/投影、caller translation/FK量缺失时始终not_ready；时戳一致非实际freshness认证，全部execution=false。旧preview audit有取后续PUSH箱位置/stance yaw作事后核对的流程，本组不复跑也不把它变成决策时输入。22项新增reader/覆盖/有限几何/native schema unit检查通过，非22个机器人回合。

`native_entry_ablation_draft_v2.json`取代旧未运行物理提案：同v317 caller/处理逻辑的E0 support-only、E1末端、E2全云、E3侧向集合；共同world goal(−.25,0,0yaw)只作为全变体一致的return-target参数新协议，原ctrl/guard/阈值/96s保持。不混用旧相对goal8条终态。1次≤180s SDK0env和16新Isaac starts只是未分配提案，未实现/未启动，不动旧预算。下一是新隔离观察层与source/同caller准入，不重复旧物理/SDK/全套控制审计。章节/结果见已有docs第10节；原始新图`executed-navigation-history-development-v1.png`明确历史开发与scope。

## 第六轮：授权先导、一次SDK门未留证、受预算保护的r2修复

用户已批准SDK0env1次≤180s及通过技术门后16次新Isaac。`native_pilot/`实现冻结v317组装/同caller有限云观察和标量需求、共有world goal、拉丁循环4新seed120401–120404。原controller AST保持，仅预期观察/共有goal/meta接入；E2在真实私有几何CPU检查与原helper一致。所有variant共建/保存同2624点并单列共同观察成本，不能当独立episode或实时提速。

原包source manifest `dfd30848...`在远端`/mnt/yuanyue/data/go2-piper/reachability-native-entry-global-goal-20261020-v1`；SDK PID1307300/timeout1307304/子1307305已结束，27.814s/rc0但**final JSON缺失、gate=false，SDK1/1已消耗**。本组SDK checker把报告放在App.close后，native shutdown可能直接终止Python；四组云仅说明到了几何循环，最终PASS未知。没有env/物理派发，physical0/16保留，旧包/日志未补写或替换。

r2 `sdk_evidence_io.py`先fsync/atomic持久化pass/fail与checkpoint再close，CPU hard-exit0不会洗掉失败。revision需要匹配源manifest的新显式approval，physical ledger/claim钉在原family防止改目录重置16次；r2只stage、没有授权文件，plain-Python已验证拒绝自动App。额外SDK1次≤180s需补充批准，原16物理不增加。14个新source/真实私有几何/关闭持久化/评价tests通过，CPU初始两项组装失败保留，不等于SDK/机器人试验。

`evaluate_pilot.py`独立核实际固定goal事件/最终位置与native门/物理覆盖，旧relative目标或SDK fixture不得冒新成功；未运行/缺报告保留unknown/all16注册格，当前配对效应不可估计。不从exit0推PASS、不重启SDK或新物理、不重刷旧图/全控制审计。完整状态与source/log/PID见现有docs第11节和新增`native-pilot-approved-run-repair-increment-v1.json`。
