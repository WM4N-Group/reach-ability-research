# E20/40mm唯一动态main失败与完整1×原片：先交最少结果

scope data-46308-E20-prearrival40-direct-live-20261116-v3；source04a9c0fe…/program39ef86d5…/asseted6267bb…。own-zero1/main1已closed，原准入/相机/NN/安全门不热改、不重跑。此为三箱+C箱顶20cm的DEV，不是原.60m高台成功或五组胜出。

原NAV15.090 succeeded、首PUSH15.095 started。**26.470sim真实触发单点40mm提前原brake**（gap34.992mm），geometry仍false，未伪标到位。27.190sim原内部NN clock确认true/0.5s，但placement仍false（XY31.810mm/gap−30.993mm）；**27.410sim/5482tick原confirmation丢失硬停**：`Original native settled confirmation lost during placement brake`。PUSH无复合succeeded/failed终态回执，保持None，CLIMB/后箱0、共有H attempt0；不由异常补技能负类，也不宣称更早触发已修复问题。40mm dynamic family main合计1，不扫margin/换seed追胜。

完整现场原片：`/mnt/yuanyue/data-team/deployments/46308-20261114/runtime/workers/data-46308-E20-prearrival40-direct-live-20261116-v3/main/E-direct-live-1x.mp4`；本机仅196166bytes副本`/home/yuanyue/main/work/data-team/manifests/E20-prearrival40-direct-live-46308-20261116-v3/E20-direct-live-1x.mp4`。SHA 2b6c43ce4edb1208d73457f5cd8aadf1b0335ca753e48d6ef291605a127f18ed，1280×720/10Hz/275帧/1×约27.5s；18 raw chunks逐SHA、ffprobe实际解码275帧通过。原母版保留，非状态回放/重渲染/插帧/成功剪辑。最后grid画面5480tick/27.400sim，真实终态27.410来自原result/event，不从片长推任务时间。完整FIFO/PD冷审尚未补，不冒已全流通过。

main原成本5482命令/27.410task+6.505aux sim/**3522.131102207wall**，usage_known=true、resource_censored=false、close0、峰值RSS2286088192bytes/GPU810549248bytes。own-zero另18.663792928wall+6.505auxsim；新静态资产编译11.758566817wall，旧5a静态失败10.479544644wall、Data v2漏privacy-helper的zero授权1/Runtime0/main0及未知wall/RSS全部保留，不合成免费0/项目总费。原episode.censored=true为异常截断，不改成资源watchdog。

原loaded路径/目录策略未动：15926002次路径出现请求、10968 path pass，resolve2121.001589334s（非内核I/O次数）；Data guard1163.920884856s含size281.162020663s，原driver3432.376559024s，这些包含/重叠不能相加。新19:35计划02dc65ed…已接：下一项先改静态/资源审计热循环，只做新源/离线资格后独立性能验证，不再新增E/五组/bulk先排、不热改此closed run。
