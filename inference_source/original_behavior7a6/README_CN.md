# 原7a6推理源码闭包（不含权重/数据/训练运行）

五个Python文件由原`GO2-PIPER/scripts/piper_world_model`逐byte复制，来源/哈希见SOURCE_INVENTORY.json；未重写架构或预测头。只供本次用户已授权的现有WM推理接入。原源码中的模型定义/兼容加载定义保留，不执行训练/optimizer或扩大7a6适用性。

权重留46308，原SHA7a6ba61e…；不进入Git/本地新副本。`restore_original_WM_cpu.py`只恢复CPU eval模型，禁止native/API/world/Actor；另需原实际RGBD/200Hz已发历史/公开context构建当前因果query，才有实际预测。源码可导入/权重可恢复不等native资格或本方法优势，旧closed实验不恢复。原工程license/attribution继续适用。
