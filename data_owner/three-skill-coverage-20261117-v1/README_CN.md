# 三技能覆盖输入：只读既有metadata，不是新L0/L1/L2实验

当前优先完成三技能能力/重训判断的Data输入，不再串行等待D3。该reader只消费既有fixed24正式release/result/cold-audit，以及单独的StageB三分支metadata；原始journal、数组、视频和环境不重扫，不运行原cold auditor或任何物理/模型/API。原76份metadata SHA逐项核；旧scope、用途/标签/费用不变，J数据不入本分母。

默认OFF；实际使用：

```bash
python3 -I -B /home/yuanyue/main/work/data-team/development/three-skill-coverage-20261117-v1/derive_fixed24_coverage.py \
  --enabled --deliveries /home/yuanyue/main/work/data-team/consumer-deliveries \
  --out /absolute/new-derived-output.json
```

输出不得覆盖现文件。按scope/intent/option/原receipt精确连接，区分root语义请求、native子option及准备角色；不把PUSH的NAV准备receipt算PUSH失败或额外独立NAV样本。未达CLIMB、入口/退出gate stop、原终态缺失与工程截断分开；没有可连接的主体Actor激活证据时输出None，不补0/成功率/训练必要性。命名为NAV Actor的事件计数不自动等于root NAV技能的激活分母。

L0原训练域未核，L1只有旧链先后关系证据，L2只有旧几何/context/准备差分；全部只作回顾性候选，不冒新预登记三层筛查。StageB三分支单列，不与fixed24池化；一TRAIN祖先不是独立验证。90次建议仍为草案，本reader不生成case资格/新AUTH或派发。

当前三技能表只维护在`/home/yuanyue/main/work/data-team/STATUS.md`并同步共享Data段，不另造三张训练结论报告。原Actor/训练与测试入口合同归AINav，可靠域差距/重训对象归Reach；Data交真实分母与有限执行原件。原件入口`/home/yuanyue/main/work/data-team/manifests/three-skill-robustness-coverage-20261117-v1/`。
