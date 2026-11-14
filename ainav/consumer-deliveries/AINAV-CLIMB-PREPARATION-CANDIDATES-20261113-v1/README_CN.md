# 同任务后继接近候选：有限NAV目标，默认关闭，未物理资格

本包落实2026-11-13 23:39总计划AINav任务。版本名来自该计划实施起点；完整验证/发布跨至2026-11-14。不是旧收臂成功/审计包的重复接收，新增变量是**同一CLIMB任务的NAV准备子goal横向选择**。

## 立即可消费的接口

```python
from climb_preparation_candidates import public_candidates, selection_from_payload, bind_to_host

# 公开静态CLIMB reference，不传GT base pose/脚力/未来cost。
rows = public_candidates(target_ref=declared_ref.ref,
                         declared_approach_xy=declared_ref.xy,
                         source_surface_height_m=declared_ref.surface_height_m,
                         registered_climb=bool(declared_ref.climb_surface))
selection = selection_from_payload({
    'schema': 'AINav-finite-CLIMB-preparation-selection-v1',
    'target_ref': declared_ref.ref,
    'candidate_id': 'lateral_plus_0p04',  # original / plus / minus有限三值
})
# 新source实际导入的Host module；新host首步前，不热改已有module/global。
bind_to_host(host, actual_caller_module, selection=selection,
             enabled=explicit_arm_enabled, emit=existing_journal_sink)
```

`original`=原接近参考，另外两候选仅NAV子goal的WORLD y±.04m；源层只收0。PUSH公开任务目标、同一CLIMB ref/目的height、原READY和CLIMB stop都不改。当前公开例子(0.050000000000000044,-2)→NAV准备(-2/-1.96/-2.04)，不是允许任意XY、侧推或yaw。

只有原judge已判PREPARE才会调用本口；若原本READY，绝不强制多走NAV。原型是API0/离线H1方案验证，不冒VLM自主规划/部署时可用的后继cost模型。完整cost/成功预测None，真实局部最优与整链最优排序反转未证。

## 文件与源差分

- `climb_preparation_candidates.py`：stdlib有限catalogue/严格payload/默认关闭fresh绑定。
- `source-delta/ainav/native/execution_judged_course.py`与patch：原caller SHA22a10aad…，仅`_native_nav`加可逆goal口。其它Host方法，包括原judge、READY、原目标恢复、期限/准备次数，都不变。
- `common-source/`：完整283源，280原样＋既有Reach-v2两capture hook＋新增caller；`ainav-source.json`只记baseline lineage。
- `explicit_preparation_consumer.py`：原consumer仅source verifier显式三文件SHA白名单和逆变换，其余组合/driver/原两请求planner不改。`COMMON_SOURCE_FORK_MANIFEST_v1.json`是current bytes，旧strict loader应拒新fork，不能改旧expected来掩盖。
- `CANDIDATE_CONTRACT_v1.json`、`INFORMATION_PERMISSIONS_v1.json`、公开候选payload与源码位置表：供Reach固定同任务/同域/同信息评价，供Data精确接入。

建议新H1共同底座显式固定已验证v2 direct stow，所有arms相同；`original`只指原NAV准备goal，不伪称整个控制源未改。core、原成功门、Actor/物理/任务/退出保持；Data须在新程序自己显式绑定既有stow库，本包不会自动安装它。

完整说明：`/home/yuanyue/main/work/ainav/docs/AINAV_SUCCESSOR_PREPARATION_CANDIDATES_20261114.md`。

## 软件证据与不能冒称的部分

25项本机stdlib CPU过；25是同一新套件，不把此前20/17中间结果另加。执行固定原caller/原reference冻结与原factory方法，使用真实NativeOptionExecutor/NativeOptionSession/TwoPhasePlacementMachine/RegisteredNavMachine类，保留旧PUSH root/proxy/TargetBridge别名；RegisteredCompactNav模型/几何/捕获构造是显式记录端口，不是实际资格。另fresh解释器从本common-source真实导入完整Host类定义，禁numpy/torch/mujoco等，未构造Host/Runtime/模型/世界或step。

实际原环境NumPy/NavSkill profile、deadband/arrival、原capture/geometry/QP/动态仍未验证。不同有效goal并不保证每状态电机不同；owner应在CPU和实际新结果核原controller消费与归并，若等价就否证/停此候选，不换δ/seed/障碍追胜。46308只读preflight仍连接关闭，远端本套件未执行，不能称两端过；该连接不是Data运行门。

## Data下一最小动作（不是许可或新成功门）

1. 接收此包的精确文件SHA和3-file current fork；在其自己新owned staging/loader消费，不改旧reference-source/P1/P2/stow-v1/v2。
2. 原环境核actual RegisteredCompactNav/NavSkill goal及profile；确认root/executor/factory和previous PUSH proxy是原真实关系，不能压平样例签资格。原身分/immutable/支撑12N/queue/逐步guard/effort/QP/FIFO/4s/stop全保留。
3. 与Reach固定H1完整协议：共同task与terminal、同信息/版本/场景起态和重复规则，区分两固定方案离线问题验证与真正current-only/successor-aware策略比较。原数字不喂planner/fit，不能构造未执行oracle。
4. 尚无新物理scope/任务派发。本包不授权resume旧zero/根；新整程序/fresh own-zero/lease/watchdog由Data。不要自动重跑旧成功的0-offset只为录像/标签；任何必要新配对baseline需属于明确的新H1预注册cohort，而非旧成功点重演。
5. 未来第三视角如录制，只直接live Runtime原片/同模拟钟，冻结前接入，不回放或补造旧视频。可选视频/诊断不当原native成功门。

Default-off只是不安装/不替换，不卸载已经安装的callback。零/主阶段与不同arm须新解释器/module身份，禁止hot switch。主任务goal不变、没有新的完整成功/代价权衡/排序反转结果；WM暂停，训练/真机不开放，evaluation_ready=false/holdout0。
