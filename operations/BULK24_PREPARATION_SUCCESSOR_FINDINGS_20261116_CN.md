# 准备路径优化：已从真实closed原件提取完整后继端点，不以局部READY或失败短时冒收益

2026-11-16 00:46（北京时间）。**这是现有bulk24前10个closed采集的独立回顾消费，不是V4五组实验、新物理运行、critic训练或本优化收益。** 采集、原技能成功及安全实现归Data/AINav；Reach新增的是源绑定的公开输入/准备阶段/完整后继与失败评价。

## 本轮真正完成

- 原reader只认ordinal01首包，面对原ordinal02的fixed-closed-v2真实拒绝。准确扩到已发布的两种原格式（v1仅01；v2仅02—24），不放宽新用途/固定schedule/scene ancestry/TRAIN split/whole-package及禁止fit门。旧cohort reader、已冻结协议、source与run没有改。
- 在46308运行无native/神经/API/子进程的只读consumer，新增**02/03/05/09四条成功＋10一条原生hard-stop**的首CLIMB PREPARE原公开48槽输入/端点，和先前01合为6条。完整原journal、released小成员逐SHA与原链检查，使用exact PREPARE原observation及原READY/原requested CLIMB，未用最近grid或未来观测。
- 固定前10分母：**5原成功/5原失败；6到首CLIMB PREPARE/4未到**。04/06/07/08未到，48槽和CLIMB后果None；不造CLIMB负类。10已READY并开始CLIMB，随后原`base_collision`，不能与未到决策失败混淆。
- 10原链没有CLIMB failed receipt；准确保留**started→chain hard stop→原controller failure clock**，不制造失败receipt。成功成本None；18.035s是决策至失败耗时，4.410s是READY至失败耗时，均非成功Finish成本，也不因cold完整性PASS洗掉失败。

## 实际阶段数值（秒，均模拟时钟）

| ordinal | 声明context / 事前候选 | 首PREPARE时刻 | PREPARE→READY | PREPARE→完整requested CLIMB成功 | 原结局 |
|---|---|---:|---:|---:|---|
| 01 | g01 / left / original | 95.370 | 13.500 | 23.540 | 原成功 |
| 02 | g01 / right / +0.04 | 85.900 | 13.425 | 24.185 | 原成功 |
| 03 | g02 / left / −0.04 | 95.465 | 13.565 | 23.245 | 原成功 |
| 05 | g09 / left / +0.04 | 97.760 | 13.440 | 23.380 | 原成功 |
| 09 | g01 / left / +0.04 | 95.370 | 13.375 | 23.475 | 原成功 |
| 10 | g01 / right / −0.04 | 85.900 | 13.625 | **None** | CLIMB started后base_collision |

这六条有6个不同完整48槽向量、4个不同public45＋age向量，均非原TRAIN6的精确数值重复；**不据此宣称独立场景、可学性或泛化**。bulk仍只有一个既有TRAIN祖先，固定4几何/8context，不是4个独立holdout。

## 对准备路径评价的具体约束

1. **局部缩短并不等额传到后继。** 01/09同声明g01-left、同95.37原查询时钟，实测public45＋age逐值相等，候选offset不同；+0.04局部READY少.125s，但完整requested成功仅少.065s，其后CLIMB多.060s。只是两次既有采集的阶段差，不是因果或本方法收益；未证明RGBD/全部公开观测或隐藏世界同一，不能叫严格同起点反事实。
2. **达到READY不等于完整后继成功。** 02/10同声明g01-right、同85.9时钟，public45＋age相等；两者都READY，但+0.04完整成功，−0.04在后继CLIMB碰撞。10提前停止不可作为更便宜的完整成功路径。这是当前评价必须保留失败/UNKNOWN的真实案例，**不证明优化器能够事前预测、也不预设需挑+0.04固定获胜**。
3. 不能把这两个观察硬编码为V4路线/权重或重训现critic。原frozen fit3371ac20…/model a8b1f165…保持；本轮无fit、refit、CAL/VAL评分或WM forward。完整V4 cost provider/准备退出变体与实时query仍需真正接通，不能拿回顾端点充在线预测。

## 原件与代码

- 本地只有约30KiB标量＋SHA/指针：`/home/yuanyue/reach-ability-research/operations/BULK24_FIRST10_PREPARATION_ENDPOINTS_20261116.json`。
- 完整源绑定汇总（含源pin目录）留46308：`/mnt/yuanyue/reach-runs/bulk24-new-closed-public-boundaries-20261116-v1/FIRST10_STAGE_CONTRASTS.json`，SHA **97509b4ec8b4262fe497201144ea47ee2c46eb100cc11209b670bb1188b0d29c**。五条新48槽/geometry记录仍仅远端同目录；01原报告不重写。
- `operations/measure_bulk24_public_boundary.py`只读提取/原端点绑定；`operations/summarize_closed_bulk24_prefix.py`核全部10分母与两个声明context对照。25项针对性软件检查两端过，包含新增格式/误绑定/缺started/别的owner/错failure clock/失败不造receipt的拒绝，非25次物理试验。
- 旧closed实验与全部dirty、箱参数/scene6394740e…、原Actor/12N/4s/FF/QP/FIFO/CLIMB stop均不改。Data单owner，原bulk driver不中断/不代重派；V4新world/zero/main仍0，原WM真实restore仍1、现场query/forward仍0。

## 接续

最新总计划bdfc613c…已读：新增V-JEPA并行/低优先资源边界不改变当前V4五组或旧数据用途。优先与AINav新cold入口/公共语义caller接当前observer/issued-history与WM-anchor target8；Reach自己完成共同名义后继评价，不推给Data。收尾已核Data原件：00:41 stage19 source/3 base全SHA通过，00:47新component program b125b188…/466-member inventory已出，均no H write/dispatch；GPU0空闲/锁free快照不是lease，不冒zero已开始或通过（source-stage-proof SHA4fb4d977…、inventory-control-proof SHAc439b2ae…，均在`/home/yuanyue/main/work/data-team/manifests/V4-native-components-46308-20261116-v1/`）；.20→.60的原20cm能力缺口/static deck及完整terminal不得绕过。下一次正式原件到达可直接增量消费未读条目，不重复本6行/不追胜重开，必要前置未变时安静等待实际caller增量而非继续堆fixture。
