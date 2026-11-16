"""Original planner composition with an explicit __new__ backend METADATA fixture.
No authenticated backend construction, credentials, API, role inference or native
world. The fixture is not a production backend receipt or dispatch permission.
"""
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace as NS
import json,sys,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Original composition metadata fixture only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child/probe')
sys.addaudithook(fence)
import backbone_entry as entry
_,modules=entry._original_types(SOURCE)
Backend=modules['ainav.deepseek'].DeepSeekBackend
Planner=modules['ainav.planner'].AinavPlanner
Roles=modules['ainav.vlm'].RoleRunner

class Tests(unittest.TestCase):
    def setUp(self):self.rows=[]
    def backend(self):
        # No __init__, no key, no opener, no authenticated /models or generate.
        b=Backend.__new__(Backend);b.model='deepseek-flash';b.calls=b.total_tokens=0
        b.max_calls=100;b.max_tokens=8192;b.max_total_tokens=900000
        b.identity=dict(provider='DeepSeek',endpoint='https://api.deepseek.com/chat/completions',requested_model=b.model,
            thinking='disabled',model_capability={'id':b.model,'input_modalities':['text','image']},
            model_list_sha256='a'*64,max_calls=100,max_tokens=8192,max_total_tokens=900000)
        return b
    def journal(self,row):self.rows.append(row);return 'EXPLICIT_SOFTWARE_METADATA_NOT_AUTH_OR_NATIVE'
    def build(self,backend=None,**kwargs):
        values=dict(enabled=True,arm='C',source_root=SOURCE,backend=self.backend()if backend is None else backend,
            journal=self.journal,guard=lambda:None);values.update(kwargs);return entry.build_original_ainav_backbone(**values)
    def test_default_off_and_other_arm_refusal_need_no_backend(self):
        self.assertIsNone(entry.build_original_ainav_backbone())
        with self.assertRaises(ValueError):entry.build_original_ainav_backbone(enabled=1)
        for arm in ('A','B','E',None):
            with self.assertRaises(ValueError):entry.build_original_ainav_backbone(enabled=True,arm=arm)
    def test_owner_false_refuses_before_any_original_constructors(self):
        with patch.object(Roles,'__init__',side_effect=AssertionError('No role construction')):
            with self.assertRaises(ValueError):self.build(guard=lambda:False)
        self.assertEqual(self.rows,[])
    def test_actual_original_types_and_all_planning_methods_unchanged(self):
        baseline=self.build();self.assertIs(type(baseline),Planner);self.assertIs(type(baseline.roles),Roles)
        for name in ('_role','_expand','select','observe','reject_intent','observe_intent'):
            self.assertIs(getattr(baseline,name).__func__,getattr(Planner,name))
        self.assertTrue({'object_proposer','skill_proposer','evaluator','advisor','arborist'}<=set(modules['ainav.vlm'].ROLE_INSTRUCTIONS))
        self.assertIs(baseline.roles.run.__func__,Roles.run)
        self.assertIs(baseline.journal.__self__,self);self.assertEqual(baseline.calls,0)
        self.assertIsNone(baseline.pending);self.assertTrue(baseline._v4_backbone_only_not_full_method)
    def test_full_course_profile_is_parsed_not_default_weakened_or_launcher_run(self):
        baseline=self.build();profile=entry._full_course_profile(SOURCE)
        self.assertEqual(profile,dict(backend_caps=dict(max_calls=100,max_tokens=8192,max_total_tokens=900000),roles={'timeout_s':90.},planner={'plan_count':5,'terminal_bonus':10.}))
        self.assertEqual(baseline.plan_count,5);self.assertEqual(baseline.tree.terminal_bonus,10.)
        self.assertEqual(baseline.roles.timeout_s,90.);self.assertEqual(baseline.max_role_calls,8)
    def test_C_D_have_same_original_backbone_not_treatment_or_WM(self):
        c=self.build(arm='C');d=self.build(arm='D')
        self.assertIs(type(c),type(d));self.assertEqual(c.plan_count,d.plan_count)
        self.assertEqual(c.tree.terminal_bonus,d.tree.terminal_bonus)
        self.assertFalse(hasattr(c,'enabled'));self.assertFalse(hasattr(d,'enabled'))
    def test_no_backend_constructor_transport_role_inference_or_secret_access(self):
        original_get=Backend.__getattribute__
        def metadata_only(obj,name):
            if name in ('_key','_opener','api_key','headers'):raise AssertionError('Secret/transport inspection forbidden')
            return original_get(obj,name)
        backend=self.backend()
        with patch.object(Backend,'__init__',side_effect=AssertionError('No backend/auth probe'))as constructor,patch.object(Backend,'generate',side_effect=AssertionError('No generate'))as generate,patch.object(Backend,'__getattribute__',metadata_only):
            baseline=self.build(backend);self.assertIs(baseline.roles.backend,backend)
            constructor.assert_not_called();generate.assert_not_called()
        self.assertFalse(hasattr(backend,'_key'));self.assertFalse(blocked)
    def test_fake_kind_or_wrong_provider_and_missing_image_metadata_refuse(self):
        with self.assertRaises(ValueError):self.build(NS(kind='deepseek_vision_api'))
        for change in ('provider','image','digest','thinking'):
            backend=self.backend()
            if change=='provider':backend.identity['provider']='SOFTWARE_wrong_provider'
            elif change=='image':backend.identity['model_capability']['input_modalities']=['text']
            elif change=='digest':backend.identity['model_list_sha256']='SOFTWARE-not-digest'
            else:backend.identity['thinking']='enabled'
            with self.assertRaises(ValueError):self.build(backend)
    def test_used_backend_and_capacity_drift_are_not_reset_or_hidden(self):
        for field,value in [('calls',1),('total_tokens',1),('max_calls',99),('max_tokens',4096),('max_total_tokens',200000)]:
            backend=self.backend();setattr(backend,field,value)
            with self.assertRaises(ValueError):self.build(backend)
            self.assertEqual(getattr(backend,field),value)
    def test_backend_cannot_spawn_a_replacement_backbone_even_without_API_calls(self):
        backend=self.backend();self.build(backend)
        with self.assertRaises(ValueError):self.build(backend)
        self.assertEqual(backend.calls,0)
    def test_second_owner_refusal_and_journal_failure_cannot_return_ready_object(self):
        calls=iter([None,False])
        with self.assertRaises(ValueError):self.build(guard=lambda:next(calls))
        self.assertEqual(self.rows,[])
        with self.assertRaises(ValueError):self.build(journal=lambda row:None)
    def test_public_record_never_serializes_unknown_backend_metadata(self):
        backend=self.backend();backend.identity['EXPLICIT_UNTRUSTED_EXTRA']='DO_NOT_COPY_EXTRA'
        self.build(backend);encoded=json.dumps(self.rows)
        self.assertNotIn('DO_NOT_COPY_EXTRA',encoded);self.assertNotIn('EXPLICIT_UNTRUSTED_EXTRA',encoded)
        self.assertEqual(self.rows[-1]['backend_constructor_or_generate_calls'],0)
        self.assertFalse(self.rows[-1]['physical_action_issued'])
    def test_ambient_original_module_and_constructor_source_drift_refuse(self):
        module=modules['ainav.planner']
        with patch.object(module,'__file__','/SOFTWARE/foreign/planner.py'):
            with self.assertRaises(ValueError):entry._original_types(SOURCE)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='EXPLICIT_ORIGINAL_BACKBONE_COMPOSITION_AND_NEW_BACKEND_METADATA_FIXTURE_NOT_REAL_AUTH_OR_NATIVE',checks=result.testsRun,failures=len(result.failures),errors=len(result.errors),forbidden_attempts=blocked,authenticated_backend_constructors_API_role_VLM_WM_Actor_physics_calls=0)))
    sys.exit(0 if result.wasSuccessful()and not blocked else 1)
