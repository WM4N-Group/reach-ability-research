"""Prospective scheduling SOFTWARE checks only; no capture/world or fitted model."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import json,unittest
from .bulk_coverage_registration import build_bulk24_registration,CANDIDATES,GROUPS
from .successor_aware_choice import digest
ROOT=Path(__file__).resolve().parents[3]


class BulkRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.matrix=json.loads((ROOT/'protocols/2026-11-15/G2-bulk24-lane-width-new-purpose-v1/SOURCE_BULK_MATRIX.json').read_bytes())
        self.base=json.loads((ROOT/'protocols/2026-11-15/G2-new-purpose-finite-cohort-v1/FINITE_COHORT_PROTOCOL.json').read_bytes())
    def build(self):
        return build_bulk24_registration(self.matrix,self.base,registered_at='2026-11-15T16:40:00+08:00',
            source_commit='0fff23aaf80d9a4ce0b3f34d7935df0ed1bab181',source_files={'SOFTWARE_ONLY_SOURCE_PIN':'a'*64})
    def test_fixed_balanced_24_NOT_full_60_or_seed_repeats(self):
        p=self.build();rows=p['attempt_schedule']
        self.assertEqual(len(rows),24);self.assertEqual([r['ordinal']for r in rows],list(range(1,25)))
        self.assertEqual(len({r['attempt_key']for r in rows}),24)
        self.assertEqual(Counter(r['candidate_id']for r in rows),dict.fromkeys(CANDIDATES,8))
        for c in p['conditions']:
            self.assertEqual({r['candidate_id']for r in rows if r['condition_key']==c['condition_key']},set(CANDIDATES))
        self.assertEqual(p['sampling']['reset_or_seed_repetitions'],0)
    def test_all_variants_have_one_existing_TRAIN_ancestor_not_holdout(self):
        p=self.build();ancestor=next(s for s in self.base['scenes']if s['case_id']=='full-4')['scene_ancestry_key']
        self.assertEqual({s['scene_ancestry_key']for s in p['scenes']},{ancestor})
        self.assertEqual(set(p['scene_split_assignments'].values()),{'TRAIN'})
        self.assertEqual({r['split']for r in p['attempt_schedule']},{'TRAIN'});self.assertEqual(p['independent_TEST'],0)
        self.assertEqual({s['group_id']for s in p['scenes']},set(GROUPS))
    def test_requests_translate_the_real_task_goal_Y_not_just_geometry_labels(self):
        p=self.build();scenes={s['group_id']:s for s in p['scenes']}
        for c in p['conditions']:
            lane=scenes[c['group_id']]['scene_key_canonical_payload']['integrated_case']['lane_y_m']
            nav,push,climb=c['requested_intents']
            self.assertEqual(nav['parameters']['goal_world_y_m'],lane+(.15 if c['prefix_side']=='left'else -.15))
            self.assertEqual(push['parameters']['goal_world_y_m'],lane)
            self.assertEqual(push['parameters']['goal_world_x_m'],2.3)
            self.assertEqual(climb,dict(skill='CLIMB',target_ref='cuboid-2:upper-entry',parameters=dict(surface_height_m=.2)))
            self.assertFalse(c['whole_task_goal_unchanged_claim'])
    def test_source_scene_and_condition_hashes_are_exact_canonical_payloads(self):
        p=self.build()
        for s in p['scenes']:self.assertEqual(s['source_scene_sha256'],digest(s['scene_key_canonical_payload']))
        for c in p['conditions']:self.assertEqual(c['condition_binding_sha256'],digest(c['condition_binding_payload']))
    def test_generation_is_deterministic_and_does_not_change_old_protocol_or_matrix(self):
        old=deepcopy((self.base,self.matrix));self.assertEqual(self.build(),self.build())
        self.assertEqual((self.base,self.matrix),old)
    def test_native_safety_caps_training_permission_and_old_fit_stay_unchanged(self):
        p=self.build();self.assertEqual(p['physical_limits'],self.base['physical_limits'])
        self.assertFalse(p['dispatch']or p['physical_admission']or p['current_frozen_critic_refit_allowed'])
        self.assertEqual(p['trained_models'],0);self.assertEqual(p['new_scopes_allocated'],0)
        self.assertFalse(p['old_TRAIN6_or_CAL_VAL_schedule_modified'])
        self.assertFalse(p['qualified_entry_condition_family'])
    def test_arbitrary_factor_candidate_or_material_drift_refused(self):
        self.matrix['candidates'].reverse()
        with self.assertRaisesRegex(ValueError,'finite prefixes/candidates'):self.build()
        self.setUp();self.matrix['groups'][0]['source_case']['bridge_mass_kg']=20.
        with self.assertRaisesRegex(ValueError,'geometry changes'):self.build()
    def test_metadata_is_not_meaningful_input_coverage_or_dynamic_qualification(self):
        p=self.build();self.assertEqual(p['sampling']['meaningful_groups_verified_before_capture'],0)
        self.assertTrue(p['observation_coverage']['RGBD_hash_difference_is_not_effective_group_proof'])
        self.assertFalse(any(s['qualified_dynamic_domain']for s in p['scenes']))


if __name__=='__main__':unittest.main()
