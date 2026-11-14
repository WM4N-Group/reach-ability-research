"""One actual SDK App, zero env/actor/integration: source/CFG/geometry admission.

Execute the actual patched probe definitions, not a replacement parent class.
Run real native geometry and compare E2 against frozen v317 helper. This gate
is NOT dynamic/whole-task success or a freshness certificate.
"""
import ast,hashlib,importlib.util,json,sys,traceback
from pathlib import Path
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
result=dict(schema='native-entry-SDK0env-source-CFG-geometry-gate-v1',passed=False,SDK_Apps=1,envs=0,actor_loads=0,physics_steps=0)
ns=None
from sdk_evidence_io import durable_json,persist_then_close

def checkpoint(stage):
    result["last_stage"]=stage
    durable_json(HERE.parent/"sdk_progress.json",result)
    print("SDK_STAGE",stage,flush=True)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def fail_actor(*args,**kwargs):raise RuntimeError('Actor loading is forbidden in SDK0env')
def fail_env(*args,**kwargs):raise RuntimeError('Environment construction is forbidden in SDK0env')
def fail_step(*args,**kwargs):raise RuntimeError('Physics integration forbidden in SDK0env')

try:
    checkpoint("before_actual_App_and_probe_definitions")
    tree=ast.parse((HERE/'probe.py').read_text())
    if not isinstance(tree.body[-1],ast.Try) or ast.unparse(tree.body[-1].body[0])!='main()':
        raise ValueError('Unexpected final native main entry; refusing to execute')
    body=[]
    for node in tree.body[:-1]:
        body.append(node)
        if isinstance(node,ast.Import):
            names={x.name for x in node.names}
            if 'torch' in names:body.extend(ast.parse('torch.load=fail_actor\ntorch.jit.load=fail_actor').body)
            if 'gymnasium' in names:body.extend(ast.parse('gym.make=fail_env').body)
    module=ast.fix_missing_locations(ast.Module(body=body,type_ignores=[]))
    ns=dict(__name__='reach_bound_native_probe_sdk',__file__=str(HERE/'probe.py'),fail_actor=fail_actor,fail_env=fail_env)
    exec(compile(module,str(HERE/'probe.py'),'exec'),ns)
    checkpoint("actual_App_and_probe_definitions_loaded")
    # SAME actual main configuration prefix, stopping before gym.make.
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    setup=[]
    for node in main.body:
        if isinstance(node,ast.Assign) and isinstance(node.value,ast.Call) and ast.unparse(node.value.func)=='gym.make':break
        setup.append(node)
    else:raise ValueError('Cannot find exact original environment construction boundary')
    exec(compile(ast.fix_missing_locations(ast.Module(body=setup,type_ignores=[])),str(HERE/'probe.py'),'exec'),ns)
    checkpoint('actual_main_CFG_prefix_complete')
    cfg=ns['cfg'];torch=ns['torch']
    assert issubclass(ns['Router'],ns['ResidualPushAction'])
    assert cfg.actions.joint_pos.class_type is ns['Router']
    assert cfg.terminations.box_settled.func is ns['PushSettledEvent']
    assert cfg.actions.joint_pos.hand_pitch==1.0
    assert tuple(cfg.box_size)==(1.2,1.2,.2)
    assert cfg.episode_length_s==96.
    root=Path(ns['a'].source);geometry=Path(cfg.push_geometry_root)
    # Verify original frozen train inventory, including source-relative JSON/assets.
    source_plan=json.loads((root.parent/'plan.json').read_text())
    for rel,expected in source_plan['source_hashes'].items():
        if sha(root/rel)!=expected:raise ValueError('Frozen train source mismatch '+rel)
    import numpy as np
    import mujoco
    for name in ['mj_step','mj_step1','mj_step2']:setattr(mujoco,name,fail_step)
    import LeggedManip_Lab.tasks.manager_based.leggedmanip_lab.mdp.box_push_geometry as geom
    assert Path(geom.__file__).resolve()==(root/'source/LeggedManip_Lab/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/mdp/box_push_geometry.py').resolve()
    checkpoint('native_CFG_assertions_and_train_inventory_verified')
    g=geom.PiperBaseArmGeometryShield(geometry,.035)
    checkpoint('actual_native_geometry_compiled')
    spec=importlib.util.spec_from_file_location('frozen_tip_source',HERE/'box_approach_standoff_frozen_v317.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    import box_approach_standoff as new
    fixture=json.loads((HERE/'fixture_robot_state.json').read_text())
    waypoints=np.array(json.loads((root/'mujoco/deploy/piper_push_safe_approach.json').read_text())['waypoints'])
    joint_names=fixture['joint_names'];q=np.array(fixture['q']);pos=np.array(fixture['root_position']);quat=np.array(fixture['root_quaternion'])
    env=SimpleNamespace(episode_length_buf=torch.tensor([0]),step_dt=.02,
                        scene={'robot':SimpleNamespace(data=SimpleNamespace(joint_vel=torch.zeros((1,18))))})
    args=(g,joint_names,q,pos,quat,np.array([1.8,0.,.1]),np.array([1.,0.,0.,0.]),waypoints,[1.2,1.2,.2])
    state=tuple(v.copy() for v in (g.data.qpos,g.data.qvel,g.data.ctrl))
    original=old.required_standoff(*args,residual_limit=.02,nominal_translation_w=np.zeros(3),forecast_margin_m=.005)
    checks=[]
    for arm in ['E0','E1','E2','E3']:
        new.configure_study(arm,ns['a'].output)
        new.set_query_context(env,list(range(18)),joint_names)
        value=new.required_standoff(*args,residual_limit=.02,nominal_translation_w=np.zeros(3),forecast_margin_m=.005)
        assert all(np.array_equal(a,b) for a,b in zip(state,(g.data.qpos,g.data.qvel,g.data.ctrl)))
        assert g.data.time==0
        if arm=='E2':
            for key in ['minimum_shift_m','maximum_box_local_x','samples_in_expanded_yz']:
                assert value[key]==original[key],(key,value[key],original[key])
            assert np.array_equal(value['source_hand_position_w'],original['source_hand_position_w'])
        checks.append(dict(arm=arm,request=value['minimum_shift_m'],restored=True))
        result['completed_variant_checks']=checks.copy()
        checkpoint('variant_'+arm+'_verified')
    result.update(passed=True,actual_native_definitions_executed=True,actual_main_CFG_prefix_executed=True,
        train_inventory_files_verified=len(source_plan['source_hashes']),native_geometry_real=True,
        E2_matches_frozen_helper=True,variant_geometry_checks=checks,
        fixture='historical robot q plus EXPLICIT SYNTHETIC far-box identity pose; not an observed task or pilot outcome',
        dynamic_success=False,actual_runtime_freshness_certified=False)
except BaseException as exc:
    result.update(error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
finally:
    # Native fastShutdown may terminate the interpreter with rc0. Persist BEFORE it.
    close=(lambda:ns['launcher'].app.close()) if ns is not None and 'launcher' in ns else (lambda:None)
    persist_then_close(HERE.parent/'sdk_result.json',result,close)
if not result['passed']:raise SystemExit(1)
