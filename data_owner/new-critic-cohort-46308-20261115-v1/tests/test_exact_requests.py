"""Software terminal-contract fixtures ONLY, not measured native receipts."""
from pathlib import Path
import sys,copy,unittest,ast
from types import SimpleNamespace as NS
W=Path(__file__).resolve().parents[1];sys.path.insert(0,str(W))
from request_contract import verify_completed_requests
class ExactRequests(unittest.TestCase):
 def setUp(self):
  self.expected=[dict(skill=s,target_ref=s,parameters={}) for s in ('NAV','PUSH','CLIMB')]
  self.planner=NS(requests=tuple(copy.deepcopy(self.expected)),complete=True,index=3,pending=None);self.events=[]
  for i,request in enumerate(self.expected):
   self.events += [dict(event='explicit_engineering_intent_requested',request_index=i,request=request,intent_sha256='intent'+str(i)),dict(event='intent_actual_native_outcome',execution_role='preparation',intent_succeeded=False),dict(event='intent_actual_native_outcome',execution_role='interaction',intent_sha256='intent'+str(i),native_option_sha256='native'+str(i),receipt=dict(option_sha256='native'+str(i),status='succeeded',evidence_ref='SOFTWARE#'+str(i)),intent_succeeded=True),dict(event='engineering_intent_actual_result',intent_sha256='intent'+str(i),native_option_sha256='native'+str(i),actual_status='succeeded',receipt_ref='SOFTWARE#'+str(i),binding_ref='SOFTWARE-BIND#'+str(i))]
 def test_exact3_ignores_preparation(self):self.assertEqual(verify_completed_requests(self.planner,self.expected,self.events)['exact_requested_semantic_success_count'],3)
 def test_index2_rejected(self):
  self.planner.index=2
  with self.assertRaises(ValueError):verify_completed_requests(self.planner,self.expected,self.events)
 def test_omitted_NAV_rejected(self):
  with self.assertRaises(ValueError):verify_completed_requests(self.planner,self.expected,self.events[4:])
 def test_failed_receipt_rejected(self):
  self.events[2]['receipt']['status']='failed'
  with self.assertRaises(ValueError):verify_completed_requests(self.planner,self.expected,self.events)
 def test_wrong_option_rejected(self):
  self.events[2]['receipt']['option_sha256']='foreign'
  with self.assertRaises(ValueError):verify_completed_requests(self.planner,self.expected,self.events)
 def test_wrong_goal_rejected(self):
  self.events[0]['request']=dict(self.expected[0],parameters={'goal_world_y_m':123})
  with self.assertRaises(ValueError):verify_completed_requests(self.planner,self.expected,self.events)
 def test_reorder_rejected(self):
  self.events[2],self.events[3]=self.events[3],self.events[2]
  with self.assertRaises(ValueError):verify_completed_requests(self.planner,self.expected,self.events)
 def test_no_old_worker_or_native_step_change(self):
  s=(W/'full_host_worker.py').read_text();ast.parse(s)
  self.assertNotIn('planner.index==2',s);self.assertIn('max_requests=3',(W/'prepare_prefix.py').read_text());self.assertIn("candidate_id=plan['preparation_payload']['candidate_id']",s)
  self.assertIn('verify_completed_requests(planner',s);self.assertNotIn('mj_step(',s);self.assertNotIn('runtime.step(',s)
if __name__=='__main__':unittest.main()
