# AINav接任V4五组：精确资产移植与能力缺口，不是原生通过

2026-11-15，按22:53总计划。当前优先A/B=VLM+WM无/有共享优化，C/D=原AINav无/有同一共享优化，E=无VLM/WM/优化的固定规则；主比较B−A/D−C。旧API0 greedy/multistep两组不是这五组的代理。

## 已接手的实际实现

- scene.json逐byte保留用户确认V4（SHA6394740e…），没有修改墙、箱体、C对接或0.60m平台追胜。research资产代码已移入本组可迁移目录，不再依赖本机research绝对路径。
- `v4_native_asset.construct_into_native_spec`只准fresh task0/FIFO空的Data spec：先加真实collision goal_deck，再调原complex_scene构造器加墙/三箱，保原robot/Actor。尚无原MjModel编译/zero/world/派发。
- `registry`实际调用选定冻结原SceneRegistry，goal.surface_ref=goal_deck/top=.6；公开投影包含平台声明，不公开private review/正确路线。不能原样套旧ground-only driver/catalogue/终点。
- `elevated_stop_sample_only`仅为私有必要sample谓词：foot Z相对.60、目标XY、每脚12N/速度/tilt原门，并需实际contact provenance的goal_deck引用。ground同XY必须false。**不是完成判据已集成**：仍缺同world原owner证明、三immutable placement、原CLIMB回执、实际contact reader、连续dwell及safe-stop caller。

## 已定位的真实阻塞，不以“高度相似”掩盖

`capability_boundary.selected_climb_rise_audit`只AST抽取当前原SceneRegistry的纯climb_geometry判定，SHA钉住，不导入Runtime/NumPy/Actor。declared geometry只是用于该纯谓词检查，不作为真实感知或控制输入：

1. ground0→箱顶.20符合该原20cm高度谓词；**箱顶.20→平台.60的.40增量被同原谓词明确拒绝**。这是选定完整v6/283当前registered路径的边界，不声称所有其他仓库/技能绝无40cm能力。不能把常数.2改成.4/降低门后称原技能资格。
2. 原`RegisteredClimbAdapter.bind`还要求当前RGBD关联映射到registry.objects中的body；goal_deck是static SurfaceSpec，不在可移动object集合。加surface registry本身**不自动打通static-deck CLIMB**。把静态平台伪装freejoint箱体或用静态GT代当前关联都不可接受。
3. 原ground-only TerminalStop核foot Z≈.022，不是高台.622；旧NAV/compact support owner、CLIMB exit→后继owner也必须逐段核实际适用域，特别不能宣称旧.2后NAV/PUSH站稳缺口已修。

**主运行前的最小方案供共享设计决定：** 若坚持当前20cm registered技能，不改Actor/原门，需一个真实0.40m中间支撑，把高度接续变成0→.20→.40→.60；它改变已确认布局/原两段预期，必须五组共享、在新主运行前明确确认/重新冻结，并另核static-surface association/owner桥。这里**没有加平台或改V4图**。另一方向只能先找出已有准确40cm原技能/权重及真实接口/资格；没有证据不能宣称已支持，更不能擅自训练。

## VLM/WM身份与后续实现

- 原AINav应复用冻结`AinavPlanner`的object/skill proposer、tree evaluator、advisor/arborist与replanning，不换成固定脚本或API0有限搜索。Reach负责A/B现有WM推理与B/D同一优化；此包尚未实现四个方法adapter，未调用WM/VLM。
- **用户已明确本轮使用DeepSeek，provider疑问关闭，不重复索key。** `VLM_PROFILE.json`复用本机既有TLS官方endpoint/deepseek-flash图像模型配置，原DeepSeekBackend及RoleRunner/原AINav树保留，旧sol_gateway profile不用于新V4。只接受既有受保护的进程环境DEEPSEEK_API_KEY，不把聊天密钥写入代码/manifest/argv/日志，也未跨组传明文。当前未构造backend/发API，未声称用户提供的密钥已注入计算进程；未来在Data预冻程序的正常模型身份资格中验证实际served model，A—D同版/同采样/预算，E调用0。
- 新source当前仅资产/必要谓词与准确边界，不能提交五main派发请求或宣称共同可行链。下一实际工作：确认选定现有CLIMB能力/最小共享设计修订，继续surface-aware实际caller与终点/已明确DeepSeek的强baseline真实VLM接缝。基础场景/registry代码可先由Data纳入必要新端组件资格；本包不是该准入证明，也不要求额外收件签字。

