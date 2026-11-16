"""Canonical C/D composition fixtures: no authenticated backend/API/model/world.

Backend is __new__ PUBLIC-METADATA ONLY (from the explicit existing fixture).
One case uses production factor flags to test journal wiring with synthetic
stow aliases, NOT an authenticated method, native owner or dispatch permission.
"""
from pathlib import Path
from types import SimpleNamespace as NS,ModuleType
from unittest.mock import patch
import os,sys,json,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
sys.path[:0]=[str(OWN),str(OWN/'tests')]
from test_backbone_entry import Tests as MetadataFixture,Backend,SOURCE,blocked
import method_entry as entry
import factor_scope as factors
REACH=Path(os.environ.get('AINAV_V4_REACH_SOURCE_ROOT',str(ROOT/'manifests/V4_four_arm_source_20261115_v1/reach-adapter-readonly-reference')))

class Tests(unittest.TestCase):
    def setUp(self):self.rows=[];self.journal=lambda row:self.rows.append(row)or'EXPLICIT_SOFTWARE_COMPOSITION_NO_AUTH_OR_NATIVE'
    def backend(self):return MetadataFixture.backend(self)
    def build(self,**kw):
        args=dict(enabled=True,arm='C',source_root=SOURCE,reach_source_root=REACH,
            backend=self.backend(),journal=self.journal,guard=lambda:None,software_fixture=True)
        args.update(kw);return entry.build_original_cd_method(**args)
    def test_default_off_does_not_import_read_authenticate_or_wrap(self):
        with patch.object(entry,'_reach_modules',side_effect=AssertionError('No source IO')):
            self.assertIsNone(entry.build_original_cd_method())
        self.assertFalse(self.rows)
    def test_wrong_arm_flags_and_unbound_or_C_treatment_refuse(self):
        for arm in 'ABE':
            with self.assertRaises(ValueError):self.build(arm=arm)
        for kw in [dict(enabled=1),dict(software_fixture=1),dict(arm='D'),dict(shared_path_cost=lambda *a,**k:None)]:
            with self.assertRaises(ValueError):self.build(**kw)
        self.assertFalse(self.rows)
    def test_C_exact_original_backbone_profile_and_canonical_adapter(self):
        p=self.build();_,module=entry._reach_modules(REACH)
        self.assertIs(type(p),module.AinavSuccessorAdapter);self.assertFalse(p.enabled)
        self.assertTrue(p.software_fixture);self.assertIsNone(p.path_cost)
        self.assertIs(p.journal,p.baseline.journal);self.assertIs(p.journal,p.baseline.roles.journal)
        self.assertEqual((p.baseline.plan_count,p.baseline.tree.terminal_bonus,p.baseline.roles.timeout_s),(5,10.,90.))
        self.assertEqual(p.baseline.roles.backend.calls,0)
    def test_D_same_explicit_cost_callable_no_eval_or_WM_gain(self):
        def cost(*args,**kw):raise AssertionError('No cost invocation during assembly')
        p=self.build(arm='D',shared_path_cost=cost)
        self.assertTrue(p.enabled);self.assertIs(p.path_cost,cost)
        self.assertFalse(hasattr(p,'wm'));self.assertEqual(p.baseline.calls,0)
        self.assertFalse(self.rows[-1]['method_or_native_or_task_ready_claimed'])
    def test_fixture_cost_cannot_enter_production_flags(self):
        def fixture(*args,**kw):raise AssertionError('Not called')
        fixture.software_fixture=True
        with self.assertRaises(ValueError):self.build(arm='D',shared_path_cost=fixture,software_fixture=False)
        self.assertFalse(self.rows)
    def test_no_backend_constructor_generate_or_provider_calls(self):
        with patch.object(Backend,'__init__',side_effect=AssertionError('No auth'))as init,patch.object(Backend,'generate',side_effect=AssertionError('No API'))as generate:
            self.build();init.assert_not_called();generate.assert_not_called()
        self.assertFalse(blocked)
    def test_C_selection_and_actual_feedback_delegate_exact_arguments(self):
        p=self.build();batch=object();selection=object();intent=object();actual=object();receipt=object()
        for name,args in [('select',(batch,)),('observe_intent',(intent,actual,receipt,'binding-SOFTWARE')),
                          ('reject_intent',(intent,'blocked','evidence-SOFTWARE')),('observe',(actual,receipt))]:
            with patch.object(p.baseline,name,return_value=selection)as callback:
                self.assertIs(getattr(p,name)(*args),selection);callback.assert_called_once_with(*args)
        self.assertIsNone(p.last_choice.get('selected_path')if p.last_choice else None)
    def test_ambient_reach_or_successor_kernel_identity_refuse(self):
        _,module=entry._reach_modules(REACH)
        with patch.object(module,'__file__','/SOFTWARE/foreign/v4_backbone_adapters.py'):
            with self.assertRaises(ValueError):self.build()
        with patch.object(module,'choose',lambda *a,**k:None):
            with self.assertRaises(ValueError):self.build()
    def test_current_source_bytes_drift_refuse_before_backbone_claim(self):
        with patch.dict(entry.REACH_PINS,{'v4_backbone_adapters.py':'0'*64}):
            with self.assertRaises(ValueError):self.build()
        self.assertFalse(self.rows)
    def test_one_factor_ledger_reaches_wrapper_original_planner_and_roles(self):
        p=self.build(software_fixture=False)  # ONLY synthetic metadata + alias installation, not live inputs.
        sim=NS(data=NS(time=0.),queue=[],model=NS(),controller=NS(),box_push_target=NS())
        host=NS(r=NS(step_count=0,sim=sim),source_root=SOURCE,owner_guard=lambda:None,loop=None)
        host._world=(sim,sim.model,sim.data,sim.queue,sim.controller,sim.box_push_target)
        for i,name in enumerate(('mujoco_zyh/stall_stow.py','ainav/native/current_stall_stow.py')):
            module=ModuleType('EXPLICIT_SOFTWARE_CD_STOW_ALIAS_'+str(i));module.__file__=str(SOURCE/name)
            exec("class ProtectedStow:\n def update(self):return globals().get('_reach_stow_path_choice_at_capture')",vars(module))
            module.np=NS(array=lambda *a,**kw:None);sys.modules[module.__name__]=module;self.addCleanup(sys.modules.pop,module.__name__,None)
        ledger=factors.install_legacy_common(host,arm='C',planner=p,journal=self.journal)
        self.assertIs(host.journal,ledger)
        for owner in (p,p.baseline,p.baseline.roles):
            self.assertIs(owner.journal,ledger);owner.journal(dict(event='EXPLICIT_SOFTWARE_journal_probe'))
        self.assertTrue(all(row['v4_factor_scope']['arm']=='C'for row in self.rows[-3:]))
        self.assertEqual(ledger.counts['legacy_kernel_attempts'],0);self.assertEqual(p.baseline.roles.backend.calls,0)
    def test_used_or_divergent_journals_refuse_without_state_reset(self):
        p=self.build();p.baseline.roles.backend.calls=1
        with self.assertRaises(ValueError):entry.bind_original_cd_journal(p,self.journal)
        self.assertEqual(p.baseline.roles.backend.calls,1)
        p=self.build();p.baseline.journal=lambda row:'divergent'
        with self.assertRaises(ValueError):entry.bind_original_cd_journal(p,self.journal)
    def test_backend_cannot_retry_method_assembly_and_bad_journal_returns_no_method(self):
        b=self.backend();self.build(backend=b)
        with self.assertRaises(ValueError):self.build(backend=b)
        with self.assertRaises(ValueError):self.build(journal=lambda row:None)
        self.assertEqual(b.calls,0)

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='EXPLICIT_CANONICAL_CD_ASSEMBLY_AND_FACTOR_JOURNAL_FIXTURES_NOT_AUTH_OR_NATIVE',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,authenticated_backend_constructors_API_VLM_WM_Actor_physics_calls=0)))
    sys.exit(0 if r.wasSuccessful()and not blocked else 1)
