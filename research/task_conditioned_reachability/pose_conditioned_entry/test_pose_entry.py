"""CPU-only snapshot/point algebra/private FK tests; NOT SDK or new episodes."""
import ast,hashlib,importlib.util,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from build_pose_package import PARENT,REPO,PARENT_SHA,build,transform_probe,verify_parent
from pose_entry_selection import ARMS,reference_pose_cloud,select,scalar_request

RAW=REPO.parent/'artifacts/go2-piper/reachability-native-entry-global-goal-20261020-v1/runs/seed120401-E1'
SAVED_QUERIES=[q for line in (RAW/'entry_geometry.jsonl').read_text().splitlines() if (q:=json.loads(line))['event']=='finite_tip_query']
SAVED_REFERENCE=next(r for line in (RAW/'control.jsonl').read_text().splitlines() if (r:=json.loads(line))['step']==921)['stance_orientation_target']


def module_at(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module


class AssemblyTests(unittest.TestCase):
    def test_byte_frozen_parent_and_unchanged_controller_nodes(self):
        verify_parent();original=(PARENT/'probe.py').read_text();changed=transform_probe(original)
        a={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(original).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        b={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(changed).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        self.assertEqual({name for name in a if a[name]!=b[name]},{'prospective_entry','main'})
        self.assertIn('if fk_error>.0002:raise ValueError',changed)
        self.assertIn("term.return_nav_goal[:,:2]=torch.tensor([-.25,0.]",changed)
        self.assertLess(changed.index('require_execution_authority()'),changed.index('from isaaclab.app import AppLauncher'))
    def test_final_call_has_explicit_common_role(self):
        tree=ast.parse(transform_probe((PARENT/'probe.py').read_text()))
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='prospective_entry']
        self.assertEqual(len(calls),3)
        final=[c for c in calls if any(k.arg=='evaluation_role' and k.value.value=='final_actual' for k in c.keywords)]
        self.assertEqual(len(final),1)
    def test_exact_refusal_branch_exits_before_activation_not_success(self):
        tree=ast.parse(transform_probe((PARENT/'probe.py').read_text()))
        condition=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=="verified['shift_m'] != 0.0")
        body=ast.Module(body=[ast.For(target=ast.Name(id='_',ctx=ast.Store()),iter=ast.List(elts=[ast.Constant(0)],ctx=ast.Load()),
            body=[condition,*ast.parse("report['activation_marker']=True").body],orelse=[])],type_ignores=[])
        for shift in [.01,0.]:
            ns=dict(verified={'shift_m':shift},row={'step':1095,'time_s':21.9},report={})
            exec(compile(ast.fix_missing_locations(body),'<synthetic branch fixture>','exec'),ns)
            if shift:self.assertEqual(ns['report']['outcome'],'entry_final_preview_refused');self.assertNotIn('activation_marker',ns['report'])
            else:self.assertTrue(ns['report']['activation_marker'])
    def test_new_snapshot_has_eight_cases_no_approval_or_old_launcher(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'source';p=build(out)
            self.assertEqual(len(p['schedule']),8);self.assertEqual(p['seeds'],[120501,120502])
            self.assertEqual(p['approved_budgets'],dict(SDK_Apps=0,physical_starts=0));self.assertFalse(p['execution_authorized'])
            self.assertFalse((out/'sdk_check.py').exists());self.assertFalse((out/'run_supervisor.py').exists())
            self.assertEqual(hashlib.sha256((out/'finite_cloud_sampler_frozen.py').read_bytes()).hexdigest(),hashlib.sha256((PARENT/'box_approach_standoff.py').read_bytes()).hexdigest())
    def test_direct_probe_invocation_refuses_before_App_or_output(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'source';build(out)
            result=subprocess.run([sys.executable,str(out/'probe.py')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('CPU-only pose-entry',result.stderr)
            self.assertNotIn("No module named 'isaaclab'",result.stderr)


class SelectionTests(unittest.TestCase):
    def test_known_exposed_development_query_matches_logged_reference_shadow(self):
        expected=.0050858835464281426
        for arm in ARMS:
            r=select(SAVED_QUERIES[0],arm,'planning',SAVED_REFERENCE)
            self.assertAlmostEqual(r['minimum_shift_m'],expected if arm in ('P1','P3') else 0.,places=13)
            self.assertEqual(set(r['all_planning_requests']),set(ARMS))
            self.assertIsNone(r['prospective_pose_error_bound'])
    def test_measured_full_cloud_verifier_is_identical_for_all_planning_arms(self):
        values=[select(SAVED_QUERIES[1],arm,'final_actual') for arm in ARMS]
        self.assertTrue(all(v==values[0] for v in values))
        self.assertAlmostEqual(values[0]['minimum_shift_m'],.0013871248566571035,places=13)
        self.assertIsNone(values[0]['reference_quaternion_wxyz'])
    def test_final_does_not_read_or_apply_a_reference(self):
        a=select(SAVED_QUERIES[1],'P0','final_actual',None)
        b=select(SAVED_QUERIES[1],'P3','final_actual',[float('nan')]*4)
        self.assertEqual(a,b)
    def test_final_cannot_mislabel_a_forecast_as_actual(self):
        with self.assertRaisesRegex(ValueError,'forbids nominal translation'):
            select(SAVED_QUERIES[0],'P0','final_actual')
    def test_missing_reference_fails_equally_for_all_planning_arms(self):
        for arm in ARMS:
            with self.assertRaisesRegex(ValueError,'Common planning input missing'):select(SAVED_QUERIES[0],arm,'planning')
    def test_bad_phase_or_quaternion_is_not_silently_projected(self):
        with self.assertRaises(ValueError):scalar_request([[-.61,0,0]],[float('nan')],[.6,.6,.1],[1,0,0],.015,endpoint=False,swept=True)
        with self.assertRaises(ValueError):select(SAVED_QUERIES[0],'P1','planning',[2,0,0,0])
    def test_reference_transform_preserves_inputs(self):
        q=SAVED_QUERIES[0];encoded=json.dumps(q);ref=list(SAVED_REFERENCE)
        points=reference_pose_cloud(q['tip_cloud_box_m'],q['root_position_w'],q['root_quaternion_wxyz'],q['box_position_w'],q['box_quaternion_wxyz'],q['nominal_translation_w'],ref)
        self.assertEqual(points.shape,(2624,3));self.assertEqual(encoded,json.dumps(q));self.assertEqual(ref,SAVED_REFERENCE)


class RealPrivateGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.package=Path(cls.temp.name)/'source';build(cls.package)
        sys.path.insert(0,str(cls.package))
        module_at('finite_cloud_sampler_frozen',cls.package/'finite_cloud_sampler_frozen.py')
        module_at('pose_entry_selection',cls.package/'pose_entry_selection.py')
        cls.runtime=module_at('pose_factor_runtime_test',cls.package/'box_approach_standoff.py')
        owner=Path('/home/yuanyue/re-nav -piper-deploy/artifacts/go2-piper/sim2sim-current-20261008-a')
        root=owner/'runtime-push-detour-v1/mujoco';sys.path.insert(0,str(root))
        file=owner/'push-direct-approach-v212/train/source/LeggedManip_Lab/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/mdp/box_push_geometry.py'
        tree=ast.parse(file.read_text());node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='PiperBaseArmGeometryShield')
        ns=dict(np=np,Path=Path);exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(file),'exec'),ns)
        cls.geometry=ns['PiperBaseArmGeometryShield'](root,.035)
        cls.path=np.array(json.loads((owner/'push-direct-approach-v212/train/mujoco/deploy/piper_push_safe_approach.json').read_text())['waypoints'])
        cls.q=SAVED_QUERIES[0];cls.names=cls.q['joint_names']
        class Counter:
            def __init__(self,module):self.module=module;self.calls=0
            def __getattr__(self,name):return getattr(self.module,name)
            def mj_forward(self,*args):self.calls+=1;return self.module.mj_forward(*args)
        cls.original=module_at('pose_cpu_frozen_original_helper',cls.package/'box_approach_standoff_frozen_v317.py')
        cls.counter=Counter(cls.geometry.mujoco);cls.geometry.mujoco=cls.counter
        cls.before=tuple(v.copy() for v in [cls.geometry.data.qpos,cls.geometry.data.qvel,cls.geometry.data.ctrl]);cls.results=[]
    @classmethod
    def tearDownClass(cls):
        print('PRIVATE_GEOMETRY_NEW_mj_forward_CALLS',cls.counter.calls)
        sys.path.remove(str(cls.package));cls.temp.cleanup()
    def env(self,reference=True,query=None):
        q=self.q if query is None else query;term=SimpleNamespace()
        if reference:term.stance_orientation_target=np.array([SAVED_REFERENCE])
        return SimpleNamespace(episode_length_buf=np.array([q['step']]),step_dt=.02,
            action_manager=SimpleNamespace(get_term=lambda name:term),
            scene={'robot':SimpleNamespace(data=SimpleNamespace(joint_vel=np.array([q['dq_rad_s']])))}),term
    def evaluate(self,arm,role,output):
        q=self.q if role=='planning' else SAVED_QUERIES[1];env,_=self.env(query=q);self.runtime.configure_study(arm,output)
        self.runtime.set_query_context(env,list(range(18)),self.names,evaluation_role=role)
        result=self.runtime.required_standoff(self.geometry,self.names,np.array(q['q_rad']),np.array(q['root_position_w']),np.array(q['root_quaternion_wxyz']),
            np.array(q['box_position_w']),np.array(q['box_quaternion_wxyz']),self.path,q['box_size_m'],residual_limit=.02,
            nominal_translation_w=q['nominal_translation_w'],forecast_margin_m=q['forecast_margin_m'])
        self.assertTrue(all(np.array_equal(a,b) for a,b in zip(self.before,[self.geometry.data.qpos,self.geometry.data.qvel,self.geometry.data.ctrl])))
        self.assertEqual(self.geometry.data.time,0);self.assertEqual(int(env.episode_length_buf[0]),q['step'])
        error=float(np.linalg.norm(result['source_hand_position_w']-q['source_hand_position_w']))
        self.assertLess(error,.0002) # ORIGINAL model-source agreement gate, not a changed runtime threshold.
        result['CPU_model_vs_logged_preview_source_hand_error_m']=error
        return result
    def test_real_geometry_eight_role_calls_restore_private_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            persistent=os.environ.get('POSE_CPU_RAW_OUTPUT')
            output=Path(persistent) if persistent else Path(temporary)
            if persistent:output.mkdir(parents=True,exist_ok=False)
            results={};details=[]
            q=SAVED_QUERIES[1]
            expected_final=self.original.required_standoff(self.geometry,self.names,np.array(q['q_rad']),np.array(q['root_position_w']),np.array(q['root_quaternion_wxyz']),
                np.array(q['box_position_w']),np.array(q['box_quaternion_wxyz']),self.path,q['box_size_m'],residual_limit=.02,
                nominal_translation_w=None,forecast_margin_m=0.)
            for role in ['planning','final_actual']:
                for arm in ARMS:
                    r=self.evaluate(arm,role,output);results[arm,role]=r['minimum_shift_m']
                    self.assertEqual(r['evaluation_role'],role)
                    if role=='final_actual':
                        for key in ['minimum_shift_m','maximum_box_local_x','samples_in_expanded_yz']:
                            self.assertEqual(r[key],expected_final[key])
                    details.append(dict(arm=arm,role=role,request_m=r['minimum_shift_m'],query_id=r['query_id'],
                        criterion=r['criterion'],source_hand_error_m=r['CPU_model_vs_logged_preview_source_hand_error_m']))
            # Logged-cloud algebra is checked at13 decimal places separately.
            # Cross-runtime fresh FK uses standard numeric allclose, not a safety change.
            np.testing.assert_allclose(results['P1','planning'],.0050858835464281426,rtol=1e-5,atol=1e-8)
            self.assertEqual(results['P0','planning'],0.)
            self.assertEqual(len({results[arm,'final_actual'] for arm in ARMS}),1)
            clouds=[r for line in (output/'entry_geometry.jsonl').read_text().splitlines() if (r:=json.loads(line))['event']=='finite_tip_query']
            self.assertEqual(len(clouds),8);self.assertTrue(all(len(r['tip_cloud_box_m'])==2624 for r in clouds))
            self.assertTrue(all(r['reference_generation_step'] is None and not r['reference_freshness_certified'] for r in clouds))
            (output/'CPU-summary.json').write_text(json.dumps(dict(scope='Real private geometry CPU check with already-exposed logged inputs; no SDK/actor/physics/actual caller execution',
                all_cases_are_software_queries_NOT_episodes=True,private_new_mj_forward_calls=self.counter.calls,
                original_full_cloud_final_request_m=expected_final['minimum_shift_m'],results=details),indent=2)+'\n')
    def test_missing_context_input_cannot_reuse_previous_reference(self):
        with tempfile.TemporaryDirectory() as d:
            self.runtime.configure_study('P3',Path(d));env,term=self.env();self.runtime.set_query_context(env,list(range(18)),self.names,evaluation_role='planning')
            del term.stance_orientation_target
            with self.assertRaises(ValueError):self.runtime.set_query_context(env,list(range(18)),self.names,evaluation_role='planning')
            self.assertIsNone(self.runtime.CONTEXT)
    def test_selector_failure_keeps_captured_raw_witness(self):
        # Synthetic sampler fixture: test journaling without adding any FK.
        with tempfile.TemporaryDirectory() as d:
            self.runtime.configure_study('P3',Path(d));env,term=self.env();term.stance_orientation_target=np.array([[2.,0,0,0]])
            self.runtime.set_query_context(env,list(range(18)),self.names,evaluation_role='planning')
            original=self.runtime.sampler.required_standoff
            def synthetic_sampler(*args,**kwargs):
                self.runtime._CAPTURE.append(dict(SAVED_QUERIES[0]))
                return dict(minimum_shift_m=0.,source_hand_position_w=np.zeros(3))
            self.runtime.sampler.required_standoff=synthetic_sampler
            try:
                with self.assertRaisesRegex(ValueError,'Quaternion outside'):self.runtime.required_standoff()
            finally:self.runtime.sampler.required_standoff=original
            log=json.loads((Path(d)/'entry_geometry.jsonl').read_text().splitlines()[-1])
            self.assertEqual(log['event'],'pose_entry_query_error')
            self.assertEqual(log['box_position_w'],SAVED_QUERIES[0]['box_position_w'])
            self.assertEqual(len(log['tip_cloud_box_m']),2624)
    def test_final_forecast_arguments_rejected_before_any_FK(self):
        with tempfile.TemporaryDirectory() as d:
            self.runtime.configure_study('P0',Path(d));env,_=self.env(query=SAVED_QUERIES[1])
            self.runtime.set_query_context(env,list(range(18)),self.names,evaluation_role='final_actual')
            before=self.counter.calls
            with self.assertRaisesRegex(ValueError,'forbids nominal translation'):
                self.runtime.required_standoff(nominal_translation_w=np.zeros(3))
            self.assertEqual(before,self.counter.calls)
    def test_final_context_does_not_require_controller_reference(self):
        with tempfile.TemporaryDirectory() as d:
            self.runtime.configure_study('P3',Path(d));env,_=self.env(reference=False,query=SAVED_QUERIES[1]);del env.action_manager
            self.runtime.set_query_context(env,list(range(18)),self.names,evaluation_role='final_actual')
            self.assertIsNone(self.runtime.CONTEXT['reference'])
    def test_changed_query_step_is_rejected_before_any_new_FK(self):
        with tempfile.TemporaryDirectory() as d:
            self.runtime.configure_study('P1',Path(d));env,_=self.env();self.runtime.set_query_context(env,list(range(18)),self.names,evaluation_role='planning')
            before=self.counter.calls;env.episode_length_buf[0]+=1
            with self.assertRaisesRegex(ValueError,'step changed'):self.runtime.required_standoff()
            self.assertEqual(self.counter.calls,before)

if __name__=='__main__':unittest.main()
