"""New source assembly/control-preservation and real private-geometry CPU tests.

No SDK App, actor or physics. Historical robot fixture + explicit synthetic box
is not a pilot trial. Protect the one SDK budget by checking assembly locally.
"""
import ast,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from build_package import OWNER,transform_probe,build
import runtime_tip_envelope as new

class AssemblyTests(unittest.TestCase):
    def test_preserved_original_controller_nodes(self):
        original=(OWNER/'probe.py').read_text();changed=transform_probe(original)
        a=ast.parse(original);b=ast.parse(changed)
        da={n.name:ast.dump(n,include_attributes=False) for n in a.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        db={n.name:ast.dump(n,include_attributes=False) for n in b.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        modified={name for name in da if da[name]!=db[name]}
        self.assertEqual(modified,{'prospective_entry','main'})
        self.assertIn('term.return_nav_goal[:,:2]=torch.tensor([-.25,0.]',changed)
        self.assertIn("if fk_error>.0002:raise ValueError",changed)
        self.assertEqual(changed.count("f'reach-entry-pilot-v1-{a.entry_geometry_arm}-seed{a.seed}'"),original.count("'v212-nav-legs-push-entry-arm-v317'"))

    def test_package_counts_and_balanced_fixed_registration(self):
        with tempfile.TemporaryDirectory() as d:
            p=build(Path(d)/'source')
            self.assertEqual(len(p['schedule']),16)
            self.assertEqual(len({x['source_id'] for x in p['schedule']}),16)
            self.assertEqual(p['seeds'],[120401,120402,120403,120404])
            self.assertFalse(set(p['seeds']) & {3701,3703,5311,5312})
            self.assertEqual(p['budgets']['SDK0env_apps'],1)
            for seed in p['seeds']:
                self.assertEqual({x['arm'] for x in p['schedule'] if x['seed']==seed},{'E0','E1','E2','E3'})

    def test_observer_float_outputs_serialize_and_no_extra_domain(self):
        points=np.array([[-.61,0.,0.],[-.65,0,0]])
        result=new.choose_request(points,np.array([20,40]),np.array([.6,.6,.1]),np.array([1.,0,0]),.02,'E2')
        self.assertAlmostEqual(result[0],.01)
        json.dumps(dict(request=result[0],within=result[0]<=.04),allow_nan=False)
        self.assertEqual(new.choose_request(points,np.array([20,40]),np.array([.6,.6,.1]),np.array([1.,0,0]),.02,'E0')[0],0)
        self.assertEqual(new.choose_request(points,np.array([20,40]),np.array([.6,.6,.1]),np.array([1.,0,0]),.02,'E1')[0],0)

class NativeGeometryCPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r=OWNER.parent
        gpath=r/'runtime-push-detour-v1/mujoco'
        sys.path.insert(0,str(gpath))
        path=r/'push-direct-approach-v212/train/source/LeggedManip_Lab/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/mdp/box_push_geometry.py'
        spec=importlib.util.spec_from_file_location('_native_geom_cpu_pilot',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        cls.g=module.PiperBaseArmGeometryShield(gpath,.035)
        spec=importlib.util.spec_from_file_location('_old_tip_cpu_pilot',OWNER/'box_approach_standoff.py');cls.old=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.old)
        r=json.loads((OWNER/'seed3701-native-entry/report.json').read_text());cls.names=r['joint_names'];cls.state=r['entry_state']
        cls.path=np.array(json.loads((OWNER.parent/'push-direct-approach-v212/train/mujoco/deploy/piper_push_safe_approach.json').read_text())['waypoints'])

    def test_all_arms_real_geometry_state_and_full_observation(self):
        g=self.g;s=self.state
        env=SimpleNamespace(episode_length_buf=np.array([0]),step_dt=.02,scene={'robot':SimpleNamespace(data=SimpleNamespace(joint_vel=np.zeros((1,18))))})
        args=(g,self.names,np.array(s['q']),np.array(s['root_position']),np.array(s['root_quaternion']),np.array([1.8,0,.1]),np.array([1.,0,0,0]),self.path,[1.2,1.2,.2])
        before=tuple(v.copy() for v in [g.data.qpos,g.data.qvel,g.data.ctrl])
        expected=self.old.required_standoff(*args,residual_limit=.02,nominal_translation_w=np.zeros(3),forecast_margin_m=.005)
        with tempfile.TemporaryDirectory() as d:
            for arm in ['E0','E1','E2','E3']:
                new.configure_study(arm,Path(d));new.set_query_context(env,list(range(18)),self.names)
                actual=new.required_standoff(*args,residual_limit=.02,nominal_translation_w=np.zeros(3),forecast_margin_m=.005)
                if arm=='E2':
                    for key in ['minimum_shift_m','samples_in_expanded_yz','maximum_box_local_x']:
                        self.assertEqual(actual[key],expected[key])
                self.assertTrue(all(np.array_equal(a,b) for a,b in zip(before,[g.data.qpos,g.data.qvel,g.data.ctrl])))
                self.assertEqual(g.data.time,0)
                new.record_source_hand_guard(0.) # synthetic metadata only, not a real robot measurement
            rows=[json.loads(line) for line in (Path(d)/'entry_geometry.jsonl').read_text().splitlines()]
            clouds=[r for r in rows if r['event']=='finite_tip_query']
            self.assertEqual(len(clouds),4)
            self.assertTrue(all(len(r['tip_cloud_box_m'])==2624 for r in clouds))
            self.assertTrue(all(r['box_position_w']==[1.8,0,.1] for r in clouds))

if __name__=='__main__':unittest.main()
