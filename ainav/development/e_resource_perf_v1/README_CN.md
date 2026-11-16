# Fresh size 按目录并行：Data下一新程序可采用的资源检查实现

此helper不派物理、不设置限额、不拥有lease，不改Data源码/环境/H/旧worker。
仍由Data唯一owner在**新完整冻结程序**显式使用。不加新审批，也不是运行资格证明。

## 保留的检查语义
- 与原Data fresh_size同样全量扫描每次scope树，无TTL/尺寸缓存/目录缓存。
- 每个目录每次重新scandir；不遍历目录symlink，常规file symlink跟随，hardlink逐路径计数。
- missing/dangling/loop/permission/普通I/O异常全部上抛；失败/closed/reentrant scanner不可恢复。
- 最多8线程、每波32目录future；不对文件抽样、不忽略未知路径、不提高cap或减少检查调用。
- 不是atomic filesystem snapshot，也不是写前预留协议；与原fresh_size同样存在并发写入时间窗，
  不声称解决此既有问题。本helper不接管其他进程文件，不支持无关writer并发规避Data权限。

## 最小接入
在Data新runner中：
```python
from fresh_size_parallel import FreshSizeScanner
scanner = FreshSizeScanner(workers=8)
# 每次原guard位置都保持执行，不缓存、不跳过或改变reserve：
need(scanner(S) < C['output_cap_bytes'] - 64*1024**2, 'original cap')
# 原authority/lease/GPU/RSS/wall均保持；最后ledger若仍要扫描，须在close前完成。
# finally中捕获关闭异常，保原失败结果；结束时scanner.close()，不能复用已closed scanner。
```
默认导入不建线程，首次调用才创建池。`scanner.metrics`可并入原进度，非新增监控平台。
必须保原64MiB reports/codec reserve和原有限wall/RSS/GPU/lease/authority检查；
本helper的容量计数不能冒全root容量/外部quota已知或更宽设备权限。

## 已有证据及限制
17 CPU filesystem fixtures本机通过；原真实closed E scope（约68.6MB）11配对轮：
原逐目录21.28ms，中位并行8.55ms，2.49x；非当前live guard/整段仿真提速。
前两个按文件并行候选无收益，完整负结果保留，不采用。
真实Data own-zero/main依赖完整源/运行条件新冻结，不借旧zero、不重开旧main。
