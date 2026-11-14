import unittest
import numpy as np
from mujoco_zyh.integrated_decision_contract import validate_query,DecisionGateway

class DecisionContractTests(unittest.TestCase):
    def query(self):
        commands=np.arange(40*90,dtype=np.float64).reshape(40,5,18)/1000
        obs=dict(rgb=np.zeros((1,3,4,6,3),np.uint8),depth_m=np.ones((1,3,4,6,1)),camera_K=np.eye(3)[None],T_base_optical=np.eye(4)[None],proprio=np.zeros((1,3,45)),actions_previous=np.array([[np.zeros(18),commands[19,0],commands[39,0]]]),action_valid=np.array([[False,True,True]]),timestamps_s=np.array([[0.,.1,.2]]))
        return dict(history=dict(observations=obs,issued_commands=commands,physical_ticks=np.arange(1,41),command_times_s=np.arange(1,41)*.005),candidate_tokens=('opaque-0','opaque-1'),macro_intents=np.array([[0,1,0,0,0,.3,.4,.6],[0,1,0,0,0,.6,.4,.6]]),durations_s=np.array([.5,1.]),anchor_time_s=.2,decision_id='boundary0')
    def gateway(self,journal):
        return DecisionGateway(lambda q:dict(selected_token=q['candidate_tokens'][1],candidate_costs=dict(zip(q['candidate_tokens'],[2.,1.])),model_checkpoint_sha256='a'*64),journal.append)
    def test_causal_public_query_and_exact_actual_model_dispatch(self):
        q=self.query();validate_query(q);journal=[];g=self.gateway(journal)
        self.assertEqual(g.request(q),'opaque-1')
        with self.assertRaises(ValueError):g.acknowledge_dispatch('boundary0','opaque-0',.22)
        g.acknowledge_dispatch('boundary0','opaque-1',.22)
        self.assertEqual(len(journal),2);self.assertFalse(journal[0]['actually_dispatched']);self.assertFalse(journal[1]['native_success_inferred'])
        with self.assertRaises(ValueError):g.request(q)
    def test_private_or_future_fields_and_future_command_prefix_rejected(self):
        for key in ('mass_kg','future_commands','scene_alias','target_pose_truth'):
            q=self.query();q[key]=0
            with self.assertRaises(ValueError):validate_query(q)
        q=self.query();q['history']['physical_ticks'][-1]=41
        with self.assertRaises(ValueError):validate_query(q)
        q=self.query();q['history']['observations']['timestamps_s'][0,-1]=.3
        with self.assertRaises(ValueError):validate_query(q)
    def test_original_push_goal_is_not_rebased_to_remaining_or_new_distance(self):
        q=self.query();q['macro_intents'][0,7]=.2
        with self.assertRaises(ValueError):validate_query(q)
        q=self.query();q['history']['observations']['timestamps_s']+=.1;q['anchor_time_s']+=.1
        with self.assertRaises(ValueError):validate_query(q)
    def test_invalid_model_response_cannot_fallback_to_script_choice(self):
        for response in (None,dict(selected_token='opaque-0',candidate_costs={'opaque-0':2.,'opaque-1':1.},model_checkpoint_sha256='a'*64)):
            g=DecisionGateway(lambda q:response,lambda e:None)
            with self.assertRaises(ValueError):g.request(self.query())
    def test_query_mutation_and_missing_command_interval_rejected(self):
        def bad(q):q['history']['observations']['rgb'][0,0,0,0,0]=1;return {}
        with self.assertRaises(ValueError):DecisionGateway(bad,lambda e:None).request(self.query())
        q=self.query();q['history']['issued_commands']=q['history']['issued_commands'][1:]
        with self.assertRaises(ValueError):validate_query(q)
    def test_single_candidate_reports_wiring_only_not_selection_benefit(self):
        q=self.query();q.update(candidate_tokens=('only',),macro_intents=q['macro_intents'][:1],durations_s=q['durations_s'][:1]);journal=[]
        g=DecisionGateway(lambda q:dict(selected_token='only',candidate_costs={'only':1.},model_checkpoint_sha256='b'*64),journal.append)
        self.assertEqual(g.request(q),'only');self.assertTrue(journal[0]['single_candidate_only']);self.assertFalse(journal[0]['selection_benefit_claimed'])
