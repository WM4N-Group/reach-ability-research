# 准备路径的完整三候选表：真实局部/后继排序反转与当前加性时间头的表达限制

2026-11-16 03:25（北京时间）。**固定bulk24前20个closed原件的回顾分析，不是新仿真、在线预测、critic评分/训练、V4五组对照或优化器收益。** Data/AINav持有原执行，本组新增公开输入/端点核验与机制分析。

## 完整分母，不只挑成功

- 新独立提取11/13/17/18/19五个原成功的exact首CLIMB PREPARE公开48槽＋原READY/完整requested CLIMB端点，复用先前01/02/03/05/09/10的已封存测量；**没有重复执行/重提取前6行**。
- 前20共**10原链成功/10原生失败**。其中11到首CLIMB PREPARE（10完整成功＋10号READY后base_collision），9未到。04/06/07/08/12/14/15/16/20未到，features/CLIMB成本None，不能变CLIMB负类。10的18.035s仍仅失败耗时，成功成本None、没有伪造failed receipt。
- 每支原release/成员SHA、固定24事前protocol/用途/TRAIN ancestry、关闭zero/main账和完整journal链核回。原200Hz的.005s tick仅用于精确比较已经记录的事件时钟；off-grid值拒绝，不把浮点1e-11误差当差异。
- 11个不同full48、4个不同public45＋age状态；仍**4几何/8声明context、同1既有TRAIN祖先**，无独立holdout/新TEST/泛化保证。以下“context”不是独立统计重复。

## 首次获得3个完整三候选context（每项仅各一次既有采集）

R=首PREPARE→原READY，C=首PREPARE→requested CLIMB原成功；均模拟秒，不是整个V4任务耗时。

| 声明context | original R / C | +.04 R / C | −.04 R / C | 回顾局部最小 | 回顾完整成功最小 |
|---|---|---|---|---|---|
| g01-left（01/09/17） | 13.500 / 23.540 | 13.375 / 23.475 | 13.475 / 23.295 | +.04 | −.04 |
| g01-right（18/02/10） | 13.460 / 22.700 | 13.425 / 24.185 | 13.625 / **None：base_collision** | +.04 | original |
| g02-left（11/19/03） | 13.415 / 23.335 | 13.350 / 22.910 | 13.565 / 23.245 | +.04 | +.04 |

三组各自内部public45＋age和首PREPARE clock完全相等，完整48只因公开candidate offset不同；**未证明RGBD/完整公开观测或隐藏世界严格同一起点，不冒因果克隆反事实**。

### 具体迟延后果

- g01-left：+.04局部比−.04**快20 tick=.100s**，但完整requested成功反而**慢36 tick=.180s**。+.04后续CLIMB阶段10.100s，−.04为9.820s，后继+.280s反转了局部−.100s。
- g01-right：+.04局部比original快7 tick=.035s，完整成功却慢297 tick=1.485s；第三候选失败不补0/无穷成功成本。这里两成功之间的比较不依赖给失败赋一个任意惩罚。
- g02-left局部与完整最优一致，也照实保留，不只选反转者。“3组中2组最优不同”只是本表描述，**不是方法胜率或统计证据**。
- .100s正好是20 tick，不是严格大于.100s。本bulk事前假设是覆盖/可辨识性，不能事后把它改成旧G1检验、调整双100ms门或宣告旧检验通过。

所有minimizer都是**看到完整真实后果后的oracle表**，不是部署选择器、强在线基线或本方法输出；不将该表写进V4/planner，不凭其赢家固定路线，也不把标准三点枚举当新算法。

## 对当前conditional-time head的结构诊断（没有调用/评分模型）

当前`successor_critic.py::_fit_heads`/`predict_offline`的时间头，是对全局标准化48槽作affine ridge，再截断非负；没有state×action交互。只读源码，没有加载原fit/model文件、没有调用predict_offline/fitter，也没有动CAL/VAL。

对g01-left与g02-left的+.04/−.04两对：实际48维输入差向量**逐值完全相同**，均只有第2槽+.08000000000000007，其余46个状态/age槽差为0；而实际C(+)-C(−)分别为**+36 tick=.180s**与**−67 tick=−.335s**，偏好严格相反。

若时间头为 `C_hat(s,a)=b+w_s·s+w_a·a`，同一action差向量得到的预测差必须相同。非负截断最多把差异压成平局，不能反转同一输入差的符号。因此，**这种时间头自身不能同时表达这4个观测标签的两组严格偏好**；此处没有计算frozen模型的误差或校准指标，不宣告模型在总体上失效。

这说明未来合法新版本至少应检验有state-action交互的模型/简单基线；不是已经训练成功的方案，也**没有证明当前45D状态完全不可辨识或视觉特征必然有效**（跨context的状态本来不同）。四点/一祖先不能给总体期望代价、噪声或未见泛化结论。保持原fit3371ac20…/model a8b1f165…、旧CAL07/08/09及VAL用途；当前bulk的fit/refit许可仍false，不据本诊断偷偷重训/换WM或引入第六arm。

## 原件和可复现代码

- 本地只约64KiB标量/原件SHA，无48槽向量/大数组/原片：`/home/yuanyue/reach-ability-research/operations/BULK24_FIRST20_COMPLETE_CANDIDATE_TABLES_20261116.json`，SHA **100f9cab1252b2235a2f60c755b73f3c8b266b2f6e9964711b2bd4e8388d3e07**。
- 完整815-entry source-pin inventory留远端：`/mnt/yuanyue/reach-runs/bulk24-closed11to20-public-boundaries-20261116-v1/FIRST20_COMPLETE_CANDIDATE_TABLES.json`，SHA **ecd235b4c65682fb8444ffcf609caf54d56f20d0c40e4e06de2b830a691c644d**。新5条48槽和原01—10测量不改，均只远端。
- 结构证据小报告：`/home/yuanyue/reach-ability-research/operations/BULK24_ADDITIVE_TIME_HEAD_STRUCTURE_20261116.json`，SHA **71add454d2b198dfffbe8f8755debf3ff326905998f1a378262805907113146f**；有原源码/函数SHA与两对action数值，不含模型权重/45D向量。
- `operations/summarize_closed_bulk24_prefix.py`保留旧first10 manifest，不重写旧报告；新格式要求连续完整prefix10—24而非挑成功。固定用途/原关闭账/首PREPARE与literal endpoints仍核。新增8项完整域/失败None/tick/前缀专项，连原25个bulk用途/原端点检查，共33纯软件检查两端过；不是33次物理试验。

本轮真实API/WM/Actor/physics/fit/CAL评分0，未读取frozen模型权重或复开任何scope；三箱/用户scene/原Actor/12N/4s/FF/QP/FIFO/CLIMB stop、全部dirty、Data唯一物理owner不变。V4当前所需真实WM/caller/完整cost和.20→.60/static deck/owner/完整终点仍未由这份回顾表解决；当前优先仍五组，不以这张表结束长期任务。
