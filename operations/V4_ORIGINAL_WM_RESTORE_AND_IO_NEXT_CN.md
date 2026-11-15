# 已找到并实际恢复原7a6 WM；下一步是当前因果IO，不再等待“迁移权重”

2026-11-15 23:46（北京时间）实际完成，当前V4五组仍是22:53总计划26b67d55…。

## 本轮真实增量

- 从原training-result只读索引找回精确位置，46308已有原权重：`/mnt/yuanyue/data/go2-piper-world-model/own-M64B-behavior-training-20261027-v2/M64B-behavior-final.pt`。文件11,314,598bytes，逐byte SHA **7a6ba61e89d824cd3e0a78f469a0925f91c784ab1f77ed4273365d6c313f569c**。早先局部目录/文件名检索未命中不等于不存在；此缺口现已解除。没有连旧46174、复制权重到本地/Git、重新训练或重开旧training root。
- 从原脚本逐byte保管了**5个推理源码文件/55,165bytes**，原模型算法与checkpoint loader不改；`inference_source/original_behavior7a6/SOURCE_INVENTORY.json`逐SHA记来源。源码库不再依赖本机另一checkout的绝对import路径；不包含Runtime/Actor/环境/数据/权重。
- 新`v4_original_wm_loader.restore_original_cpu`在46308**实际执行一次**：原`load_behavior_checkpoint`严格验格式/architecture/config/contract和state_dict，恢复**BehaviorM /2,819,568参数**，CPU/eval、全部requires_grad=false，原45D normalization保留且SHA **23c4dccac745293493c7639d085851e71fb210bc370d2cd6cc96e656eb8def6a**，未fit或重算归一化。墙钟5.692586907s；CUDA空、CPU线程2，禁止native/Actor/API/network/child process的fence无触发。
- 原contract SHA **939aec4df2529f2afabed9e72aa49bef8297fe29c80e19ff54c39357276b79b8**，actual class/architecture与原action11/public60/target8 ABI一致。**真实checkpoint restore=1；WM prediction forward=0，世界/Actor/训练=0。** 构造NN并严格加载state_dict不是一次训练；恢复成功也不是V4当前query或控制资格。
- 原端报告`/mnt/yuanyue/reach-runs/V4-original7a6-CPU-restore-20261115-v1/ACTUAL_CPU_RESTORE.json`与本地小副本`operations/V4_ORIGINAL_WM_CPU_RESTORE_20261115.json` SHA均 **39c9a2f95f6325c5c1fa78b23a5093f38aa2671e4e74adeff92dcd8e9a41e246**。数组/归一化向量/权重未下载。此前过宽metadata find已仅终止本组该find PID，未碰Data进程/锁/H。

## 已可直接复用的调用

```python
wm = OriginalBehaviorWMAdapter.from_checkpoint(
    exact_existing_checkpoint_path,
    source_root=exact_original_inference_closure,
    query_provider=qualified_current_source_query_provider,
)
```

生产caller在新程序自己的资源/预算下调用一次；该函数只恢复CPU模型并装配原raw adapter，不自动创建query或预测。原文件SHA/原算法保持，不借用旧root的执行许可；实际native权重/scene/程序/freeze/zero/lease仍由Data独立处理。

## 接下来已缩小到这些真实IO问题（不是新增通用许可门）

1. **原sensor＋已发history**：source应从本回合原observer和实际accepted/issued callback接入原`BehaviorQueryBuffer`。3个真实frame、相邻0.1s，18维原已发位置参考覆盖完整200Hz窗口/尾部，actual owner/observed skill时钟单独保留；不拿torque/gain、delayed队列或候选skill覆盖observed owner，不补frame/history。Reach继续负责这层模型IO适配，不交Data代研发。
2. **VLM当前public query与WM原anchor分清**：同一当前决策clock可以有原fresh off-grid公开图和WM最近10Hz anchor（年龄有界）。target8必须对应WM实际anchor图及该时钟/原source descriptor，不能把另一时刻的bbox或已过期left alias塞入。source提交明确current-observation→original-query绑定；缺关联/target8保UNKNOWN，不因模型已加载而填0伪造可观测性。
3. **公开动作映射**：绝对PUSH goal不能通过私有实际箱位/声明initial箱位凑相对推距；原CLIMB模型tail的destination与选定registered native adapter的SOURCE height必须区分。当前source code的原native bind只收source height，语义Intent/WM可描述destination；需要同原judge/option的显式持久映射。不能用删掉same-params/option-hash检查硬过接缝，也不能把0.20→0.60的40cm增量映射成20cm。
4. **代价模块责任不变**：B/D共享后继cost provider仍由Reach实现；真实PUBLIC goal/support/caller效果映射齐后继续，不把raw terminal elapsed/logit叫成功Finish/READY/整链代价。原20cm/high-deck支撑、完整terminal和三placement资格仍未齐；不擅改图、加中台阶/降平台或用模型输出冒native能力。

新6项loader源码/namespace/错权重拒绝检查通过；与此前合计**100项软件检查（62本轮V4相关新检查＋38旧回归）**，这些不是100模型forward或研究试验。实际restore报告单列，不与fixture计数混淆。所有旧dirty/closed/失败/原门与已冻结critic/heldout用途保留。
