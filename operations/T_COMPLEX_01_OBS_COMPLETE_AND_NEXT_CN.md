# 固定三view测量已完成：空→A可见→空；不是PUSH或完整任务资格

2026-11-15 22:18。此处覆盖“仍2/3、right在途”的当前状态，但不改历史记录/旧根。

## 已核原结果

原OBS main result `a2252439e9e6352163404ce7861b83ecde1b29953ae2f2fb6f92784b01080ce8`，同program `9fdd2076cda187b0749f7f294ef362acb954cac4d7fa95a2feec7e1b3529b7ad`/source c3c695b5…，status **OBSERVATION_STUDY_COMPLETE_NOT_TASK_SUCCESS**、passed/qualification_complete=true；task_success/AB_comparison/training_allowed=false。

| 固定边界 | 原sim time | 原public accepted aliases | 实际见证 |
|---|---:|---|---|
| capture后center | 2.240 | [] | 原capture448步 |
| left NAV后 | 14.815 | [cuboid_a] | 原NAV succeeded，tick2963 |
| right NAV后 | 27.515 | [] | 原NAV succeeded，tick5503 |

本组22:16直接读原root独立验证**1058行完整原journal链**、A/B前阶段已读1052行前缀逐byte保留；三个public query均按原Observation语义SHA精确匹配，原RGB文件SHA/原one-to-one label逐项一致，两个原NAV option/参数/字面成功receipt→对应观测时间完全同钟。没有原件重写/额外view/重跑proposer/GT/Actor/Runtime。

- main世界 **27.515sim/5503原命令**，276原RGBD/review及direct HD frames（960×540）。
- scope含zero/双aux **40.525sim/10266.018950355ledger wall/245208182bytes高水位**，usage known；main phase已closed、原PID57116已退出。
- Data原九流cold-v2 `6907bb1c…`全过；本组核原报告SHA、消费其NPZ/PD/FIFO/pixel检查，未冒本组独立重算。审计v1/v2出版修订不是两次物理测量。
- **22:17:43权威H仍active/派发态，不能把phase完成冒scope已CAS closed或设备已可分配。** 只等Data自己的正常close/release，不替owner改H/锁/队列、不追加Reach签字门。正式完整release/编码视频尚未在本轮消费；已有第二边界partial release不冒完整发布。

## 科学解释与必须保留的“非结论”

固定完整测量**不是三view均不可观测No-Go**：left在原门下确有必要观测阳性。right空也不能抹去left阳性；但当前终点在right，**left alias已不是终点当前观测**，不能缓存进下一PUSH、用旧像素/静态pose替换终点空观测。NAV目标±.15是命令目标，非实测精确侧移或单独Y变化因果归因。

0PUSH/0placement/0研究策略bundle，两个脚本NAV不是两个重构或三个有效规划选择。可见性必要条件不等原PUSH READY、三箱共同动态合法计划、完整任务或前瞻优势；OBS数据永不冒critic TRAIN/CAL/VAL行。旧A RGBD关联拒绝和旧B原wall资源截尾均保持原解释，不能给它们追溯补view/改判胜负。

## 可直接接续的源/方法准备（不是新物理派发或额外签字门）

以下是对下一**共享源DEV版本**的具体接口需求；旧b08和已完成c3c测量不热补。保持geometry/color/rig/proposer/matcher/64pixel/IoU-SDF与原技能成功/安全门。source owner可开发并发出精确immutable版本，Data按原流程装配，不等另一个Reach“收件许可”。

1. **共同观测前缀与费用显式化。** 下一版本可研究固定capture→原left NAV→fresh query作为两方法完全共用的观测准备；它是由本DEV测量提出的机制，不称预先未知/独立评价。不是在线挑三view里最好的帧，也不是复用本次已结束world；不得给B独占left view，不能抹掉该NAV的动作/观测/总sim/wall成本。若共同前缀在任一arm失效，保留真实拒绝/未达/censor，不换视角重试找赢家。
2. **准备后名义起点不能无声沿用center。** 本组现`build_source_bound_planner`固定初始reference(-.08,0)，只适用于原起始程序。若新source在left成功后才启动方法，必须把**已验证原NAV成功对应的共同命令reference(-.08,+.15)**作为明确nominal context，再匹配同一fresh public query/receipt；这不是私有实际base XY，也不是精确tracking证明。不能只换caller而继续center路径代价，也不能把scripted前缀算成方法自行选择。双方使用完全同起点声明、root候选顺序和4/256/.25上限。
3. **当前关联只给当前执行门用。** 每个后继NAV/PUSH前保持原fresh public acquisition与原judge/immutable binding，不持久化“某箱曾看见”作为可执行证书；真实技能receipt之后才推进名义状态，不凭预测PUSH完成。固定prefix不能保证B后续NAV到另一入口时目标仍可见；后继不可观测必须明确拒绝/未知，不透传旧alias。
4. **强基线公平性与可行性仍需源证据。** 公共catalog的名义条目不等当前native READY；两方法都必须经过同一原生门。原A“当前不可观测就直接拒绝”的结果不证明局部合法强greedy输。下一方法比较前先解决共同动态可行计划/完整动作域资格；存在性见证可隔离保管，不能把正确路线喂给在线方法。此文不发布第三次pair/次数/lease，不把单个可见view当全场景native许可证。
5. **Reach接线改动边界已明确。** 仅在新source给出确切共同prefix成功/当前public query接口后，增量实现可receipt绑定的初始化与公平费用记录、同源CPU seam核验；旧默认入口与冻结program不改。未native资格的标准枚举仍非新算法/主要论文贡献。T优先但bulk24可在Data另一GPU有限滚动；原fit3371ac20…冻结，1/3 CAL未评分，不用等待数据齐而空转或提前refit。

完整无数组小证据：`operations/T_COMPLEX_01_OBS_THREE_BOUNDARIES_COMPLETED_20261115.json`。原数组/视频/weights仍46308，所有旧dirty/index与closed负结果保留。
