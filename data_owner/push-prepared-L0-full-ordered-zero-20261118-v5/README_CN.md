# 新独立完整 PUSH：zero 用原探针确认后再关闭
仅 zero 新增停止握手：在原 freshness 剩余窗口内，等待当前/下一次正常调度的原探针完成并发布真实较新的 stamp；不加 probe、不改 .5s/2s、不会在失败后清 latch。随后 seal，原 .2s join 成功后才允许 zero PASS。保原命名/RX映射检查、原 lease、原相机及控制成功门；超时未产生新资格。main 执行与监督沿用原完整链。旧21c206与所有其他closed不续、不借资格。没有新 native 结果时不据此判断Actor或技能成功。
