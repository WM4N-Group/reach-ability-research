"""Only two postclosure SOURCE checks; no native/old suite or canonical lock use."""
from pathlib import Path
import subprocess
import sys
import unittest
sys.path[:0]=[str(Path(__file__).resolve().parent),str(Path(__file__).resolve().parent.parent/'push-standard-parent-20261118-v1')]
from standard_runtime import bounded_exception

class FutureDeltas(unittest.TestCase):
    def test_compound_line_preserves_the_actual_call_column_not_locals(self):
        def leaf():
            harmless=1; int('not-an-int'); unused=2
        try:leaf()
        except ValueError as exc:report=bounded_exception(exc)
        frame=report['frames'][-1];span=frame['source_position']
        source=Path(__file__).read_text().splitlines()[span['start_line']-1]
        self.assertEqual(source[span['start_column']:span['end_column']],"int('not-an-int')")
        self.assertIsInstance(frame['instruction_offset'],int)
        self.assertNotIn('harmless',str(report));self.assertFalse(report['exception_text_locals_or_headers_recorded'])

    def test_physical_shell_handoff_must_stop_after_a_failed_precheck(self):
        p=subprocess.run(['bash','-e','-u','-o','pipefail','-c',
            "python3 -c 'raise AssertionError(\"fixture precheck\")'; printf SHOULD_NOT_HAND_OFF"],capture_output=True)
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(p.stdout,b'')

if __name__=='__main__':unittest.main()
