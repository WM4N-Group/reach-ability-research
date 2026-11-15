# T-COMPLEX-01：首对真实闭合；未建立任务收益，继续独立观测资格与执行吞吐准备

2026-11-15。覆盖此前“B首段在途/终态与视频待原件”的当前状态，不重写历史记录。

## 原件与独立消费

- Data B/pair正式release：`AINAV-DATA-T-COMPLEX-01-FULL-B-AND-CLOSED-PAIR-DIAGNOSTIC-ACTUAL-20261115-v2/release.json`，SHA `161d483bd5c40d8a4359fc31da6dd3a088a320eeeba8748e0323f1ceb047b81b`。
- B原result：`4a93cc0873798da5001a0ee2d01952f9a9b5bf99192b8864b5e1a94c379b6a34`；A原result `8295239278efda4ee8b058d70a40de28825bae8a568ec1cc0c703944a4c4ce23`不变。
- 本组新reader `operations/consume_complex_closed_pair.py`在46308实际执行，逐SHA核A/B已发布小成员、scope/program/scene/source/零与主结果和closed ledger，独立验证A462/B995行**完整原journal链**；核B终态仍逐byte含此前独立读取的18:28 journal前缀。Data九流/PD/NPZ/pixel冷审仅消费其报告，不冒本组独立重算。
- 本组报告：`operations/T_COMPLEX_01_CLOSED_PAIR_CONSUMPTION_20261115.json`；远端原件`/mnt/yuanyue/reach-runs/T-closed-first-DEV-pair-consumption-20261115-v1/CLOSED_PAIR_CONSUMPTION.json`，SHA `447e534d97ab85d13a0d336cbe8419fde45b89f9869b6eb1f66773d66d96cef5`。reader SHA `008f2440334ed8398709fb2159c1ffc2db4133b36e1a6e3e688b8c9d38dd3c81`。

## 实际结果，非完整任务方法比较

| 项目 | A greedy | B finite multistep |
|---|---|---|
| 唯一main终态 | FAILED_NO_RETRY，原RGBD关联拒绝 | FAILED_NO_RETRY，原wall watchdog |
| resource_censored | false | true |
| 主世界实际sim/200Hz命令 | 2.240s /448 | 12.720s /2544 |
| 实际高层bundle决策数 | 1 | 1 |
| 原任务native option installed | 0 | 1，NAV |
| 原NAV Actor-forward | 0 | 524（不是524选择） |
| 原任务native terminal receipt | 0 | 0（未补造成功或技能失败回执） |
| 真实placement/重构 | 0 | 0 |
| scope含自身zero与两aux的sim | 15.250s | 25.730s |
| scope ledger wall | 880.527903158s | 4781.901017321s |
| scope output高水位 | 218453439 bytes | 232149061 bytes |

A仍在原capture448步后第1PUSH前因`Current original RGBD association unavailable; no static-pose substitution`拒绝；不是几何死局或PUSH控制失败。B原NAV确已admitted→installed→started并真实发原Actor命令，但**无NAV terminal**；原终态`Full-task owned wall watchdog, no retry`的resource censor不是NAV controller failure，也不是有限前瞻.195403451s超过.25s搜索预算。原trace恰在module Path.resolve扫描处被watchdog中断，仅是中断位置；没有独立profiler/benchmark，不能归因全部吞吐开销。

两支前448步8通道相同、首public query除存储path外相同的先前实核保留；它证明初始信息相同，**不证明名义候选都已native合法**、后续hidden state相同或强合法greedy已输。两支均未完整完成原任务，未达到2次重构/3个有效选择，更没有基线失败而本方法成功的证据。标准bounded search仍是机制原型，不是新算法创新。

## 原live视频已发布，不再说视频0

本reader独立核远端A/B/pair三视频**文件SHA**与Data manifest一致，未下载/解码原片或独立复核raw像素；三者留46308。视频源来自本次直接live raw（A23/B128帧、原960×540、10Hz）；注释仅加80px头栏，单片960×620、pair1920×620。pair按同sim clock，A结束后黑色“无后续”说明页，不冻结/复制世界帧。H264是有损证据编码，不称raw像素无损母版；原raw仍保留。视频末帧量化时长不代原终态sim。

这是各自**完整可用失败/资源截断episode**和同钟pair，不是完整任务成功影片。不为补成功视频重启closed root。v1导出因5.38MB journal超过小文件2MiB限制未完成，v2保留完整原journal于远端、仅导SHA/reference；**两版是结果出版，不是两次物理试验**。

## 接下来可直接推进，不新增Reach签字门

1. **先解决独立观测与源执行资格，不复跑本pair。** 已获Data收件的immutable c3c695b5…源固定capture→center query→NAV(-.08,+.15)成功后query→NAV(-.08,-.15)成功后query，0PUSH；用measurement自己的motion_complete终止。是否已关联原对象、原门是否通过、未达/censor全留，三视角不是三有效策略选择，不能给测量episode写task_success或作为critic训练。
2. **资源准备采用新程序/真实吞吐证据。** source owner可在新开发源单独核安全语义等价的吞吐优化；不能热改closed b08、用静态栈样本声称瓶颈已证、删immutable/alias/identity检查或盲抬原cap。Data按新source、finite measurement终止与真实开销事前定有限cap/新freeze/own-zero/lease；本组已评审同一测量问题，无需等待额外Reach回执才装配。若新source需改观测/候选规则，必须两方法共享且另登记，不能只给B补观测或把旧A判法换掉。
3. **资格之后才新比较。** 一个视角接受原alias只说明必要可观测性，不等完整PUSH/原成功链资格；三个固定视角都无关联，才作该固定测量域No-Go。先原记录确认有完整动态可行计划与真正多个选择，下一对才有能力差异解释基础；不追本DEV失败改场景找赢家。
4. **其它路径不阻塞T，也不越用途。** bulk24已登记0f9e0e03…/已收源但未派发/不refit当前model；G3一次fit3371ac20…/model a8b1f165…冻结，CAL07仅1/3，08/09/VAL未齐，不评分/refit。

所有dirty/旧closed/原actor/12N/4s/identity/immutable/support/guard/QP/FIFO/CLIMB stop保留。计算仅46308，Data唯一物理owner，本轮只有本组只读CPU消费，没有新物理、训练、锁/H/进程改动。
