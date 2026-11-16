# E-SKILL20：用户授权环境适配后的独立任务版本

**这不是原0.60m高台V4成功。** 2026-11-16用户明确允许改变环境参数到当前技能适用范围。
本包选择已有source接线的地面PUSH→20cm动态箱顶CLIMB→同支撑NAV/原停稳，
不把新增两次静态台面CLIMB/新WM接口作为首次E前置。原V4源码、场景、closed根与结论均保留。

## 精确环境变化

- 三箱的尺寸2.4×1.4×.2m、.5kg、底摩擦.4/脚顶.8、初态、六个候选、三项必需绝对placement不变；所有PUSH仍地面、+world-X。
- **任务终点改到已推放的C箱顶0.20m**，goal矩形X[11.1,12.1]、Y[-3.2,-2.0]，仍为1.0×1.2m。
  C箱本身是实际承重目标，不能以地面相同XY或旁边静态平台验收。
- 原右侧静态goal_deck降到0.20m，作为辅助几何，**不是任务goal/必须CLIMB对象**。
- cx_lower_baffle由Y[-5,.7]缩为[-5,-3.7]，扩大地面通道。没有给E私有路线/世界pose/正确顺序。
- scene SHA：`08a260a4bda6de75e1f0012e12a4a3a04a5c682b0534f785a7b504af4a666381`。
- 三箱显式采用共同review色。新asset有环境几何改动，**不能套用af09的398 nonRGBA全不变证明**。
  原robot/actuator/engine签名、箱体质量/初态/foot-contact摩擦仍由原compiler核。

## 原方法与原门保持

`rule_baseline.py`与source59的SHA **43998a23…**逐byte相同。E仍依据共同公开候选、current关联和实际receipt，
无VLM/WM/新优化。全三placement、真正20cm原CLIMB回执、原NAV/stow与真实C接触的连续.5s停稳均须成立。
12N、NN、STOW、FF/QP、FIFO、4s和stop阈值未改。终点从.6改为.2后要求**至少一次真正20cm CLIMB**，不是免CLIMB；
原.6任务的两次/静态CLIMB义务没有被追溯改写。

`goal_support.DynamicGoalRegistry`只扩展task-goal声明类型。固定surfaces字典不塞movable geom，
原SceneRegistry.verify_compiled逐函数原样继承；cold声明不是supported witness。
只有既有sealed LiveClimbNavSourceWitness经过真实CLIMB、原12N/实际C contact/placement后，
才建立同世界私有NAV registry，并把实际C源ref作为终点support。原SceneRegistry类未全局patch。
最终reader从真实`mj_contactForce`核C geom四足normal load，不能用总foot forces/高度/声明替代C接触，
且原三placement仍current、原NAV owner和bounded HOLD/dwell完整。

适配终点与原nominal C-top NAV曾产生两个相同参数的别名；首次软件测试真实暴露歧义，
已只保留最终canonical NAV，**不改E规则让它猜**。本环境公共域为**29 intents/26 anchors**，不是原30/27。

## Data新程序直接入口

仅在新fresh进程把本目录置于sys.path前；**不能在已import旧V4的进程热切profile/模块**。
同原完整execution-judged-v6/283 source与SDK作为底座；不要导入A—D方法/WM或原af09 render-only wrapper。

```python
from native_entry import compile_static_asset, construct_cold_components
from e_entry import build_E_driver
asset = compile_static_asset(enabled=True, source_root=exact_original_common_source,
    bundle=verified_sdk, output_model=fresh_exclusive_model_path,
    expected_scene_sha256='08a260a4bda6de75e1f0012e12a4a3a04a5c682b0534f785a7b504af4a666381',
    guard=Data_actual_guard)
components = construct_cold_components(enabled=True, source_root=exact_original_common_source,
    bundle=verified_sdk, model_path=asset['model_path'], model_sha256=asset['model_sha256'],
    expected_scene_sha256=asset['scene_sha256'], guard=Data_actual_guard,
    journal=original_journal, actor_device=isolated_device)
driver = build_E_driver(enabled=True, components=components, source_root=exact_original_common_source,
    bundle=verified_sdk, output_root=fresh_output_root, writer=actual_original_writer,
    journal=original_journal, guard=Data_actual_guard)
# Data's existing guarded runner alone steps driver, records original outcomes,
# preserves raw commands/contacts and directly records the third view FROM TASK0.
```

沿Data现成runner：冻结独立新E-SKILL20场景/程序/规则与限额，原必需own-zero/资源lease后一次main；
不先排无关component、不等A—D/模型或“以前有完整E成功”。如果在途已有旧E，原freeze收束、不热换本包。
先交新环境真实初始1280×720截图供用户检查与完整1×原片/最少终态；帧率、分辨率新freeze前按实测记录，
媒体留远端、不回放重渲染、不因录像缺失重开closed arm。此源码没有world创建/派发权限。

## 有限软件验证，不是实跑

新增16软件：真实原registry/contract/规则与明确fake runtime/typed软件回执，含明确fixture来源、goal语义、
C normal-force算术、12N/地面/错geom拒绝、原source/proof门未删、连续.5s，以及三placement→CLIMB C→最终NAV的
纯软件规则消费，planner仍不能自签任务成功。受影响E入口8项在新命名空间运行。
无numpy/MuJoCo/Actor/backend/API/WM/renderer调用，未生成真实MJB或图像，不冒动态资格。
实际成败/原片只能由Data新程序原件证明；evaluation_ready=false/holdout0/五箱false。
后续其他方法如采用，须同一新环境/公开信息/候选域，不能把它与旧.6场景混作同组对照或优化收益。
