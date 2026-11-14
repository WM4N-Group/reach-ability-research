"""Information-path regressions, not prediction training or physical samples."""
import math
import unittest
from .public_information import public_snapshot,information_action


def observation(t=10.):
    return dict(time_s=t,rgb={'time_s':t,'path':'/CPU_SCHEMA_NOT_A_REAL_IMAGE.png','sha256':'a'*64,'width':192,'height':128},objects=[],declared_map={'source_ref':'CPU_PUBLIC_SCHEMA_EXAMPLE','anchors':[]},goal='same fixed task',events=[],
        public_state=dict(q=[0.]*18,dq=[.1]*18,gravity=[0.,0.,-1.],angular_velocity=[0.,0.,.2],linear_velocity=[.3,.4,0.],support_surface='public categorical ground status'))


class PublicInformationTests(unittest.TestCase):
    def extract(self,o=None,now=10.):return public_snapshot(observation() if o is None else o,now_s=now,source_role='ONLINE_PUBLIC')

    def test_actual_existing_public_vector_layout_yields_descriptors_not_prediction(self):
        s=self.extract();self.assertEqual(s['descriptors']['body_planar_speed_m_s'],.5)
        self.assertEqual(s['descriptors']['body_tilt_from_projected_gravity_rad'],0.)
        self.assertIsNone(s['current_or_future_completion_cost_s']);self.assertFalse(s['native_READY_or_success_inferred'])

    def test_fresh_packet_does_not_keep_polling_for_unpublished_state_or_dynamic_model(self):
        d=information_action(self.extract(),reobservations_used=0)
        self.assertFalse(d['request_public_acquisition']);self.assertIsNone(d['optimized_candidate_id'])
        self.assertIn('PREDICTION_UNRESOLVED',d['action'])
        self.assertFalse(d['execution_authorized'])

    def test_stale_packet_requests_once_without_timestamp_padding_or_physics(self):
        s=self.extract(now=10.2);d=information_action(s,reobservations_used=0)
        self.assertEqual(s['packet_time_s'],10.);self.assertEqual(s['status'],'STALE_PUBLIC_PACKET')
        self.assertTrue(d['request_public_acquisition']);self.assertFalse(d['native_action_or_observation_executed'])
        self.assertTrue(d['request_is_not_HOLD_or_NAV_or_retry_or_new_world'])

    def test_exhausted_capture_budget_does_not_retry_or_fill_missing_measurements(self):
        s=self.extract(now=10.2);d=information_action(s,reobservations_used=1)
        self.assertFalse(d['request_public_acquisition']);self.assertIn('MEASUREMENT_UNRESOLVED',d['action'])
        self.assertEqual(s['descriptors'],{})

    def test_existing_capture_can_refresh_allowed_measurement_but_not_create_predictor(self):
        before=self.extract(now=10.2);after=self.extract(observation(10.2),now=10.2)
        self.assertTrue(information_action(before,reobservations_used=0)['request_public_acquisition'])
        self.assertFalse(information_action(after,reobservations_used=1)['request_public_acquisition'])
        self.assertIsNone(after['current_or_future_completion_cost_s'])

    def test_missing_vector_not_zero_filled(self):
        o=observation();del o['public_state']['linear_velocity'];s=self.extract(o)
        self.assertIn('linear_velocity',s['missing_measurement_fields']);self.assertEqual(s['descriptors'],{})
        self.assertTrue(information_action(s,reobservations_used=0)['request_public_acquisition'])

    def test_lagged_publication_does_not_invent_proprio_clock(self):
        o=observation();o['rgb']['time_s']=9.99;s=self.extract(o)
        self.assertEqual(s['status'],'PROPRIO_ACQUISITION_CLOCK_UNKNOWN')
        self.assertEqual(s['descriptors'],{})

    def test_future_and_private_or_audit_fields_rejected(self):
        o=observation(11.)
        with self.assertRaisesRegex(ValueError,'Causal'):self.extract(o)
        o=observation();o['public_state']['base_world_xy']=[0.,0.]
        with self.assertRaisesRegex(ValueError,'actually published'):self.extract(o)
        with self.assertRaisesRegex(ValueError,'audit-only'):
            public_snapshot(observation(),now_s=10.,source_role='AUDIT_ONLY')

    def test_no_parser_from_categorical_support_to_native_support_pass(self):
        o=observation();o['public_state']['support_surface']='all feet definitely safe'
        s=self.extract(o);self.assertTrue(s['categorical_support_is_not_dynamic_qualification'])
        self.assertFalse(s['native_READY_or_success_inferred'])

    def test_bad_shape_nan_bool_and_extra_private_top_schema_rejected(self):
        for vector in ([0.]*17,[0.]*17+[True],[0.]*17+[float('nan')]):
            o=observation();o['public_state']['q']=vector
            with self.assertRaisesRegex(ValueError,'finite public vector'):self.extract(o)
        o=observation();o['private_catalog']={}
        with self.assertRaisesRegex(ValueError,'exact public'):self.extract(o)

    def test_zero_gravity_does_not_become_fake_zero_tilt(self):
        o=observation();o['public_state']['gravity']=[0.,0.,0.]
        self.assertIsNone(self.extract(o)['descriptors']['body_tilt_from_projected_gravity_rad'])

    def test_no_unbounded_information_request_count(self):
        for used,maximum in [(0,2),(-1,1),(True,1),(2,1)]:
            with self.assertRaisesRegex(ValueError,'At most one'):
                information_action(self.extract(),reobservations_used=used,max_reobservations=maximum)


if __name__=='__main__':unittest.main()
