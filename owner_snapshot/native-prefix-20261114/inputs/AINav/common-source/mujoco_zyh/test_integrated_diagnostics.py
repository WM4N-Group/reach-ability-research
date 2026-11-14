import unittest
import torch
from mujoco_zyh.diagnose_integrated_world_model import ablate_future,motion_bucket

class FrozenDiagnosticContracts(unittest.TestCase):
    def test_future_only_ablation_keeps_original_and_all_context_commands(self):
        a=torch.arange(2*24*1800,dtype=torch.float32).reshape(2,24,1800);original=a.clone()
        zero=ablate_future(a,5,'training_mean_future_commands')
        self.assertTrue(torch.equal(a,original));self.assertTrue(torch.equal(zero[:,:4],a[:,:4]))
        self.assertTrue(torch.equal(zero[:,4:],torch.zeros_like(zero[:,4:])))
        reverse=ablate_future(a,5,'reverse_future_200Hz_substep_order')
        self.assertTrue(torch.equal(reverse[:,:4],a[:,:4]))
        self.assertTrue(torch.equal(reverse[:,4:].reshape(2,20,20,90)[:,:,0],a[:,4:].reshape(2,20,20,90)[:,:,-1]))
        swap=ablate_future(a,5,'swap_future_command_intervals_across_windows')
        self.assertTrue(torch.equal(swap[:,:4],a[:,:4]));self.assertTrue(torch.equal(swap[0,4:],a[1,4:]))
    def test_motion_categories_are_fixed_before_diagnostic(self):
        self.assertTrue(motion_bucket(.0009).startswith('near_static'))
        self.assertTrue(motion_bucket(.001).startswith('intermediate'))
        self.assertTrue(motion_bucket(.01).startswith('intermediate'))
        self.assertTrue(motion_bucket(.011).startswith('moving'))
