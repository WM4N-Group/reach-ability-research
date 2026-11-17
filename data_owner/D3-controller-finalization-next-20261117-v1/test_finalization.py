import ast
from pathlib import Path
import sys,tempfile,unittest
HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),'/home/yuanyue/main/code/reach-ability-research/data_owner/PERF-01-NAV2000-20261116-v1/policy']
from source_candidate import derive,OLD,NEW
from scoped_io import ScopeIO,StopState,PolicyStop
from runner_outputs import write_json

class Tests(unittest.TestCase):
    def test_actual_latched_nonzero_child_can_write_bounded_final_proof_after_seal(self):
        with tempfile.TemporaryDirectory()as td:
            b=ScopeIO(td,cap_bytes=262144,reserve_bytes=65536,state=StopState(),max_open=4)
            try:b.state.fail('Controlled child nonzero exit: 1')
            except PolicyStop:pass
            with self.assertRaises(PolicyStop):write_json(b,Path(td)/'before.json',{'test':True})
            b.begin_finalization();write_json(b,Path(td)/'after.json',{'test':True})
            self.assertTrue(b.state.sealed);self.assertIsNotNone(b.state.reason);self.assertTrue((Path(td)/'after.json').is_file())
    def test_default_OFF_and_one_exact_source_site_no_callback_or_guard_change(self):
        self.assertEqual(derive(b'not read'),b'not read')
        p=HERE.parent/'D3-first-native-diagnostic-20261117-v1/phase_control.py';original=p.read_bytes();new=derive(original,enabled=True).decode();ast.parse(new)
        self.assertEqual(new.replace(NEW,OLD,1).encode(),original)
        self.assertIn('scope_active=json.loads(H.read_bytes())[KEY]',new)

if __name__=='__main__':unittest.main(verbosity=2)
