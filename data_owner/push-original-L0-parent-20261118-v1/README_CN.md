# 已执行并closed：原独立PUSH L0 parent

本程序code a8a90e828fc7…/完整program947a4b250800…已完成1804文件freeze及真实CPU prepare，zero1 PASS；唯一main在原startup840步/4.2sim被原oldest≤2s资源门截断，PUSH Actor0、无技能终态，现closed/no retry。原43帧1280×720/10Hz/1×直录、费用和原件见Data STATUS的`push-original-L0-parent-20261118-v1`入口；本目录不再是可派发候选。

事前问题：原standalone标准初始化之后，原注册PUSH主体与完整退出是否可完成。不是closed L1重试或删NAV改名；不借0fa40c…zero/AUTH，所有既有scope原状。

- `standard_runtime.py`在原RuntimeAdapter私有loader中仅绑定“原fresh INITIAL X从−1→−.08”的一个可逆constructor差分，保原camera/calibration三hunk、Actor、Runtime.step/200Hz/QP/PD/FIFO；原SDK不改。原Runtime产生的nav-push Machine只作来源保管、绝不运行其NAV。task0仍有原独立aux calibration，另计费用；零相位不做task settle/Actor。
- `l0_startup.py`沿上一a15源码，主相位逐步执行原独立`play.settle`，原Z/XY/基座速度与controller/history初始化显式登记。每条默认PD必须实际由原Runtime.step发出再ack，异常不能吞掉/续跑；原同钟视频/命令从task0开始，不抹掉startup的task sim或把它当aux。
- `L0StartupOwner`完成后才创建真正`OriginalL0Witness`：实发步数/时钟/last-two必须一致、原startup确实stable；再按原`current_push_source_support`独立验证四脚12N、原contact/geometry/arm effort、真实committed FIFO与原goal/history/issued-reference不变。**不是伪SupportedCapture，不声称其compact-transfer/.5s/NAV-arrival**；PUSH自己的原PushEntry与稳定准备仍照常物理执行，不降低12N/FF/NN/原4s/STOW。
- `connect_l0.py`只接受该实际L0 witness，接原RegisteredSkillSessionFactory/BehaviorSessionFactory/NativeOptionExecutor与当前RGBD；只发布PUSH一个合法候选，不给NAV/CLIMB许可。原public/native[1.7,0]与2.3m datum、20mm/10mm/原NN/卸载/完整STOW分开，不补.11m。
- `push_l0_driver.py`复用SHA固定的旧Data driver的6个原writer/alias/stow方法，不继承其NAV route/旧终态；不在本目录再复制299行legacy实现。新L0 loop处理startup→真实witness→当前public query/EntryJudge→原PUSH/退出；只有原succeeded receipt为完整成功。原60s interval到期单列censor，无续跑/重试、非Actor失败。
- `worker.py`接原ScopeIO/FD1/2/live10Hz1280×720 raw/编码/partial-finally/indexed guard及真实PerGpuLease；原1s poll/oldest≤2s原子pair保持。进入lease前先保留对象，仅记**历史完成**canonical rows，失败也不丢掉定位信息，不导出/借FD，不在未进入lease时强做GPU采样造二次错。tb_lasti/列位置属于新记录，不回填旧第42行。
- `phase_control.py`同一execute内foreign-target-compute/未知容量/same UUID门位于H CAS/授权计数/child之前；外层必须fail-fast，真实lease依旧最终判断、竞争仍可能，绝不空proc锁冒idle。不动J或peer锁，不永久按组分卡。

本候选事前预算：zero≤1/300wall；main≤1/1800wall、75sim/15000cmd/15200driver call；原init≤10.5sim＋单次原PUSH60s interval，retry0。native aggregate4GiB（含64MiB尾写reserve）＋独立launcher总512KiB、raw2GiB；原RSS4GiB/GPU3GiB/owned40GiB、provider quota UNKNOWN。预算需进入完整freeze/Auth后才有资格，不是本README即可派。

5项新boundary CPU检查仅验证default-OFF、拒绝NAV/第二次选择、原interval censor、拒绝伪capture和不多发命令；不替代真实witness/Actor或原生资格。本程序次数已用尽，不重新派发。未来`resource-start-cadence-20261118-v1`仅新的调度差分源码，非本scope热修/重试许可；下一有明确新问题与合法场景的完整程序必须独立资格，不借本zero，不开90次，不碰训练/真机。
