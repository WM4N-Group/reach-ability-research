# PERF-01 v2 新程序差分审阅（非native资格）

- 原未提交三文件按交接SHA核同并保存在本轮manifest；只改本组新开发目录，旧freeze/worker/AUTH/锁/binding不改。
- 新worker OWNER为当前CODEX真实01a1e4e1；原PerGpuLease中01a1d3aa是历史不可变binding身份检查，不被用来claim当前H。每次原lease.check(force=True)的authority callback仍核新H owner、新scope owner、新AUTH owner与实际PID持锁；未复制或重建规范锁。
- 精确允许已实测GL memfd名/r-xs/8192/offset0/device00:01/正inode，最多4条；不是跳过任意deleted。命名ELF仍进FrozenFiles hash/stat/canonical。新AUTH显式授权此policy，配置绑定已closed诊断result SHA与其中全部9个driver SHA；prepare核证据/driver表一致及freeze纳入。
- generated RX按每进程bootstrap接受实际地址/inode/字节SHA，后续1s原resource probe做冻结比对，不resync。它不是外部签名/root/native-memory保证；旧zero未记mapping名，不能把诊断当旧唯一因果。
- 原driver.capture_grid在task0提前一次，last_capture_tick幂等使first step不重复；不加物理/Actor forward，保持原RGBD/视觉写入且assert task0/FIFO0。原capture_grid不启动_native_guards元数据pool；实际安装仍须previous.state/pool均None。是否在main稳定须新own-zero/main实测，不宣预先bitwise等价。
- 相机必须读原main最终spec，不能用candidate0；2000步/10sim NAV-only固定，动态门/Actor/dt/率不改。原1205.164wall起点为prepare之前，比较用scope_start_to_window_end_wall_s。旧seed未知不伪造。
- 不跑旧完整CPU套件，不重下环境；仅已变更mapping关键case/default-off/配置/真实CPU prepare。自身必要zero≤1，资格通过才main≤1；失败closed保原因费用，不以改ID重试。
