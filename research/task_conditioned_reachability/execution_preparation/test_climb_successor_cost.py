"""Small parser/identity checks; not new trials or fitted cost examples."""
from copy import deepcopy
import unittest
from .climb_successor_cost import extract,compare


def fixture():
    stop=dict(first_clear_time=2.,handoff_time=3.,stable_start_time=5.,stop_seconds=2.,stop_seconds_from_clear=3.,
              events=[dict(time=6.,event='stable_confirmed')],configuration=dict(stable_seconds=1.,verify_seconds=3.))
    raw=dict(scope_id='SOFTWARE_FIXTURE_NOT_RUN',passed=True,actual_native_results=[dict(skill='climb',seconds=8.,stop=stop)])
    payloads=[dict(event='intent_native_execution_bound',native_option=dict(skill='CLIMB'),native_option_sha256='climb'),
              dict(event='ainav_native_receipt',receipt=dict(option_sha256='climb',status='started',time_s=1.)),
              dict(event='ainav_native_receipt',receipt=dict(option_sha256='climb',status='succeeded',time_s=9.))]
    return raw,[dict(sequence=i,payload=p) for i,p in enumerate(payloads)]


class SuccessorClimbStageTests(unittest.TestCase):
    def test_stage_sum_and_unknown_actor_clock(self):
        value=extract(*fixture());self.assertEqual(value['literal_motor_window_s'],8.)
        self.assertEqual(sum(value['observed_intervals_s'].values()),8.)
        self.assertIsNone(value['actual_Actor_activation_time_s'])

    def test_missing_optional_boundary_preserves_literal_success(self):
        raw,rows=fixture();raw['actual_native_results'][0]['stop'].pop('stable_start_time')
        result=extract(raw,rows);self.assertEqual(result['coverage'],'PARTIAL_NOT_INFERRED')
        self.assertTrue(result['owner_literal_passed'])
        self.assertIsNone(result['observed_intervals_s']['handoff_to_stable_start'])

    def test_counter_order_or_redundant_field_contradiction_not_fabricated(self):
        raw,rows=fixture();raw['actual_native_results'][0]['stop']['stop_seconds']=1.
        with self.assertRaisesRegex(ValueError,'redundant'):extract(raw,rows)
        raw,rows=fixture();raw['actual_native_results'][0]['stop']['first_clear_time']=4.
        with self.assertRaisesRegex(ValueError,'Ordered'):extract(raw,rows)

    def test_identical_holds_can_coexist_with_longer_stabilization(self):
        a=extract(*fixture());raw,rows=fixture();s=raw['actual_native_results'][0]['stop']
        s.update(stable_start_time=5.5,stop_seconds=2.5,stop_seconds_from_clear=3.5)
        s['events'][0]['time']=6.5;rows[-1]['payload']['receipt']['time_s']=9.5
        b=extract(raw,rows);r=compare(a,b)
        self.assertTrue(r['same_original_stop_configuration'])
        self.assertEqual(r['candidate_minus_baseline_intervals_s']['handoff_to_stable_start'],.5)
        self.assertEqual(r['total_successor_CLIMB_window_increase_s'],.5)
        self.assertFalse(r['actual_state_or_contact_or_global_control_phase_cause_identified'])

    def test_multiple_climbs_not_silently_selected(self):
        raw,rows=fixture();raw['actual_native_results'].append(deepcopy(raw['actual_native_results'][0]))
        with self.assertRaisesRegex(ValueError,'one original'):extract(raw,rows)


if __name__=='__main__':unittest.main()
