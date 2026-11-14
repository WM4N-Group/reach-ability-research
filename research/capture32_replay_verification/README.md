# capture32 独立重放证据核验（研究工具，不是控制器）

本目录归档 Reach verification 已完成的一个小型本地里程碑：checker、fcf13 NPZ 数据适配器、输入合同、必要测试和外部哈希索引。代码只读已有证据并做数组/谓词核验，**不生成候选、不执行planner/FK/IK、SDK、GPU或物理**，不导入producer诊断脚本。

## 版本与范围

固定原 source 为 `sim2real-main-team-v022r2-fresh-ground-fallback-a`，capture32 / step9411 / role=original；原控制b870、run a537及诊断fcf13的完整SHA均见 `external_evidence_index.json`。

- `replay_checker.py`：标准JSON报告契约校验；纯stdlib。检查原输入dtype/shape/值、12份完整bool mask、666有序索引、11chunk、原返回、9个gate重组及独立/exclusive/累计统计。机器匹配仍需人工源码/依赖来源审核。
- `audit_delivered_npz.py`：**仅固定fcf13布局**的实际NPZ证据适配器，复用上述校验primitive；不要求原交付伪造33个独立profile次数。该交付实际记录5类return observer，其下依赖由冻结原源码链与实际返回观测核证。
- `evidence_paths.py`：显式证据根、只读定位、路径边界与输出保护。
- `input_contract.json`：原审核合同，字节与外部已审版本一致。
- `test_checker.py` / `test_paths.py`：人工小数组和临时文件测试，不依赖native数据或NumPy。
- `external_evidence_index.json`：原件/历史回执/代码来源的root-relative路径与SHA，**不复制原件**。
- `milestone.json`：本次归仓前HEAD/分支/clean状态、授权范围和验证摘要。

**非自包含数据集、非“换电脑直接复现实验”。** 原oracle、模型资产/冻结源码、native日志、诊断NPZ和历史回执均在仓库外；缺一项要报告缺依赖，不能自动下载、重放planner、补零或重新生成“原件”。这里不纳入producer控制/诊断代码、NPZ/raw/日志/视频/权重，也不改仓库既有`docs/`和历史实验结论。

## 环境与最小测试

Python 3.11+；通用checker与24项单元测试只需stdlib。NPZ适配器另需NumPy，本次验证使用已有隔离环境的NumPy 2.4.6；未安装依赖，不应把项目库装到系统Python。用已有兼容隔离解释器替换下文`python3`。

从仓库根运行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s research/capture32_replay_verification -p 'test_*.py' -v
```

覆盖：同count错bit、同bytes错shape、错dtype/indices、strict阈值、slack/AND/拒绝统计、缺证据、symlink越界、输出覆盖保护，以及迁移后的原件hash校验。只使用临时目录，测试结束自动清理，不在repo产生日志或测试原件。

## 外部证据根（全部通过CLI提供）

设置以下环境变量为本机**已有**目录，名字可不同，但内容SHA必须保持：

|变量/CLI参数|所指根目录及最低定位|
|---|---|
|`CONTROL_ROOT` / `--control-root`|原 `wm07-fresh-ground-fallback-v022r2`，含package manifest/原代码/USD层|
|`RUN_ROOT` / `--run-root`|原 `wm07-v022r2-fresh-ground-fallback-user-test-a`，含run manifest与native-small原件|
|`TERMINAL_REVIEW_ROOT` / `--terminal-review-root`|原独立terminal_review目录，含`complete_mask_pair_index.json`、`last_native_control_line.jsonl`|
|`VERIFICATION_ROOT` / `--verification-root`|原stage2 verification目录，含**未改字节**的`original_oracle.json`及历史回执|
|`DIAGNOSTIC_ROOT` / `--candidate`|fcf13诊断目录，含diagnostic manifest、npz及已记录依赖证据|
|`OUT_PARENT`|仓库及所有证据根**之外**的可写已有目录，例如专用临时输出目录|

外部JSON中的绝对路径是原历史来源文本；本工具不改它，也不直接使用它定位原件。读取按CLI根与受信任role/relative_path映射进行。迁移只改变位置，不能改JSON字节让SHA“跟着走”。oracle和输入合同SHA固定，候选manifest SHA必须由调用者显式传入；root escape、缺文件或错SHA均拒绝。

### 复核已审fcf13数据（不运行重放）

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  research/capture32_replay_verification/audit_delivered_npz.py \
  --control-root "$CONTROL_ROOT" \
  --run-root "$RUN_ROOT" \
  --terminal-review-root "$TERMINAL_REVIEW_ROOT" \
  --verification-root "$VERIFICATION_ROOT" \
  --candidate "$DIAGNOSTIC_ROOT" \
  --manifest-sha256 fcf13d3081ed837de14cd778aa9b3ed092c4079f625f72ce419b24fffb2355a8 \
  --output-dir "$OUT_PARENT/capture32-data-check-01"
```

输出目录必须尚不存在。它只读约10MB已有NPZ并验证dtype/阈值/AND/min/argmin/索引与原返回；不会重新生成Sobol样本、重算物理几何/载荷、调用模型或启动控制。返回0表示数组与绑定检查完成，2表示缺依赖/不匹配；结果保存在新输出目录的`result.json`。

### 校验标准JSON报告

fcf13交付不是下面的标准JSON模板格式，应使用上面的专用适配器，不强行伪造trace。未来同一capture的报告若满足原合同，可调用：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  research/capture32_replay_verification/replay_checker.py check \
  --control-root "$CONTROL_ROOT" --run-root "$RUN_ROOT" \
  --terminal-review-root "$TERMINAL_REVIEW_ROOT" \
  --verification-root "$VERIFICATION_ROOT" \
  --candidate "$DIAGNOSTIC_ROOT" \
  --manifest "$DIAGNOSTIC_ROOT/artifact-manifest.json" \
  --manifest-sha256 "$MAIN_SUPPLIED_MANIFEST_SHA256" \
  --report replay_evidence.json --output "$OUT_PARENT/capture32-contract-check-01.json"
```

标准报告需提供原identity/input-schema、12完整mask/11chunk、原return、9 raw metrics/gate masks/slacks、统计、真正调用trace及model/frame来源。具体机器字段以 `input_contract.json` 与checker为准；原详细合同/模板仍位于外部verification目录。本工具不包含`prepare`，不会重建或替换既有oracle。

返回0最多为 `MACHINE_EXACT_MATCH_PENDING_INDEPENDENT_CODE_AND_DEPENDENCY_PROVENANCE_REVIEW`，1为报告不匹配，2为根缺失或输出不安全。不可把自报runtime flag当作实际调用证明，最终接受仍需人工读原代码/执行证据。

## 科学与授权边界

历史审核接受精确native **bool/有序索引/return**一致性与同次CPU分项解释；原CUDA中间浮点数组、dtype/device/TF32未直接随调用JSON记录，不能将CPU分项冒充native逐位测量。源码行序累计首先归零不等唯一物理原因；单位必须区分m、关节角余量和混合force/moment residual；10mm为ready后偏好，5mm才是leg-path hard门。

本目录不授予控制编辑、SDK/物理运行、阈值放松或Goal完成权限。里程碑只做一次本地提交，**无push授权**；原外部审核原件不改，后续研究/归仓安排仍由main协调。
