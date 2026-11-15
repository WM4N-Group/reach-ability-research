"""Bounded CLIMB/NAV query/constructor/outer-guard wiring; explicit mocks ONLY."""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from dataclasses import replace
import sys,json,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN),str(OWN/'tests'),str(SOURCE)]
import test_task_factory as fixture
import task_factory as factory_module
from execution_entry import _current_contact_owners
from climb_nav_source import ActualClimbNavSourceObservation
from climb_nav_adapter import LiveClimbNavSourceWitness
from ainav.native.registered_climb import RegisteredClimbMachine
from ainav.native.scene_registry import SurfaceSpec
from ainav.intents import ExecutionBatch
from ainav.native.behavior_authority import BehaviorOption
from public_candidates import declarations,declared_map
from v4_native_asset import load_scene

class Array:
    def __init__(self,value):self.value=value
    def tolist(self):return self.value
class Column:
    def __init__(self,value):self.value=value
    def __getitem__(self,index):return Array(self.value)

class Tests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.Tests('test_default_off_never_imports_native_or_needs_root');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.f.bind();self.host=self.f.factory;self.r=self.f.r
        self.r.sim.model=object();self.r.sim.queue=[];self.r.sim.feet_ids=[0,1,2,3]
        self.r.sim.data.xpos=Column([[12.8,-2.7,.222],[12.8,-2.5,.222],[13.2,-2.7,.222],[13.2,-2.5,.222]])
        self.r.sim.forces=Column([52.]*4)
        self.f.registry.objects['cuboid_c']=NS(ref='cuboid_c',body_name='SOFTWARE-body')
        binding=self.host._climb_bindings[self.f.inner.sha256]
        machine=RegisteredClimbMachine(self.r,NS(sim=self.r.sim),NS(complete=True),binding,{})
        self.source=fixture.SoftwareSession(self.r,machine);self.source.outcome='succeeded';self.source.entered=True
        self.host.executor.session=self.source;self.host.executor.option=self.f.outer
        self.host.executor.reported_end=True;self.host.executor.last_outcome='succeeded'
        del self.host.__dict__['_current_completed_witness']  # Exercise NEW real context wrapper.
        self.host.actual_placements=object()  # Deliberately mocked maker; not live evidence.
        self.sample=ActualClimbNavSourceObservation.__new__(ActualClimbNavSourceObservation)
        self.sample.r=self.r;self.sample.executor=self.host.executor;self.sample.registry=self.f.registry;self.sample.session=self.source
        self.sample.validate_same_tick=lambda runtime:False  # Registration is NOT admission.
        self.host.register_climb_nav_source(self.sample)
        self.seen=[]
        self.witness=LiveClimbNavSourceWitness.__new__(LiveClimbNavSourceWitness)
        w=self.witness;w.r=self.r;w.executor=self.host.executor;w.original_registry=self.f.registry
        w.support_ref='climb_nav_source__cuboid_c';w.object_ref='cuboid_c'
        surface=SurfaceSpec(w.support_ref,'SOFTWARE-body_geom',(11.8,14.2,-3.3,-1.9),.2)
        w.registry=NS(surfaces={w.support_ref:surface})
        w.validate=lambda runtime:self.seen.append(('validate',runtime))or True
        w.report=lambda:dict(kind='SOFTWARE-typed-source-NOT-live')
        w.entered_objects=lambda runtime:self.seen.append(('outer_contact',runtime))or frozenset(('cuboid_c',))
        class SoftwareNav:
            def __init__(nav,runtime,registry,*,capture_witness,goal_xy,journal):
                nav.r=runtime;nav.registry=registry;nav.capture_witness=capture_witness
                nav.goal=goal_xy;nav.height=.2;nav.check_guards=lambda:None;capture_witness.nav_owner=nav
        w.nav_type=SoftwareNav;w.nav_owner=None
        self.maker=patch.object(factory_module,'make_live_source_witness',lambda observation,placements,**kwargs:w)
        self.maker.start();self.addCleanup(self.maker.stop)
        self.nav=BehaviorOption('SOFTWARE-top-NAV','NAV',self.f.outer.target_ref,
            (('goal_world_x_m',13.),('goal_world_y_m',-2.6),('surface_height_m',.2)),60.,'SOFTWARE-only')
    def bind(self):
        self.host.begin_acquisition(self.f.obs)
        self.host.bind_batch(ExecutionBatch('SOFTWARE-top-query',self.f.obs,(self.nav,),self.f.cap))
    def test_same_source_cached_but_no_controller_before_exact_selected_call(self):
        self.assertIs(self.host.witness_for_skill('NAV'),self.witness)
        self.bind();self.assertIs(self.host.witness,self.witness)
        self.assertIsNone(self.witness.nav_owner)
        self.assertIs(self.host.registry,self.f.registry);self.assertNotIn(self.witness.support_ref,self.f.registry.surfaces)
        session=self.host(self.nav)
        self.assertIs(session.machine.native_nav.capture_witness,self.witness)
        self.assertIs(session.machine.native_nav.registry,self.f.registry)  # Constructor receives ORIGINAL registry.
        self.assertEqual(session.machine.native_nav.goal,(13.,-2.6))
    def test_original_validator_uses_private_source_but_keeps_public_goal_match(self):
        self.assertEqual(self.host._validate_option(self.nav,self.f.obs,self.witness),(13.,-2.6))
        wrong=replace(self.nav,parameters=(('goal_world_x_m',13.1),('goal_world_y_m',-2.6),('surface_height_m',.2)))
        with self.assertRaisesRegex(ValueError,'public declaration'):self.host._validate_option(wrong,self.f.obs,self.witness)
    def test_next_query_and_pending_constructor_keep_old_CLIMB_private_hash(self):
        self.bind();self.assertIs(self.host.native_option_for(self.f.outer),self.f.inner)
        self.host._constructing_outer=self.nav;self.host._constructing_inner=self.nav
        self.assertIs(self.host.native_option_for(self.f.outer),self.f.inner)
        self.assertIsNot(self.host.native_option_for(replace(self.f.outer)),self.f.inner)
    def test_outer_guard_is_synchronised_with_entered_actual_NAV_source(self):
        self.bind();session=self.host(self.nav);session.entered=True
        self.host.executor.session=session;self.host.executor.option=self.nav
        owners=dict(executor=self.host.executor,factory=self.host,backend=self.f.factory.push_backend)
        self.assertEqual(_current_contact_owners(owners,self.r,self.f.registry,RegisteredClimbMachine),(None,frozenset(('cuboid_c',))))
        self.assertEqual(self.seen[-1][0],'outer_contact')
        session.entered=False
        with self.assertRaises(ValueError):_current_contact_owners(owners,self.r,self.f.registry,RegisteredClimbMachine)
    def test_source_registration_does_not_relabel_CLIMB_success_or_replace_sample(self):
        self.assertEqual(self.host.executor.last_outcome,'succeeded')
        another=ActualClimbNavSourceObservation.__new__(ActualClimbNavSourceObservation)
        another.__dict__.update(self.sample.__dict__)
        with self.assertRaises(ValueError):self.host.register_climb_nav_source(another)
        self.assertEqual(self.host.executor.last_outcome,'succeeded')
    def test_missing_actual_source_or_placement_never_constructs_NAV(self):
        self.host._climb_nav_sources={}
        with self.assertRaises(ValueError):self.host.witness_for_skill('NAV')
        self.host._climb_nav_sources={self.source:self.sample};self.host.actual_placements=None
        with self.assertRaises(ValueError):self.host.witness_for_skill('NAV')
        self.assertIsNone(self.witness.nav_owner)
    def test_failed_private_bind_clears_selected_context(self):
        self.host.begin_acquisition(self.f.obs)
        wrong=replace(self.nav,parameters=(('goal_world_x_m',13.1),('goal_world_y_m',-2.6),('surface_height_m',.2)))
        with self.assertRaises(ValueError):self.host.bind_batch(ExecutionBatch('SOFTWARE-bad-top-query',self.f.obs,(wrong,),self.f.cap))
        self.assertIsNone(self.host._binding_skill);self.assertIsNone(self.host.batch)
    def test_new_shared_domain_only_three_finite_declared_top_centres_not_arbitrary_XY(self):
        scene=load_scene();rows=declarations(scene);top=[r for r in rows if r['skill']=='NAV'and r['target_ref'].startswith('v4-box-top-')]
        self.assertEqual(len(top),3);self.assertEqual(len(rows),30)
        self.assertEqual(sum(r['skill']=='NAV'for r in rows),20)
        for row in top:
            obj=next(o for o in scene['objects']if row['target_ref']=='v4-box-top-'+o['public_ref'])
            self.assertEqual(row['parameters'],dict(goal_world_x_m=obj['required_goal_xy_m'][0],goal_world_y_m=obj['required_goal_xy_m'][1],surface_height_m=obj['size_m'][2]))
        self.assertEqual(len(declared_map(scene)['anchors']),27)

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='BOUNDED_CLIMB_NAV_FACTORY_CONTEXT_AND_OUTER_CONTACT_SOFTWARE_MOCKS_NOT_NATIVE',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=fixture.blocked,actual_Runtime_Actor_physics_API_calls=0)))
    sys.exit(0 if r.wasSuccessful()and not fixture.blocked else 1)
