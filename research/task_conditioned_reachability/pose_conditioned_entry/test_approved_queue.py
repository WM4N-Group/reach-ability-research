"""Pure scheduling-order fixtures, no subprocess/App/GPU/FK or budget mutation."""
import unittest
from queue_approved_release import sequence

class QueueTests(unittest.TestCase):
    def run_fixture(self,waits,rcs,fail_gate=False):
        events=[]
        def wait(mode):events.append(('wait',mode));return waits[mode]
        def launch(mode):events.append(('launch',mode));return rcs[mode]
        def gate():
            events.append(('gate','sdk'))
            if fail_gate:raise PermissionError('synthetic incomplete gate')
        def evaluate():events.append(('evaluate','physical'))
        result=sequence(wait,launch,gate,evaluate,lambda status:events.append(('record',status)))
        return result,events
    def test_busy_resource_never_launches(self):
        result,events=self.run_fixture({'sdk':False},{})
        self.assertEqual(result,'WAIT_TIMEOUT_NO_SDK_CLAIM');self.assertEqual(events,[('wait','sdk')])
    def test_sdk_failure_never_launches_physical(self):
        result,events=self.run_fixture({'sdk':True},{'sdk':1})
        self.assertIn('SDK_SUPERVISOR_FAILURE',result);self.assertNotIn(('launch','physical'),events)
    def test_incomplete_sdk_gate_raises_before_physical(self):
        with self.assertRaises(PermissionError):self.run_fixture({'sdk':True},{'sdk':0},True)
    def test_second_resource_wait_never_claims_physical(self):
        result,events=self.run_fixture({'sdk':True,'physical':False},{'sdk':0})
        self.assertIn('UNSPENT_PHYSICAL',result);self.assertNotIn(('launch','physical'),events)
    def test_complete_order_and_evaluation(self):
        result,events=self.run_fixture({'sdk':True,'physical':True},{'sdk':0,'physical':0})
        self.assertEqual(result,'COMPLETED_APPROVED_SEQUENCE')
        self.assertLess(events.index(('gate','sdk')),events.index(('launch','physical')))
        self.assertEqual(events[-1],('evaluate','physical'))
    def test_physical_stop_is_not_retried_and_is_evaluated(self):
        result,events=self.run_fixture({'sdk':True,'physical':True},{'sdk':0,'physical':1})
        self.assertEqual(result,'PHYSICAL_STOPPED_PRESERVE_UNSPENT')
        self.assertEqual(events.count(('launch','physical')),1);self.assertEqual(events[-1],('evaluate','physical'))

if __name__=='__main__':unittest.main()
