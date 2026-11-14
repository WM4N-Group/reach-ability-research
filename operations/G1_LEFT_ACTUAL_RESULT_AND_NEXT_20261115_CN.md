# G1新端left实际闭合，right唯一main已派发；尚无成对可辨性结论（2026-11-15 01:06）

## 已核真实进展

Data新端v2通过仅限原生库绑定的明确修正后，left own-zero/cold及唯一main实际PASS并于00:57:18 CAS closed。main原状态`REQUESTED_API0_PASS`，核exact3语义请求原生成功：原NAV prefix left、相同PUSH absolute2.3/-2、CLIMB upper-entry；两次entry-NAV准备回执不冒语义完成。原`whole_task_success_claimed=false`保持：这是请求链通过，不是穿全far-bank任务成功、优化器增益或可训练条件族资格。

|量|实际值|语义|
|---|---:|---|
|主episode钟|121.085sim|含原保护前缀；不是旧两请求同任务对照|
|NAV前驱意图开始→完成|17.625sim|35.190→52.815，只是真实额外意图成本|
|首次CLIMB PREPARE|97.285sim|实际query/event/Observation绑定，不套旧frame3|
|PREPARE→READY|13.460sim|原entry-NAV succeeded回执|
|PREPARE→请求CLIMB成功终点|23.800sim|终点121.085；无oracle选择|
|zero+main总sim含各自aux|134.095sim|两phase分别含6.505sim原初始化|
|zero+main ledger wall|866.559200s|取closed ledger，不用result的较早wall|
|scope输出highwater|177091729bytes|max phase highwater，不将行值重复相加|
|实际命令/原live帧|24217/1211|由Data原closed流审计报告，本组不重算NPZ|

Data原cold audit全流检查通过，3意图/5bound options/10原receipt，原source SHA保持。Reach只消费其报告，不声称独立重算PD/torque/NPZ。

## 已实际取得合法首次PREPARE输入，不等待新增日志接口

`operations/read_G1_public_boundary.py`在46308运行，复用原Journal.verify与Observation.create，按原intent_native_execution_bound的CLIMB/preparation第一次实际事件，匹配intent-observation完整semantic SHA。验证原result/journal SHA与Data cold原pins一致，再读该query的公开45D及它自己指向的RGB、同目录原depth/K/T。绑定97.285sim、同packet age0；保存raw数值/decoded数组shape/dtype/byte SHA及公开标定，不把路径、UUID、绝对钟或pending字符串作state差异。

读取进程禁torch/mujoco/网络/子进程/private catalog/association，forbidden=[]；无capture/Runtime/Actor/世界/fit。字节hash仅判byte身份，下一真正数值比较仍按原decoded数组和NaN语义，不能拿PNG重编码或NaN编码不同冒观测变化。第一次PREPARE已按actualquery绑定，`_latest_public`基类指针未被当精确query。没有读READY后帧倒灌，也没有计算GT/后继预测或对本audit材料调用ONLINE_PUBLIC feature接口。

45D及实际帧引用的小报告仅留本地ignored evidence/远端reach-runs，**不提交Git/转训练数据**。云端只存reader代码、本摘要/来源pins，不存原图/数组/权重。

## right与下一接续

right本程序c663dabc…自身zero/cold已PASS，00:58:43 CAS派发唯一main；本组尚未接收main终态。已有在途不重发、不制造第二批。当前一支闭合/一支在途，不给条件归并/可辨/足够信息或candidate排序结论。新端结果与旧46174未知left不拼对。

下一项：right原main闭合就按同一reader/同一个后果前边界直接取另一实际query，在同设备同cohort比较45D分单位差、decoded RGBD及原component名义信息；direct READY/失败/缺测按原分母保留。两支结束按G1结论转G2新用途分组数据或一次有caller代码依据的新条件源验证，不重扫/换seed追胜。G3现指标代码已就绪但真实新数据0/fit0，之后G4/G5/G6长期目标不以本批成功收工。

旧46174失联zero1/main1及未知尾费、新端v1 zero启动失败15.156688wall/usage_known=false全部另保；没有因为v2通过而删账。旧机器不再连接，原12N/4s/identity/immutable/guard/QP/FIFO/stop与actor冻结、audit/GT不得fit、TEST0/主要贡献未证保持。
