"""Pure parameter/domain tests, not native skill qualification or new episodes."""
import copy
import json
from pathlib import Path
import unittest
from .v4_box_skill_domain import normalize_boxes,check_boxes
ROOT=Path(__file__).resolve().parents[3]
SCENE=ROOT/'protocols/2026-11-15/T-COMPLEX-01-V4-box-skill-lock-v1/SCENE_BOX_PARAMETERS_LOCKED.json'

class BoxSkillDomainTests(unittest.TestCase):
    def setUp(self):self.scene=json.loads(SCENE.read_bytes())
    def test_current_boxes_already_match_successful_native_prototype(self):
        out,changes=normalize_boxes(self.scene)
        self.assertEqual(out,self.scene);self.assertTrue(all(not x['changed_physical_attributes']for x in changes))
    def test_old_heavy_or_overheight_variants_are_normalized_without_editing_input(self):
        old=copy.deepcopy(self.scene);old['objects'][0].update(mass_kg=20.,size_m=[2.4,1.4,.4],bottom_mu=.6)
        snapshot=copy.deepcopy(old);out,changes=normalize_boxes(old)
        self.assertEqual(old,snapshot);self.assertEqual(out['objects'][0]['mass_kg'],.5)
        self.assertEqual(out['objects'][0]['size_m'][2],.2);self.assertTrue(changes[0]['changed_physical_attributes'])
    def test_required60cm_goals_include11cm_reference_offset(self):
        rows=check_boxes(self.scene)
        self.assertEqual(len(rows),3)
        for row in rows:
            self.assertAlmostEqual(row['required_displacement_m'],.6)
            self.assertAlmostEqual(row['candidates'][-1]['declared_native_drive_m'],.71)
    def test_bad_goal_not_clipped_or_moved_to_fake_success(self):
        self.scene['objects'][0]['allowed_placement_x_m']=[3.]
        self.scene['objects'][0]['required_goal_xy_m']=[3.,0.]
        with self.assertRaises(ValueError):normalize_boxes(self.scene)
    def test_side_push_or_non_ground_source_is_not_admitted(self):
        self.scene['objects'][0]['required_goal_xy_m'][1]=.1
        with self.assertRaises(ValueError):normalize_boxes(self.scene)
        self.setUp();self.scene['task']['source_surface_height_m']=.2
        with self.assertRaises(ValueError):normalize_boxes(self.scene)
    def test_platform_and_full_goal_not_silently_lowered(self):
        out,_=normalize_boxes(self.scene)
        self.assertEqual(out['platforms'],self.scene['platforms'])
        self.assertEqual(out['task'],self.scene['task']);self.assertEqual(out['platforms'][0]['top_z_m'],.6)
    def test_no_task_success_from_parameter_check(self):
        self.assertTrue(all(r['native_task_success_not_inferred']for r in check_boxes(self.scene)))

if __name__=='__main__':unittest.main()
