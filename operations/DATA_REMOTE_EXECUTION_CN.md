# Data：代码保管与46308执行目标（2026-11-14）

用户最新决定：仿真/获资格训练使用`root@180.97.68.228:46308`；代码持久保存在本地与本GitHub仓库；远程服务器保存环境/资产/运行大数据。凭据不写入本文件、Git、命令argv或日志。

## 代码保管

- Data本地精简checkout：`/home/yuanyue/main/code/reach-ability-research`，Data增量分支`data-team-development`；不清理/替换原工作目录或其他组dirty。
- `owner_snapshot/native-prefix-20261114/`为当前Data冻结worker及必需source的318成员保管快照。owner逐SHA核对云端原317个已有文件，并仅补齐缺少的`selected-native-nav-caller.patch`；未重写任何已有原件或他组源码。
- `provenance/DATA_OWNER_CODE_CUSTODY_20261114.json`是完整318文件SHA与保管来源，**不是新的runtime freeze、lease或zero**。无需再复制一整份Data source到另一个云端目录。
- 新计算节点若无法直接访问GitHub，可由本地fetch后用code-only Git bundle部署，核commit与source SHA；不上传个人私钥、不打开agent forwarding，也不把密码设为Git凭据。

## 独立Data部署

Data新根：`/mnt/yuanyue/data-team/deployments/46308-20261114`。

- `code/reach-ability-research`：Data部署的Git代码副本；与其他组`/mnt/yuanyue/reach-ability-research`分开，避免并发checkout/dirty相互覆盖。
- `runtime`：未来新物理/训练产物，不提交Git。
- `dependencies`：仅所需已pin的SDK/冻结Actor等大资产，按SHA复用或传输；不提交Git，不整包迁移旧episode。
- `metadata`：环境/资源/部署报告，小型元数据按需要镜像回本地。
- `resource-locks`：必须按此新主机实际GPU UUID新建规范绑定；不能复制旧inode或冒用旧lease。

已只读发现本组原私有环境`/mnt/yuanyue/data-team/env-native-v1/bin/python`仍在NAS上，Python3.11.16；metadata列NumPy1.26.4/Torch2.7.0+cu128/MuJoCo3.3.2/SciPy1.13.1/OSQP1.1.3/Pillow11.3.0/imageio2.37.0。这是环境候选的版本证据，不是完整字节环境审计或native资格；未修改/重装环境。

目标两张4090实际UUID为`GPU-297c1146-bcec-a8ee-8437-d9603392a2e1`与`GPU-6d66aa68-9a3f-fdcf-89b7-f98d4106fa39`，与46174原设备不同。索引和瞬时空闲不等独占lease。Data以后按新设备/规范锁/容量/源版本完整freeze和自身真实zero派发，不运行旧frozen快照来凑新资格。

## 单一owner与切换边界

用户切机时，46174上本窗口已派发的left唯一main仍在有界执行；先收束/核result与ledger，不因聊天中断就重复派发或抹账。在此之后不再在旧端启动right或新任务。未派发的旧设备right freeze保留未执行事实；换机版本须另记录，不把硬件变化当成单一prefix变量或自动重跑left。

代码保管、服务器连通、版本probe/软件fixture均不是实际仿真或训练结果。历史closed根/次数不恢复；旧audit/EVALUATION_ONLY资料不入fit。未来critic数据用途的既有授权仍限定新预登记数据，不恢复Actor/WM/DINO/真机。原安全/成功门、失败分母、成本、TEST0保持。

## 本地容量

本地只保精简代码、必要小型manifest/closure和少量预览；不批量回传NPZ/视频/权重或环境，不擅删旧证据。服务器切换优先重新部署同commit/核资产而不是反复迁移整批历史运行根。
