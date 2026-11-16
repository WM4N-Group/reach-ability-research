"""Exact original constructor entry seam, default-off/guard fixtures, not zero."""
from pathlib import Path
import sys,json,unittest,hashlib
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1];SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source';sys.path[:0]=[str(OWN),str(SOURCE)];blocked=[]
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):blocked.append(str(args[0]));raise RuntimeError('Software only')
 if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import native_entry as entry
import v4_native_asset as v4
class Tests(unittest.TestCase):
 def test_disabled_never_loads_native_or_needs_resource_arguments(self):
  self.assertIsNone(entry.compile_static_asset());self.assertIsNone(entry.construct_cold_components());self.assertFalse(blocked)
 def test_guard_missing_or_raises_before_any_native_import(self):
  for f in [entry.compile_static_asset,entry.construct_cold_components]:
   with self.assertRaises(ValueError):f(enabled=True)
   def owner_guard():raise PermissionError('SOFTWARE owner refusal')
   with self.assertRaises(PermissionError):f(enabled=True,guard=owner_guard,**({'journal':lambda row:'SOFTWARE-only'}if f is entry.construct_cold_components else{}))
  self.assertFalse(blocked)
 def test_original_function_bytecode_preserved_with_only_three_callback_deltas(self):
  base,_=entry._exact_base();before={n:hashlib.sha256((entry.BASE_DIR/n).read_bytes()).hexdigest()for n in entry.SOURCE_PINS}
  for name in ['compile_static_asset','construct_cold_components']:
   old=getattr(base,name);new=entry._bound_original(name)
   self.assertEqual(old.__code__.co_code,new.__code__.co_code);self.assertEqual(old.__code__.co_consts,new.__code__.co_consts);self.assertEqual(old.__kwdefaults__,new.__kwdefaults__)
   self.assertIs(new.__globals__['load_scene'],v4.load_scene);self.assertIs(new.__globals__['registry'],entry._v4_registry);self.assertIs(new.__globals__['construct_into_native_spec'],entry._v4_construct)
   self.assertIsNot(old.__globals__['load_scene'],new.__globals__['load_scene'])
  self.assertEqual(before,{n:hashlib.sha256((entry.BASE_DIR/n).read_bytes()).hexdigest()for n in entry.SOURCE_PINS})
 def test_actual_frozen_pure_registry_is_elevated_and_three_objects(self):
  r=entry._v4_registry(v4.load_scene(),source_root=SOURCE);self.assertEqual(r.goal.surface_ref,'goal_deck');self.assertEqual(r.surfaces['goal_deck'].top_z_m,.6);self.assertEqual(len(r.objects),3)
 def test_scene_default_is_own_exact_confirmed_V4_not_old_v2(self):
  f=entry._bound_original('compile_static_asset');self.assertEqual(Path(f.__globals__['__file__']).parent,OWN);self.assertEqual(f.__globals__['load_scene']()['scene_id'],'staggered-corridor-push-climb-v4-review')
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));print(json.dumps(dict(role='V4_ORIGINAL_NATIVE_ENTRY_SOFTWARE_SEAMS_NOT_ACTUAL_NATIVE_COMPILE_OR_ZERO',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,Runtime_Actor_MuJoCo_or_API_calls=0)));sys.exit(0 if r.wasSuccessful()and not blocked else 1)
