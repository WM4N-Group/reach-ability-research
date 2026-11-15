# T-COMPLEX首个真实A main：实际捕获完成，首PUSH前RGBD同色组件歧义停止（不是几何死局／方法胜负）

2026-11-15。原program `626400b8…`的唯一main已真实失败，不能继续依据17:01的在途快照写“仍运行”。原root result SHA **8295239278efda4ee8b058d70a40de28825bae8a568ec1cc0c703944a4c4ce23**；main ledger closed=true、root ledger stopped=true。Data权威CAS收束未由本组独立核到，不能擅自重派任何zero/main。

## 本组实际核到的原证据链

1. 原实际SupportedCapture完成事件已出现；任务world **448步/2.240sim**，这448条是实际capture阶段电机命令，**不是任务NAV/PUSH动作**。原journal462行全部链验证过，文件SHA `0c8fa13e…`。
2. 第一真实public Observation同钟2.240，SHA **31b92b0e…**，`objects=[]`。静态地图仍声明18 NAV/三个对象ref；声明不等当前视觉身份，也不等native READY。
3. Reach greedy实际提出第1个bundle：`cuboid_a -> (1.85,0)`，名义root6候选，route仅初始reference(-.08,0)所以无名义NAV。原semantic intent已选择，但原source判断为BLOCKED：`Current original RGBD association unavailable; no static-pose substitution`；Reach按原预登记fail-closed退出。
4. 原`native_option_installed`与`intent_native_execution_bound`事件均**0**。无任务NAV/PUSH/placement/stow、无几何死局实际轨迹，也没走到原PUSH或CLIMB controller失败。不能拿这条当G3负标签、三有效选择或“局部贪心把出口堵住”的证据。

## 已把泛“关联缺失”定位到原pixel proposer的明确域门

仅在46308对**既有2.240sim原RGB/depth/K/T**调用原纯像素proposer一次离线诊断：原source SHA **837e95ec…**从同一frozen program逐SHA核，禁止torch/mujoco/onnxruntime、子进程/网络；未起Actor/Runtime、未生成新帧/重渲染、未读私有world pose、未拟合或改阈值。

原函数检测到两个**warm**候选：

| frame-local ref | 实际bbox xyxy | pixels / valid-depth pixels | geometry_valid | 原single_visible_hypothesis |
|---|---|---:|---|---|
| visual-proposal-0 | [22,89,170,94] | 727 / 727 | true | 同family片段/实例未消歧，拒绝 |
| visual-proposal-1 | [24,46,169,74] | 2153 / 2153 | true | 同family片段/实例未消歧，拒绝 |

所以不是无RGB/缺depth/数值缺失后随意推测失败。原`RegisteredBindingResolver.observe`先调用`single_visible_hypothesis`，两者都被原保护门拒绝，尚未进入可用对象的一一几何绑定；source没有合法当前NativeTarget。两个component究竟是一个箱的遮挡片段还是多个物体，**仍未识别**；不能凭颜色或这张图指定物理ID，也不能挑大块/并色/降低pixel阈值“修通过”。

实际192×128首query原PNG仅2.4KB已按原SHA保在ignored evidence，未放Git；原depth/输入数组/录像仍远端。纯像素离线重算只用于诊断，不是额外在线决策、模型特征扩展或新训练样本。

## 费用与录像口径

- main实际含aux **8.745sim / 844.490240974ledger wall / 218453439bytes scope highwater**，usage_known=true；其中world task2.240、aux6.505。result入口wall844.401510896与ledger收束口径不同，不混用。
- own-zero6.505sim/36.037662184ledger wall先前已记；各phase的scope highwater不可相加当总存储，旧component/失败/未知账也不抹。
- 真实live母数据 **23帧/960×540/10Hz**，capture grid完整、结束world2.240，close_errors=[]。仍未编码1×/配对影片，不能用23帧启动片当完整方法能力录像，也不为补片重跑。若后续B产生原片，A须明确标原终止时刻，不拉伸/重渲染。

## 下一项与禁止误归因

这是首个DEV source/method诊断pair的真实负结果，不是benchmark胜负。B终态尚未由本组消费，不能由A失败预判B成功；即使B后续通过，也必须区分**初始可观测性/准入差异**与原拟验证的延迟通道耦合，不能自动归因“有限前瞻避免几何死局”。

AINav下一具体入口是原`RegisteredBindingResolver.observe → single_visible_hypothesis → current one-to-one association`的source可观测域/原合法感知准备映射。Reach已指出本common nominal model没有观测可用性预测，当前原门正确拒绝不确定身份；不能从静态anchor/GT制作替代target。若需合法原NAV/视角准备或公共拒绝反馈，必须新source/新协议、两策略共用、明确不算额外有效选择，不能改当前pair或特意插NAV/换颜色/调门去追预期胜负。本轮不发新运行、不改他组源/H/锁/进程，不擅自决定B派发/停止。

当前TRAIN6冻结模型/原CAL-VAL、bulk24覆盖协议及所有dirty/closed均保持。完整scalar来源在 `operations/T_COMPLEX_01_FIRST_MAIN_ASSOCIATION_FAILURE_20261115.json`。
