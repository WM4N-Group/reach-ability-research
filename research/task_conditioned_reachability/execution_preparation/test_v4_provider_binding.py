"""Public-config/source-only checks, no environment/key/API/transport calls."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from .v4_provider_binding import runtime_binding, original_full_course_limits

ROOT=Path(__file__).resolve().parents[3]
PROFILE=ROOT/'protocols/2026-11-15/T-COMPLEX-01-V4-five-arm-methods-v1/VLM_PROFILE.json'
SOURCE=ROOT/'owner_snapshot/native-prefix-20261114/inputs/AINav/common-source/ainav/deepseek.py'


class V4ProviderTests(unittest.TestCase):
    def binding(self,**kw):return runtime_binding(PROFILE,original_backend_path=SOURCE,**kw)
    def test_exact_TLS_profile_returns_original_kwargs_not_backend(self):
        b=self.binding();self.assertEqual(b['kwargs']['max_calls'],100)
        self.assertTrue(b['kwargs']['verify_models']);self.assertFalse(b['backend_constructed'])
        self.assertEqual(b['kwargs']['max_total_tokens'],900000)
        self.assertFalse(b['all_four_actual_backend_instances_compared'])
        self.assertNotIn('api_key',b['kwargs']);self.assertEqual(b['actual_API_calls'],0)
    def test_prior256_proposal_is_not_valid_original_constructor_input(self):
        with self.assertRaisesRegex(ValueError,'constructor limits'):self.binding(max_calls=256)
    def test_bool_or_zero_or_101_not_accepted_as_API_cap(self):
        for value in (True,0,101):
            with self.assertRaises(ValueError):self.binding(max_calls=value)
    def test_profile_change_or_HTTP_fallback_rejected(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'PUBLIC_PROFILE.json';p.write_bytes(PROFILE.read_bytes().replace(b'https:',b'http:'))
            with self.assertRaises(ValueError):runtime_binding(p,original_backend_path=SOURCE)
    def test_other_backend_source_not_silently_selected(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'backend.py';p.write_bytes(SOURCE.read_bytes()+b'\n')
            with self.assertRaises(ValueError):runtime_binding(PROFILE,original_backend_path=p)
    def test_no_credential_environment_is_inspected(self):
        with patch('os.environ.get',side_effect=AssertionError('NO_CREDENTIAL_READ')):
            b=self.binding();self.assertFalse(b['credentials_read_or_persisted'])
    def test_same_explicit_limits_for_all_calling_arms_not_fake_E_consumption(self):
        rows=[self.binding()for _ in 'ABCD'];self.assertTrue(all(r['kwargs']==rows[0]['kwargs']for r in rows))
        self.assertTrue(all(r['E_calls']==0 for r in rows))
    def test_backend_legal_but_nonmatching_arm_cap_does_not_pass_shared_V4_binding(self):
        for kwargs in (dict(max_calls=72),dict(max_tokens=4096),dict(max_total_tokens=1000000)):
            with self.assertRaisesRegex(ValueError,'same original full-course'):
                self.binding(**kwargs)
    def test_original_full_course_profile_is_parsed_not_executed(self):
        full=SOURCE.parent.parent/'run_full_course.py'
        self.assertEqual(original_full_course_limits(full),
            dict(max_calls=100,max_tokens=8192,max_total_tokens=900000))
        with patch('builtins.exec',side_effect=AssertionError('NO_LAUNCHER_EXECUTION')):
            self.assertEqual(self.binding()['original_full_course_api_limits']['max_total_tokens'],900000)
    def test_changed_full_course_profile_or_other_launcher_rejected(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'run_full_course.py';p.write_bytes((SOURCE.parent.parent/'run_full_course.py').read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'profile source'):
                self.binding(original_full_course_path=p)
    def test_reply_or_total_token_bounds_not_unlimited(self):
        for kw in (dict(max_tokens=8193),dict(max_total_tokens=1000001)):
            with self.assertRaises(ValueError):self.binding(**kw)


if __name__=='__main__':unittest.main()
