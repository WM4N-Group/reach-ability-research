"""Exact owner/type seam fixtures, NOT a native NAV/terminal qualification."""
from pathlib import Path
from types import SimpleNamespace as NS
import json, sys, unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Explicit owner metadata fixture only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import task_terminal as terminal
from ainav.native.registered_nav_factory import RegisteredNavMachine
from mujoco_zyh.native_behavior_executor import NativeOptionSession
from climb_nav_adapter import ownership_phase

class Tests(unittest.TestCase):
    def setUp(self):
        self.r=NS(step_count=200,last=NS(position=[0.]*18),sim=NS(data=NS(time=1.)))
        self.nav=NS(goal=(14.,-2.6),height=.6,surface=NS(ref='goal_deck'),complete=True)
        self.machine=RegisteredNavMachine(self.r,self.nav)
        self.original=NativeOptionSession(self.r,self.machine,check_guards=lambda:None)
        self.registry=NS(goal=NS(surface_ref='goal_deck'))
        self.placements=NS(r=self.r,registry=self.registry,current_required=lambda:True)
        self.chain=NS(r=self.r,registry=self.registry,verify=lambda:True,
            scene={'task':{'goal_surface_height_m':.6}})
    def wrap(self):
        return terminal.terminal_nav_session(self.original,self.placements,self.chain,
            source_root=SOURCE,journal=lambda row:'EXPLICIT_SOFTWARE_FIXTURE')
    def test_wrapper_preserves_registered_NAV_type_and_exact_existing_owner(self):
        wrapped=self.wrap()
        self.assertIsInstance(wrapped.machine,RegisteredNavMachine)
        self.assertIs(wrapped.machine.native_nav,self.nav)
        self.assertIs(wrapped.machine.original,self.original)
        self.assertIs(wrapped.check_guards,self.original.check_guards)
        self.assertIs(wrapped.machine.r,self.r)
        self.assertFalse(wrapped.machine.entered)
        self.machine.entered=True
        self.assertTrue(wrapped.machine.entered)
    def test_owner_alias_is_readonly_and_replacement_is_detected(self):
        wrapped=self.wrap()
        with self.assertRaises(AttributeError):wrapped.machine.native_nav=NS()
        self.machine.native_nav=NS()
        with self.assertRaises(ValueError):_ = wrapped.machine.native_nav
    def test_completed_NAV_is_not_full_task_or_reentered_by_wrapping(self):
        wrapped=self.wrap()
        self.assertEqual(self.original.outcome,'succeeded')
        self.assertFalse(self.original.entered)
        self.assertFalse(wrapped.entered)
        self.assertFalse(wrapped.machine.complete)
        self.assertEqual(wrapped.outcome,'running')
        self.assertEqual(wrapped.machine.results,[])
        self.assertEqual(self.r.step_count,200)
    def test_stacking_a_terminal_wrapper_is_rejected(self):
        wrapped=self.wrap()
        with self.assertRaisesRegex(ValueError,'stacked'):
            terminal.terminal_nav_session(wrapped,self.placements,self.chain,
                source_root=SOURCE,journal=lambda row:'EXPLICIT_SOFTWARE_FIXTURE')
    def test_active_identity_gate_accepts_same_entered_owner_not_a_new_owner(self):
        wrapped=self.wrap();wrapped.entered=True
        source=NS(outcome='succeeded')
        executor=NS(runtime=self.r,fatal=False,session=wrapped,option=NS(skill='NAV'),
            previous_tick=200,last_outcome=None)
        args=dict(executor=executor,source_session=source,nav_owner=self.nav,
            runtime=self.r,origin_tick=200,origin_time=1.)
        self.assertEqual(ownership_phase(**args),'ACTIVE_NAV')
        with self.assertRaises(ValueError):ownership_phase(**dict(args,nav_owner=NS()))
        wrapped.entered=False
        with self.assertRaises(ValueError):ownership_phase(**args)
    def test_prerequisites_and_exact_goal_layer_still_refuse(self):
        self.chain.verify=lambda:(_ for _ in ()).throw(ValueError('EXPLICIT missing chain'))
        with self.assertRaisesRegex(ValueError,'missing chain'):self.wrap()
        self.chain.verify=lambda:True;self.nav.height=0.
        with self.assertRaises(ValueError):self.wrap()
        self.nav.height=.6;self.placements.current_required=lambda:False
        with self.assertRaises(ValueError):self.wrap()

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='EXPLICIT_SOFTWARE_TERMINAL_OWNER_TYPE_SEAM_NOT_NATIVE_OR_TASK',
        checks=result.testsRun,failures=len(result.failures),errors=len(result.errors),forbidden_attempts=blocked,
        actual_Runtime_Actor_physics_NAV_CLIMB_contact_reader_API_calls=0)))
    sys.exit(0 if result.wasSuccessful()and not blocked else 1)
