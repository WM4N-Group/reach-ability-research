"""Pure source-bound necessary predicates/expiry fixtures, NEVER live witnesses."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys,math,json,unittest,hashlib,inspect
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Pure source fixture only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import climb_nav_source as c
from ainav.native.scene_registry import SurfaceSpec
from ainav.native.supported_capture import ActualCaptureWitness
from ainav.native.registered_compact_nav import ActualArrivalSupportWitness
from ainav.native.push_stow_witness import ActualPushStowSupportWitness

class Tests(unittest.TestCase):
    def setUp(self):
        self.surface=SurfaceSpec('SOFTWARE_private_support','SOFTWARE_geom',(0.,2.4,-.7,.7),.2)
        self.feet=[[.7,-.15,.222],[.7,.15,.222],[1.1,-.15,.222],[1.1,.15,.222]]
    def sample(self,**kwargs):
        args=dict(feet=self.feet,total_vertical_load_N=[52.]*4,selected_contact_normal_N=[12.]*4,base_xy=[.9,0.]);args.update(kwargs)
        return c.source_readiness(self.surface,**args)
    def history(self,**kwargs):
        args=dict(time_s=1.,tick=200,first_command_time_s=.005,previous_tick=200,entered=True,latest_matches=True,two_finite_global18_refs=True);args.update(kwargs)
        return c.issued_history_gate(**args)
    def test_disabled_missing_or_refusing_guard_never_imports_native(self):
        self.assertIsNone(c.read_actual_climb_nav_source())
        with self.assertRaises(ValueError):c.read_actual_climb_nav_source(enabled=1)
        with self.assertRaises(ValueError):c.read_actual_climb_nav_source(enabled=True)
        with self.assertRaises(ValueError):c.read_actual_climb_nav_source(enabled=True,guard=lambda:False,journal=lambda row:'SOFTWARE')
        self.assertFalse(blocked)
    def test_reader_has_no_sample_pose_force_history_override_arguments(self):
        params=set(inspect.signature(c.read_actual_climb_nav_source).parameters)
        self.assertFalse(params.intersection({'feet','contacts','sample','last_two','limits','pose','forces','owner_type'}))
        for name,pin in c.PINS.items():self.assertEqual(hashlib.sha256((SOURCE/name).read_bytes()).hexdigest(),pin)
    def test_new_private_reference_never_duplicates_existing_box_or_surface(self):
        name=c.support_reference('cuboid_c',{'cuboid_c','ground','goal_deck'})
        self.assertEqual(name,'climb_nav_source__cuboid_c')
        with self.assertRaises(ValueError):c.support_reference('cuboid_c',{name})
        with self.assertRaises(ValueError):c.support_reference('cube:opaque',set())
    def test_true_pure_sample_is_only_necessary_not_NAV_admission(self):
        value=self.sample();self.assertTrue(value['necessary_source_ready'])
        self.assertFalse(value['native_NAV_admitted']);self.assertTrue(value['actual_next_NAV_goal_not_selected'])
    def test_ground_same_XY_never_elevated_source(self):
        self.feet=[[x,y,.022]for x,y,z in self.feet]
        self.assertFalse(self.sample()['necessary_source_ready'])
    def test_total_foot_loads_cannot_replace_selected_object_contact(self):
        value=self.sample(selected_contact_normal_N=[52.,52.,52.,0.])
        self.assertFalse(value['necessary_source_ready']);self.assertIn('ACTUAL_SELECTED_CLIMB_OBJECT',value['reasons'][-1])
    def test_original12N_threshold_not_lowered_by_contact_or_stop_success(self):
        for key in ('total_vertical_load_N','selected_contact_normal_N'):
            self.assertFalse(self.sample(**{key:[52.,52.,52.,11.999]})['necessary_source_ready'])
    def test_side_contact_friction_is_not_upward_support_normal(self):
        loads=c.deck_normal_loads({10:0,11:1,12:2,13:3},20,[(20,g,[1.,0.,0.],52.)for g in range(10,14)])
        self.assertEqual(loads,[0.]*4);self.assertFalse(self.sample(selected_contact_normal_N=loads)['necessary_source_ready'])
    def test_original_support_footprint_and_NAV_goal_margin_still_apply(self):
        self.assertTrue(self.sample(base_xy=[.1,0.])['necessary_source_ready'])  # Base is not the unselected future goal.
        self.assertFalse(self.sample(base_xy=[.1,0.],goal_xy=[.1,0.])['necessary_source_ready'])
        self.assertFalse(self.sample(base_xy=[-.1,0.])['necessary_source_ready'])
        feet=[*self.feet[:3],[2.5,.15,.222]]
        self.assertFalse(self.sample(feet=feet)['necessary_source_ready'])
    def test_bad_contact_scalars_not_silently_masked_or_filled(self):
        for values in ([12.]*3,[12.,12.,12.,float('nan')],[12.,12.,12.,-1.]):
            with self.assertRaises(ValueError):self.sample(selected_contact_normal_N=values)
    def test_genuine_two_step_clock_gate_but_no_constructor_history_seed(self):
        self.assertIsNone(self.history())
        for changes in ({'first_command_time_s':1.},{'previous_tick':199},{'latest_matches':False},
                {'two_finite_global18_refs':False},{'entered':False},{'time_s':1.0001},{'tick':True},
                {'first_command_time_s':float('nan')}):
            with self.assertRaises(ValueError):self.history(**changes)
    def test_object_is_not_Capture_Arrival_Stow_or_directly_constructible_authority(self):
        for cls in (ActualCaptureWitness,ActualArrivalSupportWitness,ActualPushStowSupportWitness):
            self.assertFalse(issubclass(c.ActualClimbNavSourceObservation,cls))
        with self.assertRaises(ValueError):c.ActualClimbNavSourceObservation(_seal=object(),runtime=None,session=None,
            executor=None,registry=None,native_witness=None,source_root=None,guard=None,journal=None)
        self.assertFalse(hasattr(c.ActualClimbNavSourceObservation,'validate'))
    def test_same_tick_expiry_never_silently_transfers_an_old_owner_to_NAV(self):
        # Deliberate metadata-only instance; no live-reader seal/source call.
        item=c.ActualClimbNavSourceObservation.__new__(c.ActualClimbNavSourceObservation)
        sim=NS(model=object(),data=NS(time=1.),queue=[]);runtime=NS(sim=sim,step_count=200)
        item.r=runtime;item.observed_tick=200;item.observed_time=1.;item._world=(sim.model,sim.data,sim.queue)
        item.metrics={'necessary_source_ready':True};item._sample=lambda:None
        self.assertTrue(item.validate_same_tick(runtime))
        runtime.step_count=201;sim.data.time=1.005
        with self.assertRaises(ValueError):item.validate_same_tick(runtime)
        self.assertFalse(blocked)

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='CLIMB_NAV_SOURCE_PURE_METADATA_PREDICATES_NOT_LIVE_OWNER_OR_NATIVE_ADMISSION',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,actual_CLIMB_NAV_Runtime_Actor_physics_contact_reader_API_calls=0)))
    sys.exit(0 if r.wasSuccessful()and not blocked else 1)
