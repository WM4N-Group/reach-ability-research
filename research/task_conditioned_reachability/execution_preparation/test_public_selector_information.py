"""Actual AINav pure API + public-information/selector wiring, no world/model."""
from copy import deepcopy
from dataclasses import asdict
import unittest
from .public_preparation_selector import (build_problem,with_public_observation,choose,materialize_fresh_plan)
from .public_information import public_snapshot,information_action
from .successor_aware_choice import Estimate,Costs
from .test_public_preparation_selector import owner_api,reference
from .test_public_information import observation


def published(t=0.):
    row=observation(t)
    row['declared_map']['anchors']=[dict(target_ref='cuboid-2:upper-entry',
        position_xyz_m=[.050000000000000044,-2.,0.])]
    return row


class SelectorInformationTests(unittest.TestCase):
    def setUp(self):
        self.owner=owner_api();self.base=build_problem(reference(),public_candidates=self.owner.public_candidates)

    def test_existing_current_public_vectors_reach_the_shared_evaluator_exactly_once_per_candidate(self):
        observed=published();problem=with_public_observation(self.base,observed,now_s=0.,source_role='ONLINE_PUBLIC')
        calls=[];model='b'*64
        def record(inputs,candidate):
            calls.append((inputs.sha256,candidate.candidate_id))
            values={v.name:v for v in inputs.values}
            self.assertEqual(values['public_state.linear_velocity'].value,[.3,.4,0.])
            self.assertEqual(values['derived_public.body_planar_speed_m_s'].value,.5)
            self.assertTrue(all(v.visibility in ('ONLINE_PUBLIC','UNKNOWN') for v in inputs.values))
            return Estimate(candidate.sha256,inputs.sha256,model,'UNKNOWN','CPU_TEST_ONLY',Costs())
        decision=choose(problem,evaluator=record,evaluator_sha256=model)
        self.assertEqual(len(calls),3);self.assertEqual(len({c[0] for c in calls}),1)
        self.assertEqual(decision['shared_evaluation_count'],3);self.assertIsNone(decision['optimized_candidate_id'])
        self.assertTrue(decision['used_original_default_fallback'])

    def test_public_information_does_not_change_candidate_payloads_or_control_profile(self):
        p=with_public_observation(self.base,published(),now_s=0.,source_role='ONLINE_PUBLIC')
        self.assertEqual(p.payloads,self.base.payloads);self.assertEqual(p.geometry,self.base.geometry)
        self.assertEqual([c.execution_profile_sha256 for c in p.domain.candidates],
                         [c.execution_profile_sha256 for c in self.base.domain.candidates])
        self.assertEqual(p.domain.task.terminal_predicate_sha256,self.base.domain.task.terminal_predicate_sha256)
        self.assertEqual(p.domain.task.original_success_gates_sha256,self.base.domain.task.original_success_gates_sha256)

    def test_fresh_zero_packet_default_materializes_via_actual_owner_pure_API(self):
        p=with_public_observation(self.base,published(),now_s=0.,source_role='ONLINE_PUBLIC');decision=choose(p)
        selected=materialize_fresh_plan(p,decision,selection_from_payload=self.owner.selection_from_payload,phase='FRESH_PREEXECUTION')
        self.assertEqual(selected.candidate_id,'original');self.assertFalse(decision['execution_authorized'])

    def test_live_packet_can_be_evaluated_but_cannot_be_forged_into_fresh_install(self):
        p=with_public_observation(self.base,published(10.),now_s=10.,source_role='ONLINE_PUBLIC');decision=choose(p)
        self.assertEqual(decision['information_decision_time_s'],10.)
        with self.assertRaisesRegex(ValueError,'Live measured input'):
            materialize_fresh_plan(p,decision,selection_from_payload=self.owner.selection_from_payload,phase='FRESH_PREEXECUTION')

    def test_stale_packet_requests_one_refresh_then_fresh_input_can_be_evaluated(self):
        old=published(10.);snapshot=public_snapshot(old,now_s=10.2,source_role='ONLINE_PUBLIC')
        self.assertTrue(information_action(snapshot,reobservations_used=0)['request_public_acquisition'])
        with self.assertRaisesRegex(ValueError,'measurement unresolved'):
            with_public_observation(self.base,old,now_s=10.2,source_role='ONLINE_PUBLIC')
        fresh=published(10.2);p=with_public_observation(self.base,fresh,now_s=10.2,source_role='ONLINE_PUBLIC')
        self.assertIsNone(choose(p,on_unknown='abstain')['proposed_payload'])
        self.assertFalse(information_action(public_snapshot(fresh,now_s=10.2,source_role='ONLINE_PUBLIC'),reobservations_used=1)['request_public_acquisition'])

    def test_repeated_snapshots_do_not_accumulate_audit_or_hidden_history(self):
        p=with_public_observation(self.base,published(),now_s=0.,source_role='ONLINE_PUBLIC')
        with self.assertRaisesRegex(ValueError,'not accumulated'):
            with_public_observation(p,published(),now_s=0.,source_role='ONLINE_PUBLIC')

    def test_own_public_reference_must_match_measured_observation_declared_map(self):
        for kind in ('missing','duplicate','moved'):
            row=published()
            if kind=='missing':row['declared_map']['anchors']=[]
            elif kind=='duplicate':row['declared_map']['anchors']*=2
            else:row['declared_map']['anchors'][0]['position_xyz_m'][1]=-1.96
            with self.assertRaises(ValueError):with_public_observation(self.base,row,now_s=0.,source_role='ONLINE_PUBLIC')

    def test_unknown_tilt_is_not_zero_filled_in_input_schema(self):
        row=published();row['public_state']['gravity']=[0.,0.,0.]
        p=with_public_observation(self.base,row,now_s=0.,source_role='ONLINE_PUBLIC')
        tilt=next(v for v in p.inputs.values if v.name=='derived_public.body_tilt_from_projected_gravity_rad')
        self.assertIsNone(tilt.value);self.assertEqual(tilt.visibility,'UNKNOWN')

    def test_no_private_or_future_or_audit_measurements_can_enter_selector(self):
        row=published();row['public_state']['native_position_latched']=True
        with self.assertRaisesRegex(ValueError,'actually published'):
            with_public_observation(self.base,row,now_s=0.,source_role='ONLINE_PUBLIC')
        with self.assertRaisesRegex(ValueError,'audit-only'):
            with_public_observation(self.base,published(),now_s=0.,source_role='AUDIT_ONLY')
        with self.assertRaisesRegex(ValueError,'Causal'):
            with_public_observation(self.base,published(1.),now_s=0.,source_role='ONLINE_PUBLIC')

    def test_source_observation_and_base_problem_are_not_mutated(self):
        row=published();before=deepcopy(row);original=self.base.inputs.sha256
        p=with_public_observation(self.base,row,now_s=0.,source_role='ONLINE_PUBLIC')
        p.inputs.values[4].value[0]=123.
        self.assertEqual(row,before);self.assertEqual(self.base.inputs.sha256,original)


if __name__=='__main__':unittest.main()
