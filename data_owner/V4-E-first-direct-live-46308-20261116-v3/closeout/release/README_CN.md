# E完整V4目标首次真实尝试：失败原片先交（不等待完整cold）

发布时间：2026-11-16T16:12:40.725455+08:00。

- 真实E固定RuleBaseline；source `3ab9383a02bd5eeb1179cb3b273427744c3cb325`；program `f7dd66c58d988adb135b5573abd2481deba785874524159fa616af326ff1bf17`。独立fresh scope `data-46308-V4-E-first-direct-live-20261116-v3`，own-zero1/main1已closed，不重开。
- 完整任务**未成功**：准备NAV在3018tick/15.090sim原生succeeded；首cuboid_a PUSH在3019tick/15.095sim真实started。9719tick/48.595sim，原`placement_handoff.py:207`于protected stow完成后的placement复核拒绝：`Original immutable public/native placement lost after stow`。后续箱子、CLIMB、高台均未到达。
- 保留PushSettled NN内部true与任务placement不合格的区别；无该PUSH的原生succeeded/failed终态回执，不补技能负标签。最后原采样48.590sim的XY误差0.0377186312m、signed dock gap -0.0365852129m、placement_geometry_verified=false，来自隔离证据，不能喂在线planner。没有单独归因某算法或几何漂移原因。
- main实际9719条200Hz命令、48.595sim、9382.502520127wall、486机载帧，resource_censored=false/usage_known=true/close_errors=[]。录制器原episode.censored=true保持，指调用方异常截断，不能覆盖为资源watchdog或native failed。own-zero额外19.590225650wall及6.505auxsim；main另有6.505auxsim。费用非货币账单；旧v1/v2前置错误成本/旧closed失败不清零。
- VLM0/WM0/fit0/新后继选择0；共有legacy H本次attempt1/completed1/changed1真实计入，不能把E说成所有算法均0，不推B/D增益。

## 完整原片

- 远端：`/mnt/yuanyue/data-team/deployments/46308-20261114/runtime/workers/data-46308-V4-E-first-direct-live-20261116-v3/main/E-direct-live-1x.mp4`。
- 本机小副本：`/home/yuanyue/main/work/data-team/manifests/V4-E-first-direct-live-46308-20261116-v3/E-direct-live-1x.mp4`（237186 bytes，非批量raw迁移）。
- SHA256 `172e2878f3496bdcf04a88f3c3e49bde6d669ed5ecc01281b3b0475392dddad9`；1280×720、10Hz、486帧、1×、MP4约48.6s。任务终态时钟48.595sim来自原event/result，不从片长推断。采样grid末帧9700tick/48.5sim，覆盖完整事前10Hz grid；未补造9719tick画面。
- 从task0直接live MuJoCo RGB保存，31个raw chunk/486帧逐SHA核，原master留远端；非状态回放、非重渲染、无resize/插帧/成功剪辑。只对已存原RGB作H264编码。母版closure中的encoded_video_created=false是编码前原记录，实际编码见独立video-encoding-result.json，不回写原件。
- ffprobe实际尺寸/FPS/解码486帧通过；解码48秒帧QA是原MP4解码，不是Runtime重渲染。固定广角覆盖狗、三箱和高台，狗臂相对很小，不能假称可看清臂细节或用裁切放大冒另一原相机。

## 完成边界与下一步

这是完整目标的真实**失败尝试及从开始至失败的原片**，不是全链成功、不是五组完成或方法排名。E先行DEV暴露保持，后续不得据此调四组又冒未见公平对照。

原件最少结果/视频已闭合；完整200Hz/FIFO/PD cold尚未完成，不能先宣称通过。AINav应依据原源码/placement合同与末段真实记录定位stow后placement不合格；Data后续只读补cold/成本，不降低阈值、不热改/重跑本scope，不替Reach写优化器。若需新共同修复/新实验，另行登记问题/版本/用途/限额，不换ID盲重试。compute仍46308；旧46174只按具体资料缺口只读，本次未连接。
