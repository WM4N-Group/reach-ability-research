# D3即时交付：原单次predicate＋原clock＋有界sink（非原生准入）

已接2026-11-17 **15:47计划**：优先形成最多1main首条D3原生证据，必要独立对照最多1main，不等待C/D/J/Sim2Real签字；已登记DEV场景可复用，新诊断目的/分项观测/新程序明确即可。18:00是交首证据或准确阻塞的检查点，不是自动开跑/放宽门。

## 固定的首诊断问题与case输入

建议首个case复用**已登记E20 prearrival40 DEV物理场景与04a控制配置**，保原40mm brake/goal/Actor/原逆序卸载和NN/placement/STOW/安全条件，不扫margin/换seed/改变策略追胜。重新自然执行前驱NAV→原首PUSH，只问：**首次已连续确认true之后，哪一个本次原settled分项变false；该样本在原阶段字段中位于何阶段？** 多个分项同时false照录，不能伪定唯一动力学因果。

这是新诊断目的、前瞻逐原调用分项，**不是复开/续跑旧E20、找回旧27.41映射或为补旧日志原样派发**。旧失败及全部费用保留。主程序第一条证据就发布；若未确认/未丢失/早期安全或资源停止，明确未观测/UNKNOWN，不盲加main。若完成原首PUSH，则止于该原真实receipt边界，不为了凑原V4整链继续CLIMB；任务结果与诊断取证分开。

Data现owner冻结精确新case和资源/次数/STOP后执行；建议首main≤1、own-zero≤1、retry0、task≤40sim/8000 issued commands/8128 driver calls、main≤1200wall、zero≤300wall、每scope≤4GiB、sink每world≤4096rows/8MiB serialized payload。Data可在首次freeze前收紧/核实预算，运行后不延长；这不是本组对运行/容量/lease的批准。必要对照不默认派发，计入总诊断上限。

旧E20 seed未知，不能宣称新旧隐藏态同seed/配对；不为此另换seed寻胜。相机沿旧actual lookat[7.5,0,.4]/distance20/1280×720/10Hz/azimuth110/elevation−58，原生直接1×全尝试片，失败也交，不回放重渲染。

## 精确代码/绑定点：不要绑错env，不要重poll clock

1. SDK新文件用既有a1563461…候选（原399aada0…仅PushSettled.__call__展开，原helper各一次）；**本交付不再改该文件/原clock fd1a49df…/Actor/guard87a**。新SDK根及所有原源/别名/权重/模块导入由Data整程序freeze，不能热改旧根或直接更换原文件。
2. 注册目标采用原`registered_target_context.make_target_context`返回的**view**：原函数最后已构造ClockedNativeSettled，随后refresh并return view/receipt，尚无stateful predicate call。Data在该返回边界、原NativeMachine第一次termination之前绑定`bind_clocked_settled_sink(...)`。`TargetBridge`复制父bridge变量时故意跳过callable，故仅绑父p不会传到view；不可通过放宽missing-sink绕过。
3. bind要求clock.reads/advances=0、duration0/contactFalse、不reset；允许自然前驱后的fresh selected view，不要求物理世界时间0。runtime.sim.data、view.data及clock.data必须同一世界/选中box，scope/world_role明确；task/aux各注册独立sink，aux不能算task证据。任何实际调用该新SDK谓词的aux/env也必须显式绑定兼容sink；本helper只接受原clocked view，若有未clocked aux路径，需owner准确说明/绑定，不能blanket skip。
4. owner传原耐久writer（接收JSONL bytes并返回非空evidence-ref）、read-only phase getter（仅原阶段字段，不调用term/measure/report）、phase_source_ref、scope/world_role及有限预算。例如phase未构造就显式UNKNOWN，不猜阶段。使用原ScopeIO/原动态STOP和资源账，不另建后台线程或第二物理owner。
5. SDK回调在原native state更新之后、**clock post-call缓存更新之前**执行；sink只读last_read_time/previous-native-time/reads/advances原字段和实际time/200Hz tick，绝不调clock.report/_consistent/__call__。首个确认/随后首次false索引由已经确认写入的原tuple生成，非10Hz视频插值/新谓词。
6. sink同步序列化/原writer ACK；容量、上下文、写入或ACK异常立即传播，原clock失败/父STOP关闭，不跳样/不回滚native.duration/不retry。writer异常可有部分尾写，report保writer_tail_unknown，不将未ACK当0实际费用/0原生调用。payload budget不等ScopeIO/盘总用量；父层仍记真实task+aux/视频/最终收束。
7. sink.report仅自身计数/首loss evidence-ref与inclusive wall；writer wall包含在total内不相加。原生开销未测。Data原结果发布原component rows、首true/false、原阶段/clock、实际usage/STOP/cleanup/原片并给CONCLUSION/UNKNOWN；不能把CPU case或首次loss flags当Actor重训必要性。

## 当前验证

7项新增CPU：46308原私有Python3.11.16、真实CPU Torch＋原ClockedNativeSettled＋a156原谓词，env/phase/writer明确synthetic；只在本进程自有临时目录放两份源码供inspect，退出清理，无peer源/进程/H/锁写入。证明重复200Hz读无第二native call、回调clock前后语义、首true→false当前phase/flags、容量/写入/ACK失败不可resume、selected-view一次绑定；没有Runtime/MjData/world/Actor/GPU/WM/API/物理。
旧9predicate tests沿用不刷；当前仍未commit/push/部署/注册D3scope/lease/zero/main。Data不能把源CPU通过当全程序/native资格。
