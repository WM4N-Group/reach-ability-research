"""Carry the PINNED original camera hook into a fresh static MJB.

No renamed/approximate camera, renderer, MjData, stepping, or live model repair.
The original hook runs with its camera-only native-demo recipe on a transient
receipt holder, NOT on a task Runtime. Only its camera receipt is retained.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib, importlib, math
from complex_scene import need

SCENE_SHA = '18758bb505f1af255fb04e0a757dc21427faa35263a305ff471e0b21fe6bf76e'
OBSERVER_SHA = '89b41322e567dbbb10bca28848880a1095f108b427f07c19d71c4591b75490f9'
WIDTH, HEIGHT = 192, 128


def original_camera_source(source_root):
    root = Path(source_root).resolve(strict=True)
    for name, expected in [('scene', SCENE_SHA), ('observer', OBSERVER_SHA)]:
        path = root / 'mujoco_zyh' / (name + '.py')
        need(not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == expected,
             'Exact original onboard source required: ' + name)
    module = importlib.import_module('mujoco_zyh.scene')
    need(Path(module.__file__).resolve() == root / 'mujoco_zyh/scene.py',
         'Original camera hook module belongs to another source root')
    return module


def install_original_camera(sim, *, source_root):
    need(float(sim.data.time) == 0. and not sim.queue,
         'Camera installation only on original zero-step empty-FIFO constructor')
    # This source version accepts only the upstream SDK's unconfigured camera
    # domain. A preexisting/duplicated rig is not silently replaced.
    need(int(sim.model.ncam) == 0, 'Fresh SDK camera domain required; no replacement')
    original = original_camera_source(source_root)
    holder = SimpleNamespace(box_y=0.)
    extra_nv, _ = original.configure_scene(holder, sim, sim.spec,
        dict(width=WIDTH, height=HEIGHT, scene_recipe='zyh_native_single_box'))
    need(extra_nv == 0 and float(sim.data.time) == 0. and not sim.queue,
         'Original camera-only hook changed physical clock/FIFO/DOF')
    camera = dict(holder.wm_scene_receipt['camera'])
    need(camera['name'] == 'wm_onboard_rgbd' and camera['width'] == WIDTH and camera['height'] == HEIGHT,
         'Original onboard identity/resolution mismatch')
    return dict(camera=camera, scene_source_sha256=SCENE_SHA,
                observer_source_sha256=OBSERVER_SHA,
                installation='EXACT_ORIGINAL_CONFIGURE_SCENE_CAMERA_ONLY_BEFORE_COMPILE',
                transient_hook_scene_identity_not_used=True,
                original_observer_rechecks_on_actual_runtime=True)


def verify_compiled_camera(model, *, source_root):
    """Original Observer equations, but no Renderer or physical Runtime created."""
    import numpy as np
    import mujoco
    original = original_camera_source(source_root)
    K, mount = original.calibration(WIDTH, HEIGHT)
    names = [model.camera(i).name for i in range(model.ncam)]
    need(names == [original.CAMERA_NAME], 'Exactly the original onboard camera required')
    camera_id = model.camera(original.CAMERA_NAME).id
    need(int(model.cam_bodyid[camera_id]) == model.body('base_link').id,
         'Onboard camera must be attached to actual base_link')
    need(np.allclose(model.cam_pos[camera_id], mount[:3, 3], rtol=0., atol=1e-10),
         'Compiled original camera translation mismatch')
    rotation = np.empty(9)
    mujoco.mju_quat2Mat(rotation, model.cam_quat[camera_id])
    need(np.allclose(rotation.reshape(3, 3) @ np.diag([1., -1., -1.]),
                     mount[:3, :3], rtol=0., atol=1e-10),
         'Compiled original ROS-optical camera rotation mismatch')
    focal = HEIGHT / (2 * math.tan(math.radians(float(model.cam_fovy[camera_id])) / 2))
    need(np.allclose([focal, focal], K[[0, 1], [0, 1]], rtol=0., atol=1e-8),
         'Compiled original camera intrinsics mismatch')
    return dict(camera_name=original.CAMERA_NAME, parent='base_link',
                width=WIDTH, height=HEIGHT, camera_K=K.tolist(),
                T_base_optical=mount.tolist(), camera_fovy_deg=float(model.cam_fovy[camera_id]),
                renderer_created=False, actual_main_steps=0,
                not_actual_observer_or_RGBD_qualification=True)
