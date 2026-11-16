# Indexed identity guard v1：静态审计策略有意修订，不是旧逐tick fresh等价

对应总计划2026-11-16 19:35/02dc65ed…的AINav实现责任。只供**新冻结性能程序**选择，
默认OFF；不替换在途/closed 39ef86d5、04a源或原watchdog，不创建Runtime/Actor/world。

## 热路径真正移除的工作

- 任务/依赖加载后，在owner授权的可信初始化点，对去重canonical文件一次SHA和stat，
  `FrozenFiles`记录完整文件身份与manifest digest；已知source/asset SHA必须传入expected_hashes。
- 热循环每步只核真实host/runtime/model/data/queue/root-target、关键callback对象/code/default身份、
  session/target/原immutable-goal seal/config tokens、sys.modules对象/长度与有时限的owner状态。
- 非审计到期的热路径无Path.resolve、stat、文件hash、全module遍历或旧full-owner调用。
- module metadata最多每20 guard调用或0.25墙钟秒（先到为准）检查同数量替换/路径属性变化；
  module增删（长度变化）和已知关键alias/callback替换在下一步立即拒绝。
- 文件/leaf symlink的stat身份最多每5墙钟秒核；canonical路径最多每60秒重核一次。
  这不是每tick重读，也没有“永久相信缓存”。元数据变更拒绝，不重标新hash继续跑。

## 检测时限与失败语义必须如实披露

| 改变 | 新策略 |
|---|---|
| foreign runtime/queue/root-target、关键alias/callback、会话/目标/config token | 每次实际Runtime.step前拒绝；原native immutable tensor-goal检查仍独立保留 |
| owner撤销/错epoch/过期 | 每步核OwnerStamp；外部检查和跨进程传播由Data真实监督层提供，stamp有效期≤2s |
| 未计划import/exec/显式FunctionType/函数code替换 | sealed/audit期间通过Python audit hook拒绝，置FAILED；不能catch后继续发步 |
| 直接sys.modules同数量替换、非关键__file__变化 | 最多20 guard调用或0.25s后检查，非旧立即等价 |
| 持续文件写入/替换/leaf symlink retarget | 下一metadata audit（≤5s）拒绝 |
| 同inode的parent symlink/canonical-only rebinding | 下一canonical audit（≤60s）拒绝 |
| 短暂改动又在两次poll间恢复 | **不保证检测**，尤其中间父symlink切回；不得宣传绝对防篡改 |
| I/O读失败/audit超过5s | 拒绝发步，永久FAILED；若内核I/O不返回，不能承诺Python硬5s响应，Data外部watchdog需终止/收束，期间issue gate保持关闭 |

上述时间包含“下一次pre-issue检查”的调度。操作耗时另加最多5s审核预算，超预算不继续发步；
长时间没调用guard时没有任何新物理步可被授权。不是实时机器人控制方案。

## 显式暂停边界，不自动吞错误或重试controller

`engine.boundary(driver, label)`只允许不发物理步的原构造/安装操作；退出时重新执行原
完整guard、验证所有module文件已在授权inventory中、重建canonical/关键alias索引和会话tokens。
在boundary调用正常Runtime.step会被pre-issue gate拒绝；若绕过gate直接改step，检测后失败，
**不伪造回滚**。任何失败只能关闭该scope，不能resume/return True。

初次callback map固定，后来不能借boundary任意换callback/owner/world；新的有效alias可指向
同原callback。新模块只能来自预先测量授权的文件；未在inventory的文件即使位于roots内也拒绝。
加载未知依赖不能在异常后自动重做推理/控制器；资格前必须完整加载或在明确、review过的
no-step边界安装。没覆盖的lazy import会fail closed，不声称当前已通过native整链。

## 最小Data接入（非运行授权）

```python
# 新程序、冷Runtime/driver task0；先加载guard本包和所有计划依赖。
from indexed_guard import FrozenFiles, OwnerStamp, module_paths
from install_fresh_driver import install
paths = (*module_paths(), *all_frozen_source_weight_asset_paths)
inventory = FrozenFiles.measure(paths, roots=explicit_roots,
    expected_hashes=known_frozen_SHA_by_path, allow_missing=explicit_missing_module_paths)
# Data需把inventory.sha256/record和原配置/源绑定，不能把TOFU测量冒外部真实性。
# fast_owner只读Data真实cached lease/resource epoch与截止期；不得每次伪造新checked_at。
receipt = install(driver, enabled=True, files=inventory,
    owner_fast=fast_owner, owner_refresh=actual_external_resource_refresh,
    tokens=actual_session_target_goal_config_tokens)
```

`OwnerStamp`必须来自同一`indexed_guard`模块：epoch固定、valid布尔、checked_at/valid_until真实，
有效期≤2s。Data外部层必须按新协议刷新、处理撤销/容量/未知写入/磁盘故障，逾期停发；
本helper不代替它，也不证明假fixture owner有效。容量增量记账/磁盘与lease策略由Data实施。

