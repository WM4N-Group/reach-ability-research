# E59原arrival→NN_STOP有限实际命令窗口

原cold release d7bd4be9…已核所有流；此补充只为AINav定位同一已closed失败，物理次数不增。

原主世界tick5308—5332（26.540—26.660sim）共25条command：每行有原NPZ位置、dtype/shape、完整issued/delayed/q_before/dq_before/raw_torque/torque byte SHA。五个landmark ticks5314/5315/5319/5322/5326另含精确原6字段值，未重算或改动原数组。父NPZ仍在远端，SHA及原index entry齐；本机只86.8KB小证据，不迁批量NPZ/图像。

原5314tick/26.570sim测量首次合格；其后第一条issued5315依原4步FIFO在5319实际应用。首次失格测量5326/26.630sim处的delayed来自issued5322，不是同tick requested。这只是精确队列关联，不能仅凭命令差值认定controller归属或唯一动力学/接触原因。

helper仅CPU/NumPy只读一小段，父NPZ与H前后不改，无Runtime/Actor/MuJoCo/Renderer、无回放/新world/模型调用/训练。此证据为PRIVATE_EVIDENCE，禁止送在线planner或fit；任务失败/PUSH terminal=None/旧成本和原片标签保持。下一原arrival/NN_STOP根因修复由AINav负责，不把提速/E20降高当PUSH修复，不降低门或重跑closed。
