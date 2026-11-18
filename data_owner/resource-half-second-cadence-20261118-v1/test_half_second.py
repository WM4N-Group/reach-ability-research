"""Four NEW half-second-contract fixtures; fake clock, no native/real lease."""
import ast,math,os,threading,time
from pathlib import Path
import unittest
from cadence_candidate import candidate
class PolicyStop(RuntimeError):pass
class State:
    sealed=False
    def __init__(self):self.reason=None
    def check(self):
        if self.reason:raise PolicyStop(self.reason)
    def fail(self,reason):
        if self.reason is None:self.reason=reason
        raise PolicyStop(self.reason)
def original_class():
    p=Path(__file__).resolve().parent.parent/'resource-start-cadence-20261118-v1/resource_watch.py'
    node=next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.ClassDef)and n.name=='ResourceWatch')
    ns=dict(os=os,threading=threading,time=time,math=math,PolicyStop=PolicyStop)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(p)+'[new-half-second-fake]','exec'),ns)
    return ns['ResourceWatch']
class HalfSecond(unittest.TestCase):
    def watch(self,body):
        clock=[0.];state=State();calls=[]
        def probe():calls.append(True);clock[0]+=body;return True
        w=original_class()(probe,state=state,token=object(),interval_s=.5,max_stale_s=2.,clock=lambda:clock[0])
        return w,clock,state,calls
    def test_default_off_and_no_authority(self):
        self.assertIsNone(candidate());c=candidate(enabled=True);self.assertEqual(c['resource_poll_s'],.5);self.assertEqual(c['resource_oldest_max_age_s'],2.);self.assertFalse(c['execution_permission'])
    def test_original_atomic_pair_still_actual_start_not_completion(self):
        w,c,s,calls=self.watch(.3);w.probe_once();self.assertEqual(w.last_observation_stamp,(0.,.3));self.assertEqual(calls,[True]);c[0]=2.1
        with self.assertRaises(PolicyStop):w.check(w.token)
        self.assertIn('oldest observation stale',s.reason)
    def test_original_single_overage_probe_still_refused(self):
        w,c,s,calls=self.watch(2.01)
        with self.assertRaises(PolicyStop):w.probe_once()
        self.assertIsNone(w.last_observation_stamp);self.assertEqual(calls,[True])
    def test_faster_cadence_does_not_guarantee_two_long_probes(self):
        # Pure deadline arithmetic, NOT replay of world or counterfactual proof
        # that changing the period will cure observed native latency.
        self.assertGreater(max(.5,1.003272701)+1.003272701,2.)
if __name__=='__main__':unittest.main()
