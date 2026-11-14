import copy,unittest
from unittest.mock import Mock
from types import SimpleNamespace as NS
import numpy as np
import torch
from mujoco_zyh.nav_parameter_training import plan,protocol,validate,install
from mujoco_zyh.collect import validate_protocol
from mujoco_zyh.observer import OnboardObserver

class ParameterInterventionTests(unittest.TestCase):
    def tasks(self):return [dict(skill='nav',goal=[.05,-2.]),dict(skill='climb',surface='B',approach=[.05,-2.]),dict(skill='nav',goal=[2.55,-2.]),dict(skill='climb',surface='HIGH',approach=[2.55,-2.]),dict(skill='nav',goal=[6.42,-2.])]
    def test_only_assigned_first_NAV_goal_changes_and_original_tasks_retained(self):
        for row in plan()['cases']:
            p=protocol(row);validate_protocol(p);native=Mock();r=NS(start_chunk=native,event=Mock());install(r,p)
            tasks=self.tasks();before=copy.deepcopy(tasks);r.start_chunk(tasks,'B_STEP_HIGH_PLATFORM');actual=native.call_args.args[0]
            self.assertAlmostEqual(actual[0]['goal'][0],.05+row['nav_step_delta_world_x_m'])
            self.assertEqual(actual[1:],before[1:]);self.assertEqual(tasks,before)
            with self.assertRaises(ValueError):r.start_chunk(tasks,'B_STEP_HIGH_PLATFORM')
    def test_later_bridge_NAV_never_receives_first_NAV_intervention(self):
        p=protocol(plan()['cases'][0]);native=Mock();r=NS(start_chunk=native,event=Mock());install(r,p)
        tasks=[dict(skill='nav',goal=[6.55,-2.])];r.start_chunk(tasks,'BRIDGE_CLIMB_AND_CROSS')
        self.assertIs(native.call_args.args[0],tasks);self.assertEqual(tasks[0]['goal'][0],6.55)
    def test_roles_assignment_stream_and_budgets_are_frozen(self):
        for row in plan()['cases']:
            p=protocol(row);self.assertEqual(p['role'],'train');self.assertTrue(p['training_allowed']);self.assertFalse(p['WM_control'])
            self.assertEqual(p['public_control_proprio_hz'],50);self.assertFalse(p['automatic_retry']);self.assertEqual(p['training_runs'],0)
            for key,value in [('seed',1),('public_control_proprio_hz',10),('role','test')]:
                q=copy.deepcopy(p);q[key]=value
                with self.assertRaises(ValueError):validate(q)
    def test_public_body_sample_reads_original_sensor_channels_without_pose_or_writes(self):
        sensors=NS(projected_gravity_b=torch.tensor([[0.,0.,-1.]]),root_ang_vel_b=torch.tensor([[1.,2.,3.]]),root_lin_vel_b=torch.tensor([[4.,5.,6.]]))
        observer=object.__new__(OnboardObserver);observer.r=NS(sim=NS(robot=NS(data=sensors)))
        result=observer.public_body_proprio();self.assertTrue(np.array_equal(result,[0,0,-1,1,2,3,4,5,6]))
        result[:]=0;self.assertEqual(float(sensors.root_lin_vel_b[0,0]),4.)
