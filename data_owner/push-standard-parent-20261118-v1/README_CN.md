# 当前标准 NAV→PUSH L1 parent 源接续（未成为完整运行程序）

唯一 case `PUSH-SDK-STANDARD-NAV-L1-20261117-v1`：seed3701／20ms，原1.2×1.2×.2m、1kg单箱[1.1,0,.1]与机器人[-1,0,.33]，NAV[-.02,0]后PUSH.6m，native/public目标均[1.7,0]；uncompensated，不补.11m、不改原技能/安全/成功门。仍是L1候选，不冒L0或新的90次资格。

- `standard_runtime.py`：直接复用原 `runtime_adapter.construct_runtime` 的camera-only标准配方，**没有额外MJB/独立asset前置**。私有类型仅保留早期partial对象、原三种history初始化元数据；原Runtime.step/构造/独立aux不改，不恢复状态。原registered registry/observer/capture；用原PlacementContract＋RegisteredTerrain接标准域ABI，2.3m仅是目标前沿测量基准面，不添加墙/平台。20mm public、10mm gap、原native确认与完整STOW分开。
- `registered_trace.py`：沿原RegisteredSkillSessionFactory/BehaviorSessionFactory/当前RGBD绑定/NativeOptionExecutor连接NAV/PUSH；只有真实SupportedCapture完成后可接。保留原support/contact/12N/clocked settled/卸载与STOW链，不运行裸SDK Machine替代。原SDK whole Machine只保来源，不派命令。
- `actor_trace.py`：只在原Actor单次调用点增加有上限的metadata；prepared tensor、inference context、输出转换/异常保留。NAV WBC、PUSH leg/arm、CLIMB身份分开，计attempted/returned/raised及首末root/phase/真实钟；输入转换失败不是Actor调用，Actor返回后转换失败也不误记Actor raised。原history初始化仅记账不额外reset；无逐forward文件IO。新派生PUSH在原私有编译器返回、session/后继wrapper建立前绑定infer，不向实例塞base update、绕derived/Clocked检查或改共享module/旧freeze。
- `bounded_exception`：最多16个file/function/line叶栈及type/errno，无locals/异常文本/凭据。partial账按实际字段分别保留，缺钟/aux不填0；旧EAGAIN的叶因仍UNKNOWN。
- `qualify_cpu.py`：默认OFF。`--enabled --source-root <exact-common-source> --bundle <original-sdk>`只做实际私有Python的源编译/合同/类型检查，**不是全程序actual prepare**；Runtime/world/lease/模型forward0。`test_parent_source.py`是4项新增调用边界检查，不是原Actor实测/历史回放或重复旧套件。

## 尚未完成，不能直接派发

完整parent还须把以上接到已有ScopeIO/FD捕获/原1s poll且oldest≤2s/真实PerGpuLease/identity边界，接有限真实public query→原注册loop、分项终态和全程同钟HD原片/编码/partial-finally/尾账。root main/wall/sim/command/video/output预算尚未冻结；完整freeze、actual prepare、自身必要zero和fresh lease仍0。不能借D3/asset/性能程序的zero/AUTH/预算，也不改Actor或跑旧scope。

下一唯一实现项：在现有parent生命周期中接有限NAV→PUSH路由与真实query/phase上下文和上述注册连接，再做完整程序prepare；不要再造独立probe/asset/launcher平台。当前源CPU assembly通过不证明真实Runtime构造、资源拒绝修复或新技能成功率。
