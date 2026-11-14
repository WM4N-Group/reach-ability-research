"""One authorized SDK App, actual probe definitions/CFG, zero env/actor/physics.

Fixture action term is explicit synthetic adapter, NOT a runtime freshness or
measured RobotData test. Final verifier must match original helper for all arms.
"""
import ast,hashlib,importlib.util,json,sys,traceback
from pathlib import Path
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
from entry_admission import require_execution_authority
require_execution_authority()  # No App or SDK claim from a direct invocation.
result=dict(schema='native-entry-SDK0env-source-CFG-geometry-gate-v1',passed=False,manifest_sha256=hashlib.sha256((HERE/'manifest.json').read_bytes()).hexdigest(),SDK_Apps=1,envs=0,actor_loads=0,physics_steps=0)
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
    names=fixture['joint_names'];q=np.array(fixture['q']);pos=np.array(fixture['root_position']);quat=np.array(fixture['root_quaternion'])
    # Explicit SDK-only fake adapter gives the same already-present interface;
    # no claim that actual env/action-manager timestamps have been exercised.
    adapter=SimpleNamespace(stance_orientation_target=torch.tensor([quat.tolist()],dtype=torch.float64))
    env=SimpleNamespace(episode_length_buf=torch.tensor([0]),step_dt=.02,
        action_manager=SimpleNamespace(get_term=lambda name:adapter),
        scene={'robot':SimpleNamespace(data=SimpleNamespace(joint_vel=torch.zeros((1,18))))})
    args=(g,names,q,pos,quat,np.array([1.8,0.,.1]),np.array([1.,0.,0.,0.]),waypoints,[1.2,1.2,.2])
    before=tuple(v.copy() for v in (g.data.qpos,g.data.qvel,g.data.ctrl));time_before=g.data.time
    expected=old.required_standoff(*args,residual_limit=.02,nominal_translation_w=None,forecast_margin_m=0.)
    checks=[];finals=[]
    for role in ['planning','final_actual']:
        for arm in ['P0','P1','P2','P3']:
            new.configure_study(arm,ns['a'].output)
            new.set_query_context(env,list(range(18)),names,evaluation_role=role)
            actual=new.required_standoff(*args,residual_limit=.02,
                nominal_translation_w=np.zeros(3) if role=='planning' else None,forecast_margin_m=.005 if role=='planning' else 0.)
            if actual['evaluation_role']!=role:raise ValueError('Wrong explicit query role')
            if role=='final_actual':
                for key in ['minimum_shift_m','maximum_box_local_x','samples_in_expanded_yz']:
                    if actual[key]!=expected[key]:raise ValueError('Common actual verifier differs from frozen original '+key)
                finals.append(actual['minimum_shift_m'])
            if not all(np.array_equal(a,b) for a,b in zip(before,[g.data.qpos,g.data.qvel,g.data.ctrl])) or g.data.time!=time_before:
                raise ValueError('Private geometry state/time not restored')
            checks.append(dict(arm=arm,role=role,request_m=actual['minimum_shift_m'],state_restored=True))
            checkpoint('verified_'+arm+'_'+role)
    if len(set(finals))!=1:raise ValueError('Final verifier differs across arms')
    final_calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='prospective_entry'
        and any(k.arg=='evaluation_role' and isinstance(k.value,ast.Constant) and k.value.value=='final_actual' for k in n.keywords)]
    if len(final_calls)!=1:raise ValueError('Actual main does not contain one explicit final measured caller')
    parent=ast.parse((HERE/'parent_probe.original.py.txt').read_text())
    protected=lambda t:{n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name not in ('prospective_entry','main')}
    if protected(parent)!=protected(tree):raise ValueError('Original controller/function AST changed')
    result.update(passed=True,actual_native_definitions_executed=True,actual_main_CFG_prefix_executed=True,
        train_inventory_files_verified=len(source_plan['source_hashes']),native_geometry_real=True,
        common_actual_verifier_matches_original=True,completed_role_checks=checks,
        fixture='Historical robot q + explicitly SYNTHETIC far-box and orientation-target adapter; not a physical episode or actual action-manager freshness test',
        dynamic_success=False,actual_runtime_reference_freshness_certified=False)
except BaseException as exc:
    result.update(error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
finally:
    close=(lambda:ns['launcher'].app.close()) if ns is not None and 'launcher' in ns else (lambda:None)
    persist_then_close(HERE.parent/'sdk_result.json',result,close)
if not result['passed']:raise SystemExit(1)
