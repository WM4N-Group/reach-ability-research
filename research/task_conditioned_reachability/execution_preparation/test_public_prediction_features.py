"""Feature-profile invariance tests; no training and no historical rows read."""
from dataclasses import asdict,replace
from copy import deepcopy
import unittest
from .public_preparation_selector import build_problem,with_public_observation
from .public_prediction_features import physical_features,PhysicalFeatures
from .test_public_preparation_selector import owner_api,reference
from .test_public_selector_information import published


class PhysicalFeatureTests(unittest.TestCase):
    def setUp(self):
        self.base=build_problem(reference(),public_candidates=owner_api().public_candidates)
        self.problem=with_public_observation(self.base,published(),now_s=0.,source_role='ONLINE_PUBLIC')

    def vector(self,p=None,i=0):
        p=self.problem if p is None else p
        return physical_features(p,p.domain.candidates[i])

    def test_fixed48_slots_include_physics_units_frames_and_no_metadata_values(self):
        f=self.vector();self.assertEqual(len(f.values),48);self.assertTrue(all(f.known_mask))
        self.assertNotIn('time_s',f.names);self.assertNotIn('candidate_id',f.names)
        self.assertEqual(f.names[-1],'measurement_age');self.assertEqual(f.values[-1],0.)
        self.assertEqual(f.frames[-1],'ACQUISITION_AGE_NOT_SKILL_ELAPSED')
        self.assertTrue(all(not isinstance(v,str) for v in f.values))

    def test_source_paths_hashes_model_materialization_refs_cannot_change_features(self):
        p=self.problem
        inputs=replace(p.inputs,values=tuple(replace(v,source_ref='/OTHER_RUN_UUID/not-a-feature/'+str(i)) for i,v in enumerate(p.inputs.values)))
        candidates=tuple(replace(c,owner_materialization_ref='OTHER_PATH_SHA_'+str(i),control_equivalence_key='OTHER_ID_'+str(i)) for i,c in enumerate(p.domain.candidates))
        changed=replace(p,inputs=inputs,domain=replace(p.domain,candidates=candidates))
        self.assertNotEqual(changed.inputs.sha256,p.inputs.sha256)
        self.assertEqual(self.vector(changed),self.vector(p))

    def test_absolute_clock_change_with_same_fresh_age_and_physics_has_identical_features(self):
        live=with_public_observation(self.base,published(123.),now_s=123.,source_role='ONLINE_PUBLIC')
        self.assertEqual(self.vector(live),self.vector())

    def test_rgb_paths_hashes_and_opaque_detection_UUIDs_not_learnable_shortcuts(self):
        o=published();o['rgb']['path']='/OTHER_UUID/frame.png';o['rgb']['sha256']='b'*64
        o['objects']=[dict(target_ref='opaque-random-UUID-not-used-as-physics',label='observed cuboid',
            bbox_xyxy=[1.,1.,2.,2.],evidence_ref='/CPU-not-physical/object.json',
            geometry=dict(status='unknown',source='unavailable',values={},uncertainty={}))]
        changed=with_public_observation(self.base,o,now_s=0.,source_role='ONLINE_PUBLIC')
        self.assertNotEqual(changed.inputs.sha256,self.problem.inputs.sha256)
        self.assertEqual(self.vector(changed),self.vector())

    def test_candidate_conditioning_is_actual_reference_offset_not_label_or_hash(self):
        original,plus,minus=[self.vector(i=i) for i in range(3)]
        self.assertEqual(original.values[:2],(0.,0.))
        self.assertAlmostEqual(plus.values[1],.04);self.assertAlmostEqual(minus.values[1],-.04)
        self.assertEqual(original.values[2:],plus.values[2:]);self.assertEqual(plus.values[2:],minus.values[2:])
        self.assertEqual(plus.frames[1],'WORLD_REGISTERED_REFERENCE')
        self.assertIn('world_to_body_heading',plus.unavailable_capabilities)

    def test_no_measured_packet_means_unknown_slots_not_fake_standing_zeros(self):
        f=self.vector(self.base)
        self.assertEqual(sum(f.known_mask),2);self.assertTrue(all(v is None for v in f.values[2:]))
        with self.assertRaisesRegex(ValueError,'never zero imputation'):
            replace(f,values=tuple(0. if v is None else v for v in f.values))

    def test_physical_motion_change_is_preserved_not_erased_with_metadata(self):
        row=published();row['public_state']['linear_velocity'][0]=.9
        changed=with_public_observation(self.base,row,now_s=0.,source_role='ONLINE_PUBLIC')
        f=self.vector(changed);slot=f.names.index('public_linear_velocity_0')
        self.assertEqual(f.values[slot],.9);self.assertNotEqual(f,self.vector())

    def test_stale_or_mixed_packet_clock_rejected_even_if_manually_replaced(self):
        p=self.problem
        stale=replace(p,inputs=replace(p.inputs,decision_time_s=1.))
        with self.assertRaisesRegex(ValueError,'Fresh causal'):self.vector(stale)
        values=tuple(replace(v,observed_time_s=0.01) if v.name=='public_state.q' else v for v in p.inputs.values)
        # Current decision clock must permit constructing that InputValue set;
        # mixed capture clocks are still rejected by the physical view.
        mixed=replace(p,inputs=replace(p.inputs,decision_time_s=.01,values=values))
        with self.assertRaisesRegex(ValueError,'One actual acquisition'):self.vector(mixed)

    def test_foreign_candidate_not_silently_joined_by_id(self):
        other=replace(self.problem.domain.candidates[0],owner_materialization_ref='FOREIGN')
        with self.assertRaisesRegex(ValueError,'Exact candidate'):physical_features(self.problem,other)

    def test_geometry_cannot_silently_move_the_registered_reference(self):
        geometry=deepcopy(self.problem.geometry);geometry[0]['original_CLIMB_reference_xy'][0]=9.
        changed=replace(self.problem,geometry=geometry)
        with self.assertRaisesRegex(ValueError,'same registered public input'):self.vector(changed)

    def test_no_current_pose_latch_or_outcome_inferred_from_feature_profile(self):
        f=self.vector();self.assertIn('registered_reference_relative_pose',f.unavailable_capabilities)
        self.assertIn('native_position_yaw_latch_history',f.unavailable_capabilities)
        self.assertIn('complete_successor_predictor',f.unavailable_capabilities)
        self.assertFalse(any('success' in name or 'outcome' in name or 'sha' in name for name in f.names))


if __name__=='__main__':unittest.main()