提供的fresh adapter只修改这个私有新driver class/instance：把便宜guard放到**原Runtime.step
body之前**；原step body/碰撞/足力/FF/effort/QP/FIFO/NN/STOW/4s/stop不改。显式no-step
边界包括capture→execution、judge_intent、原executor.start和PUSH原begin_brake构造。
这些是原代码的前后审核，不重写控制/重做Actor或改变sim dt。晚期其他lazy代码安装若未加载，
必须准确拒绝并补资格，不能先说全链可用。原安装/registry/frame/任务成功口径不变。

## 信任边界（没有把chmod当证明）

- inventory记录os.access写权限，`readonly_enforcement_proven=false`；不改任何文件权限、挂载或他组环境。
- 它是owner授权的bootstrap测量，不是供应链签名/安全沙箱。Data必须核真实只读副本/访问控制；
  root/native扩展攻击、内存任意改写、已加载代码与pyc一致性不由此Python helper绝对保证。
- 每步token不替代原native tensor-goal值校验；关键callback身份不等所有模块global语义完全不可变。
- audit hook每进程只允许一个active guard；close后停用，不能卸载Python已有hook，不开子进程/线程。

## 当前证据/下一验收

46新policy/失效/文件/owner/foreign identity纯软件＋14 fresh adapter/owner-bridge fixtures本机通过；
不是native/容量/真实lease/5倍系统资格。相同CPU loaded模块、文件树和相同合成call轨迹的
旧batch32与本版配对benchmark由`benchmark_same_loaded_cpu.py`提供，cold SHA/边界成本
分开、exclusive hot分项不相加重计。真实同阶段性能验证只由Data新scope实施，未达目标
如实报告，不回退无限加watchdog或偷偷缩门。未来五组共用同性能/保护策略。


## 与Data当前ResourceWatch接口的具体接缝

`data_resource_watch_callbacks(watch, epoch=scope_and_authority_epoch)`直接对接Data v1的
`check(token)/last_ok/max_stale/token`，要求max_stale≤2秒。它保留监督线程真正检查的last_ok，
不以本次guard调用的now伪造freshness；refresh回调只是ACK现有有效结果，**不额外probe**，
从而不与Data每1秒的外部监督重复检查。Data自行持有原lease并start/close监督线程，
容量/磁盘/撤销失败由watch.check传播。本桥接器没有证明真实watch已通过资格，仍需Data测量。


## 完整依赖范围不能混淆

本索引自动覆盖loaded module.__file__，不自动发现ELF/DT_NEEDED、已dlopen但无module字段的
native动态库、pyc来源、Actor权重或MJB。Data必须把真实依赖闭包/权重/资产以显式extra paths
纳入同一授权inventory并按原source/环境manifest核SHA；CPU benchmark的约1300模块文件
**不是完整可执行环境或native资格证明**。初始化测量root范围也不是外部真实性签名。

owner桥接仅一次读取真实last_ok再构造同一stamp，避免后台线程更新时拼出虚假更长有效期；
对应并发读fixture的修复前失败保留，不是物理失败或改变检查时限。


## 周期审计也要测，不能只挑无I/O的快路径

首版真实CPU loaded corpus成对测量：16次非到期hot check约4.747s→0.458ms，但稀疏周期
12调用轨迹旧3.547s/新5.728s，**新策略反而更慢**，原负结果完整保留。定位为周期audit重复
follow/nonfollow stat以及串行FUSE元数据开销。当前修为同raw/canonical regular路径只一次
lstat语义，并按同parent目录一次scandir收取**本次新DirEntry**，只stat预登记名字；不扫描
output tree、不跨audit留DirEntry，不降原5s/60s周期。原same-inode parent alias等失效测试仍在。
最终基准保留原两条调用轨迹，并增加每5s都触发的完整周期轨迹，防止只挑稀疏区间报收益。
文件系统缓存/可见性不由Python绝对控制；上表为应用poll上界，真实FUSE backend延迟仍须
Data资格验证，不把新DirEntry或chmod说成即时防篡改证明。


## Bootstrap别名和额外资产的回归加固

新增三个失败复现已保留并修复：同canonical文件的raw alias不能忽略冲突expected SHA；
有expected hash的必需文件不能放进missing白名单；显式额外权重/资产的raw→canonical关系
也必须进入metadata/canonical审核，不能只监控module文件。当前inventory记录全部raw别名，
新seal拒绝bootstrap后别名指向变化；文件内容SHA仍仅在可信初始化测量，不降低5s/60s检测层。

owner桥同时要求watch.check返回None或True；False/未知结果不可被包装成有效stamp，拒绝回归首版失败另保留。
