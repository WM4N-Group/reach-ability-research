"""Two NEW CPU source fixtures for actual-run helper closure, no old test suite."""
from pathlib import Path
from types import SimpleNamespace as NS
import ast,builtins,hashlib,json,resource,sys,tempfile,time,unittest
START=time.perf_counter();HERE=Path(__file__).resolve().parent
tree=ast.parse((HERE/'worker.py').read_bytes())
names=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='HELPER_NAMES'for t in n.targets)))
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='_preload_and_verify_execution_helpers')
run=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='run')
gate=next(n for n in run.body if isinstance(n,ast.For)and isinstance(n.iter,ast.Tuple)and any(isinstance(x,ast.Constant)and x.value=='registered_arm_ff'for x in n.iter.elts))
assert names==ast.literal_eval(gate.iter)

def fixture(mode=None):
 d=tempfile.TemporaryDirectory(prefix='data-helper-closure-CPU-');root=Path(d.name)
 mods={};files={};calls=[]
 for name in names:
  p=root/(name+'.py');p.write_text('# explicit SOFTWARE helper fixture\n')
  mods[name]=NS(__file__=str(p));files[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 def importer(name):
  calls.append(name)
  if mode=='missing'and name=='registered_arm_ff':raise ModuleNotFoundError(name)
 def import_hook(name,*args,**kwargs):
  if name=='importlib':return NS(import_module=importer)
  return builtins.__import__(name,*args,**kwargs)
 def need(ok,msg):
  if not ok:raise ValueError(msg)
 env=dict(Path=Path,sys=NS(modules=mods),HELPER_NAMES=names,need=need,
  sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest(),__builtins__=dict(vars(builtins),__import__=import_hook))
 exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'[source-only all-helper CPU fixture]','exec'),env)
 if mode=='changed':Path(mods['registered_arm_ff'].__file__).write_text('# changed fixture\n')
 return d,env,files,calls

class Checks(unittest.TestCase):
 def test_01_exact_original_run_set_ALL_present_and_imported_before_gate(self):
  d,env,files,calls=fixture()
  try:
   got=env['_preload_and_verify_execution_helpers'](dict(files=files))
   self.assertEqual(tuple(n for n,p in got),names);self.assertEqual(tuple(calls),names)
   self.assertIn('registered_arm_ff',names)
   prepare=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='prepare')
   preload_calls=[n for n in ast.walk(prepare)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='_preload_and_verify_execution_helpers']
   self.assertEqual(len(preload_calls),1)
   scan_import=next(n for n in prepare.body if isinstance(n,ast.ImportFrom)and n.module=='indexed_guard')
   self.assertLess(preload_calls[0].lineno,scan_import.lineno)
  finally:d.cleanup()
 def test_02_missing_or_changed_helper_fails_CPU_BEFORE_native_phase(self):
  for mode,exception in [('missing',ModuleNotFoundError),('changed',ValueError)]:
   d,env,files,calls=fixture(mode)
   try:
    with self.assertRaises(exception):env['_preload_and_verify_execution_helpers'](dict(files=files))
   finally:d.cleanup()

if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
 assert not any(k=='mujoco' or k.startswith(('mujoco.','torch'))for k in sys.modules)
 print(json.dumps(dict(stage='NEW_ALL_RUN_HELPER_CLOSURE_CPU_FIXTURES_ONLY',tests=r.testsRun,passed=r.wasSuccessful(),
  wall_s=time.perf_counter()-START,maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
  helper_count=len(names),native_world_Actor_GPU_lease_or_actual_prepare=False,old_suites_not_rerun=True),indent=2))
 raise SystemExit(0 if r.wasSuccessful()else 1)
