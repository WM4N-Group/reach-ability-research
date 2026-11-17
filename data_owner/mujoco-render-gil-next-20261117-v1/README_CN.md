# 冷渲染构造最小源码候选：未编译、未部署、不是D3已测修复

当前D3仍zero1/main0 closed；21:07无world CUDA/EGL probe也已closed，二者都不能重跑或借资格。本目录仅保存未来新程序可审阅的**一处C++源码差分**，没有新guard/runner/授权/调度器或运行时monkeypatch。

## 依据与精确差分

- AINav已定位未覆盖接缝：`RegisteredObserver → OnboardObserver.__init__ → mujoco.Renderer(实际task model) → _render.MjrContext(model,fontscale)`。裸16×16 EGL不覆盖该model-context构造。
- 远端实际MuJoCo为3.3.2；已核`renderer.py` SHA **458ed1f7…**、`_render.so` **4a3edaa9…**、`libmujoco.so.3.3.2` **baa61a12…**与已装wheel RECORD对应行一致。这不是供应链/原D3因果证明。
- 官方3.3.2 tag的`renderer.py`与实际文件逐字SHA相同；已保存该tag的`render.cc/errors.h/functions.h`源与SHA。该tag的model-context C++构造调用原`InterceptMjErrors(mjr_makeContext)`，其构造binding/body未见GIL release；同文件`mjr_readPixels`已有在C调用外包一层`py::gil_scoped_release`的模式。
- **尚未证明installed `_render.so`确由该tag同构建生成，也未实测该二进制调用的GIL行为；旧D32.0806s发生在哪个叶段仍UNKNOWN。** 不把源码线索或新patch说成旧失败唯一原因。
- `mjr-context-release-gil.patch`只在这**一个原Intercept C调用**外加局部GIL-release scope，回到Python/Numpy array-view初始化前重新持GIL。原C调用、参数、error interceptor、default初始化、返回、capsule析构及array views的其余源码逐字不变；GL操作仍在原线程，不移转context、不改Renderer API/Actor/模型/物理/成功门。

源码base **9e498527…**→patch后 **65b70a5c…**；patch **5e64ad2d…**。已仅对临时源树做`patch --fuzz=0`应用/逆向逐byte还原；**这不是编译/ABI/异常/GL/性能测试**。

## 下一唯一工程动作与拒绝项

在独立私有构建树解析并记录精确Python/pybind/C++ABI、依赖headers与原libmujoco链接身份，再编译仅含此差分的私有binding候选。不能覆盖现环境/SDK/冻结文件，不能强制谎报pybind ABI key或热换在途模块；新binary必须有独立build/source SHA、CPU导入/类型注册/析构/错误路径验证和完整新程序资格，才可作有界原生验证。当前仅查到c++/cmake/ninja；预期路径的Eigen/Abseil/pybind headers尚未解析，不能称构建完成或要求用户重下环境。

**拒绝ctypes裸调用`mjr_makeContext`的快捷旁路**：不能省掉原error interception、array-view构造或原capsule析构；不能先造default context后暗换native内存来冒同一对象语义。若私有构建无法正确复用ABI，保持未部署并明确具体缺项，不扩大代码或重装整套环境。

原PerGpuLease/actual owner PID/UUID/canonical FD、ResourceWatch1s/oldest≤2s、真实完整oldest/completed原子pair、磁盘/ScopeIO/全部动态门原样保留。即使该candidate以后通过，也不回填旧D3/v5 UNKNOWN、不产生C/D或D3派发许可；需以新程序自身资格证明。

证据入口：`/home/yuanyue/main/work/data-team/manifests/resource-producer-attribution-20261117-v1/continued-2156/`；当前状态以`/home/yuanyue/main/work/data-team/STATUS.md`为准，不重复运行已闭合cold probe或合成GIL套件。
