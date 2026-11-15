"""Source-only V4 dispatch fixtures; NO native construction or success evidence."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS
import hashlib
import json
import sys
import tempfile
import unittest

OWN = Path(__file__).resolve().parents[1]
ROOT = OWN.parents[1]
SOURCE = ROOT / 'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0] = [str(OWN), str(SOURCE)]
blocked = []
def fence(event, args):
    if event == 'import' and str(args[0]).split('.')[0] in ('numpy', 'torch', 'mujoco', 'onnxruntime'):
        blocked.append(str(args[0])); raise RuntimeError('Software only')
    if event in ('socket.connect', 'socket.bind', 'socket.getaddrinfo', 'subprocess.Popen'):
        blocked.append(event); raise RuntimeError('No network/child')
sys.addaudithook(fence)
import task_factory as v4
from ainav.contracts import Observation, canonical
from ainav.intents import ExecutionBatch, IntentBatch, SkillIntent
from ainav.native.behavior_authority import BehaviorOption
from ainav.native.registered_climb import ClimbBinding, RegisteredClimbAdapter
from ainav.native.registered_task_factory import RegisteredTaskSessionFactory

class SoftwareSession:
    """Deliberately NOT the actual NativeOptionSession; no receipt/commands."""
    def __init__(self, runtime, machine=None, **kwargs): self.runtime = runtime; self.machine = machine

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='V4-SOFTWARE-only-')
        self.addCleanup(self.tmp.cleanup)
        self.image = Path(self.tmp.name) / 'not-a-camera.bin'
        self.image.write_bytes(b'SOFTWARE ONLY; NOT RGBD OR PHYSICAL EVIDENCE')
        self.time = 1.
        self.r = NS(sim=NS(data=NS(time=self.time)))
        self.registry = NS(surfaces={'ground': NS(top_z_m=0.)}, objects={'cuboid_c': NS()})
        self.logs, self.calls = [], []
        self.cls = v4.factory_class(source_root=SOURCE, enabled=True)
        fixture = self
        class SoftwareAdapter(self.cls.destination_adapter_class):
            def bind(self, batch, options, support, *, witness):
                fixture.calls.append(('bind', batch, options, support, witness))
                if getattr(fixture, 'mutate', False): fixture.time += .005
                return {options[0].sha256: ClimbBinding(batch.sha256, options[0].sha256,
                    options[0].target_ref, getattr(fixture, 'bound_object', 'cuboid_c'), 'SOFTWARE-body', 23, 'ground', (('top', .2), ('base_height', 0.)))}
            def construct(self, option, binding, witness):
                fixture.calls.append(('construct', option, binding, witness))
                if getattr(fixture, 'fail_construct', False): raise RuntimeError('SOFTWARE constructor refusal')
                return SoftwareSession(fixture.r)
        self.adapter = SoftwareAdapter(self.r, self.registry, NS(), journal=lambda row: 'SOFTWARE-only')
        self.api = NS(world_snapshot=lambda runtime: ('SOFTWARE-world', fixture.time), NativeOptionSession=SoftwareSession)
        self.witness = NS(support_ref='ground', validate=lambda runtime: True,
                          report=lambda: dict(kind='SOFTWARE-only-no-actual-owner'))
        self.factory = self.cls(self.r, self.registry, initial_witness=None,
            journal=lambda row: self.logs.append(row) or 'SOFTWARE-only',
            push_backend=NS(runtime=self.r, resolver=NS(registry=self.registry)), placement_contracts={},
            native_api=self.api, nav_constructor=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('No NAV construct')),
            climb_adapter=self.adapter)
        self.factory.attach_executor(NS(runtime=self.r, factory=self.factory, session=None, reported_end=True, last_outcome='succeeded'))
        # This override exists ONLY in this fixture. The production factory
        # inherits the unchanged original real-owner validation method.
        self.factory._current_completed_witness = lambda: self.witness
        self.cap = canonical(dict(source_ref='SOFTWARE-only', skills=['NAV', 'PUSH', 'CLIMB'], constraints=['No physical permission']))
        self.obs = self.observation()
        self.outer = BehaviorOption('SOFTWARE-public', 'CLIMB', 'cuboid_c:upper-entry',
                                    (('surface_height_m', .2),), 60., 'SOFTWARE-entry')
        self.inner = replace(self.outer, token='SOFTWARE-native', target_ref='SOFTWARE-opaque')
        self.batch = ExecutionBatch('SOFTWARE-private', self.obs, (self.outer,), self.cap)
        self.factory.begin_acquisition(self.obs)

    def observation(self, time=1.):
        return Observation.create(dict(time_s=time, rgb=dict(path=str(self.image),
            sha256=hashlib.sha256(self.image.read_bytes()).hexdigest(), time_s=time, width=192, height=128),
            objects=[dict(target_ref='SOFTWARE-opaque', label='SOFTWARE current object', bbox_xyxy=[1,1,10,10],
                evidence_ref='SOFTWARE-only', geometry=dict(status='unknown', source='unavailable', values={}, uncertainty={}))],
            public_state={}, declared_map=dict(source_ref='SOFTWARE-only', anchors=[dict(target_ref='cuboid_c:upper-entry',
                description='SOFTWARE declaration', position_xyz_m=[13.,-2.6,.2], uncertainty_xyz_m=[0.,0.,0.])]),
            goal='SOFTWARE not a mission', events=[]))

    def bind(self):
        self.factory.prepare_public_climb(self.outer, self.inner)
        self.factory.bind_batch(self.batch)

    def test_default_off_never_imports_native_or_needs_root(self):
        self.assertIsNone(v4.factory_class()); self.assertFalse(blocked)
        with self.assertRaises(ValueError): v4.factory_class(enabled=1)

    def test_MRO_preserves_original_owner_and_construct_methods(self):
        self.assertIn(RegisteredTaskSessionFactory, self.cls.__mro__)
        self.assertIs(self.cls.original_completed_witness_implementation, RegisteredTaskSessionFactory._current_completed_witness)
        self.assertIs(self.cls.destination_adapter_class.construct, RegisteredClimbAdapter.construct)
        self.assertEqual(self.cls.connected_skills, ('NAV','PUSH','CLIMB'))

    def test_bind_identity_only_preserves_destination_and_exact_witness(self):
        self.bind(); kind, private, options, support, witness = self.calls[0]
        self.assertEqual(kind, 'bind'); self.assertEqual(options, (self.inner,))
        self.assertIs(options[0], self.inner); self.assertIs(witness, self.witness)
        self.assertEqual(support, 'ground'); self.assertIs(private.observation, self.obs)
        self.assertEqual(dict(options[0].parameters)['surface_height_m'], .2)
        self.assertIs(self.factory.native_option_for(self.outer), self.inner)
        self.assertEqual(len(self.calls), 1); self.assertEqual(self.logs[-1]['native_controllers_constructed'], 0)
        with self.assertRaises(ValueError): private.public()

    def test_original_selected_constructor_only_and_no_ground_terminal_hook(self):
        self.bind(); self.factory.terminal_target_ref = self.outer.target_ref
        session = self.factory(self.outer)
        self.assertIsInstance(session, SoftwareSession); self.assertIs(session.runtime, self.r)
        self.assertIs(self.calls[-1][1], self.inner)
        self.assertIs(self.calls[-1][3], self.witness)
        self.assertFalse(self.logs[-1]['task_terminal_verified'])
        with self.assertRaises(ValueError): self.factory(self.outer)

    def test_NAV_still_uses_original_selected_constructor_and_no_ground_terminal(self):
        outer = BehaviorOption('SOFTWARE-NAV', 'NAV', self.outer.target_ref,
            (('goal_world_x_m', 0.), ('goal_world_y_m', 0.), ('surface_height_m', 0.)), 60., 'SOFTWARE-entry')
        batch = ExecutionBatch('SOFTWARE-NAV-query', self.obs, (outer,), self.cap)
        # Geometry is deliberately a fixture, not a claim of actual loaded feet.
        self.factory._validate_option = lambda option, observation, witness: (0., 0.)
        self.factory.nav_constructor = lambda runtime, registry, **kwargs: NS(goal=(0.,0.), height=0., check_guards=lambda: None)
        self.factory.terminal_target_ref = outer.target_ref
        self.factory.bind_batch(batch)
        session = self.factory(outer)
        from ainav.native.registered_nav_factory import RegisteredNavMachine
        self.assertIsInstance(session.machine, RegisteredNavMachine)
        self.assertFalse(self.logs[-1]['task_terminal_verified'])
        self.assertFalse(self.calls)

    def test_current_RGBD_other_object_cannot_satisfy_selected_public_CLIMB(self):
        self.bound_object = 'cuboid_a'
        with self.assertRaisesRegex(ValueError, 'PUBLIC object'): self.bind()
        self.assertIsNone(self.factory.batch)
        self.assertEqual(len(self.calls), 1)

    def test_uninstalled_prior_session_cannot_rebind(self):
        self.factory._constructed_session = SoftwareSession(self.r)
        with self.assertRaises(ValueError): self.bind()
        self.assertFalse(self.calls)

    def test_wrong_params_or_budget_cannot_map_source_as_destination(self):
        for inner in [replace(self.inner, parameters=(('surface_height_m', 0.),)), replace(self.inner, budget_s=40.)]:
            with self.assertRaises(ValueError): self.factory.prepare_public_climb(self.outer, inner)
        self.assertFalse(self.calls)

    def test_no_mapping_no_implicit_CLIMB_binding(self):
        with self.assertRaises(ValueError): self.factory.bind_batch(self.batch)
        self.assertFalse(self.calls)

    def test_acquisition_expires_old_mapping_and_exact_object_required(self):
        self.factory.prepare_public_climb(self.outer, self.inner)
        with self.assertRaises(ValueError): self.factory.prepare_public_climb(self.outer, self.inner)
        with self.assertRaises(ValueError): self.factory.bind_batch(replace(self.batch, options=(replace(self.outer),)))
        self.factory.begin_acquisition(self.obs)
        with self.assertRaises(ValueError): self.factory.bind_batch(self.batch)

    def test_stale_clock_and_tampered_image_refuse_before_adapter(self):
        self.factory.prepare_public_climb(self.outer, self.inner)
        self.r.sim.data.time = 2.
        with self.assertRaises(ValueError): self.factory.bind_batch(self.batch)
        self.r.sim.data.time = 1.; self.image.write_bytes(b'SOFTWARE changed')
        with self.assertRaises(ValueError): self.factory.bind_batch(self.batch)
        self.assertFalse(self.calls)

    def test_semantic_IntentBatch_is_not_native_permission(self):
        intent = SkillIntent('SOFTWARE-intent','CLIMB', self.outer.target_ref, self.outer.parameters)
        public = IntentBatch('SOFTWARE-public', self.obs, (intent,), self.cap)
        with self.assertRaises(ValueError): self.factory.bind_batch(public)
        self.assertFalse(self.calls)

    def test_world_mutation_and_replayed_queries_fail_closed(self):
        self.mutate = True
        with self.assertRaises(ValueError): self.bind()
        self.assertIsNone(self.factory.batch)
        self.mutate = False; self.time = 1.; self.factory.bind_batch(self.batch)
        with self.assertRaises(ValueError): self.factory.bind_batch(self.batch)

    def test_constructor_failure_permanently_revokes_dispatch(self):
        self.bind(); self.fail_construct = True
        with self.assertRaises(RuntimeError): self.factory(self.outer)
        self.assertTrue(self.factory._construction_failed)
        self.fail_construct = False
        with self.assertRaises(ValueError): self.factory(self.outer)

    def test_old_actual_private_CLIMB_identity_survives_new_query_and_constructor(self):
        self.bind()
        self.factory.begin_acquisition(self.obs)
        nav = BehaviorOption('SOFTWARE-next-NAV','NAV',self.outer.target_ref,
            (('goal_world_x_m',0.),('goal_world_y_m',0.),('surface_height_m',0.)),60.,'SOFTWARE')
        self.factory._validate_option=lambda option,observation,witness:(0.,0.)
        self.factory.bind_batch(ExecutionBatch('SOFTWARE-next-query',self.obs,(nav,),self.cap))
        self.assertIs(self.factory.native_option_for(self.outer),self.inner)
        self.factory._constructing_outer=nav;self.factory._constructing_inner=nav
        self.assertIs(self.factory.native_option_for(self.outer),self.inner)
        self.assertIs(self.factory.native_option_for(nav),nav)
        self.assertIsNot(self.factory.native_option_for(replace(self.outer)),self.inner)

    def test_only_selected_NAV_binding_context_wraps_original_completed_witness(self):
        from unittest.mock import patch
        with patch.object(RegisteredTaskSessionFactory,'_current_completed_witness',lambda owner:'SOFTWARE-original-owner'):
            self.factory._binding_skill=None
            self.assertEqual(self.cls._current_completed_witness(self.factory),'SOFTWARE-original-owner')
            self.factory._binding_skill='PUSH'
            self.assertEqual(self.cls._current_completed_witness(self.factory),'SOFTWARE-original-owner')
            self.factory.witness_for_skill=lambda skill:'SOFTWARE-selected-'+skill
            self.factory._binding_skill='NAV'
            self.assertEqual(self.cls._current_completed_witness(self.factory),'SOFTWARE-selected-NAV')

    def test_wrong_selected_copy_or_changed_world_cannot_construct(self):
        self.bind()
        with self.assertRaises(ValueError): self.factory(replace(self.outer))
        self.time = 2.
        with self.assertRaises(ValueError): self.factory(self.outer)
        self.assertEqual(len(self.calls), 1)

if __name__ == '__main__':
    r = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='V4_TASK_FACTORY_SOFTWARE_FIXTURES_NOT_NATIVE_OR_TASK_SUCCESS', checks=r.testsRun,
        failures=len(r.failures), errors=len(r.errors), forbidden_attempts=blocked, native_Runtime_Actor_physics_API_calls=0)))
    sys.exit(0 if r.wasSuccessful() and not blocked else 1)
