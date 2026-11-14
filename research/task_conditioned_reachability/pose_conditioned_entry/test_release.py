"""All authorization/scheduling fixtures are SYNTHETIC temp directories.

No App, actor, real experiment budget, source-state FK or real ledger mutation.
"""
import ast,copy,hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from build_release import build
from release_authority import (approval,exclusive,family_snapshot,load,locked,make_permit,
    phase_directory,reserve_physical,save,sha,verify_source)
from release_supervisor import dispatch
from evaluate_pose_pilot import classify,summarize


def sdk_result(source):
    return dict(passed=True,manifest_sha256=sha(source/'manifest.json'),envs=0,actor_loads=0,physics_steps=0,
        actual_native_definitions_executed=True,actual_main_CFG_prefix_executed=True,common_actual_verifier_matches_original=True,
        completed_role_checks=[dict(arm=arm,role=role,state_restored=True) for arm in ['P0','P1','P2','P3'] for role in ['planning','final_actual']])


def fake_geometry(out):
    q=dict(event='finite_tip_query',query_id='SYNTHETIC-final-query',evaluation_role='final_actual',criterion='COMMON_original_full_cloud_fixed_yz',
        step=1,nominal_translation_w=None,forecast_margin_m=0,tip_cloud_box_m=[[0,0,0]]*2624)
    guard=dict(event='source_hand_FK_guard',query_id=q['query_id'],evaluation_role='final_actual',passed=True,step=1)
    (out/'entry_geometry.jsonl').write_text(json.dumps(q)+'\n'+json.dumps(guard)+'\n')


def refusal(item):
    return dict(seed=item['seed'],study_arm=item['arm'],study_global_goal_se2=[-.25,0.,0.],physical_resets_after_initial=0,
        physics_samples=1,outcome='entry_final_preview_refused',
        measured_final_support_verification=dict(shift_m=.01,box_approach_preview=dict(evaluation_role='final_actual',criterion='COMMON_original_full_cloud_fixed_yz',query_id='SYNTHETIC-final-query')),
        entry_final_preview_refusal=dict(step=1,time_s=.02,required_shift_m=.01,criterion='COMMON_original_full_cloud_fixed_yz',physics_advanced=False,command_issued=False),control_events=[])


def success(item):
    r=refusal(item);r['outcome']='nav_push_stow_nav_target_stable';r.pop('entry_final_preview_refusal')
    r['measured_final_support_verification']['shift_m']=0
    r['control_events']=[dict(event='return_nav_requested_after_stowed_ready',goal=[-.25,0,.28])]
    r['return_nav_final_state']=dict(root_position=[-.25,0,.28],root_quaternion=[1,0,0,0],return_nav_stable_seconds=.5,retracted_ready=True,exit_stable_gates=dict(synthetic_gate=True))
    return r


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.root=self.base/'release';self.family=self.base/'original-family';self.family.mkdir()
        self.old=dict(starts=2,active=None,not_run=[dict(synthetic_old_cell=i) for i in range(14)],status='STOPPED_SYNTHETIC')
        save(self.family/'physical_ledger.json',self.old);save(self.family/'approval.json',dict(budgets=dict(max_new_Isaac_starts=16)))
        self.old_bytes=(self.family/'physical_ledger.json').read_bytes();build(self.root,self.root)
        self.protocol=load(self.root/'source/protocol.json');self.protocol.update(original_family_root=str(self.family),old_physical_ledger_sha256=sha(self.family/'physical_ledger.json'))
        self.remanifest()
    def tearDown(self):
        self.assertEqual((self.family/'physical_ledger.json').read_bytes(),self.old_bytes);self.temp.cleanup()
    def remanifest(self):
        save(self.root/'source/protocol.json',self.protocol)
        manifest=load(self.root/'source/manifest.json')
        manifest['files']={n:sha(self.root/'source'/n) for n in manifest['files']}
        save(self.root/'source/manifest.json',manifest)
    def auth(self):
        a=load(self.root/'execution-request-NOT-APPROVED.json');a.update(approved=True,release_root=str(self.root),source_manifest_sha256=sha(self.root/'source/manifest.json'),source_protocol_sha256=sha(self.root/'source/protocol.json'))
        exclusive(self.root/'approval.json',a);return a
    def gate(self):
        h=sha(self.root/'source/manifest.json');save(self.root/'sdk_result.json',sdk_result(self.root/'source'))
        save(self.root/'sdk_terminal.json',dict(returncode=0,gate_passed=True,manifest_sha256=h))
    def fake_runner(self,root,mode,item,ticket,nonce,argv):
        if mode=='sdk':save(root/'sdk_result.json',sdk_result(root/'source'))
        else:
            out=root/'runs'/item['output_name'];out.mkdir();save(out/'report.json',refusal(item));fake_geometry(out)
            (out/'control.jsonl').write_text(json.dumps(dict(step=1,time_s=.02,root_position=[0,0,.28]))+'\n')
        return dict(returncode=0,wall_s=0,fixture=True)


