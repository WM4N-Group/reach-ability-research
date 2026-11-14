"""Only explicitly synthetic journal fixtures; no old/new physical logs read."""
import hashlib
import json
import unittest
from .preparation_stage_clocks import read_preparation_clocks, _sha

J='/CPU_FIXTURE_NOT_EXPERIMENT/events.jsonl'
I='a'*64;O='b'*64
P={'schema':'AINav-finite-CLIMB-preparation-selection-v1','target_ref':'ref','candidate_id':'lateral_plus_0p04'}


def fixture(*, repeats=False, status='succeeded'):
    def event(e,**k):return dict(event=e,intent_sha256=I,**k)
    rows=[event('ainav_selected_CLIMB_preparation_NAV_goal_proposed',selection={k:v for k,v in P.items() if k!='schema'},time_s=10.)]
    if repeats:rows.append(event('ainav_selected_CLIMB_preparation_NAV_goal_proposed',selection={k:v for k,v in P.items() if k!='schema'},time_s=12.))
    rows.append(event('skill_execution_judgment',status='READY',spec={'skill':'CLIMB','target_ref':'ref'},state={'time_s':14.}))
    ready_number=len(rows)
    rows += [event('intent_native_execution_bound',execution_role='interaction',intent={'skill':'CLIMB','target_ref':'ref'},
                   native_option_sha256=O,judgment_ref=J+'#'+str(ready_number)),
             event('intent_actual_native_outcome',execution_role='interaction',native_option_sha256=O,
                   receipt={'option_sha256':O,'status':status,'time_s':19.})]
    return rows


def run(rows):
    previous='0'*64;raw=b''
    for i,payload in enumerate(rows):
        r=dict(sequence=i,previous_sha256=previous,payload=payload);r['sha256']=_sha(r);previous=r['sha256']
        raw+=(json.dumps(r,ensure_ascii=False)+'\n').encode()
    return read_preparation_clocks(raw,expected_sha256=hashlib.sha256(raw).hexdigest(),journal_ref=J,intent_sha256=I,payload=P)


class PreparationClockTests(unittest.TestCase):
    def test_exact_three_clocks_not_task_success(self):
        r=run(fixture());self.assertEqual((r['current_to_READY_s'],r['READY_to_CLIMB_receipt_s'],r['decision_to_CLIMB_receipt_s']),(4.,5.,9.))
        self.assertTrue(r['complete_two_request_task_outcome'].startswith('UNKNOWN'))
        self.assertFalse(r['inferred_Actor_activation']);self.assertFalse(r['actual_motor_difference_proven'])

    def test_every_preparation_attempt_from_first_decision_not_fastest(self):
        r=run(fixture(repeats=True));self.assertEqual(r['preparation_attempts'],2);self.assertEqual(r['current_to_READY_s'],4.)

    def test_failed_receipt_elapsed_is_retained_not_success(self):
        r=run(fixture(status='failed'));self.assertEqual(r['literal_CLIMB_receipt_status'],'failed')
        self.assertEqual(r['decision_to_CLIMB_receipt_s'],9.)
        self.assertTrue(r['complete_two_request_task_outcome'].startswith('UNKNOWN'))

    def test_missing_preparation_is_nonintervention_not_failure(self):
        r=run([]);self.assertEqual(r['status'],'NO_RECORDED_PREPARATION_INTERVENTION_NOT_A_FAILURE')

    def test_wrong_exact_reference_not_nearest_ready(self):
        rows=fixture();rows[2]['judgment_ref']=J+'#1';r=run(rows)
        self.assertIsNone(r['current_to_READY_s'])

    def test_duplicate_receipt_is_unknown(self):
        rows=fixture();rows.append(rows[-1]);self.assertIsNone(run(rows)['decision_to_CLIMB_receipt_s'])

    def test_wrong_native_option_is_unknown(self):
        rows=fixture();rows[-1]['receipt']['option_sha256']='c'*64
        self.assertIsNone(run(rows)['decision_to_CLIMB_receipt_s'])

    def test_boolean_and_missing_clock_not_zero(self):
        for value in (True,None):
            rows=fixture();rows[1]['state']['time_s']=value
            self.assertIsNone(run(rows)['current_to_READY_s'])

    def test_reversed_clock_not_a_negative_cost(self):
        rows=fixture();rows[1]['state']['time_s']=9.
        self.assertIsNone(run(rows)['current_to_READY_s'])

    def test_changed_candidate_across_retries_is_rejected(self):
        rows=fixture(repeats=True);rows[1]['selection']={'target_ref':'ref','candidate_id':'original'}
        self.assertEqual(run(rows)['status'],'MISMATCHED_IMMUTABLE_PREPARATION_PAYLOAD')

    def test_schema_payload_not_confused_with_original_asdict_selection(self):
        rows=fixture();rows[0]['selection']=dict(P)
        self.assertEqual(run(rows)['status'],'MISMATCHED_IMMUTABLE_PREPARATION_PAYLOAD')

    def test_input_pin_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,'journal SHA'):
            read_preparation_clocks(b'',expected_sha256='0'*64,journal_ref=J,intent_sha256=I,payload=P)

    def test_mutated_journal_chain_rejected_even_with_new_file_pin(self):
        raw=(json.dumps({'sequence':0,'previous_sha256':'0'*64,'payload':{},'sha256':'0'*64})+'\n').encode()
        with self.assertRaisesRegex(ValueError,'hash chain'):
            read_preparation_clocks(raw,expected_sha256=hashlib.sha256(raw).hexdigest(),journal_ref=J,intent_sha256=I,payload=P)


if __name__=='__main__':unittest.main()
