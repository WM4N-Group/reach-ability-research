# D3：原PushSettled单次谓词审计（默认OFF，非物理准入）

唯一问题：在未来**有明确新问题且独立获资格**的自然PUSH刹停/卸载过程中，首次持续确认失效的本次原调用，首先失格的是goal-XY、3D速度、contact-seen、tip还是forbidden-contact？现有E20 exact27.41无法回答，不再读同通道或原样复跑补日志；本候选也不证明旧次原因。

`instrument_push_settled_source(source, enabled=False)`默认原bytes不变；显式ON只接受SDK完整SHA399aada0…/原call归一化SHA d3cf0468…。返回**新源码bytes**，不写源文件/安装hook/启动进程。仅改原PushSettled.__call__，其他字节/原reset/Actor/控制器不改。不得热装closed或在途程序。

原hand_contact、push_target（可能lazy创建目标）、box_tipped、forbidden_box_contact保持原顺序且各一次；`&`仍eager/左结合，原0.12m/0.08m/s/.5s/default、dt增量、contact latch、duration reset和返回tensor保持。输出只包含本次已算出的量/flags/前后duration/returned，Python scalar/tuple无tensor/env alias；不二次poll stateful term/Stop/clock。

新owner在原env绑定**单一、有界**`_ainav_push_settled_audit(row)`。sink自行加原实际sim/native-clock、control tick、阶段/实际scope与source identity并接原容量/异常安全门，不能读私有量喂planner。该sink需与Data新程序一同冻结，不能用observer回调代替训练/物理权限；本组不写peer源或代派。

缺sink在原term执行前拒绝；sink/序列化故障在原state更新后传播，不能catch后resume/回滚/重试，原owner必须按既有STOP/cleanup关闭。新增tolist/IO可能有CPU/GPU同步开销，**尚无native开销测量**；有限新诊断需记录运行/容量/费用/stop。不是对root/任意恶意sink的只读隔离保证。

目前只做CPU合成输入差分：原/新predicate同输入流、严格阈值/3D速度、连续.5s与失效时刻、contact latch/reset、helper各一次、异常/无sink/坏sink及源码边界。不会创建Runtime/Actor/MjData/world、恢复模型、调用API或GPU。通过不等实际D3结论，不开放Actor重训/真机。
