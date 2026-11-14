"""CPU-only synthetic branch tests. These are not robot episodes."""
import math
import unittest

from native_influence import (EXPECTED_SUFFIX, compare_requests, describe_request,
                              proposal_readiness, verify_native_branch, frozen_cloud_translation_window)


def native_fixture(baseline, minimum, pass_mask):
    calls = []
    def support(*args, minimum_shift_m, **kwargs):
        calls.append(minimum_shift_m)
        for i in range(9):
            shift = i * .005
            if shift < minimum_shift_m - 1e-9:
                continue
            if pass_mask & (1 << i):
                return dict(shift_m=0. if i == 0 else min(.04, shift+.005),
                            push_support_shift_m=.04)
        raise ValueError('No native support solution')
    # Execute the actual bound branch shape, not a max-based mock policy.
    code = 'def select_branch(baseline, preview):\n' + ''.join(
        '    '+line+'\n' for line in EXPECTED_SUFFIX.splitlines())
    ns = dict(prospective_support=support, c=None, robot=None, joint_ids=None,
              joint_names=None, reserve_for_late_parking=True, nominal_translation_w=None)
    exec(code, ns)
    return ns['select_branch'](baseline, {'minimum_shift_m': minimum}), calls


class NativeInfluenceTests(unittest.TestCase):
    def test_certificate_matches_reuse_for_511_nonempty_support_masks(self):
        count = 0
        for mask in range(1, 512):
            first = next(i for i in range(9) if mask & (1 << i))
            d0 = 0. if first == 0 else min(.04, first*.005+.005)
            baseline = dict(shift_m=d0, push_support_shift_m=.04, token='same-plan')
            for request in (0., d0/2., d0):
                observed, calls = native_fixture(baseline, request, mask)
                cert = describe_request(d0, request)
                self.assertIs(observed, baseline)
                self.assertEqual(calls, [])
                self.assertEqual(cert['selected_shift_m'], observed['shift_m'])
                self.assertEqual(cert['status'], 'baseline_reuse_proven')
                count += 1
        self.assertEqual(count, 1533)

    def test_recompute_is_not_max(self):
        observed, calls = native_fixture({'shift_m': 0.}, .021, 1 << 5)
        self.assertAlmostEqual(observed['shift_m'], .03)
        self.assertNotEqual(observed['shift_m'], max(0., .021))
        cert = describe_request(0., .021)
        self.assertEqual(cert['status'], 'native_recomputation_required')
        self.assertIsNone(cert['selected_shift_m'])

    def test_recompute_can_refuse_and_must_not_be_reported_as_success(self):
        with self.assertRaisesRegex(ValueError, 'No native support'):
            native_fixture({'shift_m': .02}, .03, 1 << 3)
        c = compare_requests(.02, .01, .03)
        self.assertIsNone(c['selected_shift_delta_m'])
        self.assertFalse(c['same_native_entry_shift_proven'])

    def test_exact_threshold_no_new_tolerance(self):
        self.assertTrue(describe_request(.02, .02)['baseline_plan_reused'])
        self.assertFalse(describe_request(.02, math.nextafter(.02, math.inf))['baseline_plan_reused'])

    def test_invalid_values_are_unknown(self):
        for bad in (None, True, '0.02', math.nan, math.inf, -.001, .040001):
            for a,b in ((bad,.01),(.02,bad)):
                c = describe_request(a,b)
                self.assertEqual(c['status'], 'unknown')
                self.assertIsNone(c['selected_shift_m'])
                self.assertIsNone(c['task_success'])

    def test_pair_symmetry_and_no_outcome_claim(self):
        a,b = compare_requests(.02,.002,.01),compare_requests(.02,.01,.002)
        self.assertEqual(a['selected_shift_delta_m'], b['selected_shift_delta_m'])
        self.assertTrue(a['same_native_entry_shift_proven'])
        self.assertFalse(a['left']['execution_authorized'])
        self.assertIsNone(a['left']['task_success'])

    def test_negative_control_is_retained_not_screened_out(self):
        d = proposal_readiness(.02,.002,.01)
        self.assertEqual(d['predecision_stratum'], 'support_masked_negative_control')
        self.assertTrue(d['must_keep_registered_failure_and_masked_cases'])
        self.assertFalse(d['dispatch_enabled'])

    def test_translation_window_uses_signed_maximum_not_clipped_zero_request(self):
        # Original clipped requests are both zero, but their activation offsets differ.
        w = frozen_cloud_translation_window(0., -.640, -.632, .6, .020, 1.)
        self.assertEqual(w['status'], 'conditional_finite_cloud_window')
        self.assertAlmostEqual(w['lower_open_m'], .012)
        self.assertAlmostEqual(w['upper_closed_m'], .020)
        self.assertEqual(w['midpoint_requests']['left']['selected_shift_m'], 0.)
        self.assertFalse(w['midpoint_requests']['right']['baseline_plan_reused'])
        self.assertFalse(w['physical_state_validated'])

    def test_translation_window_does_not_invent_a_window_when_cap_prevents_it(self):
        for d0 in (.02,.04):
            w = frozen_cloud_translation_window(d0,-.64,-.64,.6,.02,1.)
            self.assertEqual(w['status'], 'no_positive_translation_window')
            self.assertIsNone(w['nominal_midpoint_m'])

    def test_window_agrees_with_finite_point_cloud_scalar(self):
        import numpy as np
        from pose_entry_selection import scalar_request
        a=.99;d0=.02
        w=frozen_cloud_translation_window(d0,-.617,-.610,.6,.02,a)
        delta=w['nominal_midpoint_m']
        for name,x in [('left',-.617),('right',-.610)]:
            result=scalar_request(np.array([[x+delta,0.,0.]]),[40],[.6,.6,.1],
                                  [a,0.,0.],.02,endpoint=False,swept=True)
            self.assertAlmostEqual(result['minimum_shift_m'],w['midpoint_requests'][name]['minimum_shift_m'])

    def test_translation_window_missing_maxima_or_invalid_axis_stays_unknown(self):
        for left,axis in [(None,1.),(-.64,.5),(-.64,float('nan'))]:
            self.assertEqual(frozen_cloud_translation_window(.02,left,-.61,.6,.02,axis)['status'], 'unknown')

    def test_branch_binding_rejects_semantic_drift(self):
        source = 'def prospective_entry():\n'+''.join('    '+x+'\n' for x in EXPECTED_SUFFIX.splitlines())
        self.assertIn('selection_branch_ast_sha256', verify_native_branch(source))
        for changed in (source.replace('minimum<=','minimum<'),
                        source.replace("baseline['shift_m']", "baseline['push_support_shift_m']",1),
                        source.replace('minimum_shift_m=minimum','minimum_shift_m=0.')):
            with self.assertRaises(ValueError): verify_native_branch(changed)


if __name__ == '__main__': unittest.main()
