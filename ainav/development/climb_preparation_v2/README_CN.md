# CLIMB preparation 开发版：安装身份封存与原生 latch 条件

2026-11-14，承接11:15解耦计划。**这是后续开发版，不是当前Stage-B实验包的替换，也不是新实验请求。** 当前三分支继续用已经冻结的v1，不搬仓、不重装、不热补，不重跑旧scope。

## 1. 接口、默认与准确差分

`/home/yuanyue/main/work/ainav/development/climb_preparation_v2/climb_preparation_candidates.py` 沿用稳定接口：

- `public_candidates(...)`：原ground-source公开三点，original/±.04；不增连续域。
- `selection_from_payload(payload)`：仍是原v1 payload schema；不增字段。
- `bind_to_host(host, caller_module, selection=..., enabled=False, emit=...)`：默认off不读host；控制/原意图/READY/stop与guard不变。

AST逐定义比较，仅 **`bind_to_host`** 变化；候选生成、payload、source transform/restore、caller delta均不变。不另造loader/协议/manifest。需要未来实际采用时，应从这个**同一个module**同时构造selection并调用bind，不能混用两module的严格dataclass实例。原完整common-source和显式consumer可继续按原接口使用；新的module字节必须进入未来自己的program freeze，**绝不能直接覆盖当前冻结源路径**。

## 2. 已复现的 guard 覆盖缺口与修复

v1 callback验证调用当时的root/executor/factory/current intent一致，但没有把安装时的身份存进closure。软件故障注入中，将host root与factory/executor引用成套换成另一组一致对象，v1仍返回候选。它不是“.sim必须等于PUSH proxy.sim”的旧错误；保持proxy/view分离仍是必须的。

开发修复：

1. 安装时要求root/factory/executor一致、fatal=false、FIFO空。
2. 以强对象引用封存安装时root、root.sim、model/data/FIFO以及factory/executor/coordinator。
3. 目标proposal前、evidence sink返回后都核同一安装身份；异常只拒绝、不rollback、不发命令。
4. **不封存**会正常演化的session/option或immutable reference table；原完成PUSH proxy/TargetBridge同model/data/FIFO仍合法，不压平它。

8种软件对象替换（root/world wrapper/model/data/queue/factory/executor/coordinator）已逐项复现v1允许proposal、开发版拒绝；另外覆盖sink内same-content coordinator/world-wrapper替换、dirty安装及正常owner接续。

**当前运行影响：** 没有观测到Data运行发生上述替换。已查看的原`FullCourse.__init__`建立factory/executor、`ExecutionJudgedFullCourse.__init__`建立coordinator；当前worker按单root原host生命周期使用，不在任务中做这种graft。该问题是API故障注入下的拒绝路径补强，不应据此宣称当前物理失败或要求无证据热补／重跑。若真实发现root/queue/owner被替换或一致性异常，仍须停止受影响运行并由owner核查，不能以解耦为由绕过。

## 3. 可直接给Reach使用的原请求语义结论

本节直接给稳定接口消费者，不经Data补研究评价。沿用原源码与此前实际profile证据：

- `nav_efficiency.py` SHA `878fe53241784c6f2dfbd8125b0664a1607033460766847f0876c7f1c64d0efd`。
- 原`navigation.py` SHA `7b5758a489cb3b5a238b488dcff2fc38f8dde1027e6381c0536a9f4eb753396a`；`control_profiles.py` SHA `4bfb33ccd7b27ea861f44abca030094e28f33e621271df8d154b34965021eb72`。
- 原profile记录SHA `ee41a8abe1a33fa83a84d2e4b495cfaeb8f3450cb24329f87cdf2c0d84d0bbdc`，不是本次新拟合/新合成科学数据。

### 精确条件（不换δ、profile或seed）

| 条件 | 原代码行为 | 对候选比较的含义 |
|---|---|---|
| distance≤.065m | position latch=true | 该候选XY请求置零，不代表实际速度0/稳定/完整arrival |
| .065m<distance≤.13m | **保留原position latch值** | 同一XY/yaw无法唯一确定请求；缺历史就UNKNOWN，不重置latch方便比较 |
| distance>.13m | position latch=false；此前true则增加一次reacquisition | 严格外边界，第三次reacquisition按原source censor，非允许retry/成功 |
| yaw error≤.075rad | yaw latch=true | 与position latch独立 |
| .075rad<yaw error≤.25rad | 保留原yaw latch | 同样有历史依赖；不能只用平面距离代替整请求 |
| actual cold elapsed<3.24s | 原request为0 | RegisteredCompactNav已恢复原skills warmup；不是helper的.24s，也不是到达 |
| 已warm、position未latch，abs(body lateral error)≤.035 | 横向request=0 | 边界是原计算值上的严格`>`，不能给误差加人为容忍 |
| 已warm、position未latch，abs(body lateral error)>.035 | 横向request=.4×sign(error) | 原nonzero floor与clip饱和：不同距离常同请求，不按目标距离估速度/耗时 |

