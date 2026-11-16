# 原E59 closed只读完整数据流cold补充：通过不改任务失败

原最少结果与完整1×视频早先已交，release `13082992532fe8b8ae537671129121d7558312d7d715a6a7a4f9257864d9269a` 不回写。此补充不增加物理次数，不恢复world。

## 完整性

515 frozen source/asset成员逐SHA核；4711行原journal完整序列/哈希链；9719条200Hz命令/原4步FIFO完全一致；原PD raw和硬effort clip最大重现误差均0；486机载RGBD帧前一动作/时间grid通过。31个1280×720 raw chunk/486帧解压核像素SHA、dtype/shape、实际tick/时间，10Hz完整事前grid通过。所有原scope文件及H在只读audit前后SHA相同，close_errors0。audit本身为CPU/NumPy只读13.979637s，不计新task或免费抹去其开销；不导入Runtime/Actor/MuJoCo/Renderer/WM。

## 准确首次失格，不误归因收臂/H

- sequence2500，26.570sim：placement首次合格，XY误差8.8551mm、signed dock gap +3.4623mm。
- sequence2503，26.590sim：进入NN_STOP_MOVING_PUSH时仍合格。
- **sequence2507，26.630sim：NN_STOP_MOVING_PUSH内首次再次失格**，距首次合格仅60ms；XY14.6202mm、signed gap −13.7201mm。之后原测量未恢复合格。
- 原NN在27.210sim内部确认，不等task placement合格。29.390 BRAKE_MOVING_PUSH及30.210 UNLOAD_CAPTURE已在失格状态；32.910才进入PROTECTED_STOW，早于它的legacy H首attempt为sequence3137；44.610进入STOW_VERIFY。
- **48.595sim**才在原placement_handoff.py:207于保护收臂完成后的复核抛异常。`lost after stow`是原报错位置，不是首次越界发生时刻；不能把已有失格倒归因于后面的H路径选择。末48.590sim XY37.7186mm、signed gap −36.5852mm；具体动态/接触原因尚未仅凭此timeline确定。

## 标签与后续

任务仍未成功，原PUSH terminal=None、CLIMB0；NN true/数据流通过都不补完整PUSH成功/failed标签或成功cost。resource_censored=false与原recorder.censored=true分别保持。原E DEV暴露/用途、旧v1/v2元数据错误、原费用、其它closed失败全部保留；无V-JEPA/WM训练准入。

下一项由AINav定位arrival→NN_STOP的原动作/FIFO/卸载接触；Data维护这份真实证据和下一版完整同门计时，不降低成功/安全门、不单纯降高或提速后换ID盲试、不重跑本scope。最少视频和正式补充均可先独立消费，不待A—D/WM/VLM/J。