class AuthorityTests(Fixture):
    def test_missing_approval_consumes_nothing(self):
        with self.assertRaisesRegex(PermissionError,'No explicit'):dispatch(self.root,'sdk',gpu_busy=lambda:'',runner=self.fake_runner,external=lambda r:None)
        self.assertFalse((self.family/'pose_allocations').exists())
    def test_changed_source_or_approval_binding_rejected(self):
        self.auth();(self.root/'source/pose_entry_selection.py').write_text('tampered')
        with self.assertRaisesRegex(PermissionError,'source mismatch'):approval(self.root,'sdk')
    def test_old_ledger_change_detected_without_writing_it(self):
        self.auth();self.protocol['old_physical_ledger_sha256']='not-the-original';self.remanifest()
        with self.assertRaisesRegex(PermissionError,'Old ledger changed'):family_snapshot(self.protocol)
    def test_busy_gpu_consumes_neither_sdk_nor_physical_reservation(self):
        self.auth();self.gate()
        for mode in ['sdk','physical']:
            with self.assertRaisesRegex(RuntimeError,'GPU busy'):dispatch(self.root,mode,gpu_busy=lambda:'OTHER_GROUP_PID',runner=self.fake_runner,external=lambda r:None)
        self.assertFalse((self.family/'pose_allocations').exists())
    def test_sdk_claim_exclusive_across_releases_and_retries(self):
        self.auth();make_permit(self.root,'sdk',[])
        with self.assertRaises(FileExistsError):make_permit(self.root,'sdk',[])
    def test_sdk_returncode_zero_without_report_is_not_pass(self):
        self.auth();r=dispatch(self.root,'sdk',gpu_busy=lambda:'',runner=lambda *a:dict(returncode=0),external=lambda r:None)
        self.assertFalse(r['gate_passed'])
        with self.assertRaises(FileExistsError):dispatch(self.root,'sdk',gpu_busy=lambda:'',runner=self.fake_runner,external=lambda r:None)
    def test_physical_requires_exact_sdk_result_not_just_terminal(self):
        self.auth();self.gate();v=load(self.root/'sdk_result.json');v['passed']=False;save(self.root/'sdk_result.json',v)
        with self.assertRaises(PermissionError):reserve_physical(self.root)
    def test_reservations_not_only_used_starts_count_toward_parent16(self):
        self.auth();self.gate();reserve_physical(self.root)
        fake=self.family/'pose_allocations/other-phase';fake.mkdir();save(fake/'reservation.json',dict(max_starts=8))
        # Same proposed eight cannot be allocated again even if none have launched.
        with self.assertRaisesRegex(PermissionError,'overallocated'):reserve_physical(self.root)
    def test_partial_sdk_true_json_is_not_complete_gate(self):
        self.auth();self.gate();r=load(self.root/'sdk_result.json');r['completed_role_checks'].pop();save(self.root/'sdk_result.json',r)
        with self.assertRaisesRegex(PermissionError,'partial'):reserve_physical(self.root)
    def test_parent_cap_counts_other_phase_reservation_without_any_start(self):
        self.auth();self.gate();phase=self.family/'pose_allocations/OTHER';phase.mkdir(parents=True);save(phase/'reservation.json',dict(max_starts=7))
        with self.assertRaisesRegex(PermissionError,'overallocated'):reserve_physical(self.root)
        self.assertFalse((self.root/'physical_ledger.json').exists())
    def test_exclusive_budget_lock_prevents_concurrent_mutation(self):
        self.auth()
        with locked(self.family/'pose_budget.lock'):
            with self.assertRaises(BlockingIOError):make_permit(self.root,'sdk',[])
    def test_direct_both_entrypoints_refuse_without_any_App_import(self):
        for name in ['probe.py','sdk_check.py']:
            env=os.environ.copy();env.pop('REACH_POSE_PERMIT',None)
            r=subprocess.run([sys.executable,str(self.root/'source'/name)],capture_output=True,text=True,env=env)
            self.assertNotEqual(r.returncode,0);self.assertIn('No launcher ticket',r.stderr)
            self.assertNotIn("No module named 'isaaclab'",r.stderr)
        self.assertFalse((self.family/'pose_allocations').exists())
    def test_one_ticket_consumes_once_but_allows_same_PID_probe_definition_guard(self):
        self.auth();ticket,nonce=make_permit(self.root,'sdk',['--synthetic'])
        env=os.environ.copy();env.update(REACH_POSE_PERMIT=str(ticket),REACH_POSE_NONCE=nonce)
        code=f"import sys;sys.path.insert(0,{str(self.root/'source')!r});sys.argv=[{str(self.root/'source/sdk_check.py')!r},'--synthetic'];from entry_admission import require_execution_authority;require_execution_authority();require_execution_authority();print('TWO_GUARDS_SAME_PID_OK')"
        first=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,env=env)
        self.assertEqual(first.returncode,0,first.stderr);self.assertIn('SAME_PID_OK',first.stdout)
        second=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,env=env)
        self.assertNotEqual(second.returncode,0);self.assertIn('FileExistsError',second.stderr)
    def test_ticket_cannot_change_argv_or_nonce(self):
        self.auth();ticket,nonce=make_permit(self.root,'sdk',[])
        env=os.environ.copy();env.update(REACH_POSE_PERMIT=str(ticket),REACH_POSE_NONCE='wrong')
        code=f"import sys;sys.path.insert(0,{str(self.root/'source')!r});sys.argv=[{str(self.root/'source/sdk_check.py')!r}];from entry_admission import require_execution_authority;require_execution_authority()"
        r=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,env=env)
        self.assertNotEqual(r.returncode,0);self.assertIn('command/nonce',r.stderr)


