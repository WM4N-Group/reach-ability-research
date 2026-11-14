# Reachability 文档

当前只维护以下五份文档。**新窗口先读[当前交接顶部快速接续](AGENT_HANDOFF_CN.md)，再读目标与main最新事项；历史结果按需查阅。**

1. [当前交接](AGENT_HANDOFF_CN.md)：顶部为新窗口当前状态、最新上游变化和首要待办；下文历史按需追溯。
2. [项目目标与验收](PROJECT_PLAN_CN.md)：研究边界、评价指标和安全门槛。
3. [公式方案](IDEA_PAPER_CN.md)：先读顶部当前公式与限制，历史候选按需查看。
4. [关键结果](RESULTS_CN.md)：已核验的结果与证据，结论带对应版本。
5. 本页：文档维护规则。

旧的逐实验 Markdown 已从现行树移除，可通过 Git 历史查看；已被检查脚本引用的 JSON 证据保留在仓库根目录 `evidence/`。大报告、视频和权重仍在仓库外 `../artifacts/go2-piper/`，以哈希和实验版本核对。

以后直接更新对应现有文档，保持 `docs/` **最多五个文件**。只有用户明确要求独立文档，或现有五份无法容纳必要的可复现规格时，才增加文件；增加前先合并或替换旧文档。实验新结果先写入 [关键结果](RESULTS_CN.md)，不要按一次试验新建一份说明。

当前执行口径：main已通过[Reachability正式指导（已合并Q1–Q4）](/home/yuanyue/main/docs/Reachability小组_推进指导与交付要求_2026-10-16.md)明确异常标签、净空辅助量、唯一实现分工和两组共用36回合预算。按[项目目标](PROJECT_PLAN_CN.md)推进R0–R2与R3草案，[共享合同与标签入口](/home/yuanyue/main/work/shared_push_v212_20261016/README.md)已有三条历史真实标签样例，待双方对齐。历史整链日志不作当前待办。

当前实际数据产物：P0三条已登记训练序列的491查询净空标签与规则参照，见[关键结果](RESULTS_CN.md)。完整标签登记在main共享labels_index，账本／split同步与双方对齐尚待完成，已通过共享实施反馈交给main。

## main新沟通入口

- 正式执行：main `docs/`两组指导已吸收D1–D6与Q1–Q4；旧逐项答复归档供追溯。
- 日常同步：[Reach三文档入口](/home/yuanyue/main/反馈与同步/Reachability组/当前进展.md)。固定维护当前进展、下一步计划、问题与待确认事项；一个事项只有一个主记录，跨组回复写回该条目。
- 当前跨组主记录：[WM-01／WM-02](/home/yuanyue/main/反馈与同步/世界模型组/问题与待确认事项.md)。本组不复制其状态，不把单方回复当共同确认。
- 数据与合同仍用main共享数据入口。带哈希的历史JSON保持原字节；旧路径按[整理映射](/home/yuanyue/main/work/document_organization_20261016/sync_layout_v2/path_map.json)和整理前副本追溯，不为修链接改写历史证据。
