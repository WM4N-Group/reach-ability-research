"""Pre-compile scene/camera additions; never write live physical state.

Native demos are separately named, never mislabeled as the A20/B.5/C1 research
scene. The latter preserves opaque identity and has NO selected-B executor yet.
"""
import math
import numpy as np

IDENTITY = {
    'light': dict(scene_key='box', body='push_box', mass_kg=20., dy=0., color=[.74,.36,.18,1.]),
    'middle': dict(scene_key='wm_object_middle', body='wm_object_middle', mass_kg=.5, dy=-1.8, color=[.18,.62,.47,1.]),
    'heavy': dict(scene_key='wm_object_heavy', body='wm_object_heavy', mass_kg=1., dy=1.8, color=[.75,.1,.12,1.]),
}
CAMERA_NAME = 'wm_onboard_rgbd'


def calibration(width, height):
    if type(width) is not int or type(height) is not int or min(width, height) < 16 or width * 2 != height * 3:
        raise ValueError('Explicit 3:2 RGBD resolution >=16 required')
    pitch = math.radians(22.)
    c, s = math.cos(pitch), math.sin(pitch)
    mount = np.eye(4)
    mount[:3,:3] = np.array([[0.,-s,c],[-1.,0.,0.],[0.,-c,-s]])  # ROS optical x right/y down/z forward
    mount[:3,3] = [.25,0.,.18]
    f = width * 9. / 36.
    K = np.array([[f,0.,width/2],[0.,f,height/2],[0.,0.,1.]])
    return K, mount


def configure_scene(runtime, sim, spec, config):
    import mujoco
    from scipy.spatial.transform import Rotation
    K, mount = calibration(config['width'], config['height'])
    gl_rotation = mount[:3,:3] @ np.diag([1.,-1.,-1.])
    xyzw = Rotation.from_matrix(gl_rotation).as_quat()
    spec.body('base_link').add_camera(name=CAMERA_NAME, pos=mount[:3,3], quat=xyzw[[3,0,1,2]],
        fovy=math.degrees(2*math.atan(config['height']/(2*K[1,1]))))
    if config.get('stall_stow_mode'):
        spec.body('push_box').pos=[1.1,0.,.1]
        runtime.box_y=0.
    recipe = config['scene_recipe']
    extra_nv = 0
    if recipe == 'integrated_course':
        from .integrated_course import configure_scene as configure_integrated
        extra_nv=configure_integrated(runtime,sim,spec,config)
    elif recipe == 'easy_engineering_suite':
        from .five_scene_suite import configure_scene as configure_suite
        configure_suite(runtime,sim,spec,config)
    elif recipe == 'research_threebox':
        # The caller has placed the native A body before this hook. Do not move
        # it or swap IDs; append B/C at their declared side-lane offsets.
        anchor = np.array([1.1,0.,.1])
        spec.body('push_box').pos = anchor
        runtime.box_y = 0.
        a = spec.geom('push_box_geom'); a.mass = 20.; a.rgba = IDENTITY['light']['color']
        for candidate in ('middle','heavy'):
            item = IDENTITY[candidate]
            body = spec.worldbody.add_body(name=item['body'],pos=anchor+np.array([0.,item['dy'],0.]))
            body.add_freejoint(name=item['body']+'_free')
            geom = body.add_geom(name=item['body']+'_geom',type=mujoco.mjtGeom.mjGEOM_BOX,
                size=[.6,.6,.1],mass=item['mass_kg'],contype=2,conaffinity=3,condim=3,
                friction=[.15,0.,0.],priority=2,rgba=item['color'])
            for other in list(spec.geoms):
                if other.name == geom.name or not (other.contype or other.conaffinity):
                    continue
                pair = spec.add_pair(geomname1=geom.name,geomname2=other.name,condim=3)
                pair.friction = [.15,.15,0.,0.,0.]
            extra_nv += 6
        # Frozen A/B/C contact physics: explicit A pairs must match the same
        # .15 surface value; changing geom friction alone does not update pairs.
        a.friction=[.15,0.,0.]
        for pair in spec.pairs:
            if 'push_box_geom' in (pair.geomname1,pair.geomname2):pair.friction=[.15,.15,0.,0.,0.]
        # Frozen research geometry: fixed40cm platform beyond the nominal A goal.
        # This is NOT the native20cm CLIMB task and is not dispatched to that actor.
        if any(g.name=='platform' for g in spec.geoms):
            spec.geom('platform').delete()
        front=anchor[0]+.6+.6+.04
        spec.worldbody.add_geom(name='wm_research_platform',type=mujoco.mjtGeom.mjGEOM_BOX,
            pos=[front+1.,0.,.2],size=[1.,3.,.2],contype=2,conaffinity=3,
            friction=[.6,0.,0.],condim=3,rgba=[.14,.36,.65,1.])
    elif recipe != 'zyh_native_single_box':
        raise ValueError('Unknown scene recipe; never silently relabel native1kg as failed A20kg')
    if config.get('probe_physics'):
        from .push_forecast_protocol import configure_probe
        configure_probe(spec,config['probe_physics'])
    if config.get('option_forecast_case') or config.get('recovery_exit_diagnostic_case') or config.get('push_protection_mode') or config.get('supported_push_mode'):
        geometry=config['initial_probe_geometry'];body=spec.body('push_box')
        body.pos=[1.1+geometry['initial_box_dx_m'],geometry['initial_box_dy_m'],.1]
        yaw=geometry['initial_box_yaw_rad'];body.quat=[np.cos(yaw/2),0.,0.,np.sin(yaw/2)]
        runtime.box_y=geometry['initial_box_dy_m']
    runtime.wm_scene_receipt = dict(schema='zyh-mujoco-scene-construction-v1',recipe=recipe,
        camera=dict(name=CAMERA_NAME,width=config['width'],height=config['height'],
            camera_K=K.tolist(),T_base_optical=mount.tolist(),depth='metric optical-axis Z',clip_m=[.05,15.]),
        extra_free_dofs=extra_nv,object_identity=IDENTITY if extra_nv else ({'probe_object':dict(body='push_box',**config['probe_physics'])} if config.get('probe_physics') else {'upstream_demo':dict(body='push_box',mass_kg=1.)}),
        live_scene_alias_or_pose_swap=False,initial_construction_only=True,
        failed_A_recovery_or_selected_B_binding_implemented=False,
        full_platform_or_bridge_task_implemented=False)
    if config.get('integrated_course_mode'):
        identity={k:dict(v) for k,v in IDENTITY.items()}
        identity['heavy']['mass_kg']=config['registered_materials']['C_mass_kg']
        runtime.wm_scene_receipt['object_identity']=identity
    return extra_nv, runtime.box_y