软件14项只测原纯API/资产与拒绝边界，不是14研究样本或native资格。旧closed A/B/OBS根、bulk在途/冻结程序不改；WM只开放本任务既有推理，不恢复新训练/底层Actor/真机/第二物理owner。evaluation_ready=false、独立TEST0、五箱false保留。

## 新增E规则源（未接完整native driver）

`rule_baseline.RuleBaseline`是真实原IntentBatch/Selection/NativeReceipt接口：按公开initial X/public_ref固定工程优先级处理required placement；当前关联缺失时只试一次已声明approach NAV，fresh仍空则明确UNKNOWN/停止，不盲按时间播动作。PUSH只在真实同intent/params succeeded receipt后计入已完成；所有地面placement后，以公开最小下一高度/到goal的一跳名义距离选CLIMB，平局target_ref；无VLM/WM/B-D优化、私有pose/未来轨迹/存在性路线。每次64上界/fresh query，拒绝/失败不换seed或静默fallback。

这是场景公开几何的工程规则，不冒通用规划或最优策略；不使用V4主运行后果调优。当前.2→.6会按同原20cm域明确停止，static-deck/owner/完整终点尚未集成，E不能自行签task success。E接口代码存在不等E具备主运行资格，更不把旧API0实验改名E。

## 已补实际deck接触reader与连续停稳（仍非完整成功门）

`elevated_terminal.read_current_goal_sample`为Data实际runtime编写，不构造Runtime/Actor、不中断或改写世界/FIFO：按真实compiled foot geom/body与static goal_deck geom读取MuJoCo mj_contactForce；只把目标deck接触的法向世界Z分量累积到相应脚，其他箱/地面载荷和侧面法向不冒高台支撑。deck实际几何/姿态、原snapshot源SHA、原脚body与global loads也核。私有样本仅供终点验收，不进VLM/WM/优化/E特征，不能用声明高度替代接触身份。显式pair中的foot geom即使contype/conaffinity为0仍按实际contact纳入，不误排除。

`ElevatedGoalDwell`按真实连续200Hz clock/tick维持原.5s必要停稳：重复clock不积时、漏tick重置、载荷/支撑/速度失效重置，ground同XY不通过。它故意没有task complete属性/回执：原同world已成功owner/stow、三immutable placement与真实CLIMB链仍需单独接入，不把这个ready布尔冒完整任务。

新9项仅验证接触算术/顺序/多geom累积/非有限拒绝/时钟和停稳；没有调用实际MuJoCo collector或产生真实接触样本，原生ABI/平台contact动态资格仍待Data自己的新程序。没有因reader代码写好就恢复旧根或放行五main。

## 五组真实共同公开候选与效果声明

`public_candidates.py`导出原SkillIntent目录/declared_map/capability_contract与PUBLIC_EFFECTS.json。五组同序同域：ground NAV只列平台外声明点；高台终点NAV唯一以.60m目标层声明，绝不把平台下面ground同XY当终点；6个地面绝对PUSH目标保原数字、不额外加.11；3个物体与static deck的CLIMB均保public DESTINATION高度，private source support/20cm rise/当前关联仍由native judge建立。原IntentBatch契约与真实E.select已接通软件seam，但不是V4实际runtime caller已完成。

公开效果只列请求的reference/placement/destination和必须原回执，实际exit pose、成功概率、后继成功耗时全部None；合法准备/退出变体尚未原生导出时显式UNKNOWN，不补0、不把G2偏移直接挪来。Reach自己实现共同完整代价provider，本组不替其研究评价；不造WM public60/target8/真实issued-history。

## 当前硬交付目标与并行授权

用户最新明确E规则必须完整实跑成功，A—D各自交完整直接live原片，失败/API或资源截断也留全片；软件checks/示意图/进程exit不替代。E若未成功只报告实际失败阶段并修具体新版本，不能洗旧失败或在原closed root反复重试。五组共同执行底座先资格，正式顺序/策略与源结果前freeze；E后果不能反调其他方法后还声称同一未见对比。

用户同时明确尽量并行、充分利用服务器。仍Data唯一physical owner；AINav不自己开world/改Data进程或锁。新scope可按Data合法隔离lease/CPU/GPU/显存与HD录制容量并发，不是限制为必然一GPU只能一world；已有bulk专slot/CPU与watchdog不能热改。先实测必要own-zero资源，再决定同卡多world是否安全；没有method/native资格不为占卡而启动假任务，不把空闲快照当lease。
