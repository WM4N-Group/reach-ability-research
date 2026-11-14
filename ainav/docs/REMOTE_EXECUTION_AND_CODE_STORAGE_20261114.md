# 计算端与代码存储分离（用户2026-11-14最新指令）

## 当前执行位置

- 用户指定服务器：`root@180.97.68.228`，SSH端口`46308`。认证仅走现有安全SSH连接；密码/密钥不得进入源码、Git、日志或命令行。
- 实际核到主机：`is-ddj7fmngzagfchvv-devmachine-0`；双RTX4090，各24564MiB。
- GPU0 UUID `GPU-297c1146-bcec-a8ee-8437-d9603392a2e1`；GPU1 UUID `GPU-6d66aa68-9a3f-fdcf-89b7-f98d4106fa39`。
- 23:06观测两卡各free24080MiB，只是资源快照，不是exclusive lease/启动许可；运行前必须fresh核验。旧46174端GPU UUID/设备锁身份/lease不得迁移冒用。
- 本次代码部署根为`/mnt/yuanyue/ainav-compute/code/<代码版本>/`。未来大型datasets/checkpoints/outputs/logs留在同服务器的运行区，和Git代码目录分开；不恢复旧任务world或runtime根。

## 代码与大文件的职责

1. 本地`/home/yuanyue/main/work/ainav`保留开发源码与必要小型协议/摘要；已有dirty/untracked/历史证据保持，不以节省空间为由reset/clean或删除封存产物。
2. 云端代码仓库：`https://github.com/WM4N-Group/reach-ability-research.git`。AINav用独立`ainav-development`分支和`ainav/`命名空间，不覆盖其他组分支/目录。导出已发布完整源码、当前AINav开发模块和有限prefix试验包，不批量提交原开发工作树继承dirty。
3. 仿真/训练/大型结果放远端；本次不搬1GB历史outputs/manifests、Actor权重、SDK、虚拟环境、RGBD/NPZ或录像进Git。本地只新增几MB代码快照和部署摘要；不做无选择的全目录rsync。
4. 服务器是可替换计算节点，不是唯一代码存储。迁移先取Git版本/源码SHA，再接已有合法依赖/资产并重新核资源及程序资格，不携旧进程/状态/lease作为“恢复实验”。

## 已有环境与仍需满足的运行条件

现有`/mnt/yuanyue/ainav-native-env-20261112-v2/bin/python`为Python3.11.13、PyTorch2.7.0+cu128、NumPy1.26.4、MuJoCo3.3.2、Pillow11.3.0。可作本机迁移代码检查，**不能冒Data当前完整worker的Python3.11.16/精确sys.prefix/native资格**。Data须在新owner部署中使用其合格环境或重新冻结准确新环境；不把改版本字符串/伪造sys.prefix当适配。

最新用户指令明确远端用于仿真和训练，不再按旧“本组服务器仅CPU”作为计算资源禁令。但Data仍唯一物理owner：当前left/right原生NAV前缀pilot应在此新指定端重新核Host/Actor/GL、canonical设备锁、完整freeze/自身zero后执行，不另开第二world或恢复旧closed根。此次只做代码部署/CPU检查，不自行抢跑物理。

训练按实际模型任务和数据用途推进，不假造训练数据：当前两条件pilot是NEW_DEV_AUDIT_ONLY，旧Stage-B/历史public queries/隔离GT不能fit；已获准的未来新数据高层critic可在合格数据产生后在该端训练。部署迁移不意味着恢复WM/DINO、底层技能重训或真机，也不改变安全门/独立TEST0/五箱未通过事实。

## 无副作用的部署检查

```bash
<现有python> -I -B <代码根>/ainav/scripts/remote_code_smoke.py --root <代码根>/ainav
```

该检查只编译源码、核原发布299成员、验证原两请求默认关闭/显式三请求构造；拒绝NumPy/torch/MuJoCo导入与网络/子进程，不产生native world、命令回执或训练样本。不是仿真通过、训练完成或新的研究结果。
