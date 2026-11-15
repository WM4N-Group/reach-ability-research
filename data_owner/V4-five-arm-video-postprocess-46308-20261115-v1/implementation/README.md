# 当前V4五组：五份1×原片、同钟五横栏、可先发布E

对应22:53主计划26b67d55…：A=VLM+WM，B=前者+共享优化，C=原AINav，D=AINav+同一共享优化，E=事前冻结规则策略（不调用VLM/WM/优化器）。**这是Data后处理，不实现/认证任何方法，不创建世界/API/WM/Actor/Renderer。真实V4五组目前仍zero0/main0/影片0。** 不能把五条bulk/API0轨迹改标签当五组对照；方法身份须从原实际决策/API/WM/native记录核验。

## 已实现

- 兼容现有原direct raw metadata/closure/NPZ；读取已关闭main，核原scope/program/ledger/result/camera/原chunk SHA、RGB bytes SHA、完整整数tick/原采集钟。未知完整任务结局保None/UNKNOWN，phase PASS不冒任务成功，native终止钟不以MP4帧长代替。
- 五个不同原root，原相机/网格一致，真实raw至少960×540；不对低清放大，不裁切/缩放世界区域。原画面外加96px头，再做明确有损H264；原raw保为母版。1280×720目标、采集FPS/负载仍待完整源装配后冻结前实测，本工具不签采集资格。
- 五栏同模拟钟，提前结束后纯黑说明页，不冻结末帧、不延长/插值/重复世界；输出5份独立完整1×及一份五横栏1×。
- **`--individual-only`允许E等已关闭arm先交自己的原片，不等WM或其它组**，不生成缺组的拼接、不宣称五组对照完成。E是否先执行、顺序和规则须在结果前冻结，由AINav实现/Reach核信息语义/Data按原资格执行；本工具不造规则、不触发main。
- 输出原root外的新目录，不覆盖；流式读chunk、同时只有一个ffmpeg/两CPU线程，默认1800wall/1GiB派生输出限额。失败保已写部分，不补帧或重跑物理。API原始错误/凭据不画进头或派生manifest。全部是EVIDENCE，不作在线特征或自动fit。

## 新端11项新版本软件检查

结果：`/home/yuanyue/main/work/data-team/manifests/V4-five-arm-video-postprocess-46308-20261115-v1/software-fixture-test-result.json`，exit0/11 tests/2.793s。

原视频回归＋新增E单独发布/E缺其它arm不得造完整对照；实际编码并ffprobe了6个微型fixture MP4，源960×540＋96头，五横栏4800×636；单组分母[3,2,1,3,2]、拼接3帧。另核原RGB、黑色结束页、未知/失败分开、相机不同/低清/重复root/SHA坏/补hash后的缺tick仍拒绝、源改动和fixture不能升真实。

**全部SOFTWARE_FIXTURE_NO_PHYSICS；临时NPZ/MP4自动移除，没有真实实验影片、模型/世界/API调用，也未消费旧scope片充新试验。** 原四组版本和其9项检查完整保留，不累加成20个研究样本，也未重复research原9平台差分测试。检查只用新端既有私有Python/NumPy/Pillow/ffmpeg、CPU36,37、CUDA空/MUJOCO禁用；本机未装依赖。

## 用法（正式稳定V4源真实结束后）

新端现有`/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B`运行`encode_five_arm_originals.py`，给`--arm A=/absolute/root`至`--arm E=/absolute/root`、`--out /absolute/new/derived`、两可用CPU`--cpus 36,37`。只交E则提供`--individual-only --arm E=/absolute/closed/root`。原步长默认0.005，未来协议若改变须准确传`--physics-step-s`，不能猜钟。

只在软件输入使用`--fixture-mode`，原result及ledger须同软件标签，输出强制软件角色。原11项测试已完成，不重复一次性runner充进度。此工具只服务录制交付，不增一个native准入/签字门。
