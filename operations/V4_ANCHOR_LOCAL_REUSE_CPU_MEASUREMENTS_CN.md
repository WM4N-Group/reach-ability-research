# 同次WM anchor几何复用：局部CPU优化与边界

记录：2026-11-16 19:59。实现db3799c。只改本组`v4_anchor_target8.py`的同一次provider call；不涉及当前E、原生guard/lease/磁盘检查、任何他组源或闭合程序。

## 原问题与最小实现

多个候选可以关联同一当前96×64 plane。旧代码对每个候选重跑原proposals、1024次RANSAC和geometry_vector，输入相同却重复计算。新局部字典按`(frame_local_ref, type(standoff), standoff)`复用已验证的tuple向量/原proof SHA。数组/RGB/深度/标定共享的是同次deepcopy，不是跨帧缓存。数字类型保留；每候选证据重新拷贝，subject/association scope不合并。原拒绝复用为UNKNOWN，不补valid零target8，不合并同色碎片或选最大块；其他异常照原抛出。原拷贝和source anchor的最终只读/新鲜时钟检查不变。

原geometry三文件SHA未动，纯函数原随机种子/1024 RANSAC/64px/深度/normal/span等阈值不动。未来原始功能/输入变化必须重做必要验证；本局部reuse不提供native身份/许可。

## 必要测试

新10项：16重复项只算一次plane/vector；跨调用不复用（即便字节/clock相同）；不同ref/standoff/int-vs-float不合并；拒绝仍UNKNOWN；无关联不计算；候选subject/evidence独立；source/copy mutation拒；mask0拒；非ValueError不吞。旧受影响anchor13项回归，本地23/23、46308同代码23/23。起初fixture的self.options命名被原setUp覆盖，已改fixture；过度限定错误文字亦修fixture，没有放松生产条件。修代码前经修正的10测试为4性能断言失败/6过，非物理失败。

## 原算法CPU成对测量（3轮、交替先后）

使用`run_v4_anchor_local_reuse_benchmark.py`，baseline取仓库c6bccd1原producer；同一个已逐SHA加载的原geometry API、同一合成anchor/合法关联/参数列表。软件fixture身份始终开启，不得升级真实模型输入。63%原native路径热点与这组测量无关。

| 合成查询 | 旧完整provider中位数ms | 新中位数ms | 原plane次数/新次数 | 局部倍率 |
|---|---:|---:|---:|---:|
| 16候选、同一几何 | 1296.875 | 81.132 | 16/1 | 15.985 |
| 16候选、四组几何 | 1300.958 | 325.656 | 16/4 | 3.995 |
| 4候选、四份唯一几何control | 316.977 | 315.256 | 4/4 | 1.005 |

每轮完整返回（数值、状态、proof SHA、所有evidence字段）与旧实现严格相等。测量是完整provider wall；记录的geometry subtime属于其中，不能加到总耗时上。单CPU67、BLAS/OMP/MKL1；同次调用内localcache，无持久状态。原始各轮数据/代码SHA/输入SHA见`V4_ANCHOR_LOCAL_REUSE_CPU_BENCHMARK_20261116.json`，无真实相机/旧closed帧/NPZ读取、无WM/Torch推理或world/Actor/physics/API/fit。

本机默认Python无NumPy，故实际原NumPy函数计时仅在46308既有env进行，不安装包/改环境；本地仅metadata软件测试。不把差异归成硬件/当前E/整个WM推理提速。

## 交接边界

当前E20不调用WM，改动不能让其guard变快；AINav/Data仍必须按19:35计划完成原guard/capacity结构改造及同条件原生性能验证。不得把15.985×写成端到端仿真倍率或与其他局部收益相乘。该producer本来就是default-off条件关联的后续组件，实际传感器/模型/bootstrap/动作映射/新palette准确性仍未验证；完整后继effects/退出fresh与cost仍缺。不是Reach方法收益/新物理试验/训练样本。

## 同回合增量：E20正式失败片

Data新正式release与既有结果一致：275帧/18chunk/1280×720/10Hz/1×，末grid27.400s与异常stop27.410s区分。只核9小metadata/现成小MP4 SHA/closure grid，不重新读raw/cold或修改成功门。详细记录增量追加到`E20_V3_PREARRIVAL40_REAL_MAIN_FAILURE_INTAKE_20261116.json`，不新增物理次数或40mm搜索。
