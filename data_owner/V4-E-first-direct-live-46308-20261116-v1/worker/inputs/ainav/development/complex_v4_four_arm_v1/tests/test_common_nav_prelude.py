"""Actual original coordinator + Reach policy, EXPLICIT SOFTWARE receipts only.

No Runtime/MjData/Actor/model/backend/import, camera image or command is created.
The public Observation image verifier is patched ONLY inside each fixture test.
"""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from dataclasses import replace
import json, os, sys, unittest
OWN = Path(__file__).resolve().parents[1]; ROOT = OWN.parents[1]
SOURCE = ROOT / 'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
REACH = Path(os.environ.get('AINAV_V4_REACH_PRELUDE_ROOT', str(ROOT / 'manifests/V4_four_arm_source_20261115_v1/reach-common-prelude-readonly-reference')))
sys.path[:0] = [str(OWN), str(SOURCE)]
blocked = []
def fence(event, args):
    if event == 'import' and str(args[0]).split('.')[0] in ('numpy', 'torch', 'mujoco', 'onnxruntime'):
        blocked.append(str(args[0])); raise RuntimeError('Explicit coordinator metadata fixtures only')
    if event in ('socket.connect', 'socket.bind', 'socket.getaddrinfo', 'subprocess.Popen'):
        blocked.append(event); raise RuntimeError('No transport/child/API probe')
sys.addaudithook(fence)
import common_nav_prelude as entry
import live_driver
from factor_scope import FactorJournal
from public_candidates import declared_map, intent_catalogue, capability_contract
from v4_native_asset import load_scene
from ainav.contracts import Observation, Primitive
from ainav.intents import ExecutionBatch
from ainav.planner import Selection
from ainav.native.intent_execution import IntentExecutionCoordinator
from ainav.native.behavior_authority import BehaviorOption, NativeReceipt

class ExplicitMethodFixture:
    def __init__(self, journal):
        self.journal = journal; self.pending = None; self.calls = 0; self.feedback = []
    def select(self, batch):
        self.calls += 1; self.pending = batch.options[0]
        return Selection(batch.sha256, self.pending.token, self.pending.sha256,
                         Primitive.from_option(self.pending).key, 0, 'EXPLICIT_SOFTWARE_method_select')
    def observe_intent(self, *args): self.feedback.append(args); self.pending = None
    def reject_intent(self, *args): raise AssertionError('No prefix feedback to an arm that did not choose it')

