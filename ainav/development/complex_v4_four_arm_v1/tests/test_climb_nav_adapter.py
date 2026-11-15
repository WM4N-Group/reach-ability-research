"""Typed source/lifecycle and exact original NAV reuse fixtures, NOT native runs."""
from pathlib import Path
from types import SimpleNamespace as NS
import ast,sys,json,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Source fixture only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import climb_nav_adapter as c
from ainav.native import registered_compact_nav as original
from ainav.native.supported_capture import ActualCaptureWitness
from ainav.native.push_stow_witness import ActualPushStowSupportWitness
from climb_nav_source import ActualClimbNavSourceObservation

class Tests(unittest.TestCase):
    def test_disabled_never_loads_native_or_needs_runtime(self):
        self.assertIsNone(c.nav_class());self.assertIsNone(c.make_live_source_witness())
        with self.assertRaises(ValueError):c.nav_class(enabled=1)
        self.assertFalse(blocked)
    def test_only_two_exact_invertible_original_source_sites_changed(self):
        text=(SOURCE/'ainav/native/registered_compact_nav.py').read_text();init,guard=c.changed_methods(text)
        tree=ast.parse(text);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='RegisteredCompactNav')
        old={n.name:ast.get_source_segment(text,n)for n in cls.body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(init.replace(c.NEW_TYPE,c.OLD_TYPE),__import__('textwrap').dedent(old['__init__']))
        self.assertEqual(guard.replace(c.NEW_CONTACT,c.OLD_CONTACT),__import__('textwrap').dedent(old['check_guards']))
        self.assertIn('ActualCaptureWitness,ActualArrivalSupportWitness,ActualPushStowSupportWitness,LiveClimbNavSourceWitness',init)
        self.assertNotIn('ActualClimbNavSourceObservation',init)
    def test_changed_or_duplicated_source_patterns_fail_closed(self):
        text=(SOURCE/'ainav/native/registered_compact_nav.py').read_text()
        with self.assertRaises(ValueError):c.changed_methods(text.replace(c.OLD_CONTACT,'SOFTWARE_changed_guard'))
        with self.assertRaises(ValueError):c.changed_methods(text.replace(c.OLD_TYPE,'SOFTWARE_other_type'))
    def test_original_actor_command_arrival_and_after_step_all_inherited_unchanged(self):
        cls=c.nav_class(source_root=SOURCE,enabled=True)
        self.assertTrue(issubclass(cls,original.RegisteredCompactNav))
        for name in ('update','command','after_step','report','_sync_arrival'):
            self.assertIs(getattr(cls,name),getattr(original.RegisteredCompactNav,name))
        self.assertFalse(cls.source_receipt['actual_native_qualification'])
        self.assertTrue(cls.source_receipt['not_installed_in_V4_factory_or_public_catalogue'])
    def test_no_observation_or_fake_capture_direct_NAV_constructor_shortcut(self):
        cls=c.nav_class(source_root=SOURCE,enabled=True)
        for fake in (NS(),ActualClimbNavSourceObservation.__new__(ActualClimbNavSourceObservation)):
            with self.assertRaises(ValueError):cls(None,None,capture_witness=fake,goal_xy=(0.,0.),journal=lambda row:'SOFTWARE')
        for old in (ActualCaptureWitness,original.ActualArrivalSupportWitness,ActualPushStowSupportWitness):
            self.assertFalse(issubclass(c.LiveClimbNavSourceWitness,old))
        self.assertFalse(blocked)
    def test_make_source_requires_actual_reader_type_not_scalar_or_owner_label(self):
        with self.assertRaises(ValueError):c.make_live_source_witness(NS(necessary_source_ready=True),None,source_root=SOURCE,enabled=True)
        self.assertFalse(blocked)
    def fixture(self):
        self.runtime=NS(step_count=200,sim=NS(data=NS(time=1.)))
        self.source=NS(outcome='succeeded')
        self.executor=NS(runtime=self.runtime,fatal=False,session=self.source,reported_end=True,
            last_outcome='succeeded',option=NS(skill='CLIMB'),previous_tick=200)
        self.nav=NS()
    def phase(self):
        return c.ownership_phase(executor=self.executor,source_session=self.source,nav_owner=self.nav,
            runtime=self.runtime,origin_tick=200,origin_time=1.)
    def test_pending_constructor_keeps_true_same_tick_CLIMB_not_new_active_NAV(self):
        self.fixture();self.assertEqual(self.phase(),'SOURCE_BOUNDARY')
        self.executor.reported_end=False
        with self.assertRaises(ValueError):self.phase()
    def active(self):
        self.fixture();self.session=NS(runtime=self.runtime,entered=True,machine=NS(native_nav=self.nav),outcome='running')
        self.executor.session=self.session;self.executor.option=NS(skill='NAV');self.executor.reported_end=False;self.executor.last_outcome=None
    def test_active_gait_uses_actually_installed_NAV_not_old_stopped_owner(self):
        self.active();self.assertEqual(self.phase(),'ACTIVE_NAV')
        self.runtime.step_count=201;self.runtime.sim.data.time=1.005;self.executor.previous_tick=201
        self.assertEqual(self.phase(),'ACTIVE_NAV')
        self.executor.session=self.source;self.executor.reported_end=True;self.executor.last_outcome='succeeded'
        with self.assertRaises(ValueError):self.phase()
    def test_different_or_unentered_controller_cannot_inherit_contact_authority(self):
        for field in ('different','unentered','wrong_skill','fatal'):
            self.active()
            if field=='different':self.session.machine.native_nav=NS()
            elif field=='unentered':self.session.entered=False
            elif field=='wrong_skill':self.executor.option.skill='CLIMB'
            else:self.executor.fatal=True
            with self.assertRaises(ValueError):self.phase()
    def test_failed_expired_or_missing_issued_tick_revokes_owner(self):
        for field in ('failed','missing','clock'):
            self.active()
            if field=='failed':self.executor.last_outcome='failed';self.session.outcome='failed'
            elif field=='missing':self.executor.previous_tick=199
            else:self.runtime.sim.data.time=1.0001
            with self.assertRaises(ValueError):self.phase()
    def test_one_constructor_attempt_even_if_an_alternative_is_available(self):
        # State-machine-only fixture; not a genuine live witness or Native NAV.
        witness=c.LiveClimbNavSourceWitness.__new__(c.LiveClimbNavSourceWitness)
        class SoftwareNav:pass
        witness.nav_type=SoftwareNav;witness.revoked=False;witness.construction_attempted=False;witness.r=NS();seen=[]
        witness.validate=lambda runtime:seen.append(runtime)or True
        witness.begin_constructor(SoftwareNav())
        with self.assertRaises(ValueError):witness.begin_constructor(SoftwareNav())
        self.assertEqual(len(seen),1)
    def test_constructed_pending_NAV_is_not_reported_as_installed_active_owner(self):
        self.fixture()
        witness=c.LiveClimbNavSourceWitness.__new__(c.LiveClimbNavSourceWitness)
        witness.origin=NS(observed_time=1.,observed_tick=200,original_option_sha256='f'*64,surface=NS(top_z_m=.2))
        witness.r=self.runtime;witness.source_session=self.source;witness.executor=self.executor
        witness.object_ref='SOFTWARE-object';witness.support_ref='SOFTWARE-support'
        witness.nav_owner=self.nav;witness.construction_attempted=True;witness.revoked=False
        report=witness.report();self.assertTrue(report['native_NAV_constructed'])
        self.assertTrue(report['constructor_pending_at_source_boundary']);self.assertFalse(report['active_native_NAV_owner'])
        self.executor.session=NS(runtime=self.runtime,entered=True,machine=NS(native_nav=self.nav),outcome='running')
        self.executor.option=NS(skill='NAV');self.executor.last_outcome=None
        self.assertTrue(witness.report()['active_native_NAV_owner'])
        self.executor.fatal=True
        self.assertFalse(witness.report()['active_native_NAV_owner'])

    def test_revoked_source_and_wrong_NAV_type_cannot_construct(self):
        witness=c.LiveClimbNavSourceWitness.__new__(c.LiveClimbNavSourceWitness)
        witness.revoked=True;witness.construction_attempted=False;witness.nav_type=NS
        with self.assertRaises(ValueError):witness.begin_constructor(NS())
        witness.revoked=False
        with self.assertRaises(ValueError):witness.begin_constructor(object())
        self.assertFalse(blocked)

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='CLIMB_TO_ORIGINAL_NAV_TYPED_ADAPTER_SOFTWARE_LIFECYCLE_NOT_NATIVE_OR_FULL_FACTORY_INTEGRATION',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,actual_live_source_Runtime_NAV_Actor_physics_API_calls=0)))
    sys.exit(0 if r.wasSuccessful()and not blocked else 1)
