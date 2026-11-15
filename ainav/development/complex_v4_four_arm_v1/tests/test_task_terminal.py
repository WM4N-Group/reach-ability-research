"""Task-chain/scalar proof refusal fixtures, NOT actual native task completion."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys,json,unittest,inspect,hashlib
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Source metadata only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import task_terminal as t
from rule_baseline import RuleBaseline
from v4_native_asset import load_scene
class Tests(unittest.TestCase):
    def rows(self):return [dict(time_s=1.,source_height_m=0.,destination_height_m=.2,target_ref='SOFTWARE_any_box',native_stop_success=True),dict(time_s=2.,source_height_m=.2,destination_height_m=.6,target_ref='goal_deck',native_stop_success=True)]
    def check(self,rows):return t.check_chain_rows(rows,goal_ref='goal_deck',goal_height=.6)
    def test_pure_chain_is_actual_transition_validation_not_fixed_box_letter_route(self):
        rows=self.rows();self.assertTrue(self.check(rows));rows[0]['target_ref']='SOFTWARE_other_box';self.assertTrue(self.check(rows))
    def test_single_CLIMB_or_unknown_terminal_never_full_goal(self):
        with self.assertRaises(ValueError):self.check(self.rows()[:1])
        rows=self.rows();rows[-1]['target_ref']='SOFTWARE_box'
        with self.assertRaises(ValueError):self.check(rows)
    def test_height_continuity_and_positive_rise_not_filled_from_blueprint(self):
        for key,value in [('source_height_m',0.),('destination_height_m',.2)]:
            rows=self.rows();rows[-1][key]=value
            with self.assertRaises(ValueError):self.check(rows)
        rows=self.rows();rows[-1]['destination_height_m']=.4
        with self.assertRaises(ValueError):self.check(rows)
    def test_clock_replay_and_native_stop_false_rejected(self):
        for key,value in [('time_s',1.),('time_s',.5),('native_stop_success',False)]:
            rows=self.rows();rows[-1][key]=value
            with self.assertRaises(ValueError):self.check(rows)
    def test_public_rule_cannot_self_sign_with_string_boolean_or_fake_proof(self):
        rule=RuleBaseline(load_scene(),journal=lambda row:'SOFTWARE')
        for proof in (None,True,NS(confirm_rule=lambda *args,**kwargs:True)):
            with self.assertRaises(RuntimeError):rule.confirm_original_task_terminal(evidence_ref='SOFTWARE-text',terminal_proof=proof)
        self.assertFalse(rule.complete)
    def test_type_correct_but_uncollected_proof_still_cannot_complete_E(self):
        rule=RuleBaseline(load_scene(),journal=lambda row:'SOFTWARE')
        proof=t.VerifiedV4TaskTerminal.__new__(t.VerifiedV4TaskTerminal)
        with self.assertRaises(ValueError):rule.confirm_original_task_terminal(evidence_ref='SOFTWARE-text',terminal_proof=proof)
        self.assertFalse(rule.complete)
    def test_private_constructor_and_false_guard_refuse_before_native(self):
        with self.assertRaises(ValueError):t.VerifiedV4TaskTerminal(_seal=object(),runtime=None,executor=None,placements=None,chain=None,guard=None)
        with self.assertRaises(ValueError):t.collect_verified_terminal(None,None,None,None,guard=lambda:False)
        self.assertFalse(blocked)
    def test_actual_NAV_session_required_not_ground_pose_or_complete_label(self):
        with self.assertRaises(ValueError):t.terminal_nav_session(NS(complete=True),None,None,source_root=SOURCE,journal=lambda row:'SOFTWARE')
        self.assertFalse(blocked)
    def test_expired_same_tick_terminal_evidence_not_reused(self):
        proof=t.VerifiedV4TaskTerminal.__new__(t.VerifiedV4TaskTerminal)
        proof.guard=lambda:None;proof.r=NS(step_count=201,sim=NS(data=NS(time=1.005)));proof.tick=200;proof.time_s=1.
        with self.assertRaises(ValueError):proof.validate()
        self.assertFalse(blocked)
    def test_collector_has_no_sample_or_declared_success_override(self):
        self.assertFalse(set(inspect.signature(t.collect_verified_terminal).parameters).intersection({'sample','pose','success','feet','loads','stop_verified','dwell'}))
        self.assertEqual(hashlib.sha256((SOURCE/'ainav/native/registered_hold.py').read_bytes()).hexdigest(),t.HOLD_SHA)

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='V4_ACTUAL_TERMINAL_COLLECTOR_SOURCE_CHAIN_REFUSAL_FIXTURES_NOT_TASK_SUCCESS',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,actual_Runtime_Actor_NAV_CLIMB_contact_reader_physics_API_calls=0)))
    sys.exit(0 if r.wasSuccessful()and not blocked else 1)
