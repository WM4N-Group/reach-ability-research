"""Two-factor source/namespace fixtures; NO actual stow/controller/kernel trial."""
from pathlib import Path
from types import SimpleNamespace as NS, ModuleType
import sys,json,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Source metadata fixture only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import factor_scope as f
from rule_baseline import RuleBaseline
from v4_native_asset import load_scene

class Tests(unittest.TestCase):
    def setUp(self):self.rows=[];self.journal=lambda row:self.rows.append(row)or'SOFTWARE-only'
    def host(self,arm='E'):
        sim=NS(data=NS(time=0.),queue=[],model=NS(),controller=NS(),box_push_target=NS())
        host=NS(r=NS(step_count=0,sim=sim),source_root=SOURCE,owner_guard=lambda:None,loop=None)
        host._world=(sim,sim.model,sim.data,sim.queue,sim.controller,sim.box_push_target)
        planner=RuleBaseline(load_scene(),journal=self.journal)if arm=='E'else NS(journal=self.journal,enabled=arm in('B','D'),software_fixture=False)
        return host,planner
    def aliases(self,invalid_second=False,prior=False):
        modules=[]
        for i,name in enumerate(('mujoco_zyh/stall_stow.py','ainav/native/current_stall_stow.py')):
            module=ModuleType('SOFTWARE_V4_stow_alias_%d'%i);module.__file__=str(SOURCE/name)
            # Explicit synthetic module, never imported native code or world.
            exec("class ProtectedStow:\n def update(self):return globals().get('_reach_stow_path_choice_at_capture')",vars(module))
            module.np=NS(array=lambda *args,**kwargs:None)
            key=module.__name__;sys.modules[key]=module;self.addCleanup(sys.modules.pop,key,None)
            modules.append(module)
        if invalid_second:modules[1].ProtectedStow.update=lambda owner:None
        if prior:setattr(modules[1],'_reach_stow_path_choice_at_capture',lambda:None)
        return modules
    def test_all_five_keep_identical_common_H_only_B_D_new_treatment(self):
        for arm in 'ABCDE':
            p=f.factors(arm);self.assertTrue(p['legacy_common_stow_H_enabled'])
            self.assertIs(p['new_successor_optimizer_enabled'],arm in('B','D'))
            self.assertTrue(p['legacy_H_is_not_new_treatment'])
        with self.assertRaises(ValueError):f.factors('F')
    def test_A_C_E_cannot_record_new_selector_under_common_H_label(self):
        for arm in 'ACE':
            ledger=f.FactorJournal(arm,self.journal)
            with self.assertRaises(ValueError):ledger(dict(event=f.NEW_CHOICE_EVENT,choice_changed=True))
            self.assertEqual(ledger.counts['new_successor_choice_events'],0)
        self.assertFalse(self.rows)
    def test_B_D_new_choice_events_not_legacy_kernel_or_gain(self):
        for arm in 'BD':
            ledger=f.FactorJournal(arm,self.journal)
            ledger(dict(event=f.NEW_CHOICE_EVENT,choice_changed=True,software_fixture=False))
            self.assertEqual(ledger.counts['new_successor_choice_events'],1)
            self.assertEqual(ledger.counts['legacy_kernel_attempts'],0)
        self.assertTrue(all(r['v4_factor_scope']['legacy_H_is_not_new_treatment']for r in self.rows))
    def test_private_binding_keeps_exact_bytecode_and_Reach_globals_unchanged(self):
        ledger=f.FactorJournal('E',self.journal);module,bound=f._binding(SOURCE,ledger)
        self.assertIs(bound.__code__,module.bind_to_host.__code__)
        self.assertEqual(bound.__kwdefaults__,module.bind_to_host.__kwdefaults__)
        self.assertIsNot(bound.__globals__,vars(module));self.assertIsNot(bound.__globals__['optimize'],module.optimize)
        self.assertEqual(set(k for k in vars(module)if bound.__globals__[k]is not vars(module)[k]),{'optimize'})
        self.assertEqual(ledger.counts['legacy_kernel_attempts'],0)
    def test_kernel_attempt_before_call_args_and_return_identity_unchanged(self):
        ledger=f.FactorJournal('A',self.journal);arg=object();result={'changed':True};seen=[]
        def kernel(*args,**kwargs):
            self.assertEqual(self.rows[-1]['event'],'V4_legacy_common_H_kernel_attempt');seen.append((args,kwargs));return result
        returned=ledger.kernel(kernel)(arg,guard_segment=arg)
        self.assertIs(returned,result);self.assertIs(seen[0][0][0],arg);self.assertIs(seen[0][1]['guard_segment'],arg)
        self.assertEqual((ledger.counts['legacy_kernel_attempts'],ledger.counts['legacy_kernel_completed'],ledger.counts['legacy_kernel_result_changed']),(1,1,1))
        self.assertEqual(ledger.counts['new_successor_choice_events'],0)
        self.assertFalse(self.rows[-1]['actual_motor_change_or_task_gain_inferred'])
    def test_failed_kernel_attempt_preserved_no_zero_or_exception_text_leak(self):
        ledger=f.FactorJournal('C',self.journal);error=RuntimeError('SOFTWARE-private-error-text')
        def fail():raise error
        with self.assertRaises(RuntimeError)as caught:ledger.kernel(fail)()
        self.assertIs(caught.exception,error);self.assertEqual(ledger.counts['legacy_kernel_failed'],1)
        self.assertEqual(ledger.counts['legacy_kernel_attempts'],1);self.assertEqual(ledger.counts['legacy_kernel_completed'],0)
        self.assertNotIn('SOFTWARE-private-error-text',json.dumps(self.rows))
    def test_existing_factor_identity_and_fixture_choice_not_silently_relabelled(self):
        ledger=f.FactorJournal('B',self.journal)
        with self.assertRaises(ValueError):ledger(dict(event='SOFTWARE',v4_factor_scope={}))
        with self.assertRaises(ValueError):ledger(dict(event=f.NEW_CHOICE_EVENT,software_fixture=True))
        self.assertFalse(self.rows)
    def test_fresh_task_zero_method_flag_and_same_journal_required(self):
        host,planner=self.host('A');planner.enabled=True
        with self.assertRaises(ValueError):f.install_legacy_common(host,arm='A',planner=planner,journal=self.journal)
        host,planner=self.host();host.r.step_count=448
        with self.assertRaises(ValueError):f.install_legacy_common(host,arm='E',planner=planner,journal=self.journal)
        host,planner=self.host();planner.journal=lambda row:'SOFTWARE other'
        with self.assertRaises(ValueError):f.install_legacy_common(host,arm='E',planner=planner,journal=self.journal)
        self.assertFalse(self.rows)
    def test_common_E_install_keeps_alias_guard_and_does_not_call_kernel(self):
        aliases=self.aliases();host,planner=self.host()
        ledger=f.install_legacy_common(host,arm='E',planner=planner,journal=self.journal)
        self.assertIs(planner.journal,ledger);self.assertIs(host.journal,ledger)
        self.assertEqual(ledger.counts['legacy_kernel_attempts'],0)
        self.assertEqual(len(host._stow_installed),2)
        for module in aliases:self.assertIs(host._stow_installed[str(Path(module.__file__).resolve())],vars(module)[host._stow_callback_name])
        import live_driver
        cls=live_driver.driver_class(source_root=SOURCE,enabled=True)
        cls._native_guards(host)
        setattr(aliases[1],host._stow_callback_name,lambda:None)
        with self.assertRaises(ValueError):cls._native_guards(host)
        with self.assertRaises(ValueError):f.install_legacy_common(host,arm='E',planner=planner,journal=self.journal)
    def test_bad_second_alias_leaves_first_uninstalled_no_partial_override(self):
        aliases=self.aliases(invalid_second=True);host,planner=self.host()
        with self.assertRaises(ValueError):f.install_legacy_common(host,arm='E',planner=planner,journal=self.journal)
        self.assertNotIn('_reach_stow_path_choice_at_capture',vars(aliases[0]))
        self.assertFalse(hasattr(host,'_v4_factor_journal'))
    def test_preexisting_callback_not_removed_to_claim_legacy_off(self):
        aliases=self.aliases(prior=True);old=vars(aliases[1])['_reach_stow_path_choice_at_capture'];host,planner=self.host()
        with self.assertRaises(ValueError):f.install_legacy_common(host,arm='E',planner=planner,journal=self.journal)
        self.assertIs(vars(aliases[1])['_reach_stow_path_choice_at_capture'],old)
        self.assertNotIn('_reach_stow_path_choice_at_capture',vars(aliases[0]))

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='V4_COMMON_LEGACY_H_AND_NEW_SUCCESSOR_FACTOR_METADATA_FIXTURES_NOT_NATIVE_OR_METHOD_RESULTS',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,actual_stow_kernel_or_Runtime_Actor_physics_API_calls=0)))
    sys.exit(0 if r.wasSuccessful()and not blocked else 1)
