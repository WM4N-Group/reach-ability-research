"""Synthetic three-cell continuation checks; no SDK, subprocess or physics."""
import copy
from pathlib import Path
from test_followup import Fixture,write,sha
from continue_unstarted import continue_three

class ContinuationTests(Fixture):
    def stop_three(self):
        self.approve_fixture();self.sdk_fixture();calls=0
        def gpu():
            nonlocal calls
            calls+=1
            return 'OTHER_OWNER' if calls>=5 else ''
        state=self.s.dispatch(self.root,'physical',gpu_busy=gpu,runner=self.fake_runner,external=lambda r:None)
        self.assertEqual(state['starts'],3);self.assertEqual(state['status'],'STOPPED_GPU_BUSY_UNSPENT_RESERVED')
        self.stopped=copy.deepcopy(state);self.ledger_sha=sha(self.root/'physical_ledger.json');self.source_sha=sha(self.source/'manifest.json')
        self.stop_bytes=(self.root/'physical_ledger.json').read_bytes()
    def run_remaining(self,**kwargs):
        return continue_three(self.root,self.ledger_sha,self.source_sha,'EXPLICIT SYNTHETIC USER REQUEST',self.a,self.s,
                              runner=kwargs.get('runner',self.fake_runner),gpu_busy=kwargs.get('gpu_busy',lambda:''),external=lambda r:None)
    def test_only_three_unstarted_are_consumed_and_existing_prefix_unchanged(self):
        self.stop_three();called=[]
        def runner(*args):called.append(args[2]['output_name']);return self.fake_runner(*args)
        result=self.run_remaining(runner=runner)
        self.assertEqual(result['status'],'COMPLETED_REGISTERED_SIX');self.assertEqual(result['starts'],6)
        self.assertEqual(result['entries'][:3],self.stopped['entries'])
        self.assertEqual(called,[x['output_name'] for x in self.p['schedule'][3:]])
        self.assertEqual((self.root/'continuations/explicit-unstarted-v1/stopped-ledger.original.json').read_bytes(),self.stop_bytes)
        self.assertEqual(len(list((self.family/'pose_allocations').glob('*/reservation.json'))),2)
    def test_second_continuation_cannot_repeat_cases(self):
        self.stop_three();self.run_remaining()
        with self.assertRaises(PermissionError):self.run_remaining()
    def test_still_busy_consumes_nothing(self):
        self.stop_three()
        with self.assertRaisesRegex(RuntimeError,'GPU busy'):self.run_remaining(gpu_busy=lambda:'OTHER_OWNER')
        self.assertEqual((self.root/'physical_ledger.json').read_bytes(),self.stop_bytes)
        self.assertFalse((self.root/'continuations').exists())
    def test_technical_stop_not_resumable(self):
        self.stop_three();v=self.a.load(self.root/'physical_ledger.json');v['status']='STOPPED_TECHNICAL_OR_SEVERE_NO_RETRY';write(self.root/'physical_ledger.json',v);self.ledger_sha=sha(self.root/'physical_ledger.json')
        with self.assertRaisesRegex(PermissionError,'resource-only'):self.run_remaining()
    def test_pending_output_not_retried(self):
        self.stop_three();(self.root/'runs'/self.p['schedule'][3]['output_name']).mkdir()
        with self.assertRaisesRegex(PermissionError,'already has evidence'):self.run_remaining()
    def test_orphan_claim_not_retried(self):
        self.stop_three();claims=self.a.phase_directory(self.p)/'physical_claims';write(claims/(self.p['schedule'][3]['output_name']+'.json'),{})
        with self.assertRaisesRegex(PermissionError,'Claims'):self.run_remaining()
    def test_changed_completed_raw_blocks_continuation(self):
        self.stop_three();(self.root/'runs'/self.p['schedule'][0]['output_name']/'report.json').write_text('{}')
        with self.assertRaisesRegex(PermissionError,'evidence changed'):self.run_remaining()
    def test_changed_source_blocks_continuation(self):
        self.stop_three();(self.source/'scene_contract.py').write_text('# drift')
        with self.assertRaises(PermissionError):self.run_remaining()
    def test_nonprefix_schedule_blocks_continuation(self):
        self.stop_three();v=self.a.load(self.root/'physical_ledger.json');v['not_run'].reverse();write(self.root/'physical_ledger.json',v);self.ledger_sha=sha(self.root/'physical_ledger.json')
        with self.assertRaises(PermissionError):self.run_remaining()
    def test_new_technical_failure_stops_remaining_without_retry(self):
        self.stop_three();result=self.run_remaining(runner=lambda *args:dict(returncode=1))
        self.assertEqual(result['starts'],4);self.assertEqual(len(result['not_run']),2)
        self.assertEqual(result['status'],'STOPPED_TECHNICAL_OR_SEVERE_NO_RETRY')
    def test_resource_loss_between_cells_preserves_unspent(self):
        self.stop_three();n=0
        def gpu():
            nonlocal n
            n+=1
            return 'OTHER_OWNER' if n==3 else ''
        result=self.run_remaining(gpu_busy=gpu)
        self.assertEqual(result['starts'],4);self.assertEqual(len(result['not_run']),2)
        self.assertEqual(result['status'],'STOPPED_GPU_BUSY_UNSPENT_RESERVED')
