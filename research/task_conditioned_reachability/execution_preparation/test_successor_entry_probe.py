"""Geometric/schema design checks only; no world or new legal candidate evidence."""
import unittest
from .successor_aware_choice import InputSchema,InputValue,DecisionInput
from .successor_entry_probe import propose


def fixture(position,visibility='ONLINE_NATIVE_LOCAL'):
    schema=InputSchema('CPU_SCHEMA_NOT_OWNER_PERMISSION',(('base_xy',visibility,('REACH_NATIVE_LOCAL',)),))
    ip=DecisionInput('a'*64,schema.sha256,1.,'REACH_NATIVE_LOCAL',(InputValue('base_xy',position,visibility,1.,'CPU_CURRENT_STATE_FIXTURE'),))
    return ip,schema


def call(position,status='PREPARE'):
    return propose(*fixture(position),base_position_field='base_xy',entry_center_xy=(0.,0.),original_radius_m=.16,
                   frame_id='WORLD_XY_CPU_FIXTURE',base_position_frame_id='WORLD_XY_CPU_FIXTURE',original_entry_spec_ref='CPU_ORIGINAL_SPEC_NOT_EXECUTION',original_judgment_status=status)


class EntryProbeDesignTests(unittest.TestCase):
    def test_projection_inside_original_half_radius_not_new_native_permission(self):
        r=call((1.,0.));self.assertEqual(r['proposals'][1]['preparation_xy'],[.08,0.])
        self.assertFalse(r['execution_authorized']);self.assertFalse(r['native_domain_or_tracking_support_safety_or_success_certified'])

    def test_already_READY_means_no_controller_change_not_two_fake_candidates(self):
        r=call((.01,0.),'READY');self.assertEqual(r['proposals'],[])
        self.assertEqual(r['status'],'NO_CONNECTOR_REQUEST_NO_DISTINCT_CONTROL')

    def test_original_refusal_or_unknown_not_bypassed(self):
        for status in ('BLOCKED','UNKNOWN'):
            self.assertEqual(call((1.,0.),status)['proposals'],[])

    def test_center_alias_not_counted_as_two(self):
        r=call((0.,0.));self.assertEqual(len(r['proposals']),1)
        self.assertEqual(r['status'],'GEOMETRIC_ALIAS_NO_NEW_COMPARISON')

    def test_unknown_position_not_filled_with_origin(self):
        ip,schema=fixture(None,'UNKNOWN')
        r=propose(ip,schema,base_position_field='base_xy',entry_center_xy=(0.,0.),original_radius_m=.16,frame_id='WORLD',base_position_frame_id='WORLD',original_entry_spec_ref='owner',original_judgment_status='PREPARE')
        self.assertEqual(r['status'],'UNRESOLVED_CURRENT_BASE_POSITION')

    def test_only_source_bound_terminal_error_can_reduce_available_slack(self):
        ip,schema=fixture((1.,0.))
        r=propose(ip,schema,base_position_field='base_xy',entry_center_xy=(0.,0.),original_radius_m=.16,frame_id='WORLD',base_position_frame_id='WORLD',
            original_entry_spec_ref='owner',original_judgment_status='PREPARE',nav_composite_terminal_error_bound_m=.10,error_bound_source_ref='CPU_BOUND_NOT_REAL_GUARANTEE')
        self.assertAlmostEqual(r['proposals'][1]['preparation_xy'][0],.03)
        self.assertTrue(r['necessary_XY_margin_under_supplied_bound_verified'])
        self.assertFalse(r['native_domain_or_tracking_support_safety_or_success_certified'])
        with self.assertRaisesRegex(ValueError,'sourced bound'):
            propose(ip,schema,base_position_field='base_xy',entry_center_xy=(0.,0.),original_radius_m=.16,frame_id='WORLD',base_position_frame_id='WORLD',
                original_entry_spec_ref='owner',original_judgment_status='PREPARE',nav_composite_terminal_error_bound_m=.10)

    def test_exhausted_declared_error_margin_is_not_global_task_cut(self):
        ip,schema=fixture((1.,0.))
        r=propose(ip,schema,base_position_field='base_xy',entry_center_xy=(0.,0.),original_radius_m=.16,frame_id='WORLD',base_position_frame_id='WORLD',
            original_entry_spec_ref='owner',original_judgment_status='PREPARE',nav_composite_terminal_error_bound_m=.16,error_bound_source_ref='CPU_BOUND')
        self.assertEqual(r['status'],'NO_EXTRA_REFERENCE_CERTIFIED_BY_SUPPLIED_ERROR_BOUND')
        self.assertFalse(r['global_task_infeasibility_inferred'])

    def test_mixed_camera_and_world_coordinates_rejected(self):
        ip,schema=fixture((1.,0.))
        with self.assertRaisesRegex(ValueError,'same declared frame'):
            propose(ip,schema,base_position_field='base_xy',entry_center_xy=(0.,0.),original_radius_m=.16,
                frame_id='WORLD',base_position_frame_id='CAMERA',original_entry_spec_ref='owner',original_judgment_status='PREPARE')

    def test_audit_input_rejected_before_geometry(self):
        with self.assertRaises(ValueError):fixture((1.,0.),'AUDIT_ONLY')

    def test_bounded_geometry_not_sim_completion_cost(self):
        r=call((0.,1.));self.assertEqual(r['proposals'][1]['preparation_xy'],[0.,.08])
        self.assertTrue(r['raw_reference_distance_is_not_actual_NAV_or_successor_cost'])


if __name__=='__main__':unittest.main()
