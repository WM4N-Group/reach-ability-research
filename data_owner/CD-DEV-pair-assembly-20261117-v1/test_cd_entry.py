"""New Data wiring/protocol fixtures only, NOT original backend/native qualification."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cd_entry as entry
import prepare_pair
HERE=Path(__file__).resolve().parent


class Tests(unittest.TestCase):
    def fixture(self):
        log=[];native=NS(step_count=0,sim=NS(data=NS(time=0.),queue=[]));writer=NS(steps=0,append_command=lambda *a:None,append_visual=lambda *a:None)
        backend=NS(calls=0,total_tokens=0);journal=lambda record: log.append(record)or'original-ref'
        class FactorJournal:
            def __init__(self,arm):self.policy={'arm':arm}
            def __call__(self,row):return journal(row)
        def assemble(**kw):
            log.append(('method',kw));roles=NS(calls=0,journal=kw['journal']);base=NS(calls=0,pending=None,journal=kw['journal'],roles=roles)
            return NS(journal=kw['journal'],baseline=base)
        class Driver:
            def __init__(self,components,**kw):
                log.append(('driver',kw));self.r=components['runtime'];self.arm=kw['arm'];self.planner=kw['planner'];self.journal=FactorJournal(self.arm);self.loop=self.executor=None;self.tick=0
                p=self.planner;p.journal=p.baseline.journal=p.baseline.roles.journal=self.journal
        factory=lambda **kw:Driver
        modules=dict(v4_native_asset=NS(SCENE_SHA256='scene',load_scene=lambda:{'task':'original'}),method_entry=NS(build_original_cd_method=assemble,_parts=lambda p:(p.baseline,p.baseline.roles)),live_driver=NS(driver_class=factory),factor_scope=NS(FactorJournal=FactorJournal,factors=lambda a:{'arm':a}))
        kw=dict(components={'runtime':native,'scene_sha256':'scene','scene':{'task':'original'}},arm='C',source_paths={},source_root='original',reach_source_root='reach',bundle='sdk',output_root='unused',writer=writer,journal=journal,guard=lambda:True,backend=backend,enabled=True)
        return kw,modules,log

    def test_default_off_no_sources_files_guards_or_imports(self):
        before=set(sys.modules)
        with patch.object(entry,'_verified_imports',side_effect=AssertionError):
            self.assertIsNone(entry.build_cd_driver('/DO_NOT_READ'))
        self.assertEqual(before,set(sys.modules))
        self.assertNotIn('torch',sys.modules);self.assertNotIn('mujoco',sys.modules)

    def test_C_original_factory_and_one_ledger_no_calls_or_steps(self):
        kw,mods,log=self.fixture()
        with patch.object(entry,'_verified_imports',return_value=mods):d=entry.build_cd_driver(**kw)
        self.assertEqual(d.arm,'C');self.assertEqual(d.r.step_count,0);self.assertEqual(kw['backend'].calls,0)
        self.assertEqual(len([r for r in log if isinstance(r,tuple)and r[0]=='method']),1)
        self.assertFalse(next(r for r in log if isinstance(r,dict))['new_successor_optimizer_enabled'])
        self.assertIs(d.journal,d.planner.baseline.roles.journal)

    def test_D_forwards_same_callable_without_evaluating(self):
        kw,mods,log=self.fixture();kw['arm']='D';cost=lambda *a,**k:(_ for _ in()).throw(AssertionError('no evaluation'))
        kw['shared_path_cost']=cost
        with patch.object(entry,'_verified_imports',return_value=mods):d=entry.build_cd_driver(**kw)
        sent=next(r[1]for r in log if isinstance(r,tuple)and r[0]=='method')
        self.assertIs(sent['shared_path_cost'],cost);self.assertFalse(sent['software_fixture']);self.assertEqual(d.r.step_count,0)

    def test_wrong_arm_or_missing_D_cost_or_C_treatment_refused(self):
        for arm,cost in [('E',None),('D',None),('C',lambda:None)]:
            kw,mods,log=self.fixture();kw.update(arm=arm,shared_path_cost=cost)
            with self.assertRaises(entry.AssemblyError):entry.build_cd_driver(**kw)
            self.assertEqual(log,[])

    def test_nonzero_runtime_or_queue_or_writer_refused(self):
        for attr in ['step','time','queue','writer']:
            kw,mods,log=self.fixture();r=kw['components']['runtime']
            if attr=='step':r.step_count=1
            if attr=='time':r.sim.data.time=.005
            if attr=='queue':r.sim.queue.append('old')
            if attr=='writer':kw['writer'].steps=1
            with self.assertRaises(entry.AssemblyError):entry.build_cd_driver(**kw)
            self.assertEqual(log,[])

    def test_fixture_cost_refused_before_any_original_factory(self):
        kw,mods,log=self.fixture();cost=lambda:None;cost.software_fixture=True;kw.update(arm='D',shared_path_cost=cost)
        with self.assertRaises(entry.AssemblyError):entry.build_cd_driver(**kw)
        self.assertEqual(log,[])

    def test_easier_scene_refused_not_silently_changed(self):
        kw,mods,log=self.fixture();kw['components']['scene']={'task':'easier'}
        with patch.object(entry,'_verified_imports',return_value=mods),self.assertRaises(entry.AssemblyError):entry.build_cd_driver(**kw)
        self.assertEqual(log,[])

    def test_missing_shared_ledger_binding_refused(self):
        kw,mods,log=self.fixture();old=mods['method_entry']._parts
        mods['method_entry']._parts=lambda p:(p.baseline,NS(journal=object()))
        with patch.object(entry,'_verified_imports',return_value=mods),self.assertRaises(entry.AssemblyError):entry.build_cd_driver(**kw)

    def test_factory_error_propagates_no_retry_or_substitute(self):
        kw,mods,log=self.fixture();calls=[]
        def fail(**k):calls.append(k);raise RuntimeError('original failure')
        mods['method_entry'].build_original_cd_method=fail
        with patch.object(entry,'_verified_imports',return_value=mods),self.assertRaisesRegex(RuntimeError,'original failure'):entry.build_cd_driver(**kw)
        self.assertEqual(len(calls),1);self.assertEqual(kw['components']['runtime'].step_count,0)

    def test_final_owner_revocation_refused(self):
        kw,mods,log=self.fixture();answers=iter([True,False]);kw['guard']=lambda:next(answers)
        with patch.object(entry,'_verified_imports',return_value=mods),self.assertRaises(entry.AssemblyError):entry.build_cd_driver(**kw)

    def test_all_sources_checked_before_any_import(self):
        paths={k:'/DO_NOT_READ/'+k for k in entry.SOURCE_PINS}
        with patch.object(entry.importlib,'import_module',side_effect=AssertionError)as imported,self.assertRaises(entry.AssemblyError):entry._verified_imports(paths)
        imported.assert_not_called()

    def test_ambient_resolution_refused_before_execution(self):
        with tempfile.TemporaryDirectory()as td:
            p=Path(td)/'one.py';p.write_text('raise AssertionError("never execute")\n');pin=hashlib.sha256(p.read_bytes()).hexdigest()
            with patch.object(entry,'SOURCE_PINS',{'one':pin}),patch.object(entry.importlib.util,'find_spec',return_value=NS(origin='/foreign/one.py')),patch.object(entry.importlib,'import_module')as imported,self.assertRaises(entry.AssemblyError):entry._verified_imports({'one':str(p)})
            imported.assert_not_called()

    def test_no_native_step_API_backend_constructor_or_dispatch_source(self):
        tree=ast.parse((HERE/'cd_entry.py').read_text());names=[ast.unparse(n.func)for n in ast.walk(tree)if isinstance(n,ast.Call)]
        self.assertFalse(any(n.endswith(('.step','.step_one','.generate','.Popen'))or n in ('Runtime','MjData','create_vision_backend')for n in names))
        self.assertIn('method.build_original_cd_method',names);self.assertIn("modules['live_driver'].driver_class",names)

    def protocol(self):return json.loads((HERE/'CD_DEV_PROTOCOL_DRAFT.json').read_text())
    def test_preview_two_arm_configs_same_common_no_dispatch(self):
        r=prepare_pair.preview(self.protocol(),enabled=True)
        self.assertFalse(r['dispatchable']);self.assertEqual(r['original_driver_or_method_factory_calls'],0)
        self.assertEqual(r['arm_config_preview']['C']['common'],r['arm_config_preview']['D']['common']);self.assertEqual(len(r['blockers']),4)

    def test_arm_nested_config_is_not_shared_mutable_state(self):
        r=prepare_pair.preview(self.protocol(),enabled=True)
        c=r['arm_config_preview']['C']['common'];d=r['arm_config_preview']['D']['common']
        d['original_constructor_profile']['backend_caps']['max_calls']=1
        self.assertEqual(c['original_constructor_profile']['backend_caps']['max_calls'],100)

    def test_protocol_unfairness_retry_or_fake_pair_refused(self):
        for mutate in [lambda p:p['fairness'].update(same_backend_profile_and_caps=False),lambda p:p.update(automatic_retry=True),lambda p:p['fairness'].update(private_state_pair_claimed=True),lambda p:p['optimizer_evidence'].update(all_UNKNOWN_fallback_is_M1_complete=True),lambda p:p.update(execution_enabled=True)]:
            p=self.protocol();mutate(p)
            with self.assertRaises(prepare_pair.ProtocolError):prepare_pair.preview(p,enabled=True)

    def test_protocol_default_off_and_undeclared_task_refused(self):
        self.assertIsNone(prepare_pair.preview(None));p=self.protocol();p['common']['supported_DEV_task_and_initialization']={'invented':'scope'}
        with self.assertRaises(prepare_pair.ProtocolError):prepare_pair.preview(p,enabled=True)


if __name__=='__main__':unittest.main(verbosity=2)