三个目标以原参考为中心且横向±.04；在参考附近共同inner-latch区域非空。理想平面几何中，离中心严格小于(.065-.04)=.025m的圆盘是三者同时可latch的一个充分子集，**不是完整NAV+arrival误差界、不是允许在线使用的base pose，也不保证原CLIMB READY/动态稳定**。数值边界仍按原source实际浮点运算，不能借此调门。

前版Reach `nav_request_equivalence.diagnose_lateral_errors`已经覆盖单axis floor/clip，本组不复制其API或另做同一评价器。本次补的是此前未覆盖的原position/yaw hysteresis及reacquisition拒绝语义：对三候选，应将“当前状态的瞬时目标误差”和“本分支原controller记忆”分开；不知道记忆或未有实际control事件就不能判整请求/轨迹等价。

**信息边界保持：** 当前host未公开sim base world XY/quaternion，latch/history也不能从私有审计量偷渡为planner输入；公开RGBD/q/dq/速度不等于已接入全局pose。以上只是源语义/离线诊断，不是新cost模型/部署selector许可。未执行分支的未来成本仍UNKNOWN；旧actual不进预测/fit。

## 4. 已做验证与唯一外部阻塞

- 新5项身份/拒绝回归＋新5项**原source AST逐字提取scalar IF**测试；既有25项稳定API/default-off/意图恢复/原12N/代理关系回归复用。合计35执行，**不是35新项**。全部本机3.12.3隔离过，0fail/error/skip，禁NumPy/Torch/MuJoCo/ONNX/network/child attempts空。
- AST slice只执行给定distance/yaw-error的原if，不实现假NumPy、不执行完整EfficientNav.update，不冒RegisteredCompactNav构造、capture、Actor或真实model。远端CPU未执行，物理未资格。
- 原实验release0c17…/299成员及Data worker源未改；本开发模块不在当前冻结程序内。
- 本组开发修复与source条件已可直接使用，无需等Data写新loader/报告。**唯一必须外部证据**仍是Data当期Stage-B三分支的实际控制、原READY→接管/stop及完整终点结果；当前original own-zero已经通过、main由owner继续，后续合法分支无需等本组完整回执。

证据：`/home/yuanyue/main/work/ainav/manifests/climb_preparation_binding_hysteresis_dev_20261114_v1/LOCAL10_NEW_PLUS25_EXISTING_DIFFERENCE_CPU_v1.json`；`COHERENT_GRAFT_ORIGINAL_RED_DEV_REJECTS_v1.json`；`binding-only-v1-to-dev-v2.diff`。

## 5. Reach新开发选择器到本binder的真实API接缝已验证（11:50）

直接导入Reach现有`public_preparation_selector`，没有另造loader/decision schema/evaluator。新6项集成检查实际串起`build_problem → choose → materialize_fresh_plan → 本开发版bind_to_host → 原_native_nav`；保留原完成PUSH root/proxy/view关系，几何入口仍明确software port。

- 无动态预测器时，原default payload能实际绑定并到原NAV目标，`optimized_candidate_id=None`，不冒优化选择。
- 严格UNKNOWN弃权不安装、不发proposal；live PREPARE阶段拒绝materialize。
- 即使传入字符串`FRESH_PREEXECUTION`，实际host已有步数时仍被binder拒绝；字符串不是fresh准入证明。
- selection必须由同一owner版本的`selection_from_payload`生成；v1对象混入开发版严格dataclass检查会拒绝。
- Reach原default不能压过原生entry拒绝；proposal并不等于entry/option执行。

6项本机隔离全过/0fail/error/skip，重模块/network/child为空；无旧actual/新native后果输入或合成cost表，不构建假预测器。源码及输入SHA见：
`/home/yuanyue/main/work/ainav/manifests/reach_selector_binding_interop_20261114_v1/LOCAL6_REACH_SELECTOR_TO_BINDER_INTEROP_v1.json`。
当前Stage-B v1不采用此开发组合，也不因此重新资格或重跑。
