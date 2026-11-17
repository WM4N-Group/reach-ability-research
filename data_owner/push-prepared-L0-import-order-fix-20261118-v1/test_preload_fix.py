"""Three NEW targeted import-order SOFTWARE regressions; no old complete suite."""
from pathlib import Path
from types import SimpleNamespace as NS
import ast,hashlib,importlib.util,json,resource,sys,tempfile,time,types,unittest,textwrap
START=time.perf_counter();HERE=Path(__file__).resolve().parent
FAILED,BUILDER=map(Path,sys.argv[1:3]);sys.argv[1:]=[]
spec=importlib.util.spec_from_file_location('_prospective_preload_fix',HERE/'worker_preload_fix.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
raw=FAILED.read_bytes();changed,proof=m.derive(raw,enabled=True)
oldtree,newtree=ast.parse(raw),ast.parse(changed)

def gate(tree):
 fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='run')
 return next(n for n in fn.body if isinstance(n,ast.For)and isinstance(n.iter,ast.Tuple)and
             any(isinstance(x,ast.Constant)and x.value=='registered_arm_ff'for x in n.iter.elts))

def isolated_gate(tree,present):
 """Execute exact original helper-gate AST on explicit fake module table/files.

 Does NOT call worker.run/prepare, import native modules, touch H or claim a lease.
 """
 g=gate(tree)
 with tempfile.TemporaryDirectory(prefix='data-preload-CPU-only-')as d:
    d=Path(d);modules={};files={}
    for x in g.iter.elts:
        if x.value=='registered_arm_ff' and not present:continue
        p=d/(x.value+'.py');p.write_text('# explicit software helper-file fixture\n')
        modules[x.value]=NS(__file__=str(p));files[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    def need(ok,msg):
        if not ok:raise ValueError(msg)
    ns=dict(Path=Path,sys=NS(modules=modules),freeze=dict(files=files),
            sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest(),need=need)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[g],type_ignores=[])),'[exact helper gate fixture]','exec'),ns)

class Checks(unittest.TestCase):
    def test_01_exact_old_KeyError_reproduced_then_same_gate_passes_after_early_import(self):
        with self.assertRaises(KeyError)as got:isolated_gate(oldtree,False)
        self.assertEqual(got.exception.args,('registered_arm_ff',))
        self.assertEqual(ast.dump(gate(oldtree),include_attributes=False),ast.dump(gate(newtree),include_attributes=False))
        # The new source imports the real pinned stdlib-only builder at top level.
        n=next(n for n in newtree.body if isinstance(n,ast.Import)and n.names[0].name=='registered_arm_ff')
        self.assertLess(n.lineno,next(n for n in newtree.body if isinstance(n,ast.FunctionDef)and n.name=='prepare').lineno)
        spec=importlib.util.spec_from_file_location('_real_source_only_arm_ff',BUILDER)
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        self.assertIsNone(builder.prepare(enabled=False))
        isolated_gate(newtree,True)

    def test_02_CPU_prepare_new_presence_pin_assertion_rejects_unknown_or_changed_helper(self):
        inserted=ast.parse(textwrap.dedent(m.PREPARE_PROOF)).body
        with tempfile.TemporaryDirectory(prefix='data-preload-pin-CPU-')as d:
            p=Path(d)/'registered_arm_ff.py';p.write_bytes(BUILDER.read_bytes())
            def need(ok,msg):
                if not ok:raise ValueError(msg)
            ns=dict(Path=Path,registered_arm_ff=NS(__file__=str(p)),need=need,
                    sha=lambda x:hashlib.sha256(Path(x).read_bytes()).hexdigest(),freeze=dict(files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()}))
            c=compile(ast.Module(body=inserted,type_ignores=[]),'[only new CPU prepare helper assertion]','exec')
            exec(c,ns)
            p.write_bytes(p.read_bytes()+b'\n# changed fixture\n')
            with self.assertRaises(ValueError):exec(c,ns)
            ns['freeze']['files']={}
            with self.assertRaises(ValueError):exec(c,ns)

    def test_03_exact_inverse_disabled_tamper_and_no_native_or_frozen_write(self):
        self.assertIsNone(m.derive(enabled=False));self.assertTrue(proof['inverse_restores_original'])
        with self.assertRaises(ValueError):m.derive(raw+b'\n',enabled=True)
        self.assertEqual(hashlib.sha256(FAILED.read_bytes()).hexdigest(),m.FAILED_WORKER_SHA256)
        self.assertFalse(proof['physics_FF_or_safety_or_success_or_budget_changes'])
        self.assertFalse(any(k=='mujoco' or k.startswith(('mujoco.','torch'))for k in sys.modules))

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    print(json.dumps(dict(stage='EARLY_HELPER_PRELOAD_PROSPECTIVE_SOURCE_CPU_ONLY',tests=result.testsRun,
        passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),
        wall_s=time.perf_counter()-START,maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        no_actual_worker_run_prepare_native_or_frozen_write=True,source_proof=proof),indent=2))
    raise SystemExit(0 if result.wasSuccessful()else 1)
