# G2新批24：原full4祖先内的lane×width覆盖采集（已预登记，未派发／不准refit）

2026-11-15 16:40:13，已固定 `protocols/2026-11-15/G2-bulk24-lane-width-new-purpose-v1/BULK24_COLLECTION_PROTOCOL.json`，SHA **0f9e0e03a4cdf8263b1c69f69db9697968040023f42d4c1f383a320631d9e57e**。不是T-COMPLEX原生A/B，也不热扩旧TRAIN6/12根。

## 为什么选这24，而非照目录跑60或重复至100

AINav source `0fff23aaf80d9a4ce0b3f34d7935df0ed1bab181`提供10个真实几何配置，均原full4祖先。首批只选事前两极lane −1.75/−2.15m × B宽1.4/1.5m：**bulk-g01/g02/g09/g10**。每几何left/right两原ground prefix，每context原/+.04/−.04三候选各一次，共24 main上限/8context/4几何/**1既有TRAIN祖先族**，不是24独立scene/新holdout。固定循环Latin arm顺序、seed4301，不用失败反馈选case/seed/重复。

问题是：这些任务相关几何变化能否在**原first-CLIMB-PREPARE的固定48槽**产生有效可辨性，还是暴露profile别名/缺信息？改变lane会同时移动原B/C/高台和任务goal-Y，**不是同世界目标不变**；B宽度改变支撑/视觉几何。保持原材料、Actor/成功安全门、同common-stow与原NAV→PUSH→CLIMB消费。原48不含scene/case标签，也不新加私有pose或未来后果，RGBD只保原件不悄悄扩特征。即使图像SHA全异也不自动叫有效组；round1e−6状态计数只是诊断，不是物理不同/learnability/安全保证。若profile无法分辨，完整报告负结论，不刷随机输入凑十组或100条。

## 给Data的实际装配字段

代码在 `/mnt/yuanyue/reach-ability-research`；上述协议/源矩阵小副本随Git部署。AINav immutable source根：

`/mnt/yuanyue/ainav-compute/code/0fff23aaf80d9a4ce0b3f34d7935df0ed1bab181/ainav`

从其 `development/bulk_registered_conditions_v1` 取 `source_delta(enabled=True)`，**只在新Data source snapshot**安装额外plan；原integrated代码/精确validate_protocol/原full_course/HostProfile/candidate API不改。每行按：

```python
selection = BulkCondition(row['group_id'], row['prefix_side'], row['candidate_id'])
condition = build_condition(selection=selection, source_root=new_source_root,
    integrated=original_integrated, host_profile=original_profile,
    candidate_api=original_candidate_api, enabled=True)
```

对照协议同condition_key的原requested_intents/condition SHA、同scene的planned original native protocol SHA及row的preparation_payload。使用原opt-in3 requested-intent consumer/max_requests3和原prefix_bindings，在fresh tick0绑定实际candidate。**原native training_allowed=false不回写**；新用途/role由预登记后的新acquisition manifest、freeze/program/scope binding记录。源码返回UNASSIGNED不等自动准入，Data按新协议显式分配TRAIN用途，而不是把旧DEV改role。

这些原request/payload/原native protocol SHA已由原source helper的pure函数/原validator检查24组合一致。该检查使用source-owner AST软件harness与临时小source副本，**world/Actor/物理/实际数据均0**，不能当新布局native资格。Data仍需自己的source/程序/环境/Model/原流/zero/lease；不得借用T组件成功zero给不同程序。

## 原门、排程与收束

- 整批最多24新scope，各zero≤1/main≤1，无自动retry/replacement/同seed复跑。原每root主sim240/主wall2400/zero wall180/CPU2/RSS4GiB/ownGPU3GiB/输出1GiB外watchdog保持；原native420门不热改，zero/aux/失败费用单列，全项目旧未知不补0。资源/容量由Data fresh核，未预约GPU/存储。
- **T-COMPLEX full程序资格→A/B/live视频优先首资源窗口**。bulk合格组可以先滚动，不等10几何全部动态合格；不能挤占T或绕旧锁开第二物理owner。原CAL08/09和VAL独立旧协议不改。
- 按固定ordinal推进可准入行，可按真实容量逐GPU并发；不能因原生成败替换场景/候选。共性source/identity/安全实现故障停该source版；普通单根失败保账，不为了隐藏失败停掉其它已合格行。未准入/未开始状态明确保留，不冒完成或丢出分母。
- 必须发布每个固定行的PREPARE到达／未达／资源censor／原门失败／UNKNOWN／成功与全部成本。上游未达不造48槽或CLIMB负标签，失败elapsed不作成功成本。批末不自动扩成其它36目录组合。
- **这只是新用途覆盖采集，不授权重新fit当前冻结model**。TRAIN6 fit3371ac20…/model a8b1f165…/原CAL/VAL继续；本批所有变体同TRAIN祖先，不给新模型独立holdout。任何新model版本需另一个在训练前固定的训练/评价manifest及实际source/feature/label门；本collection文件不直接交旧train-only当训练许可。

当前本批新scope分配0/main0/真实有效组0，Data接收/队列未确认。不是经济/消费签字等待：技术门合格即可由唯一owner落实，不需另造NN表或审批层。证据在本组ignored `evidence/2026-11-15/T-native-components-pass-and-bulk24-registration-v1/`。
