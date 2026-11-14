"""CPU source/config/authorization fixtures only; never App or robot episodes."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest

from build_followup import PARENT, PARENT_SHA, SCENES, build, sha, write
from scene_contract import apply_scene, observe_plan


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec)
    sys.modules[name]=value;spec.loader.exec_module(value);return value


def reset_push_box():pass


def fixture_cfg():
    return NS(scene=NS(box=NS(init_state=NS(pos=(1.10,0.,.1))),robot=NS(init_state=NS(pos=(-.25,0.,.33)))),
              events=NS(reset_box=NS(func=reset_push_box,mode='reset')))


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.root=self.base/'release'
        build(self.root,self.root);self.source=self.root/'source'
        self.family=self.base/'family';self.family.mkdir();self.prior=self.base/'prior';(self.prior/'source').mkdir(parents=True)
        write(self.family/'physical_ledger.json',dict(starts=2,active=None,not_run=[{'old':i} for i in range(14)],status='STOPPED_SYNTHETIC'))
        write(self.family/'approval.json',dict(budgets=dict(max_new_Isaac_starts=16)))
        self.old_bytes=(self.family/'physical_ledger.json').read_bytes()
        write(self.prior/'physical_ledger.json',dict(status='COMPLETED_REGISTERED_EIGHT',starts=8,active=None))
        write(self.prior/'source/manifest.json',dict(synthetic='NOT an actual SDK/physical source'))
        reservation=self.family/'pose_allocations/prior-eight';reservation.mkdir(parents=True)
        write(reservation/'reservation.json',dict(max_starts=8))
        self.p=json.loads((self.source/'protocol.json').read_text())
        self.p.update(original_family_root=str(self.family),old_physical_ledger_sha256=sha(self.family/'physical_ledger.json'),
                      prior_phase_root=str(self.prior),prior_closed_ledger_sha256=sha(self.prior/'physical_ledger.json'),
                      prior_source_manifest_sha256=sha(self.prior/'source/manifest.json'))
        self.remanifest()
        self.names=['release_authority','evaluate_pose_pilot','entry_admission','native_influence']
        self.saved={name:sys.modules.get(name) for name in self.names}
        self.a=module('release_authority',self.source/'release_authority.py')
        self.e=module('evaluate_pose_pilot',self.source/'evaluate_pose_pilot.py')
        module('native_influence',self.source/'native_influence.py')
        self.s=module('followup_fixture_supervisor',self.source/'run_supervisor.py')
    def tearDown(self):
        self.assertEqual(self.old_bytes,(self.family/'physical_ledger.json').read_bytes())
        for name,value in self.saved.items():
            if value is None:sys.modules.pop(name,None)
            else:sys.modules[name]=value
        sys.modules.pop('followup_fixture_supervisor',None);self.tmp.cleanup()
    def remanifest(self):
        write(self.source/'protocol.json',self.p)
        m=json.loads((self.source/'manifest.json').read_text());m['files']={name:sha(self.source/name) for name in m['files']}
        write(self.source/'manifest.json',m)
    def approve_fixture(self):
        request=json.loads((self.root/'execution-request-NOT-APPROVED.json').read_text())
        request.update(approved=True,source_manifest_sha256=sha(self.source/'manifest.json'),source_protocol_sha256=sha(self.source/'protocol.json'))
        write(self.root/'approval.json',request)
    def sdk_fixture(self,arms=('P2','P3')):
        h=sha(self.source/'manifest.json')
        checks=[dict(arm=arm,role=role,state_restored=True) for arm in arms for role in ('planning','final_actual')]
        write(self.root/'sdk_terminal.json',dict(returncode=0,gate_passed=True,manifest_sha256=h))
        write(self.root/'sdk_result.json',dict(passed=True,manifest_sha256=h,envs=0,actor_loads=0,physics_steps=0,
            completed_role_checks=checks,actual_native_definitions_executed=True,actual_main_CFG_prefix_executed=True,
            common_actual_verifier_matches_original=True,fixture='SYNTHETIC SOFTWARE TEST, NOT SDK'))
    def fake_runner(self,root,mode,item,ticket,nonce,argv):
        self.assertEqual(mode,'physical')
        out=root/'runs'/item['output_name'];out.mkdir()
        receipt=dict(item,applied_before_environment_construction=True,native_reset_unchanged=True)
        write(out/'report.json',dict(seed=item['seed'],study_arm=item['arm'],study_scene_receipt=receipt,
            study_global_goal_se2=[-.25,0.,0.],physical_resets_after_initial=0,physics_samples=1,
            outcome='push_timeout',control_events=[],terminal={}))
        write(out/'actual-initial-state.json',dict(fixture='SYNTHETIC, not actual simulator state'))
        (out/'control.jsonl').write_text(json.dumps(dict(step=1,time_s=.02,root_position=[0.,0.,.33]))+'\n')
        return dict(returncode=0,wall_s=0.,fixture='NO ACTUAL PROCESS')


class SourceAndSceneTests(Fixture):
    def test_six_new_cells_frozen_before_outcomes(self):
        self.assertEqual(len(self.p['schedule']),6);self.assertEqual(self.p['arms'],['P2','P3'])
        self.assertEqual(self.p['seeds'],[120601,120602,120603])
        self.assertEqual(self.p['scene_specs'],SCENES)
        self.assertFalse((self.root/'approval.json').exists())
        self.assertFalse(self.p['execution_authorized'])
        self.assertEqual(self.p['approved_budgets'],dict(SDK_Apps=0,physical_starts=0))
        for s in SCENES:
            pair=[x for x in self.p['schedule'] if x['seed']==s['seed']]
            self.assertEqual({x['arm'] for x in pair},{'P2','P3'})
            self.assertEqual({x['box_default_world_x_offset_m'] for x in pair},{s['box_default_world_x_offset_m']})
    def test_runtime_case_id_prefix_matches_schedule(self):
        text=(self.source/'probe.py').read_text()
        self.assertNotIn('reach-pose-entry-cpu-v1-',text)
        for x in self.p['schedule']:
            self.assertEqual(x['source_id'],f"reach-native-pose-six-{x['arm']}-seed{x['seed']}")
        self.assertIn("f'reach-native-pose-six-{a.entry_geometry_arm}-seed{a.seed}'",text)

    def test_only_main_and_passive_prospective_function_changed(self):
        def protected(path):
            tree=ast.parse(path.read_text())
            return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name not in ('main','prospective_entry')}
        self.assertEqual(protected(PARENT/'source/probe.py'),protected(self.source/'probe.py'))
        for name in ('prospective_support.py','pose_entry_selection.py','finite_cloud_sampler_frozen.py','box_approach_standoff.py'):
            self.assertEqual(sha(self.source/name),sha(PARENT/'source'/name))
    def test_cfg_offset_is_once_before_make_without_reset_or_target_override(self):
        cfg=fixture_cfg();robot=copy.deepcopy(cfg.scene.robot);event=cfg.events.reset_box
        receipt=apply_scene(cfg,120602,self.source/'protocol.json')
        self.assertAlmostEqual(cfg.scene.box.init_state.pos[0],1.086)
        self.assertEqual(cfg.scene.box.init_state.pos[1:],(0.,.1))
        self.assertEqual(vars(cfg.scene.robot.init_state),vars(robot.init_state));self.assertIs(cfg.events.reset_box,event)
        self.assertTrue(receipt['native_reset_unchanged']);self.assertFalse(receipt['actual_initial_state_validated'])
        with self.assertRaisesRegex(ValueError,'accumulate'):apply_scene(cfg,120602,self.source/'protocol.json')
        text=(self.source/'probe.py').read_text()
        self.assertLess(text.index('scene_receipt=apply_scene('),text.index('env=gym.make('))
    def test_unknown_seed_rejected_no_fallback(self):
        cfg=fixture_cfg();before=cfg.scene.box.init_state.pos
        with self.assertRaisesRegex(ValueError,'unique registered'):apply_scene(cfg,120501,self.source/'protocol.json')
        self.assertEqual(before,cfg.scene.box.init_state.pos)
    def test_passive_observer_preserves_all_control_fields_and_final_role(self):
        plan=dict(shift_m=.02,push_support_shift_m=.035,support_only_shift_m=.02,checks=[{'passed':True}])
        before=copy.deepcopy(plan)
        preview=dict(query_id='SYNTHETIC',all_planning_requests={'P2':dict(minimum_shift_m=.003),'P3':dict(minimum_shift_m=.011)})
        observed=observe_plan(plan,preview,'planning')
        self.assertIs(observed,plan)
        self.assertEqual({k:plan[k] for k in before},before)
        self.assertTrue(plan['reach_action_influence']['comparison']['same_native_entry_shift_proven'])
        final={'shift_m':0.};self.assertIs(observe_plan(final,{},'final_actual'),final);self.assertEqual(final,{'shift_m':0.})
    def test_direct_invocation_stops_before_isaac_and_output(self):
        result=subprocess.run([sys.executable,str(self.source/'probe.py')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('No launcher ticket',result.stderr)
        self.assertNotIn('No module named',result.stderr);self.assertFalse((self.root/'sdk-app').exists())
    def test_build_never_overwrites(self):
        with self.assertRaises(FileExistsError):build(self.root,self.root)


class EvaluationTests(Fixture):
    def test_prepared_source_has_six_unknown_not_zero_successes(self):
        from evaluate_followup import evaluate
        result=evaluate(self.root)
        self.assertEqual(result['state'],'PREPARED_NOT_EXECUTED')
        self.assertIsNone(result['descriptive_success_delta'])
        self.assertIsNone(result['matched_input_success_delta'])
        self.assertEqual(len(result['native_evaluation']['rows']),6)
        self.assertTrue(all(r['primary_success'] is None for r in result['native_evaluation']['rows']))
    def test_synthetic_failures_retained_but_missing_packets_do_not_claim_attribution(self):
        from evaluate_followup import evaluate
        self.approve_fixture();self.sdk_fixture()
        self.s.dispatch(self.root,'physical',gpu_busy=lambda:'',runner=self.fake_runner,external=lambda r:None)
        result=evaluate(self.root)
        self.assertEqual(result['descriptive_success_delta'],0.)
        self.assertIsNone(result['matched_input_success_delta'])
        self.assertEqual(result['registered_cases_filtered'],0)
    def test_null_initial_packets_do_not_match_as_valid_evidence(self):
        from evaluate_followup import comparison_witness
        folder=self.base/'null_fixture';folder.mkdir()
        write(folder/'actual-initial-state.json',dict(robot_position=None,robot_quaternion=None,box_position=None,box_quaternion=None,push_target=None))
        self.assertIsNone(comparison_witness(folder,{}))

    def test_changed_source_is_not_evaluated(self):
        from evaluate_followup import evaluate
        (self.source/'scene_contract.py').write_text('#tamper')
        with self.assertRaisesRegex(ValueError,'source changed'):evaluate(self.root)
    def test_initial_state_corruption_is_not_ignored(self):
        from evaluate_followup import evaluate
        self.approve_fixture();self.sdk_fixture()
        self.s.dispatch(self.root,'physical',gpu_busy=lambda:'',runner=self.fake_runner,external=lambda r:None)
        first=self.p['schedule'][0]
        (self.root/'runs'/first['output_name']/'actual-initial-state.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'initial/geometry SHA'):evaluate(self.root)

    def test_recorded_report_corruption_is_not_ignored(self):
        from evaluate_followup import evaluate
        self.approve_fixture();self.sdk_fixture()
        self.s.dispatch(self.root,'physical',gpu_busy=lambda:'',runner=self.fake_runner,external=lambda r:None)
        first=self.p['schedule'][0]
        (self.root/'runs'/first['output_name']/'report.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'raw report SHA'):evaluate(self.root)


class WatchReportTests(Fixture):
    def test_prepared_report_keeps_unknown_and_six_rows(self):
        from evaluate_followup import evaluate
        from watch_followup import render
        result=evaluate(self.root);text=render(self.root,result)
        self.assertIn('0/6',text)
        self.assertEqual(sum(line.startswith('|1206') for line in text.splitlines()),6)
        self.assertIn('None',text)

    def test_one_shot_publish_is_idempotent_and_never_touches_problem_page(self):
        from evaluate_followup import evaluate
        from watch_followup import publish
        pages=self.base/'pages';pages.mkdir()
        for name in ('当前进展.md','下一步计划.md','问题与待确认事项.md'):(pages/name).write_text('# Fixture\n\nOriginal\n')
        result=evaluate(self.root);publish(pages,self.root/'comparison',result)
        first=(pages/'当前进展.md').read_text();publish(pages,self.root/'comparison',result)
        self.assertEqual((pages/'当前进展.md').read_text(),first)
        self.assertEqual((pages/'问题与待确认事项.md').read_text(),'# Fixture\n\nOriginal\n')


class GateAndBudgetTests(Fixture):
    def test_no_approval_no_claim_or_new_reservation(self):
        with self.assertRaisesRegex(PermissionError,'No explicit'):
            self.s.dispatch(self.root,'sdk',gpu_busy=lambda:'',runner=lambda *a:None,external=lambda r:None)
        self.assertEqual(len(list((self.family/'pose_allocations').glob('*/reservation.json'))),1)
        self.assertFalse((self.root/'sdk_terminal.json').exists())
    def test_sdk_gate_requires_exact_four_role_completions(self):
        self.approve_fixture();self.sdk_fixture(('P2',))
        with self.assertRaisesRegex(PermissionError,'partial'):self.a.sdk_gate(self.root)
        self.sdk_fixture();self.a.sdk_gate(self.root)
    def test_changed_parent_eight_identity_blocks_reallocation(self):
        self.approve_fixture();self.sdk_fixture()
        write(self.prior/'physical_ledger.json',dict(status='RUNNING',starts=8,active={'fixture':True}))
        with self.assertRaisesRegex(PermissionError,'identity changed'):self.a.reserve_physical(self.root)
    def test_old_eight_approval_cannot_authorize_new_six(self):
        self.approve_fixture();p=self.root/'approval.json';a=json.loads(p.read_text());a['budgets']['physical_starts']=8;write(p,a)
        with self.assertRaisesRegex(PermissionError,'explicit6'):self.a.approval(self.root,'physical')
    def test_all_reservations_count_toward_original_sixteen(self):
        self.approve_fixture();self.sdk_fixture()
        extra=self.family/'pose_allocations/another-phase';extra.mkdir();write(extra/'reservation.json',dict(max_starts=1))
        with self.assertRaisesRegex(PermissionError,'overallocated'):self.a.reserve_physical(self.root)
    def test_six_reservation_fits_but_cannot_be_repeated(self):
        self.approve_fixture();self.sdk_fixture();v=self.a.reserve_physical(self.root)
        self.assertEqual(v['max_starts'],6)
        self.assertEqual(2+sum(json.loads(f.read_text())['max_starts'] for f in (self.family/'pose_allocations').glob('*/reservation.json')),16)
        with self.assertRaises((FileExistsError,PermissionError)):self.a.reserve_physical(self.root)
    def test_all_six_synthetic_ordinary_failures_keep_denominator_and_no_retry(self):
        self.approve_fixture();self.sdk_fixture()
        result=self.s.dispatch(self.root,'physical',gpu_busy=lambda:'',runner=self.fake_runner,external=lambda r:None)
        self.assertEqual(result['status'],'COMPLETED_REGISTERED_SIX');self.assertEqual(result['starts'],6)
        self.assertTrue(all(r['primary_success'] is False for r in result['entries']))
        evaluation=self.e.summarize(self.p,result,{(x['seed'],x['arm']):json.loads((self.root/'runs'/x['output_name']/'report.json').read_text()) for x in self.p['schedule']})
        self.assertEqual(evaluation['effects'],{'P3_minus_P2':0.})
        self.assertEqual(evaluation['arms']['P2']['registered'],3)
        with self.assertRaises(PermissionError):
            self.s.dispatch(self.root,'physical',gpu_busy=lambda:'',runner=self.fake_runner,external=lambda r:None)
    def test_missing_or_wrong_scene_remains_unknown(self):
        item=self.p['schedule'][0]
        report=dict(seed=item['seed'],study_arm=item['arm'],outcome='push_timeout')
        v=self.e.classify(report,item)
        self.assertIsNone(v['primary_success']);self.assertFalse(v['protocol_valid'])
    def test_technical_launch_failure_stops_after_one_claim(self):
        self.approve_fixture();self.sdk_fixture()
        result=self.s.dispatch(self.root,'physical',gpu_busy=lambda:'',runner=lambda *a:dict(returncode=1),external=lambda r:None)
        self.assertEqual(result['starts'],1);self.assertEqual(result['status'],'STOPPED_TECHNICAL_OR_SEVERE_NO_RETRY')
        self.assertEqual(len(result['not_run']),5)


if __name__=='__main__':unittest.main()
