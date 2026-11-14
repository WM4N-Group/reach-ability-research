# G3独立备选：离线失败漏报/UNKNOWN分母（2026-11-15）

G1仍由Data执行，G3此增量不构成其派发前置。只在既有successor_critic的heldout报告中补具体缺失指标，不新建采集合同、wrapper或日志平台，不改变参数拟合/公开48槽/原native门。

- `raw_score_diagnostic`固定以未校准logistic score≥0.5计作“scored success”；是常规符号分类诊断，不是校准成功概率、部署阈值、feasibility PASS或风险保证，不从旧audit或heldout挑阈值。
- `native_failure_miss_rate`：真实native failures中被scored success的个数/真实native failures。没有native failure时为None，不伪报0漏报。
- `success_false_refusal_rate`：真实success中被scored failure的个数/真实success。没有success时为None。
- `failure_fraction_among_scored_success`：scored success中的真实native failures/全部scored success。与failure miss不同分母，没有scored success为None。
- CENSORED不作两个类别，也不作短成功cost；保其计数。未到达决策的尝试继续单独保留，不编输入/预测分数，不能混入“可预测rows”分母。
- 同时给TRAIN-only常量成功score的同规则诊断，不能只报告新模型分数。补READY时间MAE和TRAIN-only均值基线，成功完整时间仍只条件于真实成功终点。
- `full_successor_feasibility_UNKNOWN_rows/fraction`按已准入预测rows（含resource-censored）报告。当前模型未资格，仍全UNKNOWN/qualified PASS0，classifier原始分数可高也不自动改成native PASS；这不等于实际在线fallback率，因为没有在线执行。

在46308的Data既有Python3.11.16解释器执行20项critic检查（原16＋4项新定向）及既有11项feature检查共31，通过。只用测试内显式SOFTWARE内存算术/fixture，不读取真实训练资料或导出权重，不把31项当样本/物理实验。模型标准化与参数仍仅TRAIN拟合，heldout没有调参权；未重复真实数据入口或空preflight。

本次G1新端v1启动失败应归“未到达PREPARE/基础设施或构造资格失败”，不加入native task失败分类/训练。实际判定以Data原zero result/ledger为准；usage_known=false不能因记录sim_s0就报完整成本0。旧失联attempt和新端启动attempt分别留分母，不互相覆盖。

真实训练数据仍0、fit0。未来G2合格新协议需绑定实际learner commit及这些诊断约定；没有做校准、部署资格或导航收益评价。只有这些前置满足后，才谈G3研究验证，不以此软件增量宣告G1/G3完成。