class Tests(unittest.TestCase):
    def setUp(self):
        self.scene = load_scene(); self.rows = []; self.acquisitions = []
        self.verify = patch.object(Observation, 'verify_image', return_value=None); self.verify.start()
        self.addCleanup(self.verify.stop)
    def host(self, arm='A'):
        journal = FactorJournal(arm, lambda row: self.rows.append(row) or 'EXPLICIT_SOFTWARE_durable')
        return NS(arm=arm, journal=journal, _v4_factor_journal=journal, planner=ExplicitMethodFixture(journal),
                  owner_guard=lambda: None, source_root=SOURCE, tick=0,
                  r=NS(step_count=0, sim=NS(data=NS(time=0.), queue=[])), writer=NS(steps=0),
                  loop=None, coordinator=None, executor=None)
    def attach(self, host=None, **kw):
        host = host or self.host()
        args = dict(enabled=True, driver=host, reach_source_root=REACH, software_fixture=True); args.update(kw)
        return host, entry.attach_common_nav_prelude(**args)
    def observation(self, now):
        self.acquisitions.append(now)
        return Observation.create(dict(time_s=now,
            rgb=dict(path='/EXPLICIT_SOFTWARE_NOT_IMAGE', sha256='0'*64, time_s=now, width=192, height=128),
            objects=[], public_state={}, declared_map=declared_map(self.scene), goal=self.scene['task']['instruction'], events=[]))
    def coordinator(self, host, caller):
        def judge(intent, now):
            return 'READY', BehaviorOption('EXPLICIT_SOFTWARE_native', intent.skill, intent.target_ref,
                intent.parameters, 60., 'EXPLICIT_SOFTWARE_judge'), 'EXPLICIT_SOFTWARE_binding'
        c = IntentExecutionCoordinator(planner=host.planner, observe=self.observation,
            catalogue=lambda obs: intent_catalogue(self.scene, obs, sequence=len(self.acquisitions)),
            judge=judge, bind=lambda batch: None, snapshot=lambda: 'EXPLICIT_SOFTWARE_UNCHANGED_WORLD',
            protection=lambda now: None, journal=host.journal, capability_contract=capability_contract())
        host.coordinator = c; caller.bind_coordinator(c); return c
    def finish(self, c, *, status='succeeded', time=2.):
        actual = c.actual_option
        receipt = NativeReceipt(actual.sha256, time, status, 'a'*64, 'EXPLICIT_SOFTWARE_NOT_REAL_COMMAND')
        c.observe(actual, receipt)
        return actual, receipt
    def test_default_OFF_no_source_or_owner_access(self):
        with patch.object(entry, '_helper', side_effect=AssertionError('No source read')):
            self.assertIsNone(entry.attach_common_nav_prelude())
        with self.assertRaises(ValueError): entry.attach_common_nav_prelude(enabled=1)
    def test_actual_coordinator_same_fixed_prefix_all_five_methods_untouched(self):
        choices=[]
        for arm in 'ABCDE':
            h, caller = self.attach(self.host(arm)); method=h.planner; c=self.coordinator(h, caller)
            batch = c(1.)
            self.assertIs(type(batch), ExecutionBatch); self.assertIs(h.planner, method)
            self.assertEqual((method.calls, method.pending, method.feedback), (0, None, []))
            self.assertIs(c.model, caller.policy); choices.append((c.intent.skill,c.intent.target_ref,c.intent.parameters))
            self.assertEqual(caller.policy.status, 'PENDING'); self.assertFalse(caller.handed_off)
        self.assertEqual(len(set(choices)), 1); self.assertEqual(choices[0][0:2], ('NAV','v4-ground-nav-007'))
    def test_true_TYPED_software_terminal_then_ONE_new_acquisition_restores_same_method(self):
        h, caller=self.attach(); c=self.coordinator(h,caller); method=h.planner
        c(1.); self.finish(c); self.assertEqual(caller.policy.status,'SUCCEEDED')
        self.assertIs(c.model,caller.policy); self.assertEqual(method.calls,0)
        c(2.); self.assertEqual(self.acquisitions,[1.,2.]); self.assertTrue(caller.handed_off)
        self.assertIs(c.model,method); self.assertIs(h.planner,method); self.assertEqual(method.calls,1)
        self.assertIs(c.journal,caller.policy.journal); self.assertIs(c.journal,method.journal)
        self.assertTrue(any(r['event']=='V4_common_NAV_return_to_same_original_method' for r in self.rows))
        self.assertFalse(any(r.get('actual_WM_forward_or_method_decisions_inferred') for r in self.rows))
    def test_failed_hard_stop_and_expiry_cannot_fall_back_or_retry(self):
        for status in ('failed','hard_stop','budget_expired'):
            with self.subTest(status=status):
                h,caller=self.attach(); c=self.coordinator(h,caller); c(1.);self.finish(c,status=status)
                self.assertEqual(caller.policy.status,'UNAVAILABLE')
                with self.assertRaises(ValueError):c(2.)
                self.assertEqual(h.planner.calls,0);self.assertTrue(caller.failed);self.assertIs(c.model,caller.policy)
    def test_admitted_started_running_are_not_prefix_completion(self):
        for status in ('admitted','started','running'):
            h,caller=self.attach();c=self.coordinator(h,caller);c(1.)
            with self.assertRaises(ValueError):self.finish(c,status=status)
            self.assertFalse(caller.handed_off);self.assertEqual(h.planner.calls,0)
    def test_original_judge_rejection_no_other_target_or_method_call(self):
        h,caller=self.attach();c=self.coordinator(h,caller)
        c.judge=lambda intent,now:('BLOCKED','EXPLICIT_SOFTWARE_REFUSAL','EXPLICIT_SOFTWARE_ref')
        with self.assertRaises(ValueError):c(1.)
        self.assertEqual(caller.policy.status,'UNAVAILABLE');self.assertEqual(h.planner.calls,0)
        self.assertEqual(len(self.acquisitions),1)
    def test_same_image_or_older_observation_cannot_handoff(self):
        for now in (1.,1.5):
            h,caller=self.attach();c=self.coordinator(h,caller);c(1.);self.finish(c)
            with self.assertRaises(ValueError):c(now)
            self.assertTrue(caller.failed);self.assertFalse(caller.handed_off);self.assertEqual(h.planner.calls,0)
    def test_wrong_or_changed_native_option_does_not_complete_prefix(self):
        h,caller=self.attach();c=self.coordinator(h,caller);c(1.)
        actual=c.actual_option; wrong=replace(actual,target_ref='v4-ground-nav-008')
        receipt=NativeReceipt(wrong.sha256,2.,'succeeded','a'*64,'EXPLICIT_SOFTWARE_wrong')
        with self.assertRaises(ValueError):c.observe(wrong,receipt)
        self.assertEqual(caller.policy.status,'PENDING');self.assertEqual(h.planner.calls,0)
    def test_method_journal_or_coordinator_swap_refuses_without_arm_call(self):
        for change in ('host_method','journal','coordinator_method'):
            h,caller=self.attach();c=self.coordinator(h,caller);c(1.);self.finish(c)
            old=h.planner
            if change=='host_method':h.planner=ExplicitMethodFixture(h.journal)
            elif change=='journal':old.journal=lambda row:'EXPLICIT_SOFTWARE_other'
            else:c.model=old
            with self.assertRaises(ValueError):c(2.)
            self.assertEqual(old.calls,0);self.assertTrue(caller.failed)
    def test_guard_and_non_durable_handoff_error_remain_closed(self):
        for error in ('guard','journal','image'):
            h,caller=self.attach();c=self.coordinator(h,caller);c(1.);self.finish(c)
            if error=='guard':h.owner_guard=lambda:False
            if error=='journal':h.journal.original=lambda row:None
            if error=='image':self.verify.stop();self.verify=patch.object(Observation,'verify_image',side_effect=ValueError('EXPLICIT_SOFTWARE_missing_image'));self.verify.start()
            with self.assertRaises(ValueError):c(2.)
            self.assertTrue(caller.failed);self.assertEqual(h.planner.calls,0);self.assertIs(c.model,caller.policy)
    def test_no_double_attach_bind_or_midstream_attachment(self):
        h,caller=self.attach()
        with self.assertRaises(ValueError):self.attach(h)
        c=self.coordinator(h,caller)
        with self.assertRaises(ValueError):caller.bind_coordinator(c)
        for attr in ('tick','step','writer','calls','forward'):
            h=self.host()
            if attr=='tick':h.tick=1
            if attr=='step':h.r.step_count=1
            if attr=='writer':h.writer.steps=1
            if attr=='calls':h.planner.calls=1
            if attr=='forward':h.planner.wm=NS(forward_batches=1)
            with self.assertRaises(ValueError):self.attach(h)
    def test_fixture_refused_in_actual_driver_before_native_execution_assembly(self):
        h,caller=self.attach();cls=live_driver.driver_class(source_root=SOURCE,enabled=True)
        shell=object.__new__(cls);shell._v4_common_nav_prelude=caller
        with self.assertRaisesRegex(ValueError,'Fixture prefix'):shell._connect_execution()
        self.assertFalse(blocked)
    def test_fixture_cannot_promote_and_cross_world_or_coordinator_refuses(self):
        for change in ('runtime', 'sim', 'queue', 'coordinator'):
            h,caller=self.attach();c=self.coordinator(h,caller);c(1.);self.finish(c)
            with self.assertRaises(AttributeError):caller.software_fixture=False
            if change=='runtime':h.r=NS(sim=h.r.sim)
            if change=='sim':h.r.sim=NS(queue=h.r.sim.queue)
            if change=='queue':h.r.sim.queue=[]
            if change=='coordinator':h.coordinator=object()
            with self.assertRaises(ValueError):c(2.)
            self.assertTrue(caller.failed);self.assertEqual(h.planner.calls,0)
    def test_native_and_common_factor_guard_sources_not_replaced(self):
        import hashlib
        self.assertEqual(hashlib.sha256((SOURCE/'ainav/native/intent_execution.py').read_bytes()).hexdigest(),entry.COORDINATOR_SHA)
        self.assertEqual(entry._helper(REACH).CommonNavObservationPrelude.decision_source,'V4_COMMON_NAV_OBSERVATION_PRELUDE_NOT_ARM_METHOD')
        self.assertFalse(hasattr(entry._helper(REACH).CommonNavObservationPrelude,'enabled'))
        self.assertFalse(blocked)

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='REAL_ORIGINAL_COORDINATOR_REACH_POLICY_EXPLICIT_SOFTWARE_RECEIPTS_NOT_NATIVE_OR_WM',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,model_restore_forward_backend_Actor_or_physics_calls=0)))
    sys.exit(0 if r.wasSuccessful() and not blocked else 1)
