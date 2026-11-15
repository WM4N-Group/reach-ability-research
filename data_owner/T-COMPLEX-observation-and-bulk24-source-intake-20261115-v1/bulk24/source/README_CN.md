# 十个新几何配置：批量采集的可执行source矩阵（不是派发/训练许可）

本包按2026-11-15 14:00总计划的百级采集/十组覆盖目标推进，**不替代当前优先T-COMPLEX-01**，不修改其任何已冻结source/program，也不因采用本包重跑已成功scope。既有TRAIN6/CAL/VAL按原协议继续。

## 具体变化与真正计数

以完整v6原`full-4`为共同祖先，只变化两个任务相关几何因子：

| 组 | B所在lane Y(m) | B宽(m) |
|---|---:|---:|
| bulk-g01 / g02 | -1.75 | 1.4 / 1.5 |
| bulk-g03 / g04 | -1.85 | 1.4 / 1.5 |
| bulk-g05 / g06 | -1.95 | 1.4 / 1.5 |
| bulk-g07 / g08 | -2.05 | 1.4 / 1.5 |
| bulk-g09 / g10 | -2.15 | 1.4 / 1.5 |

lane是原场景B/C/高台与相应目标任务坐标的一起平移，不是step后传送或body/live pose覆盖；相对初始机器人与A的入口几何会变化。B宽度直接改变原free body/平台支撑边缘与视觉支持，不是只改远端gap/UUID/seed。长度2.4m/高度.2m/质量.5kg/底μ.4/足顶μ.8、C原full4材料/其它布局、机器人/Actor/原门/seed4301均不变。没有要求`.2`后NAV→下一PUSH，也没有20kg目标或超高技能；原A仍是场景背景，不请求其PUSH。

`BULK_MATRIX.json`固定10个几何配置、left/right两个已存在ground prefix与三个原CLIMB preparation candidate。**20 context/60潜在candidate组合是配置目录，不是20/60已批准或已运行main，也不是60独立样本。** 当前新几何dynamic资格/实际capture/有效不同决策state均0；高度/footprint/source静态一致不代表动态可行。若实际同钟公开状态/视觉仍归并，按归并后覆盖报告，不能为凑十组把几何label当有效组。

所有十组共享full4初始化/构造祖先；这是同TRAIN祖先族内覆盖扩展提议，**不是十个独立祖先/TEST组**。同geometry所有prefix/candidate/repeat必须同split；既有full4已TRAIN的祖先不能因新case_id当blind heldout。Reach须在新采集前固定新用途/分组/首批范围/重复与停止规则，Data按实测容量冻结具体新batch/自身zero/lease，保所有失败/未达/资源censor。预设全六十派发或凭本包fit均不允许；原`training_allowed=false`是冻结原native protocol的底层/DEV守卫，不是把新数据自动改为旧DEV或自动授予高层fit。

## 最小实际源差分（Data只用于新snapshot，不写在途）

原`integrated_course.validate_protocol`严格只收自己plan的精确case。本包**不删该校验、不 monkeypatch函数/扩大任意XY**；提供一份显式增量plan：原五条case逐字段保留，再加十条精确case。原Python构造器/validator/HostProfile/candidate/控制器源码不改。

`source_delta(enabled=True)`返回唯一source目标`mujoco_zyh/integrated_course_plan_v1.json`的新文件bytes及旧/新SHA。它不执行安装。只可由Data在一个**全新、尚未冻结/运行的source snapshot**中使用该bytes替换那一个plan文件（新SHA515b4d7f…）；不在旧环境/旧closed或当前T/CAL source中替换。新完整source/program必须记该明确几何差分，不能冒仍为原283字节完全不变。

```python
# Within Data's new fresh source/program only; dependencies are its same-source
# original modules, not shims or a parallel world. No code here allocates scope.
selection = BulkCondition('bulk-g01', 'left', 'original')
condition = build_condition(selection=selection, source_root=NEW_SOURCE,
    integrated=original_integrated_module, host_profile=original_host_profile,
    candidate_api=original_published_candidate_api, enabled=True)
# Existing owner build_plan must really consume all four values:
native = condition['original_native_protocol']
config = condition['runtime_config']  # original device-only overlay
requests = condition['requested_intents']  # exact NAV -> PUSH -> CLIMB
payload = condition['preparation_payload']  # actual original finite arm binder
planner = OriginalRequestedIntentPlanner(requests, journal, max_requests=3)
# Existing original request_contract still requires exact3 matching successful
# semantic receipts. No cold Runtime/world/Actor or dispatch is done by this API.
```

helper核新plan SHA与原integrated/full_course/template/deployment源码SHA、同source callable namespace/HostProfile、稳定原candidate API。返回的新protocol由**原validate_protocol实际调用**验证；原max420/12N/4s/immutable goal/FF/effort/QP/FIFO/CLIMB stop全部保持。Data若为新batch冻结更严技术watchdog可沿现runner做，不能热改旧根。不是绕过源检查/`scope`或`authority`的新层。

## 下一步验收和No-Go

- 最小source资格后合格组即可进入Reach新用途有限batch，不等十组全动态通过；当前T复杂任务原可用窗口仍优先。建议先按原candidate/固定两prefix接新geometry，不直接把完整60目录当自动实验计划。
- original first CLIMB PREPARE之前的真实前缀/各原门、source/实际candidate消费、first same-clock public45D/RGBD可辨性是有效覆盖依据。源拒绝/前驱失败/缺观察/资源censor全保，不填负标签/终点数据回灌，不换新ID重试到成功。
- 不做姿态/摩擦/gain/成功门调优追胜；共享源/安全故障停止该版本，单组真实失败完整发布，Data按原停止规则决定后续合格组，不由本source自动replacement。
- 当前只是可执行装配与stdlib软件检查。测试60组合只说明有限接口/原公共catalogue匹配，**不是60物理或科学样本**。动态Model/Runtime/Actor/原8流/原command NPZ仍由Data实际资格，不旁路锁/新开本组world。
