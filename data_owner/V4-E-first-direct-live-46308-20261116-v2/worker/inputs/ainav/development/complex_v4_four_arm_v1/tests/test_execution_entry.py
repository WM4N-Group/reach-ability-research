"""Execution assembly seams/authorization fixtures, NOT native qualification."""
from pathlib import Path
from types import SimpleNamespace as NS
from dataclasses import replace
import sys, json, unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN), str(SOURCE)]
blocked=[]
def fence(event,args):
    if event=='import' and str(args[0]).split('.')[0] in ('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Software only')
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import execution_entry as entry
from v4_native_asset import load_scene
from public_candidates import declarations
from ainav.native.behavior_authority import BehaviorOption
from ainav.native.registered_climb import RegisteredClimbMachine, ClimbBinding
from ainav.native.registered_guards import contact_authorized

class Tests(unittest.TestCase):
    def test_default_off_and_owner_guard_fail_before_native_import(self):
        self.assertIsNone(entry.build_after_actual_capture())
        with self.assertRaises(ValueError):entry.build_after_actual_capture(enabled=1)
        with self.assertRaises(ValueError):entry.build_after_actual_capture(enabled=True)
        def deny():raise PermissionError('SOFTWARE owner denied')
        with self.assertRaises(PermissionError):entry.build_after_actual_capture(enabled=True,guard=deny,journal=lambda row:'SOFTWARE')
        self.assertFalse(blocked)

    def test_six_original_contracts_match_only_shared_public_PUSH_domain(self):
        scene=load_scene();contracts=entry.finite_placement_contracts(scene,source_root=SOURCE)
        public={(r['target_ref'],r['parameters']['goal_world_x_m'],r['parameters']['goal_world_y_m']) for r in declarations(scene) if r['skill']=='PUSH'}
        self.assertEqual(len(contracts),6)
        self.assertEqual({(c.target_ref,*c.public_goal_xy_m) for c in contracts.values()},public)
        for key,c in contracts.items():
            self.assertEqual(key,c.sha256);self.assertEqual(c.source_surface_height_m,0.)
            self.assertEqual(c.drive_goal_xy_m,(c.public_goal_xy_m[0]+.11,c.public_goal_xy_m[1]))

    def test_scene_mutation_cannot_silently_change_shared_contracts(self):
        scene=load_scene();scene['objects'][0]['required_goal_xy_m'][0]+=.01
        with self.assertRaises(ValueError):entry.finite_placement_contracts(scene,source_root=SOURCE)

    def setup_owner(self,skill='CLIMB'):
        data,queue=NS(),[];runtime=NS(sim=NS(data=data,queue=queue))
        outer=BehaviorOption('SOFTWARE-public',skill,'cuboid_c:upper-entry',(('surface_height_m',.2),),60.,'SOFTWARE')
        inner=replace(outer,token='SOFTWARE-native',target_ref='SOFTWARE-opaque')
        binding=ClimbBinding('f'*64,inner.sha256,inner.target_ref,'cuboid_c','SOFTWARE-body',23,'ground',(('top',.2),))
        # Actual original Python machine class, but explicitly unentered fixture
        # with NO native controller, histories, receipt or physical evidence.
        machine=RegisteredClimbMachine(runtime,NS(sim=NS(data=data,queue=queue)),NS(),binding,{})
        session=NS(runtime=runtime,machine=machine,entered=True)
        factory=NS(native_option_for=lambda option:inner)
        executor=NS(runtime=runtime,factory=factory,option=outer,session=session)
        owners=dict(executor=executor,factory=factory,backend=NS(_bindings={}))
        registry=NS(objects={'cuboid_c':NS(ref='cuboid_c',body_name='SOFTWARE-body')})
        return runtime,registry,owners,session,inner

    def test_declaration_or_visual_association_does_not_grant_contacts(self):
        runtime,registry,owners,session,inner=self.setup_owner();owners['executor'].option=None
        self.assertEqual(entry._current_contact_owners(owners,runtime,registry,RegisteredClimbMachine),(None,frozenset()))
        owners['executor'].option=replace(inner,skill='NAV')
        self.assertEqual(entry._current_contact_owners(owners,runtime,registry,RegisteredClimbMachine),(None,frozenset()))

    def test_only_entered_selected_same_world_CLIMB_admits_its_foot_contacts(self):
        runtime,registry,owners,session,inner=self.setup_owner()
        selected,entered=entry._current_contact_owners(owners,runtime,registry,RegisteredClimbMachine)
        self.assertIsNone(selected);self.assertEqual(entered,frozenset(('cuboid_c',)))
        args=dict(object_ref='cuboid_c',registered_objects=set(registry.objects),retired_objects=frozenset(),robot_is_descendant=True,force_norm_N=12.,selected_push_ref=selected,entered_climb_refs=entered)
        self.assertTrue(contact_authorized(**args,robot_body_forbidden=False))
        self.assertFalse(contact_authorized(**args,robot_body_forbidden=True))
        self.assertFalse(contact_authorized(**dict(args,object_ref='cuboid_a',registered_objects={'cuboid_a','cuboid_c'}),robot_body_forbidden=False))

    def test_unentered_or_wrong_machine_cannot_authorize_contacts(self):
        for change in ('unentered','fake_machine'):
            runtime,registry,owners,session,inner=self.setup_owner()
            if change=='unentered':session.entered=False
            else:session.machine=NS(binding=session.machine.binding)
            with self.assertRaises(ValueError):entry._current_contact_owners(owners,runtime,registry,RegisteredClimbMachine)

    def test_wrong_option_or_body_or_world_FIFO_refuses_contact_authority(self):
        for change in ('option','body','world','FIFO','executor'):
            runtime,registry,owners,session,inner=self.setup_owner()
            if change=='option':session.machine.binding=replace(session.machine.binding,option_sha256='e'*64)
            elif change=='body':registry.objects['cuboid_c'].body_name='OTHER-SOFTWARE-body'
            elif change=='world':session.machine.global_runtime=NS()
            elif change=='FIFO':session.machine.r.sim.queue=[]
            else:owners['executor'].runtime=NS()
            with self.assertRaises(ValueError):entry._current_contact_owners(owners,runtime,registry,RegisteredClimbMachine)

    def test_current_supported_capture_type_and_actual_steps_are_not_replaceable(self):
        original,_=entry._exact_base()
        runtime=NS(step_count=0,sim=NS(data=NS(time=0.)))
        fake=dict(runtime=runtime,capture=NS(r=runtime,s=runtime.sim,complete=True,actual_issued_steps=2))
        with self.assertRaises(ValueError):original.completed_initial_witness(fake)
        self.assertFalse(blocked)

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='V4_POST_ACTUAL_CAPTURE_EXECUTION_ENTRY_SOFTWARE_ONLY_NOT_NATIVE',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,native_Runtime_Actor_physics_API_calls=0)))
    sys.exit(0 if r.wasSuccessful() and not blocked else 1)
