# PERF-01 v3：仅已复现inventory路径资格修正（非旧scope重试）

v2 program7c382864真实zero1/main0已closed；18.648151243wall/task0/aux6.505sim，准确失败是NumPy实际包目录在roots外，其他失败/账不抹。

CPU-only实际读原env-native-v1：frozen-native-dependencies.pth明确先引用piper-zyh-mujoco-340d7d8-v1 site-packages再引用go2-isaac；NumPy/MuJoCo来自前者。只补这个实际site-packages root，pin原pth SHA1559afc8…，不改环境/包/guard，不把/mnt全放开。torch.ops/classes是实际_Ops/_Classes伪模块，分别__file__为相对_ops.py/_classes.py，真实定义文件在go2-isaac torch下且pin真实SHA；不制造这两文件、不重写模块。新worker/launcher固定cwd为自身W，显式仅两个missing槽，AINav原有allow_missing策略跟踪其持续不存在，不能把缺失源码泛白名单。stdin产生的__main__路径不属于实际worker，不纳入missing。

新prepare仅CPU导入原依赖/已review模块并核已加载路径均在精确roots或这两个missing槽；不构造Runtime/Actor/EGL/Renderer/物理，不重复全环境SHA，失败可在native前暴露。RX快照移到FrozenFiles.measure之前写入result，避免后继路径异常丢具体mapping。

原87a guard、v2严格memfd形状/字节变更拒绝、原Actor/dt/命令/原动态门、真实新OWNER/原PerGpuLease/历史binding、相机与2000步10sim窗口/预算均保持。新AUTH/freeze/own-zero≤1、main≤1独立，不复活v2。原CPU-only路径证据在v2 manifest中。
