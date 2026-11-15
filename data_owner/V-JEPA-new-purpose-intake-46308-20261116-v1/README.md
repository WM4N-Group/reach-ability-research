# 新增V-JEPA分支：Data已读新计划，当前用途隔离不变

已读2026-11-16 00:03新主计划34c169d5…及J组README/PLAN。V-JEPA组独立负责选定合法编码器/技能条件预测器、序列提取、训练/离线评价与推理接口；Data负责其未来明确新用途cohort的真实采集，不代写神经训练表/预测器，不要求其等V4五组/百级全部齐。

当前bulk24/critic新数据、旧audit/EVALUATION_ONLY不能直接升级V-JEPA训练许可，也不从本批原件release宣布J1 dataset ready。待J组给具体新用途/过去输入与未来监督分离/共同技能参数/组split及最小采样停止规则后，沿现采集器新scope/新freeze收集；不新增通用采集平台、不热改当前24。现有记录能力与该组全部必需字段覆盖仍应按实际接口逐项确认，不用shape或源名称猜齐。J组自己提取未来序列和mask，未来实际motor序列不冒决策前候选输入。

新J模型先独立验证，再单独登记只换WM的未来对照，不成为当前V4第六arm，不热换原7a6/critic或恢复旧WM/DINO/Actor训练。J组GPU训练与Data按fresh资源协调，Data仍唯一物理owner，但这份收件不授予新lease/显存或声称组已运行。当前requests目录未见Data具体cohort请求，不据初始STATUS推断对方未开展J0工作。

当前V4及固定bulk继续；Data没有创建J组聊天/agent/Goal/自动化、下载权重/环境或执行训练/forward/新采集，也不写H。原申请/源SHA与边界见Data-new-purpose-boundary-ack.json。
