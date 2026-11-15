# 首两条新用途监督行真实提取（不是拟合或优化收益）

## 2026-11-15 13:44：新TRAIN01/02真实PASS已消费并提取两条因果48槽监督行；03 plus-left唯一main已派，未提前fit/判gate

- 正式ordinal01 f253b6af…46成员/ordinal02 daa22f04…41成员SHA已核，原9流cold/ledger/新purpose/TRAIN/原2f82530d…/new program/同scope CAS与实际journal链绑定。01于13:17:30 closed，121.085main sim；02于13:30:25 closed，109.865main sim。不是旧DEV重标/复用zero/世界，仍同一个full4 TRAIN scene，不增加独立scene数或新优化收益。
- 新`operations/extract_new_critic_attempt.py`已在46308真实执行：首次原CLIMB judgment PREPARE→exact judgment_ref preparation binding→Host Observation语义SHA，分别落实际query4/query3而非固定frame；复用原48槽函数SHA efe42ae3…，public reference+公开45D+age，原候选API与actual native child goal一致。private judgment只用状态/clock、后果只作监督，private pose/FF/模型ID不入48槽；native install明确命令未发、首次命令分别97.290/86.585，均晚于feature97.285/86.580，age0。RGBD仅SHA不解码/不跑proposer，raw48值留远端。
- 两新行均original偏移[0,0]/SUCCESS：PREPARE→READY分别13.460/13.485sim，至原请求CLIMB成功终点23.800/23.285；不冒far-bank整任务或方法胜出。原actual_choice_changed布尔涉及共享stow，不能代替准备offset消费。2prefix/2不同公开proprio状态但仅1scene、目前2成功/0失败；完整6TRAIN尚未齐，既不fit也不提前No-Go/补类。新批已闭合2scope费用256.970sim/1567.950872ledger wall/高水位和339712775bytes，open03/其余未执行/旧未知另列，不冒全batch或全项目账。
- 13:39只读H快照：03 full4-left+lateral_plus_0p04新程序3259848d…已13:37:07 CAS唯一main，zero/main各1；04—06尚未派，07—12仍TRAIN门阻，不重发。新reader旧DEV实包在读数组/journal前拒绝，未知postdecision失败不凭error字符串造负标签：保UNKNOWN待原失败证据；未达不造输入、resource censor单列。首版reader的journal索引断言已按正式cold raw pin修正，未改Data任何artifact/物理，版本01v1/v2只算同一条。
- 已在未采heldout前补齐原协议承诺的Brier/常量Brier及READY/成功条件耗时RMSE/均值基线RMSE；censor与缺分母None规则不变，模型/超参/阈值/协议不变。本地/46308各32回归过仅软件，真实fit0/完整合格TRAIN批0/未出training manifest。下一消费03—06 closure、真实失败源资格、完整6门→一次真实fit或有限No-Go，再CAL/VAL只评价冻结model；G4/G5/G6继续。
- 入口`/home/yuanyue/reach-ability-research/operations/G2_NEW_TRAIN_ROWS_EXTRACTION_CN.md`与operations/G2_NEW_TRAIN_FIRST_TWO_ROWS_20261115.json；raw输出在/mnt/yuanyue/reach-runs/G2-new-critic-ordinal01-extracted-20261115-v2.json、ordinal02对应v1。旧5DEV失败/UNKNOWN费用/dirty/closed/12N/4s/identity/immutable/support/guard/QP/FIFO/stop/独立TEST0/主要贡献未证保持。

## 后续closed原件复用同一提取器

```bash
cd /mnt/yuanyue/reach-ability-research
/mnt/yuanyue/data-team/env-native-v1/bin/python operations/extract_new_critic_attempt.py \
 --release-root <Data新用途ordinal正式发布目录> --expected-release-sha <其release精确SHA> \
 --source-root /mnt/yuanyue/data-team/deployments/46308-20261114/workspace/workers/new-critic-cohort-46308-20261115-v1/inputs/AINav/common-source \
 --output <新的exclusive远端JSON路径>
```

输入必须是新用途正式发布，不接受旧DEV reader输出更换role，也不读在途scope造行。提取器只调用原Observation/Journal verifier与候选纯API、已有physical_features，不构造Host/Actor/Runtime，不解码RGBD、不重算proposer，不拟合。public-feature投影函数参数中没有result/private judgment/未来标签，输出恰原48槽；从相同原public task anchor生成名义offset后，还核本次proposal与原native NAV参数实际一致，不能只信选择布尔。

`captured_at`保留实际CAS main dispatch UTC作为**本次采集session起点**，不是伪造像素wall-clock。真实帧因果钟用原query/Observation/first PREPARE的同一sim time、采集age0、native install-before-command与首issued receipt见证。两种clock语义单独记，不用程序创建时间/后READY冒采集时刻。

原journal非本地复制member，而由正式release top-level source_journal_sha256及已pin cold.raw_source_SHA给出原path，实际原Journal.verify全链复核。正标签只取同intent原READY与实际CLIMB succeeded receipt；假如后续未达，输出无feature/无CLIMB label的attempt；资源censor不作负例。只有实际绑定native child的字面failed见证才标native failure；无terminal但有guard exception的情形须先读原失败source证明，不凭error文本补造failed receipt/负类，暂UNKNOWN不fit、不丢attempt。

两个raw行输出都带fit_allowed=false，原不可变cohort资格flag不改。完整6TRAIN门满足后才组装future-new数据及derived training manifest、按operations/G3_TRAIN_FIRST_FROZEN_EVALUATION_CN.md单次fit；若类/状态/源完整性不足就有限No-Go，不为训出模型去挖失败/扩批。旧五DEV与新行按用途隔离，原费用/上游失败保持。原定48槽/模型/超参/阈值未变；补齐的Brier/RMSE只是原预定义评价，不是引入新目标或看到heldout后换指标。