class DispatchTests(Fixture):
    def test_sdk_synthetic_runner_works_and_owns_zero_physical_claims(self):
        self.auth();result=dispatch(self.root,'sdk',gpu_busy=lambda:'',runner=self.fake_runner,external=lambda r:None)
        self.assertTrue(result['gate_passed']);self.assertFalse((self.root/'physical_ledger.json').exists())
    def test_eight_typed_refusals_remain_failures_and_complete_schedule(self):
        self.auth();self.gate();state=dispatch(self.root,'physical',gpu_busy=lambda:'',runner=self.fake_runner,external=lambda r:None)
        self.assertEqual(state['starts'],8);self.assertEqual(state['charged_global_claims'],8);self.assertEqual(state['status'],'COMPLETED_REGISTERED_EIGHT')
        self.assertTrue(all(row['primary_success'] is False and row['ordinary_refusal'] for row in state['entries']))
        self.assertEqual(len(list((phase_directory(self.protocol)/'physical_claims').glob('*.json'))),8)
        with self.assertRaisesRegex(PermissionError,'Existing phase ledger'):dispatch(self.root,'physical',gpu_busy=lambda:'',runner=self.fake_runner,external=lambda r:None)
    def test_technical_report_stops_after_first_no_replacement(self):
        self.auth();self.gate()
        def runner(root,mode,item,*rest):
            out=root/'runs'/item['output_name'];out.mkdir();r=refusal(item);r.update(outcome='runtime_error',error='synthetic technical failure');save(out/'report.json',r)
            return dict(returncode=0)
        state=dispatch(self.root,'physical',gpu_busy=lambda:'',runner=runner,external=lambda r:None)
        self.assertEqual(state['starts'],1);self.assertEqual(len(state['not_run']),7);self.assertEqual(state['status'],'STOPPED_TECHNICAL_OR_SEVERE_NO_RETRY')
    def test_launcher_exception_is_charged_and_stops_without_retry(self):
        self.auth();self.gate()
        def broken(*args):raise RuntimeError('synthetic launcher failure')
        state=dispatch(self.root,'physical',gpu_busy=lambda:'',runner=broken,external=lambda r:None)
        self.assertEqual(state['starts'],1);self.assertEqual(state['charged_global_claims'],1);self.assertEqual(len(state['not_run']),7)
        self.assertIsNone(state['active']);self.assertEqual(state['entries'][0]['outcome'],'launcher_or_terminal_exception')
    def test_missing_report_not_fabricated_success_or_ordinary_refusal(self):
        self.auth();self.gate();state=dispatch(self.root,'physical',gpu_busy=lambda:'',runner=lambda *a:dict(returncode=0),external=lambda r:None)
        self.assertEqual(state['starts'],1);self.assertEqual(state['entries'][0]['outcome'],'missing_report')
        self.assertIsNone(state['entries'][0]['primary_success'])
    def test_refusal_without_raw_final_cloud_and_guard_stops(self):
        self.auth();self.gate()
        def run(*a):
            result=self.fake_runner(*a);root,_,item=a[:3];(root/'runs'/item['output_name']/'entry_geometry.jsonl').unlink();return result
        state=dispatch(self.root,'physical',gpu_busy=lambda:'',runner=run,external=lambda r:None)
        self.assertEqual(state['starts'],1);self.assertFalse(state['entries'][0]['raw_common_final_query_and_guard_verified'])
    def test_refusal_with_a_later_recorded_physics_step_stops(self):
        self.auth();self.gate()
        def run(*a):
            result=self.fake_runner(*a);root,_,item=a[:3];(root/'runs'/item['output_name']/'control.jsonl').write_text(json.dumps(dict(step=2,time_s=.04,root_position=[0,0,0]))+'\n');return result
        state=dispatch(self.root,'physical',gpu_busy=lambda:'',runner=run,external=lambda r:None)
        self.assertEqual(state['starts'],1);self.assertTrue(state['entries'][0]['severe'])
    def test_nonzero_exit_overrides_a_well_formed_refusal(self):
        self.auth();self.gate()
        def run(*a):r=self.fake_runner(*a);r['returncode']=1;return r
        state=dispatch(self.root,'physical',gpu_busy=lambda:'',runner=run,external=lambda r:None)
        self.assertEqual(state['starts'],1);self.assertEqual(len(state['not_run']),7)


