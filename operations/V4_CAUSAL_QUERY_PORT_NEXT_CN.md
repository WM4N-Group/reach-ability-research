# 原WM因果query producer已接成直接接口；现场callback资格尚未完成

2026-11-16（北京时间）。沿原V4五组/current100次API cap/20cm技能与三箱参数策略，未改用户平台、Actor或原门。

## 本轮新增实现

- `v4_causal_wm_query.py`把原**BehaviorQueryBuffer、filter_full_native、resize_packet**三段精确源码接入原7a6 loader/adapter。`inference_source/original_behavior7a6_query`按完整顶层定义原行逐byte提取，manifest含原whole-file SHA/行号与提取SHA；不导入原trainer或native-control模块，不改过滤/插值算法。
- `build_original_buffer`生产模式只收真实strict-restore7a6模型标记，连接原normalization和原source函数；`CausalWMQueryPort`可直接作为`OriginalBehaviorWMAdapter`的query_provider。source接原observer packet→`on_visual`，原accepted200Hz位置参考/实际owner→`on_issued`，provider按当前原public45D构造query，候选不能覆盖observed owner。
- target8必须由source的**WM实际anchor图/时间**提供并逐SHA匹配，不能拿fresh off-grid VLM图或旧left alias代填；无descriptor保None。生产只收原public IntentBatch/Observation，不允许private ExecutionBatch进入。原3真实10Hz图/连续200Hz窗口与尾部、previous-action一致性、当前body clock和image-age检查均保留。
- fixture模式强制输出`EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT`，不能因给“CURRENT”标签升级成live。原raw adapter仍先核source_role再做预测；closed-audit不能作为live provider。默认生产拒随机/FakeModel、FakeBuffer或错源。

## 验证的真实身份

- 本机新增10项源码/port/时钟/fixture隔离单元检查通过；合计**110项纯软件回归（72新增＋38旧）**。
- 另在46308私有现有环境做一次**明确SOFTWARE_FIXTURE**的原函数CPU smoke：调用原resize/Buffer/filter三函数，3个synthetic帧/43个synthetic位置参考跨40间隔＋3tail，原输入存档/clock均过，错误anchor与fixture→live升级均拒绝，临时数组已删除。用的是显式FixtureModel，不加载真实权重，不做真实WM预测/训练，不是实测轨迹或新的native资格。源函数全局SKILLS依赖在此完整接通，不能仅凭AST可编译就称producer已通。
- smoke原件仅小摘要`operations/V4_ORIGINAL_QUERY_PORT_CPU_SMOKE_20261116.json`；**此前真实7a6 CPU restore仍仅1次，未来预测forward0、真实当前V4 query0、Actor/world/API/fit0**，未为这个smoke再恢复模型。

## 新原件权限与source到件

- AINav新PUBLIC_EFFECTS/DECLARED_MAP/acceptance按本地owner文件manifest逐SHA接收为**开发快照，非immutable runtime/native freeze**。当前共27条公共语义声明：17 NAV/6 PUSH/4 CLIMB、24 anchors；完整cost与实际exit均None、prep/exit variants空。不能把source新文件到件当完整cost provider，Reach继续负责估计/模型，不要求Data代写评价器或“None补0”。快照见`protocols/2026-11-16/V4-public-source-intake-v1/`。
- 旧OBS正式包明确`whole_artifact_model_input_allowed=false`。本轮只读核了公开metadata/记录格式，**没有将其frames/history送入WM**；不能因为现WM获推理授权就改旧数据用途。未拿原closed OBS/A/B做新的WM prediction，也未把原audit当新TRAIN/CAL/VAL。
- source acceptance另要求E实际成功及A—D完整直接live原片，Data可在fresh容量/新authority下并行；不是当前E已经成功或允许Reach另建world/抢卡。当前40cm/static-deck/caller/完整terminal资格仍在AINav侧收敛，没有更改用户场景。

## 下一实际动作

AINav/Data新V4 caller可直接绑定上述两个callbacks与当前descriptor provider，source自己的必要zero/main核实际IO，不再等待本组另造schema或收件签字。Reach继续在相同public capability/效果边界实现共享完整名义cost，不从原WM terminal elapsed/logit伪造成功Finish/READY；PUSH绝对→公开relative action、CLIMB语义destination→原native SOURCE要有显式原binding。现场query/优化/native消费成立前不报有效五组对照。

收尾已核最新00:03计划34c169d5abfc7edc112ac0febd6e372052021d478c847e77c60050791fdd430b：新增独立V-JEPA候选研究不阻V4，当前7a6/五组不热换、不冒第六arm，旧用途不转新训练；Reach职责继续。
