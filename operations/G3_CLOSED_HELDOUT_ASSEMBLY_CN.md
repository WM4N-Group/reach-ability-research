# 冻结模型的CAL/VAL闭合数据装配入口（不拟合、不采集）

> **2026-11-15 16:12更新：** 正式CAL07 release9249faef…现已独立消费，原reader提取717aa3ba…/48槽、SUCCESS、READY13.495/请求CLIMB终点24.095sim。仍仅1/3 CAL，未运行真实阶段装配/评分/refit；下文“正式release尚未消费”是16:08之前快照。scalar与费用见operations/G3_FIRST_CAL_ROW_SCALARS_20261115.json。

2026-11-15。首次实际TRAIN-only fit保持原3371ac20…/model a8b1f165…/TRAIN行882ca00b…，不是新增fit。总计划14:00/b2fb786e…未变，T复杂任务合格时仍优先资源。

原learner已有`calibrate-frozen/evaluate-frozen`，但读取的是完整dataset而非三份Data release。本次补齐**已提取且完整闭合heldout→保留原TRAIN的dataset**步骤；不为了凑输入重新fit、改derived protocol、改角色、丢未达或提前评价单条CAL。

- `frozen_heldout_dataset.py`在纯函数中检查原TRAIN-only数据/协议/model内容与TRAIN快照不变，按原ordinal合并每阶段全部预登记heldout。CAL须07—09全部报告，FULL须07—12全部报告；缺一、重复、TRAIN/VAL改CAL、UNKNOWN后决策异常、ABI/账本不一致均拒绝。未达保成本/分母、不造48槽/负标签；censor不转native失败，失败完整成功耗时仍None。
- `build_closed_frozen_heldout_dataset.py`从实际`TRAIN_GATE_AND_FIT_RELEASE.json`精确SHA读原4份TRAIN artifact，每个extraction report须显式PATH=SHA、其原source pins在装配前后逐SHA一致。写新exclusive dataset和assembly gate，不覆盖原fit/数据/协议；本脚本不调用fitter、scorer、world、Actor、GPU，也不写Data H/lease/派发。
- 12项新装配单测＋已有32项learner/stage检查合44项软件检查通过；所有新测试的模型只是显式SOFTWARE字典，未训练任何新模型。不是44真实样本/heldout指标。尚未在不完整真实CAL上运行装配或评价。

## 实际原件到达后在46308使用

先按每个Data正式release和SHA运行既有`operations/extract_new_critic_attempt.py`，同一原first-PREPARE/48槽/标签源门不变。不要用工作目录里的未发布main-result替代closed release，不能从旧DEV换role。原extractor的`AWAIT_COMPLETE_TRAIN_GATE`/`complete_TRAIN_gate_pending`是通用历史提示，CAL行仍按原split审查，不因此要求再次TRAIN fit。

```bash
cd /mnt/yuanyue/reach-ability-research
PY=/mnt/yuanyue/data-team/env-native-v1/bin/python
$PY operations/build_closed_frozen_heldout_dataset.py \
 --training-root /mnt/yuanyue/reach-runs/G3-TRAIN-only-20261115-v1 \
 --expected-release-sha 670d4eb5062f903ecdadb200acbd2744647388888f8070e1066a527a2813bdd3 \
 --authorization /mnt/yuanyue/reach-ability-research/protocols/2026-11-14/high-level-critic/USER_AUTHORIZATION.json \
 --phase CALIBRATION \
 --attempt '<ordinal07-extraction.json>=<sha256>' \
 --attempt '<ordinal08-extraction.json>=<sha256>' \
 --attempt '<ordinal09-extraction.json>=<sha256>' \
 --output-root '<new-exclusive-CAL-assembly-directory>'
```

随后才以同一个原`DERIVED_TRAINING_PROTOCOL.json`、原`TRAIN_FROZEN_FIT.json`与新`CLOSED_FROZEN_EVALUATION_DATASET.json`调用既有learner `--phase calibrate-frozen`，冻结CAL报告后Data才能独立准入原VAL（本脚本不是VAL派发许可）。CAL仅诊断，模型/阈值/标准化均不调整。FULL_COHORT只在原07—12完整release已到时装配，再`evaluate-frozen`；不把原先partial报告覆盖/升格。

当前已核Data接收一次fit并启动原CAL07；工作目录已有main/cold metadata，**正式完整closed release尚未由本组消费，CAL3/heldout评价仍未完成**。不将main PASS元数据当完整批门/泛化证明。raw48、模型、完整数据/原流始终留46308，不拷本地/Git。