class SDKStructureTests(unittest.TestCase):
    def test_sdk_actual_definition_CFG_boundary_and_durable_shutdown_order(self):
        source=Path(__file__).with_name('release_sdk_check.py').read_text();tree=ast.parse(source)
        self.assertLess(source.index('require_execution_authority()'),source.index('exec(compile(module'))
        self.assertIn("ast.unparse(node.value.func)=='gym.make'",source)
        self.assertIn('torch.load=fail_actor',source);self.assertIn('torch.jit.load=fail_actor',source)
        self.assertIn('gym.make=fail_env',source)
        tr=next(n for n in tree.body if isinstance(n,ast.Try))
        self.assertTrue(any(isinstance(h.type,ast.Name) and h.type.id=='BaseException' for h in tr.handlers))
        self.assertIn('persist_then_close',ast.unparse(tr.finalbody[-1]))
        self.assertIn('completed_role_checks=checks',source)
        self.assertIn('explicitly SYNTHETIC',source)
    def test_original_timeout_ceilings_and_global_no_sim_import(self):
        source=Path(__file__).with_name('release_supervisor.py').read_text()
        self.assertIn("timeout=175 if mode=='sdk' else 1795",source)
        self.assertIn("'--kill-after=5'",source)
        modules={alias.name for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Import) for alias in n.names}
        self.assertFalse(modules & {'torch','mujoco','gymnasium','isaaclab','isaacsim'})


class EvaluationTests(unittest.TestCase):
    def setUp(self):self.item=dict(seed=120501,arm='P0')
    def test_common_goal_success_needs_common_actual_verifier(self):
        r=success(self.item);self.assertTrue(classify(r,self.item)['primary_success'])
        r['measured_final_support_verification']['box_approach_preview']['criterion']='planning'
        self.assertIsNone(classify(r,self.item)['primary_success'])
    def test_typed_refusal_is_real_failure_not_success(self):
        r=refusal(self.item);self.assertFalse(classify(r,self.item)['primary_success'])
        r['control_events']=[dict(event='push_activated')]
        self.assertIsNone(classify(r,self.item)['primary_success'])
    def test_wrong_goal_or_zero_physics_not_a_success(self):
        r=success(self.item);r['control_events'][0]['goal']=[0,0,0]
        self.assertIsNone(classify(r,self.item)['primary_success'])
        r=success(self.item);r['physics_samples']=0
        self.assertIsNone(classify(r,self.item)['primary_success'])
    def test_eight_registered_unknowns_without_point_effect(self):
        p=dict(arms=['P0','P1','P2','P3'],seeds=[120501,120502]);p['schedule']=[dict(seed=s,arm=a) for s in p['seeds'] for a in p['arms']]
        v=summarize(p,None,{})
        self.assertEqual(len(v['rows']),8);self.assertEqual(v['starts'],0);self.assertTrue(all(e is None for e in v['effects'].values()))
        self.assertTrue(all(a['complete_rate'] is None for a in v['arms'].values()))
    def test_complete_fixture_effects_are_only_descriptive(self):
        p=dict(arms=['P0','P1','P2','P3'],seeds=[120501,120502]);p['schedule']=[dict(seed=s,arm=a) for s in p['seeds'] for a in p['arms']]
        reports={(i['seed'],i['arm']):(success(i) if i['arm'] in ['P1','P3'] else refusal(i)) for i in p['schedule']}
        v=summarize(p,dict(entries=p['schedule'],starts=8,active=None),reports)
        self.assertEqual(v['effects']['P1_minus_P0'],1);self.assertFalse(v['full_obstacle_navigation_claim']);self.assertFalse(v['independent_generalization_claim'])

if __name__=='__main__':unittest.main()
