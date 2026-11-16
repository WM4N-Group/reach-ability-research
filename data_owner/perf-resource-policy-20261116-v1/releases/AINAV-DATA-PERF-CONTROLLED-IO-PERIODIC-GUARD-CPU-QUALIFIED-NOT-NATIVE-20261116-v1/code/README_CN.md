# Data吞吐候选：受控文件增量计数＋有界周期资源检查

依据主计划2026-11-16 19:35/02dc65ed…，这是**只供下一完整冻结程序**使用的Data组件，不是当前旧E20的热补，也不是已获原生资格/新派发。

## 已落实的代码

- `scoped_io.py`：正常写入前按文件实际增长预记账；ZIP seek重写不重复计费，UTF8按字节、临时文件replace、truncate和并发预留均覆盖。每个文本句柄最多8KiB、最多16个句柄；真实原录制buffer仍须保原边界并装入64MiB reserve，不新增无限队列。
- `resource_watch.py`：热路径只做PID/token/失败闩锁/新鲜度检查与明确绑定的便宜RSS/Torch健康检查。一次组合probe调用**原有效lease.check(force=True)**，由它核原owner/锁inode/binding/UUID/GPU；不再在每个热调用重复H/目录扫描。磁盘保底及完整目录核账在同probe执行。
- 外部检查1s周期，2s成功心跳失效上界；探测阻塞、撤销、读失败均闩锁失败，之后不能恢复。关闭时probe线程仍阻塞会明确抛close错误，必须继续封住native并在finally释放本进程lease/保错误，不能冒干净退出。**这改变旧逐调用检测延迟**：最迟下一个原guard边界拒绝，原native/OS调用若阻塞，停止时点还需加其阻塞时长；原独立硬watchdog不取消。
- `private_writer_binding.py`：在**私有模块globals**里为原recorder/Journal/raw writer绑定受控Path，不改已加载原模块/pathlib/builtins，不改数组、动作、采集时钟或原reader检查。原body字节码复用，但I/O globals有意改变；不能冒成“完整原实现/审计时延完全等价”。新身份快照必须在该私有namespace装配后建立。

## 最小调用形态（不是当前运行配置）

```python
state = StopState()
budget = ScopeIO(new_output_root, cap_bytes=1 << 30,
                 reserve_bytes=64 << 20, state=state)
probe = make_scope_probe(real_held_lease, budget,
                         min_free_bytes=explicit_disk_floor,
                         disk_free=lambda root: shutil.disk_usage(root).free)
watch = ResourceWatch(probe, state=state, token=real_process_scope_token,
                      fast_health=original_cheap_RSS_and_Torch_checks).start()
# 原owner_guard调用点调用watch；原碰撞/FF/QP/FIFO/目标/NN/stop检查不改。
# 所有受控文件写入经过budget.open或私有原writer的BudgetPath。
# 原终态/异常确定后，先封新native步骤，再在reserve内drain/报告：
budget.begin_finalization()
watch.close()
# 原writer.close、原片落盘与报告，不恢复物理。
budget.reconcile()
```

`real_held_lease`必须是真实原canonical FD/UUID绑定，不能用空probe返回True、周期快照或GPU空闲替代。`fast_health`在原生接线前必须真实绑定，候选库允许None只是为了独立CPU fixture；不是删资源门的许可。跨进程写者不能复用此内存counter；controller/encoder需要明确独立限额/预留或受控管道，不能默称已覆盖。

## 拒绝行为与边界

- 未登记文件、文件替换/大小外改、symlink/hardlink、丢事件、读失败、容量/磁盘异常均停步，不把未知当0、不静默重建账。
- 每次受控写入先检查增长；容量失败后正常native guard永久拒绝。finalization不可逆，只允许在总cap内排空预先有界buffer/写失败报告，不清除原失败状态。
- reconciliation仍是非原子filesystem观测；未知外部writer可能在周期内先超量。这里不是root对抗沙箱、provider quota或“chmod绝对防篡改”证明。检测到外写后原真实高水位可能未知；库仅报告**受控逻辑字节**高水位，不虚报全盘物理高水位。保持disk-free保底/ENOSPC拒绝与不再派发。
- native runtime/session/queue/target/callback身份及module/alias/file/symlink静态身份方案由AINav新guard实现；此包的wrong-token测试不能冒这些native资格。

## 已有证据，不扩大主张

本地30纯CPU测试；46308先26项＋新增3项＋1项停机阻塞测试（含真实阻塞probe失效）独立运行，保每次原exit。另在原源/SDK不变的CPU fixture中：40条serializer command、100行原hash-chain Journal，与原输出逐byte一致；直接NumPy压缩文件接口通过。全部为SOFTWARE_FIXTURE，**没有Runtime/Actor恢复或forward/renderer/physics/training/GPU派发**，不是新实验数据。

同closed E20的93文件/38,388,712逻辑bytes重建稀疏fixture，不搬原NPZ/图像。新旧每轮相同树与同一确定性调用时间表；初本地5ms合成时间表5000调用，目录扫描5000→26，局部中位约38.55×。这包含**策略频率变化**，不是FUSE/物理执行/5倍系统证据，不与AINav倍率相乘。目标端fuseblk已用**当前已冻结parallel8原helper（SHA052747ca…）**作正式对标：每轮1,000调用，同93文件/38,388,712逻辑bytes及均匀合成时间表（旧原平均0.108283306s/调用）。三轮旧扫描8.209/8.640/8.359s，新bootstrap+loop1.889/1.899/1.977s，配对中位**4.346×目录/资源组件改善**，扫描1000→101，热guard约1.175µs/次。原逐调用时间没有记录，不冒真实trace，不把这当全系统5×或真实稳态审计占比<10%。

早先目标serial基线9.38×和本地5ms fixture38.55×仍保留，但**不是当前parallel8基线的主结果**；不挑较大倍率展示。详细category缺口在IO_COVERAGE.json。

**尚未native_ready：** 要接完controller stdout/stderr、encoder输出和原raw/各metadata路径，绑定实际cheap health/lease/H/disk与AINav新静态身份策略，验证mutation/foreign world/queue并完成独立同条件性能scope。当前不派新E/五组/bulk，不为达5×延长watchdog或降动态安全门。已closed E59/E20失败与完整原片、费用、用途全部保持。
