"""Explicit metadata fixtures only: no recorded capture/history, sensor or model."""
from types import SimpleNamespace
import unittest
from .v4_causal_wm_query import CausalWMQueryPort, WMContextUnavailable

class FixtureBuffer:
    def __init__(self):
        self.frames=['OLD_FIXTURE_FRAME']*3;self.commands=[('OLD_FIXTURE_REF',)]
        self.owner=('NAV','old-nav');self.observed_skill='NAV';self.owner_started=0.
        self.motor_calls=[];self.visual_calls=[];self.build_calls=0
        self.raw_archive=['UNCHANGED_OLD_ARTIFACT'];self.query_archive=['UNCHANGED_QUERY_FILE']
    def actual_motor(self,position,tick,time_s,*,issued_skill,native_owner_id):
        if issued_skill not in ('NAV','PUSH','CLIMB','EXIT_PUSH','RECOVER','HOLD'):
            raise ValueError('Original unsupported generic skill')
        self.motor_calls.append((tick,issued_skill,native_owner_id));self.commands.append((tick,position))
        if self.owner!=(issued_skill,native_owner_id):
            self.owner=(issued_skill,native_owner_id);self.owner_started=time_s-.005
        self.observed_skill=issued_skill
    def visual(self,packet):self.visual_calls.append(packet);self.frames.append(packet)
    def build(self,*args,**kwargs):
        self.build_calls+=1
        return 'FIXTURE_BELIEF','FIXTURE_PUBLIC60',dict(query_sha256='a'*64,query_time_s=2.5,image_time_s=2.5,input_file='FIXTURE')

class UnmodelledOwnerTests(unittest.TestCase):
    def setUp(self):
        self.buffer=FixtureBuffer();self.port=CausalWMQueryPort(self.buffer,
            role='CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY',software_fixture=True)
        self.port.completed_queries=5
    def exclude(self,tick=448):
        return self.port.on_unmodelled_issued(tick,tick*.005,
            native_owner_id='actual-supported-capture',owner_kind='SupportedCapture')
    def test_actual_capture_revokes_only_model_window_not_raw_archive_or_query_ids(self):
        event=self.exclude()
        self.assertFalse(self.buffer.frames);self.assertFalse(self.buffer.commands)
        self.assertIsNone(self.buffer.owner);self.assertIsNone(self.buffer.observed_skill)
        self.assertIsNone(self.buffer.owner_started);self.assertEqual(self.port.completed_queries,5)
        self.assertEqual(self.buffer.raw_archive,['UNCHANGED_OLD_ARTIFACT'])
        self.assertEqual(self.buffer.query_archive,['UNCHANGED_QUERY_FILE'])
        self.assertFalse(event['raw_recording_or_native_world_modified']);self.assertFalse(event['model_forward_performed'])
    def test_capture_cannot_query_or_enter_model_as_HOLD_NAV_or_RECOVER(self):
        self.exclude()
        with self.assertRaises(WMContextUnavailable):self.port.build('fixture',public_observation=SimpleNamespace(),
            body45=[],body_observed_time_s=2.24,target8_by_option_sha256={})
        for skill in ('HOLD','NAV','RECOVER'):
            with self.assertRaises(ValueError):self.port.on_issued([0.]*18,449,2.245,
                actual_issued_skill=skill,native_owner_id='actual-supported-capture')
        self.assertFalse(self.buffer.motor_calls);self.assertEqual(self.buffer.build_calls,0)
    def test_unknown_owner_frames_not_buffered_or_relabelled_current(self):
        self.exclude();self.assertIs(self.port.on_visual('UNKNOWN_CAPTURE_FIXTURE_FRAME'),False)
        self.assertFalse(self.buffer.visual_calls)
        self.assertEqual(self.port.context_status()['status'],'CURRENT_ISSUED_OWNER_NOT_IN_ORIGINAL_GENERIC_SKILLS')
    def test_genuine_new_NAV_owner_needs_new_real_grid_context_no_padding(self):
        self.exclude();self.port.on_issued([0.]*18,449,2.245,actual_issued_skill='NAV',native_owner_id='actual-new-nav')
        self.assertEqual(self.buffer.observed_skill,'NAV')
        self.assertAlmostEqual(self.buffer.owner_started,2.24)
        self.assertEqual(self.port.context_status()['status'],'WAIT_THREE_NEW_REAL_GRID_FRAMES')
        for index in range(3):self.port.on_visual('EXPLICIT_NEW_FRAME_FIXTURE_'+str(index))
        self.assertEqual(self.port.context_status()['status'],'NECESSARY_CONTEXT_PRESENT_ORIGINAL_BUILD_CHECKS_STILL_REQUIRED')
        self.assertNotIn('OLD_FIXTURE_FRAME',self.buffer.frames)
        self.assertFalse(self.port.context_status()['native_or_WM_inference_qualification_claimed'])
    def test_later_unmodelled_control_cannot_keep_stale_prior_NAV_context(self):
        self.port.on_issued([0.]*18,1,.005,actual_issued_skill='NAV',native_owner_id='actual-nav')
        self.port.on_unmodelled_issued(2,.010,native_owner_id='actual-new-capture',owner_kind='SupportedCapture')
        self.assertIsNone(self.buffer.observed_skill);self.assertFalse(self.buffer.commands)
        self.assertEqual(self.port.context_status()['unmodelled_issued_steps'],1)
    def test_bad_duplicate_or_skipped_accepted_clock_does_not_silently_reset(self):
        for tick,time in ((True,.005),(0,0.),(1,.01),(1,float('nan'))):
            with self.assertRaises(ValueError):self.port.on_unmodelled_issued(tick,time,
                native_owner_id='capture',owner_kind='SupportedCapture')
            self.assertTrue(self.buffer.frames)
        self.exclude()
        for tick in (448,450):
            with self.assertRaises(ValueError):self.port.on_unmodelled_issued(tick,tick*.005,
                native_owner_id='capture',owner_kind='SupportedCapture')
        self.assertEqual(self.port.unmodelled_issued_steps,1)
    def test_no_automatic_new_skill_mapping_or_replay_of_missing_capture_commands(self):
        self.exclude()
        with self.assertRaises(ValueError):self.port.on_issued([0.]*18,449,2.245,
            actual_issued_skill='CAPTURE',native_owner_id='capture-renamed')
        self.assertEqual(self.port.context_status()['status'],'CURRENT_ISSUED_OWNER_NOT_IN_ORIGINAL_GENERIC_SKILLS')
        self.assertFalse(self.buffer.commands)
    def test_legitimate_HOLD_is_not_blocked_just_because_other_capture_owner_was_excluded(self):
        self.exclude();self.port.on_issued([0.]*18,449,2.245,
            actual_issued_skill='HOLD',native_owner_id='actual-distinct-HOLD-owner')
        self.assertEqual(self.buffer.observed_skill,'HOLD')
        self.assertEqual(self.port.context_status()['status'],'WAIT_THREE_NEW_REAL_GRID_FRAMES')

if __name__=='__main__':unittest.main()
