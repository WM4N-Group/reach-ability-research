"""CPU-only regression of SDK shutdown/authority bugs; never imports an SDK."""
import ast,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from sdk_evidence_io import persist_then_close

class SDKEvidenceTests(unittest.TestCase):
    def test_native_hard_exit_zero_still_leaves_pass_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'result.json'
            code="import os,sys;sys.path.insert(0,sys.argv[2]);from sdk_evidence_io import persist_then_close;persist_then_close(sys.argv[1],{'passed':True},lambda:os._exit(0))"
            r=subprocess.run([sys.executable,'-c',code,str(p),str(HERE)],capture_output=True)
            self.assertEqual(r.returncode,0)
            self.assertTrue(json.loads(p.read_text())['passed'])

    def test_native_exit_zero_cannot_promote_body_failure(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'result.json'
            code="import os,sys;sys.path.insert(0,sys.argv[2]);from sdk_evidence_io import persist_then_close;persist_then_close(sys.argv[1],{'passed':False,'error':'fixture'},lambda:os._exit(0))"
            r=subprocess.run([sys.executable,'-c',code,str(p),str(HERE)],capture_output=True)
            self.assertEqual(r.returncode,0)
            self.assertFalse(json.loads(p.read_text())['passed'])

    def test_shutdown_exception_is_not_silent(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'result.json'
            def close():raise RuntimeError('synthetic shutdown failure')
            with self.assertRaises(RuntimeError):persist_then_close(p,{'passed':True},close)
            self.assertFalse(json.loads(p.read_text())['passed'])

    def test_actual_sdk_catches_systemexit_and_writes_before_close(self):
        s=(HERE/'sdk_check.py').read_text();a=ast.parse(s)
        tr=next(n for n in a.body if isinstance(n,ast.Try))
        self.assertTrue(any(isinstance(h.type,ast.Name) and h.type.id=='BaseException' for h in tr.handlers))
        self.assertIn('persist_then_close',ast.unparse(tr.finalbody[-1]))
        self.assertIn('completed_variant_checks',s)

    def test_source_revision_approval_and_family_physical_claims_are_explicit(self):
        s=(HERE/'run_supervisor.py').read_text()
        self.assertIn('not covered by recorded approval',s)
        self.assertLess(s.index("auth_path=ROOT/'approval.json'"),s.index("claim(ROOT/'sdk.claim.json'"))
        self.assertIn("case_root/'physical_ledger.json'",s)
        self.assertIn("case_root/'claims'",s)

if __name__=='__main__':unittest.main()
