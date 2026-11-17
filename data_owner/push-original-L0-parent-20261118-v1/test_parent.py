"""New L0 parent boundaries only; no model/physics/lease or old full suite."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys,unittest,subprocess,time
D=Path(__file__).resolve().parent
sys.path[:0]=[str(D),str(D.parent/'push-original-L0-entry-20261118-v1'),str(D.parent/'push-standard-parent-20261118-v1'),
 '/home/yuanyue/main/work/data-team/workers/new-critic-cohort-46308-20261115-v1/inputs/AINav/common-source']
from push_l0_driver import L0Case,driver_class,run_case
from connect_l0 import connect

class ParentBoundaries(unittest.TestCase):
    def test_default_off_is_silent_and_no_old_scope_authority_used(self):
        for name in ('worker.py','phase_control.py'):
            p=subprocess.run([sys.executable,'-I','-B',str(D/name)],capture_output=True,check=True)
            self.assertEqual((p.stdout,p.stderr),(b'',b''))
        self.assertIsNone(driver_class(enabled=False));self.assertIsNone(connect(enabled=False));self.assertIsNone(run_case(enabled=False))
    def test_no_NAV_or_second_selection(self):
        p=L0Case(lambda row:'fixture-journal')
        with self.assertRaises(ValueError):p.select(NS(options=[NS(skill='NAV')]))
        p.selected=object()
        with self.assertRaises(ValueError):p.select(NS(options=[NS(skill='PUSH')]))
    def test_expiry_not_success_or_Actor_failure(self):
        p=L0Case(lambda row:'fixture-journal');option=NS(sha256='a'*64);p.selected=option
        from ainav.native.behavior_authority import NativeReceipt
        p.observe(option,NativeReceipt('a'*64,60.,'budget_expired','b'*64,'explicit-software-fixture'))
        self.assertTrue(p.censored);self.assertFalse(p.failed);self.assertEqual(p.index,0)
    def test_fake_capture_boolean_cannot_be_L0_witness(self):
        with self.assertRaisesRegex(ValueError,'Genuine L0 witness'):
            connect(dict(runtime=object()),witness=NS(complete=True,actual_issued_steps=1301),enabled=True)
    def test_censored_owner_stops_without_a_further_command_and_seals(self):
        state=object();calls=[]
        b=NS(state=state,finalizing=False)
        def seal():b.finalizing=True
        b.begin_finalization=seal
        class Watch:
            def __call__(self):calls.append('guard')
        w=Watch();w.state=state
        driver=NS(r=NS(step_count=0,sim=NS(data=NS(time=0.))),complete=False,censored=True,
            planner=NS(receipts=[]),startup=NS(report=lambda:dict(software_fixture=True)),step_one=lambda:calls.append('FORBIDDEN'))
        r=run_case(driver,watch=w,budget=b,video=NS(capture_if_due=lambda:None),scope_start_mono=time.monotonic(),enabled=True)
        self.assertFalse(r['full_case_success']);self.assertNotIn('FORBIDDEN',calls);self.assertTrue(b.finalizing)
        self.assertEqual(r['stop_reason'],'ORIGINAL_60S_INTERVAL_CENSORED_NOT_ACTOR_FAILURE')

if __name__=='__main__':unittest.main()
