# 独立原生观测资格测量：仅2 NAV／3观测，不是任务A/B

- source：AINav immutable `c3c695b5fa10daa826e85fcad04dd737b4810bc5`，26源逐SHA未改；三箱几何／颜色／原RGBD proposer/matcher、原Actor／12N／4s／FF／effort／QP／FIFO／接触与原NAV成功门不改。
- 精确purpose `OBSERVABILITY_QUALIFICATION_ONLY`；新scope `data-46308-T-COMPLEX-observability-only-20261115-v1`，新完整程序own-zero/main各至多1，无自动重试／替代／旧root恢复。
- 原SupportedCapture→固定原NAV(-.08,+.15,0)→固定原NAV(-.08,-.15,0)，只记录3个实际fresh边界与原关联结果；0 PUSH，不挑最好帧／补视角。按 `planner.motion_complete` 与 source `finish_from_driver` 结束，绝不套 `while not host.complete`。
- 成功只指2原NAV真实succeeded回执＋3个fresh原观测完成；`task_success=false`、`AB_comparison=false`恒定，visibility不等PUSH READY、三有效选择或全任务成功；没有Reach搜索／critic／训练输入。
- 新程序有限cap：task125sim、scope150sim含自身zero/双aux、57600wall、输出3GiB；CPU2／RSS4GiB／GPU3GiB，GPU0／原UUID／canonical inode不变。新wall cap在任何物理前，按A/B真实最慢377.005wall/sim和2×原NAV60sim＋capture2.24sim的完整域事前预算，保>1.2倍＋zero/收尾余量，不是给旧4800wall pair延时或重试；旧pair global_stop／失败／费用／scope不改。
- 代码仅已实现与新Data lifecycle软件检查；native资格和dispatch只以新权威H／新自身zero/cold／launch记录为准。软件检查不算新研究样本，未重跑AINav源fixture。
- 生命周期：`stage_and_freeze.py`→显式`control_observation_study.py OBS prepare`→`zero-dispatch`→`zero-run`→`zero-cold`→`fetch-zero`→`close-zero`；每步仅一次。main须另fresh准入后显式派发，不因代码存在自动启动。禁止重复任何已经消耗的命令；当前次数读远端H。
- 大raw／MJB／原query数组／权重／视频留46308，本地仅小metadata／少数原query，GitHub code-only。不连接旧46174，不训练WM／DINO／Actor、不启真机／第二owner／新自动化。
