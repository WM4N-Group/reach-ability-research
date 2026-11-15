"""Bounded SOURCE fixtures only; no native scene/trajectory/sample qualification."""
from pathlib import Path
from types import SimpleNamespace,MappingProxyType
import sys,unittest,json
blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):blocked.append(str(args[0]));raise RuntimeError('Software-only source fixtures')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
ROOT=Path(__file__).resolve().parents[3];SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(SOURCE)]
import complex_scene as scene
import multi_goal_factory as multi
import static_qualification as static

class ComplexSourceTests(unittest.TestCase):
    def test_hot_or_repeated_world_change_denied_before_native_import(self):
        with self.assertRaises(ValueError):scene.construct_into_native_spec(SimpleNamespace(data=SimpleNamespace(time=.005),queue=[]),main_steps=1)
        self.assertIsNone(multi.factory_class())
    def test_nominal_geometry_has_witness_without_putting_answer_in_public_task(self):
        s=scene.load_scene();r=static.evaluate(s);self.assertTrue(r['A_required_placement_first_blocks_B_nominal_approach']);self.assertFalse(r['physical_dynamic_feasible_plan_verified'])
        pub=scene.public_task(s);self.assertNotIn('static_existence_witness',pub);self.assertNotIn('body_name',pub['objects'][0]);self.assertTrue(pub['correct_order_or_route_not_provided'])
    def test_original_contract_thresholds_and_ground_registry(self):
        s=scene.load_scene();r=scene.registry(s,source_root=SOURCE);self.assertEqual(len(r.objects),2)
        for c in scene.finite_placements(s):
            p=scene.placement_contract(s,c,source_root=SOURCE);self.assertEqual((p.public_XY_tolerance_m,p.original_dock_tolerance_m,p.original_native_settled_distance_m),(.02,.01,.12));self.assertEqual(p.drive_goal_xy_m[0],p.public_goal_xy_m[0]+.11)
    def test_same_body_two_sealed_goals_and_original_binding_refusal(self):
        from ainav.native.behavior_authority import BehaviorOption
        from ainav.native.session_factory import NativeTargetBinding
        s=scene.load_scene();factory=multi.factory_class(source_root=SOURCE,enabled=True);f=factory.__new__(factory);data=object();queue=object()
        f.r=SimpleNamespace(sim=SimpleNamespace(data=data,queue=queue,model=SimpleNamespace(body=lambda name:SimpleNamespace(id=1))))
        f.push_backend=SimpleNamespace(_bindings={});f.used_queries=set();f.executor=SimpleNamespace(session=None);f.registry=scene.registry(s,source_root=SOURCE);f.push_backend.resolver=SimpleNamespace(registry=f.registry)
        goals=[c for c in scene.finite_placements(s)if c['public_ref']=='cuboid_a'];contracts={};options=[]
        for i,c in enumerate(goals):
            goal_sha=str(i+1)*64;o=BehaviorOption('test'+str(i),'PUSH','opaque_query_target',(('goal_world_x_m',-.08),('goal_world_y_m',0.),('push_distance_m',.3),('surface_height_m',0.)),60.,'SOFTWARE-only',attempt_id='attempt'+str(i),original_push_goal_sha256=goal_sha)
            target=SimpleNamespace(target_ref=o.target_ref,query_sha256='q'*64,body_name='complex_box_a',body_id=1)
            contract=scene.placement_contract(s,c,source_root=SOURCE)
            view=SimpleNamespace(box_push_target=[[contract.drive_goal_xy_m[0],contract.drive_goal_xy_m[1],.1]])
            f.push_backend._bindings[o.sha256]=NativeTargetBinding('q'*64,o.sha256,target,data,queue,'SOFTWARE-only','selected_push',view=view)
            contracts[contract.sha256]=contract;options.append(o)
        f.contracts=MappingProxyType(contracts);f.contract_hashes={k:v.sha256 for k,v in contracts.items()}
        f.install_query_contracts('q'*64,list(zip(options,contracts.values())))
        with self.assertRaises(ValueError):f.install_query_contracts('q'*64,list(zip(options,contracts.values())))
        self.assertEqual([factory.prospective_push_contract(f,o,'q'*64)[0].public_goal_xy_m[0]for o in options],[1.85,2.3])
        binding=f.push_backend._bindings[options[0].sha256];binding.view.box_push_target[0][0]+=.1
        with self.assertRaises(ValueError):factory.prospective_push_contract(f,options[0],'q'*64)
        binding.view.box_push_target[0][0]-=.1
        with self.assertRaises(ValueError):factory.prospective_push_contract(f,options[0],'wrong-query')
        f.contract_hashes[next(iter(contracts))]='0'*64
        with self.assertRaises(ValueError):factory.prospective_push_contract(f,options[0],'q'*64)


    def test_no_native_construction_by_default_or_missing_real_owner_guard(self):
        import native_construction as native
        self.assertIsNone(native.compile_static_asset());self.assertIsNone(native.construct_cold_components())
        with self.assertRaises(ValueError):native.compile_static_asset(enabled=True)
    def test_goal_dwell_requires_original_12N_two_reconstructions_and_no_clock_gaps(self):
        from terminal_stop import GoalDwell
        s=scene.load_scene();sample=dict(feet_world_m=[[8.8,-.2,.022],[9.2,-.2,.022],[8.8,.2,.022],[9.2,.2,.022]],foot_normal_N=[12.]*4,foot_speed_m_s=[0.]*4,base_linear_speed_m_s=0.,base_angular_speed_rad_s=0.,tilt_rad=0.)
        m=GoalDwell(s)
        for i in range(101):m.observe(time_s=i*.005,tick=i,sample=sample,placements_current=False)
        self.assertFalse(m.ready)
        for i in range(101,202):m.observe(time_s=i*.005,tick=i,sample=sample,placements_current=True)
        self.assertTrue(m.ready)
        weak=dict(sample,foot_normal_N=[11.99]*4);m.observe(time_s=202*.005,tick=202,sample=weak,placements_current=True);self.assertFalse(m.ready)
        for i in range(203,252):m.observe(time_s=i*.005,tick=i,sample=sample,placements_current=True)
        m.observe(time_s=300*.005,tick=300,sample=sample,placements_current=True);self.assertFalse(m.ready)

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ComplexSourceTests));print(json.dumps(dict(role='SOURCE_SOFTWARE_ONLY_NOT_NATIVE_OR_RESEARCH_SAMPLES',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,worlds_or_fit=0)));sys.exit(0 if r.wasSuccessful()and not blocked else 1)
