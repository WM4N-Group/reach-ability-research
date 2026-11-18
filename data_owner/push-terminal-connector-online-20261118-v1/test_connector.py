"""Targeted synthetic fixtures, optionally with the actual pinned native class."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS
import os
import sys
import unittest

from terminal_action import BrakeAction, brake_eligible
from native_connector import new_machine_class, factory_class, FACTORY_SHA, INHERITED
from episode_feedback import reward, TrainAttempt
from policy_update import PolicyState, collect_gradient, apply_gradient

PROGRAM = 'a'*64
ANC = frozenset({'MOCK-TRAIN-ONLY'})
CASE = NS(mode='uncompensated', source_surface_height_m=0., box_size_m=(1.2, 1.2, .2),
          public_goal_xy_m=(1.7,0.), public_XY_tolerance_m=.02)
ZERO = BrakeAction(0,0.)
EARLY = BrakeAction(1,.08)  # software test value, not a selected live action


def measurement():
    return dict(placement_geometry_verified=False, task_geometry_pass=False, actual_box_position_m=(1.64,0.,.1),
                actual_box_linear_velocity_m_s=(.20,0.,0.), actual_signed_dock_gap_m=.06, time_s=15.)


class Tests(unittest.TestCase):
    def test_only_finite_inward_current_contact(self):
        kw = dict(actual_legal_hand=True, contact_seen=True)
        self.assertTrue(brake_eligible(EARLY, measurement(), CASE, **kw))
        self.assertFalse(brake_eligible(ZERO, measurement(), CASE, **kw))
        self.assertFalse(brake_eligible(EARLY, measurement(), CASE, actual_legal_hand=False, contact_seen=True))
        for patch in (dict(actual_signed_dock_gap_m=-.01), dict(actual_box_linear_velocity_m_s=(0.,0.,0.)),
                      dict(placement_geometry_verified=True),dict(actual_box_position_m=(1.64,.03,.1))):
            self.assertFalse(brake_eligible(EARLY, dict(measurement(),**patch), CASE, **kw))
        with self.assertRaises(ValueError):brake_eligible(EARLY,dict(measurement(),actual_signed_dock_gap_m=float('nan')),CASE,**kw)

    def test_training_selection_and_update(self):
        policy=PolicyState((0.,0.));key=policy.fingerprint()
        row=TrainAttempt('mock-success',EARLY,'PUSH_TERMINAL_ONLINE_TRAIN_ONLY','MOCK-TRAIN-ONLY',True,True,
            'ORIGINAL_FULL_PUSH_SUCCESS',True,True,True,None,False,'b'*64,PROGRAM,key)
        bad=replace(row,rollout_id='mock-reject',used_action=ZERO,outcome='ORIGINAL_PHYSICAL_TERMINAL_REJECTION',
                    full_native_terminal_succeeded=False,original_placement_verified_at_terminal=False,
                    exact_guard_rejection_stage='IMMUTABLE_PLACEMENT_LOST_AFTER_STOW')
        censored=replace(bad,rollout_id='mock-resources',resource_or_engineering_failure=True)
        with self.assertRaises(ValueError):reward(replace(row,purpose='DEV'),registered_program=PROGRAM,allocated_ancestors=ANC)
        with self.assertRaises(ValueError):reward(replace(row,original_stow_verified_at_terminal=False),registered_program=PROGRAM,allocated_ancestors=ANC)
        self.assertIsNone(reward(replace(bad,exact_guard_rejection_stage='UNKNOWN'),registered_program=PROGRAM,allocated_ancestors=ANC))
        kw=dict(registered_program=PROGRAM,allocated_ancestors=ANC,used_rollout_ids=set())
        g,accepted,censor=collect_gradient(policy,(ZERO,EARLY),(row,bad,censored),**kw)
        self.assertEqual(accepted,('mock-success','mock-reject'));self.assertEqual(censor,('mock-resources',))
        nxt=apply_gradient(policy,g,len(accepted),rate=.10);self.assertGreater(nxt.probabilities()[1],.5)
        self.assertEqual(nxt.update_count,1)
        with self.assertRaises(ValueError):collect_gradient(nxt,(ZERO,EARLY),(row,),**kw)
        with self.assertRaises(ValueError):collect_gradient(policy,(ZERO,EARLY),(row,row),**kw)
        with self.assertRaises(ValueError):apply_gradient(policy,g,0,rate=.10)

    @unittest.skipUnless(os.environ.get('PUSH_ORIGINAL_SOURCE_ROOT'), 'Original source only on compute server')
    def test_exact_native_adapter_callbacks(self):
        src=Path(os.environ['PUSH_ORIGINAL_SOURCE_ROOT']);sys.path.insert(0,str(src))
        from ainav.native.placement_handoff import TwoPhasePlacementMachine as Base
        from ainav.native.registered_skill_factory import RegisteredSkillSessionFactory
        from mujoco_zyh.native_behavior_executor import world_snapshot
        calls=[];events=[];good=False
        def legal(*_):calls.append('hand');return (good,)
        def begin(*,confirmed):
            calls.append('original guarded begin');self.assertFalse(confirmed)
            return NS(complete=False,update=lambda:calls.append('brake update')),dict(guard_fixture=True)
        n=NS(phase='startup',index=-1,finish=None,update=lambda:calls.append('old native update'),
             r=NS(push={'bridge':NS(box_push=NS(hand_contact=legal))}))
        s=NS(native=n,contract=CASE,p=NS(hand_cfg=object()),assert_immutable=lambda:None,
             measure=measurement,clock_report=lambda:dict(native_contact_seen=True),native_ready=lambda:False,begin_brake=begin)
        real=NS(machine=Base(n,s,events.append),entered=False);s.session=real
        cls=new_machine_class(source_root=src,enabled=True)
        self.assertTrue(all(getattr(cls,k) is getattr(Base,k) for k in INHERITED))
        self.assertIsNone(new_machine_class())
        self.assertTrue(issubclass(factory_class(RegisteredSkillSessionFactory,source_root=src,
            factory_sha256=FACTORY_SHA,action=EARLY,world_snapshot=world_snapshot,enabled=True), RegisteredSkillSessionFactory))
        m=cls.attach_pristine(real,EARLY);self.assertIs(m.services,s);self.assertIs(m.native,n)
        real.entered=True;n.phase='run';m.update();self.assertEqual(calls,['hand','old native update'])
        good=True;m.update();self.assertEqual(calls[-3:],['hand','original guarded begin','brake update'])
        self.assertEqual(sum(e['event']=='connector_early_brake_requested' for e in events),1)
        self.assertFalse(m.complete) # even after the guarded begin, no fabricated terminal
        with self.assertRaises(RuntimeError):cls.attach_pristine(real,EARLY)
        # Teach the same class the baseline action without asking for synthetic contact.
        real.entered=False;n.phase='startup';real.machine=Base(n,s,events.append)
        m=cls.attach_pristine(real,ZERO);n.phase='run';calls.clear();m.update();self.assertEqual(calls,['old native update'])

if __name__=='__main__':unittest.main(verbosity=2)
