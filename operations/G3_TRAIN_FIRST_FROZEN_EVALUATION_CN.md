# 修复真实阶段时序阻塞：先TRAIN拟合，后heldout只评价

2026-11-15。有限cohort原件SHA仍`2f82530d1f880892c631c7b62cc79bfbd72d57e1b369faf99f542d02d4a53eda`，不修改原预登记域/数量/模型/门。

## 阻塞与修复

协议要求TRAIN1—6闭合合格→真实fit一次→CAL7—9→VAL10—12。但旧`fit_and_evaluate`在拟合前强制三split最低组数，故只有TRAIN时必因缺CAL/VAL拒绝；等heldout补齐再调用会违反预定时序。不是数据缺第三source或另需经济授权。

现在已有明确三阶段入口（同一`successor_critic`模块）：

- `--phase train-only`：只接受已闭合的完整6个TRAIN schedule attempt、原whole-scene map不变；拒绝任何CAL/VAL输入。原class/state/source/48槽门与协议≥3成功、≥1决策后native失败仍检查。只有未来新合规数据才真实fit一次，输出模型、内容SHA、TRAIN行快照SHA和training manifest digest，不提前出heldout成绩。
- `--phase calibrate-frozen --frozen-fit <原TRAIN拟合产物>`：只收已闭合TRAIN+CAL，VAL尚未采集是预定阶段，不是补0。只读同一模型，不调参/阈值、不重新拟合；VAL metrics rows=0/率和误差None，明确尚未评价。
- `--phase evaluate-frozen --frozen-fit <同一原TRAIN产物>`：收完整TRAIN+CAL+VAL，只评价。原TRAIN行快照或模型bytes内容改变、purpose/scene/condition/assigned arm/schedule不符均拒绝。评价报告不再导出第二个model。

对带`attempt_schedule`的新有限协议，旧default `full-cohort`拟合入口会显式拒绝，防止在看到heldout后误重拟合。原legacy完整数据评价接口保留，旧统计/未达/费用逻辑不变。完全未到达仍没有模型输入或successor负标签；censor不当失败、全部attempt账不删。

## 待真实TRAIN闭合时如何激活

本次**没有生成合格训练manifest或真实数据/模型**。六个新TRAIN result/cold/journal/费用闭合后，Reach按原有限协议门评价。No-Go则不fit、不派CAL/VAL、不补类。

只有通过后，从原不可变cohort协议逐字段复制生成新的小型training manifest：保留场景/schedule/特征/模型/停止设置，`collection_protocol_file_sha256`链接原2f82530d…，附原六个闭合证据pin，并将derived manifest中的`qualified_entry_condition_family=true`。不能回写原false或把DEV角色改为TRAIN。训练dataset的同名collection pin与每attempt原`new_use_protocol_file_sha256`必须都匹配它；`preregistration_sha256`则是derived manifest的既有canonical digest。原acquisition时钟仍在原12:41登记之后，不拿fit时钟冒采集前注册。

以下仅是实际有新数据和derived manifest后的命令，不是在本轮执行：

```bash
cd /mnt/yuanyue/reach-ability-research
PY=/mnt/yuanyue/data-team/env-native-v1/bin/python
# 所有输出为新exclusive路径，原TRAIN artifact不覆盖/不重新fit。
$PY -m research.task_conditioned_reachability.execution_preparation.successor_critic \
 --phase train-only --authorization <USER_AUTHORIZATION.json> \
 --protocol <derived-training-manifest.json> --dataset <closed-TRAIN-only.json> \
 --output <new-TRAIN-frozen-fit.json>
$PY -m research.task_conditioned_reachability.execution_preparation.successor_critic \
 --phase calibrate-frozen --frozen-fit <new-TRAIN-frozen-fit.json> \
 --authorization <USER_AUTHORIZATION.json> --protocol <same-derived-training-manifest.json> \
 --dataset <closed-TRAIN-and-CAL.json> --output <new-CAL-report.json>
$PY -m research.task_conditioned_reachability.execution_preparation.successor_critic \
 --phase evaluate-frozen --frozen-fit <same-new-TRAIN-frozen-fit.json> \
 --authorization <USER_AUTHORIZATION.json> --protocol <same-derived-training-manifest.json> \
 --dataset <closed-complete-new-cohort.json> --output <new-VAL-report.json>
```

原45D/特征行/模型权重等产物仅留46308，代码/小协议留本地和GitHub。8个新增定向回归与原23个learner回归（合31）只验证这项真实时序/防泄漏阻塞，不计研究样本/真实fit/优化收益。未新增Data接口、logger、采样门或重新批准用途。后续仍须真实数据、简单基线、三策略和多决策验证。
