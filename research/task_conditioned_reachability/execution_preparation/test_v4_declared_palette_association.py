"""Metadata-only scene-prior hypotheses; no RGBD/model/native renderer or API."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from . import test_v4_anchor_target8 as fixtures
from .v4_declared_palette_association import DeclaredPaletteAnchorAssociation, declared_subjects, APPEARANCE_FILE_SHA
from .v4_anchor_target8 import AnchorTarget8Provider

ROOT=Path(__file__).resolve().parents[3]
SNAPSHOT=ROOT/'protocols/2026-11-16/V4-declared-palette-WM-association-proposal-v1'


class PaletteAssociationTests(unittest.TestCase):
    def setUp(self):
        self.appearance=json.loads((SNAPSHOT/'COMMON_APPEARANCE_REVISION.json').read_bytes())
        self.public_map=json.loads((SNAPSHOT/'PROPOSED_COMMON_PUBLIC_MAP.json').read_bytes())
        self.effects=json.loads((SNAPSHOT/'PUBLIC_EFFECTS.json').read_bytes())
        self.anchor=dict(rgb=fixtures.FixtureArray((64,96,3)),depth_m=fixtures.FixtureArray((64,96)),
            camera_K='FIXTURE_K',T_base_optical='FIXTURE_T',time_s=1.)
        self.obs=SimpleNamespace(time_s=1.015,value=dict(declared_map=copy.deepcopy(self.public_map),objects=['DO_NOT_USE_OFF_GRID_ALIASES']))
        self.rows=[dict(appearance_family='warm',frame_local_ref='fixture-warm-0',geometry_valid=True,pixel_count=3552)]
        self.events=[];self.calls=0
        def proposals(*args):
            self.calls+=1
            return dict(schema='pixel-only-appearance-proposals-v1',
                RGB_sha256=hashlib.sha256(args[0].tobytes()).hexdigest(),calibration_sha256='FIXTURE_CAL',candidates=copy.deepcopy(self.rows))
        self.api=SimpleNamespace(propose_visual_candidates=proposals,visual_calibration_sha=lambda *a:'FIXTURE_CAL')
    def log(self,row):self.events.append(row);return 'FIXTURE_PUBLIC_PRIOR#'+str(len(self.events))
    def producer(self,**kwargs):
        values=dict(public_appearance=self.appearance,public_map=self.public_map,public_effects=self.effects,
            journal=self.log,enabled=True,active_revision_id=self.appearance['revision_id'],
            selected_MJB_sha256='a'*64,software_fixture=True,fixture_api=self.api,
            selected_asset_evidence=dict(revision_id=self.appearance['revision_id'],contract_sha256=APPEARANCE_FILE_SHA,
                new_static_MJB_sha256='a'*64,reference_static_MJB_sha256=self.appearance['reference_static_MJB_sha256'],
                all_five_same_new_asset_required=True,compiled_render_only_delta_proof=dict(only_changed_array='geom_rgba',
                    only_changed_rows=dict(complex_box_a_geom=1,complex_box_b_geom=2,complex_box_c_geom=3),
                    engine_options_unchanged=True,topology_names_paths_unchanged=True,unchanged_nonRGBA_array_count=1,unchanged_nonRGBA_arrays_sha256={'fixture_only_array':'b'*64})))
        values.update(kwargs);self.last_fixture_asset_evidence=copy.deepcopy(values['selected_asset_evidence'])
        return DeclaredPaletteAnchorAssociation(**values)
    def options(self,refs=('v4-ground-nav-007',)):
        rows=[r for r in self.effects['effects']if r['target_ref']in refs]
        return tuple(SimpleNamespace(sha256=hashlib.sha256(r['target_ref'].encode()).hexdigest(),
            skill=r['skill'],target_ref=r['target_ref'],parameters=tuple(sorted(r['parameters'].items())))for r in rows)
    def test_default_off_without_loading_geometry_or_model(self):
        p=self.producer(enabled=False,active_revision_id=None,selected_MJB_sha256=None)
        with self.assertRaises(ValueError):p(self.obs,self.options(),self.anchor)
        self.assertEqual(self.calls,0)
    def test_old_brown_asset_or_missing_revision_cannot_use_new_prior(self):
        for values in (dict(selected_MJB_sha256=self.appearance['reference_static_MJB_sha256']),
                       dict(active_revision_id=None),dict(selected_MJB_sha256=None)):
            with self.assertRaisesRegex(ValueError,'NEW selected-asset'):
                self.producer(**values)
    def test_fresh_hash_without_actual_source_asset_evidence_is_not_enough(self):
        with self.assertRaisesRegex(ValueError,'compiled-asset evidence'):
            self.producer(selected_asset_evidence=None)
    def test_visual_or_physical_proof_mismatch_rejected(self):
        proof=self.producer().asset_evidence_sha256
        self.assertEqual(len(proof),64)
        evidence=copy.deepcopy(self.last_fixture_asset_evidence)
        evidence['compiled_render_only_delta_proof']['only_changed_array']='body_mass'
        with self.assertRaisesRegex(ValueError,'render-only source proof'):
            self.producer(selected_asset_evidence=evidence)
    def test_prior_not_exposed_to_all_five_arms_is_rejected(self):
        plain=json.loads((SNAPSHOT/'PUBLIC_DECLARED_MAP.json').read_bytes())
        with self.assertRaisesRegex(ValueError,'ALL five arms'):
            self.producer(public_map=plain)
    def test_scene_specific_prior_is_shared_not_a_general_colour_id_certificate(self):
        p=self.producer();opts=self.options();out=p(self.obs,opts,self.anchor)
        self.assertEqual(out['frame_local_ref_by_option_sha256'][opts[0].sha256],
            dict(frame_local_ref='fixture-warm-0',declared_standoff_m=.58))
        self.assertIn('NOT_NATIVE_IDENTITY',self.events[-1]['role'])
        self.assertFalse(self.events[-1]['native_identity_or_pose_or_admission_claimed'])
    def test_generic_waypoint_is_not_assigned_a_visible_box_plane(self):
        opts=self.options(('v4-ground-nav-000',));out=self.producer()(self.obs,opts,self.anchor)
        self.assertIsNone(out['frame_local_ref_by_option_sha256'][opts[0].sha256])
    def test_all_registered_box_approach_and_top_relations_are_declarations_only(self):
        subjects=declared_subjects(self.public_map,self.effects)
        nav=[s for (skill,ref,_),s in subjects.items()if skill=='NAV'and s is not None]
        self.assertEqual(len(nav),12)
        for subject in ('cuboid_a','cuboid_b','cuboid_c'):self.assertEqual(nav.count(subject),4)
    def test_no_largest_component_even_when_second_same_family_has_bad_depth(self):
        self.rows.append(dict(appearance_family='warm',frame_local_ref='fixture-warm-1',geometry_valid=False,pixel_count=64))
        opts=self.options();out=self.producer()(self.obs,opts,self.anchor)
        self.assertIsNone(out['frame_local_ref_by_option_sha256'][opts[0].sha256])
    def test_missing_family_or_invalid_depth_stays_unknown(self):
        for rows in ([],[dict(appearance_family='warm',frame_local_ref='fixture-warm-0',geometry_valid=False)]):
            self.rows=rows;opts=self.options();out=self.producer()(self.obs,opts,self.anchor)
            self.assertIsNone(out['frame_local_ref_by_option_sha256'][opts[0].sha256])
    def test_foreign_or_stale_anchor_inventory_rejected(self):
        self.api.propose_visual_candidates=lambda *a:dict(schema='pixel-only-appearance-proposals-v1',
            RGB_sha256='b'*64,calibration_sha256='FIXTURE_CAL',candidates=self.rows)
        with self.assertRaisesRegex(ValueError,'current-anchor'):self.producer()(self.obs,self.options(),self.anchor)
    def test_different_current_public_map_rejected_not_ignored(self):
        self.obs.value['declared_map']['anchors'][0]['position_xyz_m'][0]+=1
        with self.assertRaisesRegex(ValueError,'common public declaration'):self.producer()(self.obs,self.options(),self.anchor)
    def test_raw192_or_offgrid_image_not_substituted_for96_anchor(self):
        self.anchor['rgb']=fixtures.FixtureArray((128,192,3))
        with self.assertRaisesRegex(ValueError,'WM anchor'):self.producer()(self.obs,self.options(),self.anchor)
    def test_no_cached_alias_reuse_across_actual_new_anchors(self):
        p=self.producer();opts=self.options();p(self.obs,opts,self.anchor)
        self.rows=[];self.anchor['time_s']=1.1;self.obs.time_s=1.115
        out=p(self.obs,opts,self.anchor)
        self.assertIsNone(out['frame_local_ref_by_option_sha256'][opts[0].sha256]);self.assertEqual(self.calls,2)
    def test_fixture_semantics_cannot_be_lifted_into_production_geometry(self):
        with self.assertRaisesRegex(ValueError,'Fixture semantic association'):
            AnchorTarget8Provider(association_provider=self.producer())
    def test_parent_original_plane_refusal_still_wins_over_prior_hypothesis(self):
        p=self.producer();opts=self.options()
        self.api.describe_visible_goal=lambda *a,**kw:(_ for _ in ()).throw(ValueError('FIXTURE_ORIGINAL_PLANE_REJECTED'))
        self.api.geometry_vector=lambda proof:None;self.api.source_pins={}
        target=AnchorTarget8Provider(association_provider=p,software_fixture=True,fixture_api=self.api)
        out=target(self.obs,opts,self.anchor)
        self.assertIsNone(out['target8_by_option_sha256'][opts[0].sha256])
    def test_hypothesis_evidence_is_linked_without_altering_original_target_vector(self):
        p=self.producer();opts=self.options()
        self.api.describe_visible_goal=lambda *a,**kw:dict(RGB_sha256=hashlib.sha256(a[0].tobytes()).hexdigest(),
            calibration_sha256='FIXTURE_CAL',frame_local_ref=kw['frame_local_ref'],uses_only_current_RGBD_and_calibration=True,physical_action_admitted=False)
        self.api.geometry_vector=lambda proof:(1,0,0,1,1,.001,.8,1);self.api.source_pins={}
        out=AnchorTarget8Provider(association_provider=p,software_fixture=True,fixture_api=self.api)(self.obs,opts,self.anchor)
        self.assertEqual(out['target8_by_option_sha256'][opts[0].sha256],(1.,0.,0.,1.,1.,.001,.8,1.))
        self.assertEqual(out['target8_evidence_by_option_sha256'][opts[0].sha256]['association_evidence_ref'],p.last_evidence_ref)
        evidence=out['target8_evidence_by_option_sha256'][opts[0].sha256]
        self.assertFalse(evidence['semantic_identity_verified'])
        self.assertEqual(evidence['declared_conditioning_subject'],'cuboid_a')
    def test_same_ref_with_unregistered_parameters_is_not_given_a_subject(self):
        opts=self.options();opts[0].parameters=(('goal_world_x_m',.37),('goal_world_y_m',0.),('surface_height_m',0.))
        out=self.producer()(self.obs,opts,self.anchor)
        self.assertIsNone(out['frame_local_ref_by_option_sha256'][opts[0].sha256])
    def test_public_declarations_are_copied_not_read_as_mutable_live_positions(self):
        p=self.producer();before=copy.deepcopy(self.public_map)
        self.public_map['anchors'][0]['position_xyz_m'][0]=999.
        self.assertEqual(p.map,before)
        out=p(self.obs,self.options(),self.anchor)
        self.assertIsNotNone(out['frame_local_ref_by_option_sha256'][self.options()[0].sha256])
    def test_palette_collision_or_wrong_scene_rejected(self):
        for edit in ('colour','scene'):
            a=copy.deepcopy(self.appearance)
            if edit=='colour':a['body_geom_review_hex']['complex_box_b_geom']=a['body_geom_review_hex']['complex_box_a_geom']
            else:a['scene_sha256']='c'*64
            with self.assertRaises(ValueError):self.producer(public_appearance=a)


if __name__=='__main__':unittest.main()
