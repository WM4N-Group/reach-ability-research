# 有限只读OS query／Python producer交付时延分离

源只用于本次事前固定的2pair/4条原GPU0 NVML metadata queries，无retry；第一pair不施加阻塞，第二pair只在**本诊断父进程**用PyDLL libc.usleep保持GIL2.3秒。sleep不忙算，不改peer线程/亲和性/环境、不给GPU做计算、不取lease或World/Actor/Runtime。独立query子进程记录原query各自开始/完成及exit，父线程记录接收/完成；同host monotonic，输出/超时有界，不提供OwnerStamp或ResourceWatch续权。

实际46308私有Python：无hold时父0.229764180s/两原OS queries0.108033160s；已知synthetic GIL hold时父2.512541693s/两OS queries0.193868886s，子进程确在hold内完成，父端交付又滞后2.106575524s。这是**实际OS计时＋明确synthetic CPU阻塞机制**，不是D3重跑/真实cold constructor，不证明旧2.080643503s由GIL或任何唯一NVML叶因引起。

该结果说明仅composite wall不能直接当NVML命令耗时；不是已测修复，不准因此放宽2秒/补now/completion-only、旁路PID/UUID/locks或新派native。原D3 zero1/main0 closed/UNKNOWN保持，原始尾费不回填。下一若修producer，应准确区分真实observation时间与交付/调度，同时保全原原子pair和资源权威。

证据：`/home/yuanyue/main/work/data-team/manifests/resource-producer-OS-CPU-separation-20261117-v1/`，事前协议/source SHA、实际raw JSON/stderr/exit与结论都保留。没有重复旧native/环境下载、旧完整suite或新API/物理。
