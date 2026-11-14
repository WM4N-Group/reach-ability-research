"""Do not accept failed or source-changing supplementary evaluation attempts."""
import unittest
from audit_piper_v212_frozen_margin import verify_exit_status


class FrozenMarginExitChecks(unittest.TestCase):
    def test_success_requires_clean_frozen_sources(self):
        verify_exit_status(dict(returncode=0,all_expected_sources_unchanged=True,changed_sources=[]))

    def test_failed_launch_is_not_a_prediction_result(self):
        with self.assertRaises(ValueError):
            verify_exit_status(dict(returncode=1,all_expected_sources_unchanged=True,changed_sources=[]))

    def test_changed_checkpoint_invalidates_successful_exit(self):
        with self.assertRaises(ValueError):
            verify_exit_status(dict(returncode=0,all_expected_sources_unchanged=False,changed_sources=['model.pt']))


if __name__=='__main__':unittest.main()
