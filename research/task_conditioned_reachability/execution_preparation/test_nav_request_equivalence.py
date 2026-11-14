"""Source-bound scalar checks only; chosen deadbands/errors are CPU fixtures."""
import hashlib,json,math
from pathlib import Path
import unittest
from .nav_request_equivalence import verify_primitive,diagnose_lateral_errors

ROOT=Path('/home/yuanyue/main/work/ainav/consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1')
RELEASE_SHA='0c17d2e70139a86a14b7a87fa9fb2cd6ed1bd37d8873a009a7b7613bea40718e'
MEMBER='common-source/mujoco_zyh/nav_efficiency.py'


def primitive():
    raw=(ROOT/'CANDIDATE_RELEASE_v1.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==RELEASE_SHA
    expected=json.loads(raw)['files_sha256'][MEMBER]
    source=(ROOT/MEMBER).read_bytes()
    return verify_primitive(source,expected_sha256=expected),source


class RequestEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.p,cls.source=primitive()

    def diagnostic(self,errors,deadband=.01):
        return diagnose_lateral_errors(self.p,dict(zip(('original','lateral_plus_0p04','lateral_minus_0p04'),errors)),deadband=deadband)

    def test_original_y_floor_equals_cap_quantizes_all_nonzero_requests(self):
        self.assertEqual(self.p.minimum_speeds,(.4,.4,.8));self.assertEqual(self.p.speed_limits,(.5,.4,.9))
        for v in (.011,.06,.2,1.,100.):
            self.assertEqual(self.p.request(v,axis=1,deadband=.01),.4)
            self.assertEqual(self.p.request(-v,axis=1,deadband=.01),-.4)

    def test_different_goal_errors_can_have_identical_lateral_request(self):
        out=self.diagnostic((-.12,-.08,-.16))
        self.assertTrue(out['all_lateral_axis_requests_same'])
        self.assertEqual(set(out['axis_requests'].values()),{-.4})
        self.assertTrue(out['trajectory_or_Actor_or_motor_equivalence'].startswith('UNKNOWN'))
        self.assertFalse(out['public_planner_input_permission'])

    def test_same_center_error_can_split_into_three_requests(self):
        out=self.diagnostic((0.,.04,-.04))
        self.assertEqual(out['axis_requests'],{'original':0.,'lateral_plus_0p04':.4,'lateral_minus_0p04':-.4})
        self.assertFalse(out['all_lateral_axis_requests_same'])

    def test_all_zero_when_all_three_within_supplied_deadband(self):
        self.assertTrue(self.diagnostic((0.,.04,-.04),deadband=.05)['all_lateral_axis_requests_same'])

    def test_strict_original_boundary_no_tolerance_widening(self):
        self.assertEqual(self.p.request(.04,axis=1,deadband=.04),0.)
        self.assertEqual(self.p.request(math.nextafter(.04,math.inf),axis=1,deadband=.04),.4)
        self.assertEqual(self.p.request(math.nextafter(-.04,-math.inf),axis=1,deadband=.04),-.4)

    def test_world_coordinate_subtraction_boundary_is_not_rounded_to_nominal_offset(self):
        # Declared catalogue -1.96 minus CPU base -2.0 is NOT exactly .04.
        value=-1.96-(-2.)
        self.assertGreater(value,.04)
        self.assertEqual(self.p.request(value,axis=1,deadband=.04),.4)

    def test_x_axis_is_not_falsely_declared_same_quantization(self):
        self.assertEqual(self.p.request(.21,axis=0,deadband=.01),.42)
        self.assertEqual(self.p.request(.4,axis=0,deadband=.01),.5)

    def test_private_native_diagnostic_never_makes_complete_control_claim(self):
        out=self.diagnostic((.1,.14,.06));self.assertTrue(out['whole_velocity_request_equivalence'].startswith('UNKNOWN'))
        self.assertFalse(out['execution_authorized']);self.assertFalse(out['native_admission_or_success_or_cost_prediction'])

    def test_all_three_candidates_required(self):
        with self.assertRaisesRegex(ValueError,'Complete fixed'):
            diagnose_lateral_errors(self.p,{'original':.1},deadband=.01)

    def test_unknown_profile_deadband_not_filled_with_default(self):
        for deadband in (None,True,-.01,float('nan')):
            with self.assertRaisesRegex(ValueError,'finite original-profile'):
                self.diagnostic((0.,.04,-.04),deadband=deadband)

    def test_native_errors_must_be_finite(self):
        with self.assertRaisesRegex(ValueError,'finite original-profile'):
            self.diagnostic((0.,float('inf'),-.04))

    def test_wrong_source_pin_rejected(self):
        with self.assertRaisesRegex(ValueError,'Pinned original'):
            verify_primitive(self.source,expected_sha256='0'*64)

    def test_changed_deadband_strictness_rejected_even_if_rehashed(self):
        source=self.source.replace(b'abs(body_delta[axis])>cfg.position_command_deadband',b'abs(body_delta[axis])>=cfg.position_command_deadband')
        with self.assertRaisesRegex(ValueError,'strict original deadband'):
            verify_primitive(source,expected_sha256=hashlib.sha256(source).hexdigest())

    def test_changed_nonzero_floor_expression_rejected(self):
        source=self.source.replace(b'2.*abs(body_delta[axis])',b'3.*abs(body_delta[axis])')
        with self.assertRaisesRegex(ValueError,'floor expression'):
            verify_primitive(source,expected_sha256=hashlib.sha256(source).hexdigest())

    def test_changed_slew_assignment_rejected(self):
        source=self.source.replace(b'self.command=desired.copy()',b'self.command=desired*.5')
        with self.assertRaisesRegex(ValueError,'slew'):
            verify_primitive(source,expected_sha256=hashlib.sha256(source).hexdigest())


if __name__=='__main__':unittest.main()