def verify_compiled_scene(runtime, config):
    sim = runtime.sim
    expected = IDENTITY if config['scene_recipe'] in ('research_threebox','integrated_course') else {'upstream_demo':dict(body='push_box',mass_kg=1.)}
    if config.get('integrated_course_mode'):
        expected={k:dict(v) for k,v in expected.items()}
        expected['heavy']['mass_kg']=config['registered_materials']['C_mass_kg']
    if config.get('probe_physics'):expected={'probe_object':dict(body='push_box',mass_kg=config['probe_physics']['mass_kg'])}
    for candidate, item in expected.items():
        body = sim.model.body(item['body'])
        if abs(float(sim.model.body_mass[body.id])-item['mass_kg'])>1e-6:
            raise ValueError('Compiled physical object identity/mass mismatch: '+candidate)
    if config['scene_recipe']=='research_threebox':
        for item in IDENTITY.values():
            geom=sim.model.geom(item['body']+'_geom').id
            pairs=(sim.model.pair_geom1==geom)|(sim.model.pair_geom2==geom)
            if not pairs.any() or not np.allclose(sim.model.pair_friction[pairs,:2],.15):raise ValueError('Frozen research box explicit pair friction mismatch')
        anchor = sim.data.xpos[sim.model.body('push_box').id]
        for candidate, item in IDENTITY.items():
            pos = sim.data.xpos[sim.model.body(item['body']).id]
            if not np.allclose(pos-anchor,[0.,item['dy'],0.],atol=1e-9):
                raise ValueError('Compiled object pose was exchanged: '+candidate)
    if config.get('probe_physics'):
        gid=sim.model.geom('push_box_geom').id;friction=config['probe_physics']['friction']
        pairs=(sim.model.pair_geom1==gid)|(sim.model.pair_geom2==gid)
        if not pairs.any() or not np.allclose(sim.model.pair_friction[pairs,:2],friction):
            raise ValueError('Probe compiled contact pairs differ from registered friction')
    if config.get('option_forecast_case') or config.get('recovery_exit_diagnostic_case') or config.get('push_protection_mode') or config.get('supported_push_mode'):
        geometry=config['initial_probe_geometry'];expected_pose=np.array([1.1+geometry['initial_box_dx_m'],geometry['initial_box_dy_m'],.1])
        yaw=geometry['initial_box_yaw_rad'];expected_quat=np.array([np.cos(yaw/2),0.,0.,np.sin(yaw/2)])
        if not np.allclose(sim.data.xpos[sim.box_id],expected_pose,rtol=0.,atol=1e-10) or not np.allclose(sim.data.xquat[sim.box_id],expected_quat,rtol=0.,atol=1e-10):raise ValueError('Compiled option case geometry differs from registered initial pose')
        if not np.allclose(sim.box_push_target.numpy()[0],expected_pose+[.6,0.,0.],rtol=0.,atol=1e-6):raise ValueError('Option case immutable goal not actual initial body world-X+.6')
        if sim.controller.env is not sim:raise ValueError('Single-probe controller env/context mismatch')
        runtime.wm_scene_receipt['initial_option_geometry_admission']=dict(actual_initial_xyz=sim.data.xpos[sim.box_id].tolist(),actual_initial_quaternion_wxyz=sim.data.xquat[sim.box_id].tolist(),original_goal=sim.box_push_target.tolist(),controller_env_is_selected_probe=True,native_PUSH_entry_resets_target_local_caches_before_first_action=True,physics_steps=0)
    if abs(float(sim.model.opt.timestep)-.005)>1e-12:
        raise ValueError('Native 200Hz physics required')
    return runtime.wm_scene_receipt
