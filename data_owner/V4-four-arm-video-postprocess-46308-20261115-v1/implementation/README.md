# Data V4四组原raw后处理：四份1×＋同钟四横栏

**仅后处理工具，不是V4方法/场景/native资格，不创建世界或调用API/WM。** 输入必须是四个不同的、已关闭的原main root；实际四组身份须由正式planner/WM/VLM/native记录另行核验，不能拿四条bulk/API0轨迹贴A/B/C/D标签充对照。当前真实V4 zero0/main0/原片0不因本工具改变。

## 本次实现

- 沿现有Data direct raw metadata/closure/NPZ格式读取，核原result→ledger与scope/program/camera绑定、chunk SHA和原RGB bytes SHA、完整整数physics tick/实际采集钟；任何缺失不填帧。
- 对原相机/原采样网格要求四组相同，实际raw至少960×540，不放大192×128、不裁切/缩放世界区域。目标1280×720及采集负载/FPS仍待完整V4源装配后在冻结前实测，本工具不证明采集相机已合格。
- 单组1×仅编码原帧；同钟四横栏从0时钟起，某组结束后变黑色“ENDED/NO FURTHER OBSERVATION”说明页，不冻结最后世界帧、不重渲染/插帧/重复世界帧。
- 96px说明头加在原画面外，原世界像素在H264有损编码前保持逐字不改；原raw仍为母版。native终止时间从原result取，不拿最后容器帧长度替代事件钟。UNKNOWN完整任务结局保持None/UNKNOWN，phase PASS不冒整场成功。
- 流式读取，每次一个ffmpeg/两CPU线程，默认1800wall/1GiB派生输出限额；这些是后处理技术上限，不改物理arm预算。输出须为原root外的新目录；不覆盖原件或已有输出。失败保已生成部分，不自动重跑任何物理scope。
- 不把API原始错误/凭据画到视频或复制到派生manifest。整个视频/manifest是EVIDENCE，不作在线planner输入或自动fit。

## 一次性新端纯软件核验

`/home/yuanyue/main/work/data-team/manifests/V4-four-arm-video-postprocess-46308-20261115-v1/software-fixture-test-result.json`

9项新视频检查，2.273s，exit0。生成并ffprobe四个单栏＋一个3840×636四栏微型MP4，源world区域960×540、额外头96px；原分母[3,2,1,3]，四栏3帧。另核结束后纯黑world区、UNKNOWN/失败分开、不同camera拒绝、低清拒绝、重复root拒绝、SHA损坏与补hash后的缺tick仍拒绝、源改动检测、fixture不能切换为真实模式。**全部明确SOFTWARE_FIXTURE_NO_PHYSICS，测试临时NPZ/MP4已自动移除，0新Actor/Renderer/WM/API/物理，不消费旧scope原片作新试验。** 不是research平台差分的原9项测试，也未重跑其测试。

本机没有NumPy/ffmpeg，未安装依赖；软件检查只在新端现有私有环境、CPU36,37、CUDA_VISIBLE_DEVICES为空、MUJOCO_GL禁用运行，不占GPU lease。

## 后续实际使用（仅正式V4四arm全部真实结束后）

在新端使用`/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B`执行`encode_four_arm_originals.py`：分别提供四次`--arm A=/absolute/original/root`到`--arm D=...`，`--out /absolute/new/derived-directory`，及可用的两核`--cpus 36,37`。原时间步当前0.005，若未来协议变更需准确传入`--physics-step-s`，不得为过审猜钟。四组程序/相机/方法冻结由原执行流程承担；**本工具不增加一个物理运行签字门，也不在真实四arm到齐前造电影**。

`--fixture-mode`仅用于明确软件标签且账本同标签的输入；所有输出角色强制SOFTWARE_FIXTURE_NO_PHYSICS，不能把fixture当真实结果。本次测试已完成，不重复运行原一次性`run_remote_software_tests.py`。
