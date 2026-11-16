"""Pure metadata/identity fixtures. NO native imports/world/Actor/lease validity."""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import ast,hashlib,json,os,sys,tempfile,types,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1];sys.path.insert(0,str(OWN))
import indexed_guard as mod
from indexed_guard import FrozenFiles,IndexedIdentityGuard,AuditPolicy,OwnerStamp,GuardViolation,make_indexed_guard
ORIGINAL=ROOT/'development/complex_dual_route_v1/scene_driver.py'
blocked=[]
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
  blocked.append(str(args[0]));raise RuntimeError('No native/model imports in identity fixtures')
 if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
  blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)

def original_for(registry):
 text=ORIGINAL.read_text();cls=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef)and n.name=='ComplexSceneDriver')
 node=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='_native_guards')
 ns=dict(Path=Path,sys=registry,need=mod.need);exec(compile(ast.Module(body=[node],type_ignores=[]),str(ORIGINAL),'exec'),ns)
 return ns['_native_guards']

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.owned=self.root/'owned.py';self.other=self.root/'other.py';self.later=self.root/'later.py'
  for p in (self.owned,self.other,self.later):p.write_text('# explicit metadata fixture\n')
  def cb():return 'software only'
  self.cb=cb;self.modules={'owned':NS(__file__=str(self.owned),CB=cb),'other':NS(__file__=str(self.other))};self.registry=NS(modules=self.modules)
  self.now=100.;self.checked=100.;self.valid=True;self.epoch='EXPLICIT_FAKE_OWNER';self.full_calls=0;self.refresh_calls=0
  p=NS(model=object(),data=NS(time=0.),queue=[],controller=object(),box_push_target=object())
  self.host=NS(r=NS(sim=p,step_count=0),owner_guard=self.full,_stow_allowed={self.owned},
      _stow_installed={str(self.owned):cb},_stow_callback_name='CB')
  self.host._world=(p,p.model,p.data,p.queue,p.controller,p.box_push_target)
  self.values=dict(session=None,target=None,goal='FIXTURE_GOAL',config_epoch='FIXTURE_CONFIG')
  self.original=original_for(self.registry);self.g=self.new_guard();self.addCleanup(self.g.close)
 def full(self):self.full_calls+=1
 def refresh(self,host):self.checked=self.now;self.refresh_calls+=1
 def owner(self,host):return OwnerStamp(self.epoch,self.checked,self.checked+2.,self.valid)
 def inventory(self,extra=()):return FrozenFiles.measure([self.owned,self.other,self.later,ORIGINAL,*extra],roots=[self.root,ROOT])
 def new_guard(self,files=None):
  return IndexedIdentityGuard(self.original,files=self.inventory()if files is None else files,
   owner_fast=self.owner,owner_refresh=self.refresh,tokens=lambda _:dict(self.values),
   policy=AuditPolicy(module_poll_s=.1,metadata_poll_s=.5,canonical_poll_s=1.,audit_budget_s=1.),clock=lambda:self.now)
 def seal(self):return self.g.seal(self.host)
 def advance(self,t):self.now+=t;self.refresh(self.host)
 def test_default_off_no_hook_or_world(self):
  self.assertIsNone(make_indexed_guard())
  with self.assertRaises(GuardViolation):make_indexed_guard(enabled=1)
 def test_snapshot_declares_no_readonly_enforcement_or_external_authenticity(self):
  self.assertFalse(self.g.files.record['readonly_enforcement_proven']);self.assertEqual(len(self.g.files.sha256),64)
 def test_hot_calls_no_resolve_stat_hash_or_full_original(self):
  self.seal();before=dict(self.g.metrics);calls=self.full_calls
  def forbidden(*a,**k):raise AssertionError('Filesystem reached from non-due hot check')
  with patch.object(Path,'resolve',forbidden),patch.object(mod.os,'stat',forbidden),patch.object(mod,'_hash_file',forbidden):
   for _ in range(100):self.g.before_issue(self.host)
  self.assertEqual(self.full_calls,calls);self.assertEqual(self.g.metrics['canonical_resolves'],before['canonical_resolves'])
  self.assertEqual(self.g.metrics['stat_calls'],before['stat_calls']);self.assertEqual(self.g.metrics['module_audits'],5)
 def test_foreign_runtime_even_same_sim_refused(self):
  self.seal();self.host.r=NS(sim=self.host.r.sim,step_count=0)
  with self.assertRaises(GuardViolation):self.g.before_issue(self.host)
 def test_foreign_queue_and_forged_host_world_refused(self):
  self.seal();p=self.host.r.sim;p.queue=[];self.host._world=(p,p.model,p.data,p.queue,p.controller,p.box_push_target)
  with self.assertRaises(GuardViolation):self.g.check(self.host)
 def test_new_host_same_runtime_refused(self):
  self.seal();other=NS(**vars(self.host))
  with self.assertRaises(GuardViolation):self.g.check(other)
 def test_session_target_goal_config_each_immediate(self):
  self.seal();self.values['goal']='CHANGED'
  with self.assertRaises(GuardViolation):self.g.before_issue(self.host)
 def test_owner_revocation_immediate(self):
  self.seal();self.valid=False
  with self.assertRaises(GuardViolation):self.g.before_issue(self.host)
 def test_owner_epoch_change_refused(self):
  self.seal();self.epoch='FOREIGN'
  with self.assertRaises(GuardViolation):self.g.before_issue(self.host)
 def test_owner_expiry_never_accepted_as_true(self):
  self.seal();self.now+=2.01
  with self.assertRaises(GuardViolation):self.g.check(self.host)
 def test_bool_instead_of_owner_stamp_refused(self):
  self.seal();self.g.owner_fast=lambda _:True
  with self.assertRaises(GuardViolation):self.g.check(self.host)
 def test_critical_callback_replacement_immediate(self):
  self.seal();self.modules['owned'].CB=object()
  with self.assertRaises(GuardViolation):self.g.before_issue(self.host)
 def test_same_callback_different_code_audit_denied(self):
  other=(lambda:'changed').__code__;self.seal()
  with self.assertRaises(GuardViolation):self.cb.__code__=other
  self.assertEqual(self.g.state,'FAILED')
 def test_critical_module_replacement_same_len_immediate(self):
  self.seal();self.modules['owned']=NS(__file__=str(self.owned),CB=self.cb)
  with self.assertRaises(GuardViolation):self.g.before_issue(self.host)
 def test_module_registry_dict_replacement_refused(self):
  self.seal();self.registry.modules=dict(self.modules)
  with self.assertRaises(GuardViolation):self.g.check(self.host)
 def test_new_module_direct_assignment_refused_next_check(self):
  self.seal();self.modules['new']=NS(__file__=str(self.other))
  with self.assertRaises(GuardViolation):self.g.before_issue(self.host)
 def test_same_size_noncritical_alias_has_declared_bounded_latency(self):
  self.seal();self.modules['other']=NS(__file__=str(self.owned),CB=object())
  self.g.check(self.host)  # Deliberate new policy, NOT old immediate equivalence.
  self.advance(.11)
  with self.assertRaises(GuardViolation):self.g.before_issue(self.host)
 def test_module_file_attribute_change_on_periodic_metadata_poll(self):
  self.seal();self.modules['other'].__file__=str(self.later);self.advance(.11)
  with self.assertRaises(GuardViolation):self.g.check(self.host)
 def test_file_replace_persistent_detected_by_metadata(self):
  self.seal();new=self.root/'new';new.write_text('# replacement\n');new.replace(self.other);self.advance(.51)
  with self.assertRaises(GuardViolation):self.g.before_issue(self.host)
 def test_inplace_same_size_restore_mtime_still_ctime_detected(self):
  self.seal();s=self.other.stat();raw=self.other.read_bytes();self.other.write_bytes(b'X'*len(raw));os.utime(self.other,ns=(s.st_atime_ns,s.st_mtime_ns));self.advance(.51)
  with self.assertRaises(GuardViolation):self.g.check(self.host)
 def test_symlink_retarget_metadata_tier(self):
  link=self.root/'link.py';link.symlink_to(self.other);self.modules['other'].__file__=str(link)
  self.g.close();self.g=self.new_guard(self.inventory([link]));self.addCleanup(self.g.close);self.seal()
  link.unlink();link.symlink_to(self.owned);self.g.check(self.host);self.advance(.51)
  with self.assertRaises(GuardViolation):self.g.check(self.host)
 def test_same_inode_parent_symlink_alias_needs_canonical_tier(self):
  a=self.root/'directory';a.mkdir();(a/'owned.py').hardlink_to(self.owned)
  link=self.root/'parent';link.symlink_to(a,target_is_directory=True);raw=link/'owned.py';self.modules['other'].__file__=str(raw)
  self.g.close();self.g=self.new_guard(self.inventory([raw]));self.addCleanup(self.g.close);self.seal()
  link.unlink();link.symlink_to(self.root,target_is_directory=True);self.advance(.51);self.g.check(self.host)
  self.advance(.51)
  with self.assertRaisesRegex(GuardViolation,'Canonical alias'):self.g.check(self.host)
 def test_read_failure_not_suppressed(self):
  self.seal();self.advance(.51)
  with patch.object(mod.os,'scandir',side_effect=PermissionError('fixture')):
   with self.assertRaises(PermissionError):self.g.check(self.host)
  self.assertEqual(self.g.state,'FAILED')
 def test_explicit_boundary_add_known_module_updates_tokens_no_step(self):
  self.seal()
  with self.g.boundary(self.host,'fixture-selected-constructor'):
   self.modules['later']=NS(__file__=str(self.later));self.values['session']=object();self.values['target']=object();self.values['goal']='NEW_BOUND_GOAL'
  self.g.before_issue(self.host);self.assertEqual(self.g.metrics['boundaries'],2)
 def test_new_alias_same_original_callback_allowed_only_boundary(self):
  self.seal()
  with self.g.boundary(self.host,'fixture-new-valid-source-alias'):
   self.modules['alias']=NS(__file__=str(self.owned),CB=self.cb)
  self.g.before_issue(self.host);self.assertEqual(len(self.g.critical),2)
 def test_unbound_new_alias_refused_at_boundary(self):
  self.seal()
  with self.assertRaises(GuardViolation):
   with self.g.boundary(self.host,'bad-alias'):self.modules['alias']=NS(__file__=str(self.owned),CB=object())
 def test_unpinned_file_refused_even_inside_authorized_root(self):
  self.seal();unknown=self.root/'unapproved.py';unknown.write_text('# unpinned\n')
  with self.assertRaises(GuardViolation):
   with self.g.boundary(self.host,'not-approved-file'):self.modules['new']=NS(__file__=str(unknown))
 def test_physical_issue_refused_while_paused(self):
  self.seal()
  with self.assertRaises(GuardViolation):
   with self.g.boundary(self.host,'no-physics'):self.g.before_issue(self.host)
  self.assertEqual(self.host.r.step_count,0)
 def test_boundary_bypassed_step_detected_not_rolled_back(self):
  self.seal()
  with self.assertRaises(GuardViolation):
   with self.g.boundary(self.host,'unsafe-caller'):self.host.r.step_count+=1
  self.assertEqual(self.host.r.step_count,1)  # No fake rollback; installer prevents ordinary path.
 def test_nested_metadata_boundary_one_outer_reseal(self):
  self.seal()
  with self.g.boundary(self.host,'outer'):
   with self.g.boundary(self.host,'inner'):self.values['goal']='NEXT'
  self.assertEqual(self.g.metrics['boundaries'],2)
 def test_unplanned_exec_denied_before_effect(self):
  code=compile('executed=True','<fixture-unplanned-code>','exec');scope={};self.seal()
  with self.assertRaises(GuardViolation):exec(code,scope)
  self.assertNotIn('executed',scope);self.assertEqual(self.g.state,'FAILED')
 def test_unplanned_import_event_denied(self):
  self.seal()
  with self.assertRaises(GuardViolation):sys.audit('import','EXPLICIT_FAKE_IMPORT',None,[],[],[])
 def test_exec_only_inside_explicit_boundary(self):
  code=compile('value=1','<fixture-planned-code>','exec');self.seal();scope={}
  with self.g.boundary(self.host,'planned-fixture-code'):exec(code,scope)
  self.assertEqual(scope['value'],1);self.g.check(self.host)
 def test_fail_cannot_resume_or_return_true(self):
  self.seal();self.valid=False
  with self.assertRaises(GuardViolation):self.g.check(self.host)
  self.valid=True
  with self.assertRaises(GuardViolation):self.g.seal(self.host)
  with self.assertRaises(GuardViolation):self.g.check(self.host)
 def test_closed_cannot_issue(self):
  self.seal();self.g.close()
  with self.assertRaises(GuardViolation):self.g.before_issue(self.host)
 def test_inventory_expected_hash_and_root_reject(self):
  with self.assertRaises(GuardViolation):FrozenFiles.measure([self.owned],roots=[self.root],expected_hashes={str(self.owned):'0'*64})
  with self.assertRaises(GuardViolation):FrozenFiles.measure([ORIGINAL],roots=[self.root])
 def test_missing_module_explicit_and_appearance_detected(self):
  missing=self.root/'missing.py';self.modules['missing']=NS(__file__=str(missing))
  inv=FrozenFiles.measure([self.owned,self.other,self.later,ORIGINAL,missing],roots=[self.root,ROOT],allow_missing=[missing])
  self.g.close();self.g=self.new_guard(inv);self.addCleanup(self.g.close);self.seal();missing.write_text('# appeared\n');self.advance(.51)
  with self.assertRaises(GuardViolation):self.g.check(self.host)
 def test_nonliteral_file_rejected_not_silently_omitted(self):
  self.modules['other'].__file__=self.other
  with self.assertRaises(GuardViolation):self.seal()
 def test_policy_upper_bounds_not_silently_widened(self):
  for kwargs in ({'module_poll_calls':21},{'metadata_poll_s':6},{'canonical_poll_s':61},{'owner_max_age_s':3},{'audit_budget_s':0}):
   with self.assertRaises(GuardViolation):AuditPolicy(**kwargs)

 def test_audit_deadline_failure_blocks_next_issue(self):
  self.seal();self.advance(1.01);original=self.g._canonical_check
  def slow():
   original();self.now+=1.01
  with patch.object(self.g,'_canonical_check',slow):
   with self.assertRaisesRegex(GuardViolation,'deadline'):self.g.before_issue(self.host)
  self.assertEqual(self.g.state,'FAILED')
 def test_file_inventory_drift_before_seal_rejected(self):
  self.other.write_text('# changed after inventory measurement\n')
  with self.assertRaises(GuardViolation):self.seal()
 def test_callback_install_map_changed_even_boundary_refused(self):
  self.seal()
  with self.assertRaises(GuardViolation):
   with self.g.boundary(self.host,'not-arbitrary-method-install'):
    self.host._stow_installed[str(self.owned)]=object()

 def test_periodic_metadata_uses_fresh_directory_entries_not_retained_stats(self):
  self.seal();self.advance(.51)
  real=mod.os.scandir
  with patch.object(mod.os,'scandir',wraps=real)as scan:self.g.check(self.host)
  self.assertGreater(scan.call_count,0)
  self.other.write_text('# fresh modification after successful audit\n');self.advance(.51)
  with self.assertRaises(GuardViolation):self.g.check(self.host)

 def test_conflicting_expected_hash_for_same_canonical_alias_refused(self):
  link=self.root/'alias.py';link.symlink_to(self.owned);correct=hashlib.sha256(self.owned.read_bytes()).hexdigest()
  with self.assertRaises(GuardViolation):
   FrozenFiles.measure([self.owned,link],roots=[self.root],expected_hashes={str(self.owned):correct,str(link):'0'*64})
 def test_expected_existing_hash_cannot_be_declared_missing(self):
  missing=self.root/'required.py'
  with self.assertRaises(GuardViolation):
   FrozenFiles.measure([missing],roots=[self.root],allow_missing=[missing],expected_hashes={str(missing):'0'*64})
 def test_extra_asset_raw_alias_canonical_mapping_is_monitored(self):
  asset=self.root/'asset.bin';asset.write_bytes(b'EXPLICIT NONMODEL FIXTURE')
  folder=self.root/'asset-folder';folder.mkdir();(folder/'asset.bin').hardlink_to(asset)
  link=self.root/'asset-parent';link.symlink_to(folder,target_is_directory=True);raw=link/'asset.bin'
  self.g.close();self.g=self.new_guard(self.inventory([asset,raw]));self.addCleanup(self.g.close);self.seal()
  link.unlink();link.symlink_to(self.root,target_is_directory=True);self.advance(.51);self.g.check(self.host)
  self.advance(.51)
  with self.assertRaisesRegex(GuardViolation,'Canonical alias'):self.g.check(self.host)

if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 print(json.dumps(dict(role='REVISED_AUDIT_DETECTION_POLICY_SOFTWARE_NOT_NATIVE_QUALIFICATION',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,native_world_Actor_GPU_API_calls=0)))
 sys.exit(0 if r.wasSuccessful()and not blocked else 1)
