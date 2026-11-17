"""Only new loop/health/receipt CPU fixtures; no robot/backend/lease/world."""
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
B=Path('/home/yuanyue/main/work/data-team/development/perf-resource-policy-20261116-v1')
if not B.is_dir():B=Path(__file__).resolve().parent.parent/'PERF-01-NAV2000-20261116-v1/policy'
sys.path.insert(0,str(B))
from scoped_io import ScopeIO, PolicyStop
from resource_watch import ResourceWatch
from task_loop import MainLimits, LoopError, make_cd_phase_health, run_task


class WatchFixture:
    def __init__(self,state,health):self.state=state;self.fast_health=health;self.calls=0
    def __call__(self):
        self.state.check();self.calls+=1;return self.fast_health()


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='data-CD-loop-CPU-')
        self.b=ScopeIO(Path(self.temp.name),cap_bytes=1<<20,reserve_bytes=1<<18)
        r=NS(step_count=0,sim=NS(data=NS(time=0.)))
        self.backend=NS(calls=0,total_tokens=0)
        self.d=NS(r=r,arm='D',complete=False,executor=None,
            planner=NS(baseline=NS(roles=NS(backend=self.backend))),
            journal=NS(counts={'new_successor_choice_events':0,'new_successor_choice_changed_events':0}))
        self.health_calls=0;self.video_calls=0
        def health():self.health_calls+=1;return True
        self.h=make_cd_phase_health(health,lambda:self.d,self.b.state,('NAV','PUSH','CLIMB'),enabled=True)
        self.w=WatchFixture(self.b.state,self.h);self.v=NS(capture_if_due=self.capture)
        self.limits=MainLimits(5,10,.025,60.,('NAV','PUSH','CLIMB'))
        self.steps=[]
    def tearDown(self):self.temp.cleanup()
    def capture(self):self.video_calls+=1
    def issue(self):
        self.d.r.step_count+=1;self.d.r.sim.data.time=self.d.r.step_count*.005;self.steps.append(self.d.r.step_count)
    def run_loop(self,**kwargs):
        kw=dict(budget=self.b,video=self.v,guard=self.w,limits=self.limits,
                scope_start_mono=time.monotonic(),enabled=True);kw.update(kwargs)
        return run_task(self.d,**kw)
    def error_receipt(self,**kwargs):
        with self.assertRaises(LoopError)as caught:self.run_loop(**kwargs)
        return caught.exception.receipt

    def test_default_off_no_objects_or_guards(self):
        self.assertIsNone(run_task('/NO_FILE'));self.assertIsNone(make_cd_phase_health())
        self.assertFalse(self.b.state.sealed)

    def test_no_step_false_is_not_complete_and_final_seal_refuses_native(self):
        def step():
            if len(self.steps)<2:self.issue();return True
            if self.w.calls==3:return False  # Original no-step transition, not terminal.
            self.d.complete=True;return False
        self.d.step_one=step;r=self.run_loop()
        self.assertEqual(r['status'],'ORIGINAL_TASK_GATE_COMPLETE')
        self.assertEqual(r['driver_calls'],4);self.assertEqual(r['actual_task_steps'],2)
        self.assertEqual(self.video_calls,2);self.assertTrue(self.b.state.sealed)
        self.assertFalse(r['M1_or_method_gain_or_independent_effect_claimed'])
        with self.assertRaises(PolicyStop):self.w()

    def test_command_cap_censors_without_native_failed_or_success_cost(self):
        self.d.step_one=self.issue;r=self.run_loop()
        self.assertEqual(r['censor_reason'],'COMMAND_CAP');self.assertFalse(r['accepted_task_complete'])
        self.assertIsNone(r['native_failure_label']);self.assertEqual(r['actual_task_steps'],5)
        self.assertEqual(self.video_calls,5);self.assertTrue(self.b.finalizing)

    def test_task_sim_cap_prevents_next_issue(self):
        self.d.step_one=self.issue;r=self.run_loop(limits=MainLimits(100,100,.01,60.,('NAV','PUSH','CLIMB')))
        self.assertEqual(r['censor_reason'],'TASK_SIM_CAP');self.assertEqual(len(self.steps),2)

    def test_driver_call_cap_bounds_no_progress_loop(self):
        self.d.step_one=lambda:False;r=self.run_loop(limits=MainLimits(100,3,1.,60.,('NAV','PUSH','CLIMB')))
        self.assertEqual(r['censor_reason'],'DRIVER_CALL_CAP');self.assertEqual(r['actual_task_steps'],0)
        self.assertEqual(r['driver_calls'],3);self.assertEqual(self.video_calls,0)

    def test_wall_cap_uses_scope_start_not_loop_only(self):
        self.d.step_one=self.issue;r=self.run_loop(scope_start_mono=time.monotonic()-1000)
        self.assertEqual(r['censor_reason'],'SCOPE_WALL_CAP');self.assertEqual(r['driver_calls'],0)

    def test_blocking_step_is_not_claimed_preempted_or_safety_relaxed(self):
        def step():time.sleep(.01);self.issue()
        self.d.step_one=step;r=self.run_loop(limits=MainLimits(5,10,.025,.001,('NAV','PUSH','CLIMB')))
        self.assertEqual(r['censor_reason'],'SCOPE_WALL_CAP');self.assertEqual(r['actual_task_steps'],1)
        self.assertGreater(r['loop_wall_s'],.001);self.assertTrue(r['excludes_parent_cleanup_encoding_report_wall'])

    def test_exception_after_real_issue_keeps_actual_usage_and_last_live_capture(self):
        def step():self.issue();raise RuntimeError('DO_NOT_PRINT_SECRET')
        self.d.step_one=step;r=self.error_receipt()
        self.assertEqual(r['actual_task_steps'],1);self.assertEqual(self.video_calls,1)
        self.assertEqual(r['primary_error_type'],'RuntimeError');self.assertIsNone(r['native_failure_label'])
        self.assertNotIn('DO_NOT_PRINT_SECRET',json.dumps(r));self.assertTrue(self.b.state.sealed)

    def test_video_error_does_not_hide_primary_driver_error(self):
        def step():self.issue();raise ValueError('private')
        self.d.step_one=step
        def video():raise OSError('private storage path')
        self.v.capture_if_due=video;r=self.error_receipt()
        self.assertEqual(r['primary_error_type'],'ValueError');self.assertEqual(r['video_error_types'],['OSError'])
        self.assertNotIn('private',json.dumps(r));self.assertEqual(r['actual_task_steps'],1)

    def test_late_original_completion_retained_if_capture_fails(self):
        def step():self.issue();self.d.complete=True
        self.d.step_one=step
        def fail():raise OSError('close')
        self.v.capture_if_due=fail;r=self.error_receipt()
        self.assertTrue(r['original_driver_complete_observed']);self.assertFalse(r['accepted_task_complete'])
        self.assertIsNone(r['native_failure_label'])

    def test_missing_actual_runtime_stays_unknown_not_old_zero(self):
        self.d.r=None;r=self.error_receipt()
        self.assertFalse(r['usage_known']);self.assertIsNone(r['actual_task_steps']);self.assertIsNone(r['actual_task_sim_s'])

    def test_invalid_scope_clock_is_none_not_nan_negative_or_fake_wall(self):
        for index,value in enumerate([float('nan'),float('inf'),True,time.monotonic()+100]):
            with self.subTest(value=value):
                # A fresh real ScopeIO for each independently rejected fixture.
                root=Path(self.temp.name)/("clock-case-"+str(index));root.mkdir()
                self.b=ScopeIO(root,cap_bytes=1<<20,reserve_bytes=1<<18)
                health=make_cd_phase_health(lambda:True,lambda:self.d,self.b.state,('NAV','PUSH','CLIMB'),enabled=True)
                self.w=WatchFixture(self.b.state,health)
                r=self.error_receipt(scope_start_mono=value)
                self.assertIsNone(r['scope_start_to_loop_exit_wall_s']);json.dumps(r,allow_nan=False)
                self.assertTrue(r['usage_known']);self.assertEqual(r['actual_task_steps'],0)

    def test_clock_or_multi_command_invariant_refuses_without_count_reset(self):
        def step():self.issue();self.issue()
        self.d.step_one=step;r=self.error_receipt()
        self.assertEqual(r['status'],'EXCEPTION_NO_NATIVE_FAILURE_LABEL');self.assertEqual(r['actual_task_steps'],2)

    def test_counts_are_whitelisted_public_values_not_backend_identity(self):
        self.backend.identity={'secret':'DO_NOT_LOG'};self.backend.opener='SECRET_OPENER'
        def step():self.backend.calls=3;self.backend.total_tokens=123;self.d.complete=True
        self.d.step_one=step;r=self.run_loop()
        self.assertEqual(r['backend_public_counters'],{'calls':3,'total_tokens':123})
        self.assertNotIn('DO_NOT_LOG',json.dumps(r));self.assertNotIn('SECRET_OPENER',json.dumps(r))
        self.assertTrue(r['backend_counters_are_not_total_API_or_billing'])

    def test_original_fast_health_called_once_and_policy_not_NAV_only(self):
        self.d.executor=NS(option=NS(skill='PUSH'));self.h()
        self.assertEqual(self.health_calls,1)
        self.d.executor.option.skill='CLIMB';self.h();self.assertEqual(self.health_calls,2)

    def test_newly_installed_forbidden_skill_refused_before_issue(self):
        self.limits=MainLimits(5,10,.025,60.,('NAV',))
        self.h=make_cd_phase_health(lambda:True,lambda:self.d,self.b.state,('NAV',),enabled=True)
        self.w=WatchFixture(self.b.state,self.h)
        def step():
            self.d.executor=NS(option=NS(skill='PUSH'))
            self.w()  # Emulates the ORIGINAL pre-issue watch, not a second probe.
            self.issue()
        self.d.step_one=step;r=self.error_receipt()
        self.assertEqual(r['actual_task_steps'],0);self.assertEqual(self.steps,[]);self.assertIsNotNone(self.b.state.reason)

    def test_broken_stop_latch_cannot_silently_accept_unknown_health(self):
        seen=[];state=NS(fail=lambda reason:seen.append(reason))
        h=make_cd_phase_health(lambda:object(),lambda:self.d,state,('NAV',),enabled=True)
        with self.assertRaises(RuntimeError):h()
        self.assertEqual(len(seen),1)

    def test_missing_budget_handle_does_not_fake_a_successful_seal(self):
        r=self.error_receipt(budget=None)
        self.assertFalse(r['native_seal_attempted']);self.assertIsNone(r['native_seal_completed'])
        self.assertFalse(r['accepted_task_complete']);self.assertEqual(r['driver_calls'],0)

    def test_mismatched_or_detached_health_rejected_before_driver_call(self):
        self.d.step_one=self.issue
        r=self.error_receipt(guard=lambda:True)
        self.assertEqual(r['driver_calls'],0);self.assertEqual(len(self.steps),0)

    def test_separate_watch_or_health_stop_state_refused_before_issue(self):
        self.d.step_one=self.issue
        foreign=NS(sealed=False,check=lambda:None)
        w=WatchFixture(foreign,self.h)
        r=self.error_receipt(guard=w)
        self.assertEqual(r['driver_calls'],0);self.assertFalse(foreign.sealed)

    def test_real_original_watch_pair_and_probe_count_not_refreshed_by_health(self):
        probes=[]
        watch=ResourceWatch(lambda:probes.append('synthetic_probe'),state=self.b.state,
                            token=object(),fast_health=self.h).start()
        try:
            stamp=watch.last_observation_stamp
            def step():
                if len(self.steps)<2:self.issue()
                else:self.d.complete=True
            self.d.step_one=step;r=self.run_loop(guard=watch)
            self.assertTrue(r['accepted_task_complete']);self.assertEqual(probes,['synthetic_probe'])
            self.assertEqual(watch.probe_calls,1);self.assertEqual(watch.last_observation_stamp,stamp)
            with self.assertRaises(PolicyStop):watch()
        finally:watch.close()

    def test_does_not_close_parent_writers_leases_observers_or_reset_world(self):
        self.d.step_one=lambda:setattr(self.d,'complete',True)
        r=self.run_loop();self.assertTrue(r['parent_still_owns_watch_lease_writer_observer_cleanup'])
        self.assertEqual(self.d.r.step_count,0);self.assertIsNotNone(self.d.r)
        # Final metadata remains writable through original reserve after native seal.
        with self.b.open('after-loop-report.json','x',encoding='utf-8')as f:f.write('{}')
        self.assertEqual((Path(self.temp.name)/'after-loop-report.json').read_text(),'{}')


if __name__=='__main__':unittest.main(verbosity=2)
