# V4准备路径优化器须明确共同底座与处理因子：源码范围核查，不是已污染的实验结果

2026-11-16。查看新live caller时发现具体的方法身份风险，不能只看A/B/C/D/E的高层开关。此处的原Reach stow kernel是标准有限DAG原waypoint子序列选择，不是原Actor内生控制器，也不等完整后继评价器。

## 精确调用链（AINav 4909180a…/27-source软件候选）

1. `/home/yuanyue/main/work/ainav/development/complex_v4_four_arm_v1/live_driver.py`，SHA **f6567d53…**：V4 constructor调用`self._install_common_stow()`；结尾用`setattr`把所有7个原helper装到V4类。
2. 被借用`/home/yuanyue/main/work/ainav/development/complex_dual_route_v1/scene_driver.py::ComplexSceneDriver._install_common_stow`，method SHA **e658b891…**：调用`reach_stow_choice.native_stow_path_binding.bind_to_host(..., enabled=True, ...)`，**没有arm或planner factor判断**。
3. 已交付Reach-v2 binder SHA **23c1d6b5…**，与本组`native_stow_path_binding_v2.py`逐byte相同。回调可在真正selected/confirmed ground PUSH的原capture/queue门内优化并写回`owner.waypoints`。

因此：如果未来A/C/E直接使用这个constructor，不能仅以“它们高层optimizer_enabled=false/E规则没调用优化器”就宣称所有层都没运行任何旧Reach准备路径内核。尚不能声称已经发生了实验污染：**五组main0**；真capture/assembly component未构造PUSH/NAV/CLIMB，不会因这个尚未触发的回调变成有优化成功。旧API0两组把此层设为共同项是其旧协议，本次五组定义不能默默照抄。这并不自动违反当前“新后继优化OFF”：若旧H已经是固定共同历史底座，可以继续保留，但须将legacy_common_stow与本次new_successor_optimizer计数分开，旧H不能归因本次B−A/D−C。**不得为了把泛称“优化0”做成字面0而删掉已固定共同底座、削弱完整C。** 在首次full-program freeze前由AINav/研究明确这两个层级即可，不新增用户许可门。只有明确把旧H本身纳入此次treatment时，才使用下述可选严格隔离；本轮没有擅改任何基线。

静态证据`operations/V4_STOW_FACTOR_SCOPE_REVIEW_20261116.json`，保存精确源/行号/函数SHA；这是source审阅，未import AINav native/重跑实验。

## 可选的treatment-specific隔离实现（不擅改legacy-common基线）

若此准备组件被明确登记为本次处理因子，可直接接本组`v4_stow_factor.install_v4_stow_factor(host, arm=..., enabled=False, emit=journal)`；若保留旧共同底座，则无需强行改成这个模式，只须准确分层计数：

- **默认所有arm OFF；A/C/E明确拒绝True**。B/D只有事前固定、自己新程序合格后才可显式opt-in此组件；不能因安装原H kernel就宣布完整后继优化已成立。启用时仍调用同一既有v2 binder，不另写一份搜索器或改Actor。
- 仅fresh task0/empty FIFO、新host、全部loaded stow alias逐byte恢复原source通过、回调尚未安装时接。不会在真capture448步后改变因子，不会删除旧callback伪装OFF，也不改world/已有native owner。
- OFF不会调用优化binder/kernel或向模块装callback。仍把每个已载alias登记为`_stow_installed[path]=None`，**原_native_guards的“key存在且callback身份相同”检查保持**；以后偷偷出现callback/新未登记alias照旧拒绝。不能通过直接删这条guard来让baseline走通。
- True保留原guard/endpoint/reference slew/4s全过程、原root/selected-view/FIFO/goal身份和每步门；callback仅做原bounded waypoint选择，不能构造控制器或签任务成功。算法/原12N/FF/QP/FIFO/stop全部未变。
- helper一次性检查所有已载alias，防止第二alias漂移时已经给第一alias装了优化。source应按原要求预载所需alias；后出现未登记alias仍fail-closed，不自动宽松接受。

**若采用严格隔离，AINav具体接线注意：**

1. 替换V4 constructor的旧always-TRUE安装路径，显式接事前arm/component flag；不要先调用旧installer，再调用`bind_to_host(enabled=False)`，因为原False分支根本不移除已有回调。
2. **只在class中定义同名override还不够**：当前文件末尾`setattr`会把原7 helper再覆盖上去。必须使V4实际调用的最终method是新因子版本（或直接在constructor调用本helper），不要热补原SceneDriver/已closed程序。
3. 新full-program freeze须包括实际导入的Reach helper/kernel与两份native stow alias的准确依赖。旧25-source capture的475 freeze未证明完整新driver/该包装配，不借其zero。Data沿现有新程序必要qualification执行，不要求额外签字或盲重跑。
4. B/D原root/全后继优化状态、legacy-common与treatment-specific准备path实际调用/改变次数分开记录；严格隔离模式下E/A/C的此处理因子callback/kernel次数应0。共同底座模式下不能将旧H误计成新后继优化调用，也不能抹掉其真实原生开销。即使B/D只改本地prep，也不当完整后继预测/新solver或方法收益。

8项新增明确metadata namespace fixtures在本机/46308验证OFF、非法强开、原None guard、旧callback不能伪禁用、task0/不可重绑、别名漂移/先验检查；True路径只mock既有binder安装，不冒真实guard/物理资格。本模块尚未被AINav/Data采用或执行；首次测试的空格SyntaxError已修，未改原gate/expected遮掩。
