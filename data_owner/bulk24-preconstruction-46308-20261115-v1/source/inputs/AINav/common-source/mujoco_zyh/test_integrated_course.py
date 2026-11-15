"""Full-course task/frame contracts. Actual continuous success needs a rollout."""
import copy,json,os,sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
import numpy as np
from mujoco_zyh.integrated_course import plan,protocol,layout,validate_protocol,frame_classes,elevated_push_machine

class CourseContracts(unittest.TestCase):
    def test_every_variant_requires_same_full_chain_and_real_gap(self):
        cases=plan()['cases'];self.assertEqual(len(cases),5)
        self.assertEqual(len({json.dumps(c,sort_keys=True) for c in cases}),5)
        for c in cases:
            p=protocol(c);validate_protocol(p);g=layout(c)
            self.assertLess(g['bridge_initial_front']+c['bridge_length_m'],g['near_edge'])
            self.assertGreater(g['far_deck_front'],g['far_front']+.2)
            self.assertGreater(g['finish_x'],g['far_deck_front']+.8)
            self.assertFalse(p['automatic_retry']);self.assertEqual(p['reset_after_initial_allowed'],0)
            self.assertFalse(p['training_allowed'])
    def test_cannot_drop_crossing_or_change_geometry_without_new_registration(self):
        p=protocol(plan()['cases'][0]);p['integrated_case']=dict(p['integrated_case'],gap_width_m=0.)
        with self.assertRaises(ValueError):validate_protocol(p)
    def test_original_finish_200hz_checks_do_not_reobserve_50hz_progress_monitor(self):
        from mujoco_zyh.integrated_course import Prefix
        from unittest.mock import Mock
        p=object.__new__(Prefix);p.bmachine=NS(finish=object())
        flags={'box_settled':True};p.view_original_termination=Mock(return_value=flags)
        p.monitor=Mock();self.assertIs(Prefix.B_termination(p),flags)
        p.monitor.observe.assert_not_called()

    def test_soft_margin_does_not_change_or_hide_actual_effort_exceedance(self):
        from mujoco_zyh.integrated_course import weak_flags
        limits=np.ones(18)*10;v=NS(torque=limits.copy())
        before=v.torque.copy();flags=lambda:dict(invalid_hand_contact=False,arm_effort_safety=True)
        self.assertFalse(weak_flags(v,None,flags,limits)['arm_effort_safety'])
        self.assertTrue(np.array_equal(before,v.torque))
        v.torque[-1]=10.01
        self.assertTrue(weak_flags(v,None,flags,limits)['arm_effort_safety'])

    def test_elevated_finish_translates_control_references_not_physical_state(self):
        from mujoco_zyh.integrated_course import translated_finish_type
        class Native:
            def __init__(self,sim,config=None):
                self.anchors=np.zeros((4,3));self.anchors[:,2]=.022
                self.stand_com=np.array([0.,0.,.314])
        sim=NS(qpos=np.array([1.,2.,.714]));before=sim.qpos.copy()
        finish=translated_finish_type(Native,.4)(sim)
        self.assertTrue(np.allclose(finish.anchors[:,2],.422))
        self.assertAlmostEqual(finish.stand_com[2],.714)
        self.assertTrue(np.array_equal(sim.qpos,before))

    def test_bridge_traction_revision_preserves_unloaded_push_resistance(self):
        for c in plan()['cases'][1:]:
            p=protocol(c);m=p['registered_materials']['C_mass_kg'];mu=p['registered_materials']['C_bottom_mu']
            self.assertAlmostEqual(m*mu,1.*.3)
            self.assertGreater((21.765+m)*mu,(21.765+1.)*.3)

    def test_nav_height_translation_is_invariant_and_preserves_actual_commands(self):
        from mujoco_zyh.integrated_course import surface_nav_observation
        base=np.arange(210,dtype=np.float32)/100;ground=np.zeros((3,7));ground[:,2]=.4
        indices=189+np.arange(3)*7+2;base[indices]=.4
        high=base.copy();world=ground.copy();world[:,2]+=.6;high[indices]=world[:,2]
        before=world.copy();translated=surface_nav_observation(high,world,.6)
        self.assertTrue(np.array_equal(base,translated));self.assertTrue(np.array_equal(before,world))

    def load(self):
        from mujoco_zyh.runtime_adapter import construct_runtime
        p=protocol(plan()['cases'][0]);p.update(scenario='nav-nav',auxiliary_calibration_worlds_allowed=0,auxiliary_calibration_max_sim_seconds=0)
        return construct_runtime(os.environ['ZYH_BUNDLE'],p)[0]
    def test_far_bank_stop_lands_feet_using_references_without_state_or_queue_writes(self):
        from mujoco_zyh.integrated_course import FarBankStop
        r=self.load();p=protocol(plan()['cases'][0]);world=r.sim
        before=np.r_[world.data.qpos,world.data.qvel].copy()
        queue=[a.copy() for a in world.queue]
        actual_feet=np.array([world.data.xpos[world.model.body(n+'_foot').id] for n in ('FR','FL','RR','RL')])
        stop=FarBankStop(r,p)
        self.assertTrue(np.allclose(stop.native.anchors[:,2],.622))
        self.assertTrue(np.array_equal(stop.native.anchors[:,:2],actual_feet[:,:2]))
        self.assertTrue(np.allclose(stop.native.com_goal[:2],actual_feet[:,:2].mean(axis=0)))
        self.assertFalse(stop.ready)
        self.assertTrue(np.array_equal(before,np.r_[world.data.qpos,world.data.qvel]))
        self.assertEqual(len(queue),len(world.queue))
        self.assertTrue(all(np.array_equal(a,b) for a,b in zip(queue,world.queue)))

    def test_far_bank_hold_never_resumes_completed_nav_actor(self):
        from mujoco_zyh.integrated_course import IntegratedRouter
        from unittest.mock import Mock
        router=object.__new__(IntegratedRouter)
        router.cproxy=None;router.view=None;router.far_stop=Mock(ready=False)
        router.active=Mock();router.complete=False;router.stage='FAR_BANK_BRAKE'
        router.update()
        router.active.update.assert_not_called()
        router.far_stop.update.assert_called_once()
        self.assertFalse(router.complete)
        self.assertIs(router.next_command(),router.far_stop.command.return_value)
        router.active.next_command.assert_not_called()

    def test_elevated_entry_only_uses_registered_reference_translation(self):
        root=Path(os.environ['ZYH_BUNDLE']);sys.path.insert(0,str(root/'switch'))
        M=elevated_push_machine(root,[4.42,-1.8],.4)
        self.assertTrue(callable(M))
    def test_task_y_observation_equivalent_without_world_pose_writes(self):
        # Import the original pinned module through the existing plugin loader;
        # no simulator Runtime/actor or physics construction for this fixture.
        from mujoco_zyh.runtime_adapter import load_runtime_types
        p=protocol(plan()['cases'][0]);Runtime,Machine,plans,receipt=load_runtime_types(os.environ['ZYH_BUNDLE'],p)
        from plugins import Plugin
        plugin=Plugin('climb',['bridge','stop']);fake=NS(climb=plugin)
        lane=-1.8;Frame,Stop,receipt=frame_classes(fake,lane)
        cfg=dict(plugin['bridge'].load_contract()['configuration']['task'])
        def fake_state(y):
            q=np.zeros(25);q[:3]=[-.08,y,.33]
            return NS(cfg=cfg,data=NS(qpos=q,qvel=np.zeros(24)),qids=np.arange(7,25),dids=np.arange(6,24),
                feet_ids=np.arange(4),forces=np.zeros((4,3)),reference=np.zeros(18),actions=np.zeros(18),
                history=None,height=.2,gain=1.,state=lambda:(np.eye(3),np.array([0,0,-1]),0.,0.))
        centered=fake_state(0.);translated=fake_state(lane);before=translated.data.qpos.copy()
        original=plugin['bridge'].ClimbBridge.observation(centered);adapted=Frame.observation(translated)
        self.assertTrue(np.array_equal(original,adapted));self.assertTrue(np.array_equal(before,translated.data.qpos))
