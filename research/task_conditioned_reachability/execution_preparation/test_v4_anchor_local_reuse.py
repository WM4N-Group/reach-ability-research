"""Explicit SOFTWARE fixtures: reuse a pure geometry result only within one call.

No model, real image, physics or native imports. Immutable output/evidence must
match the old per-option path. There is no persistent frame/cross-query cache.
"""
import copy
import hashlib
from types import SimpleNamespace
import unittest
from . import test_v4_anchor_target8 as fixtures
from .v4_anchor_target8 import AnchorTarget8Provider


class AnchorLocalReuseTests(unittest.TestCase):
    setUp = fixtures.AnchorGeometryTests.setUp

    def provider(self, specs, *, associate_extra=None):
        def associate(obs, options, anchor):
            out = dict(WM_anchor_RGB_bytes_sha256=hashlib.sha256(anchor['rgb'].tobytes()).hexdigest(),
                WM_anchor_time_s=anchor['time_s'], WM_anchor_calibration_sha256='FIXTURE_CAL',
                frame_local_ref_by_option_sha256={o.sha256: copy.deepcopy(s) for o,s in zip(options,specs)})
            if associate_extra: out.update(associate_extra(options))
            return out
        return AnchorTarget8Provider(association_provider=associate, software_fixture=True, fixture_api=self.api)

    def make_options(self, n):
        return tuple(SimpleNamespace(sha256=hashlib.sha256(str(i).encode()).hexdigest()) for i in range(n))

    def spec(self, ref='same-frame-local', standoff=1.05):
        return dict(frame_local_ref=ref, declared_standoff_m=standoff)

    def test_same_ref_and_standoff_get_one_plane_and_one_vector_per_call(self):
        count = []; original = self.api.geometry_vector
        self.api.geometry_vector = lambda proof: (count.append(1) or original(proof))
        out = self.provider([self.spec()]*16)(self.obs, self.make_options(16), self.anchor)
        self.assertEqual(len(self.calls),1); self.assertEqual(len(count),1)
        self.assertEqual(len(out['target8_by_option_sha256']),16)
        self.assertEqual(len(set(out['target8_by_option_sha256'].values())),1)
        self.assertEqual(len({v['proof_sha256'] for v in out['target8_evidence_by_option_sha256'].values()}),1)

    def test_cache_never_crosses_invocations_even_same_bytes_clock_or_provider(self):
        p = self.provider([self.spec()]*2); opts = self.make_options(2)
        p(self.obs,opts,self.anchor); p(self.obs,opts,self.anchor)
        self.assertEqual(len(self.calls),2)
        self.anchor['rgb'] = fixtures.FixtureArray((64,96,3),b'NEW_SYNTHETIC_FRAME')
        p(self.obs,opts,self.anchor); self.assertEqual(len(self.calls),3)

    def test_distinct_ref_standoff_and_numeric_type_not_merged(self):
        specs = [self.spec(),self.spec('other'),self.spec(standoff=.58),
                 self.spec(standoff=1),self.spec(standoff=1.)]
        self.provider(specs)(self.obs,self.make_options(len(specs)),self.anchor)
        self.assertEqual(len(self.calls),5)

    def test_plane_refusal_reused_as_unknown_never_success_zero_or_retry(self):
        calls = []
        def refuse(*a,**kw):
            calls.append(1); raise ValueError('EXPLICIT_SOFTWARE_ORIGINAL_PLANE_REFUSAL')
        self.api.describe_visible_goal = refuse
        out = self.provider([self.spec()]*4)(self.obs,self.make_options(4),self.anchor)
        self.assertEqual(len(calls),1)
        self.assertEqual(list(out['target8_by_option_sha256'].values()),[None]*4)
        self.assertTrue(all(v['reason']=='ORIGINAL_VISIBLE_PLANE_REFUSED' for v in out['target8_evidence_by_option_sha256'].values()))

    def test_missing_association_does_not_enter_geometry_cache(self):
        out = self.provider([None,None])(self.obs,self.make_options(2),self.anchor)
        self.assertFalse(self.calls)
        self.assertEqual(list(out['target8_by_option_sha256'].values()),[None,None])

    def test_shared_plane_keeps_per_option_subject_evidence_independent(self):
        def extra(options):
            return dict(association_scope='SHARED_DECLARED_APPEARANCE_HYPOTHESIS_NOT_NATIVE_IDENTITY',
                association_evidence_ref='EXPLICIT_SOFTWARE_CURRENT_ASSOCIATION',
                declared_subject_by_option_sha256={o.sha256:s for o,s in zip(options,('cuboid_a','cuboid_b'))})
        opts = self.make_options(2); out = self.provider([self.spec()]*2,associate_extra=extra)(self.obs,opts,self.anchor)
        a,b = (out['target8_evidence_by_option_sha256'][o.sha256] for o in opts)
        self.assertEqual(len(self.calls),1)
        self.assertEqual((a['declared_conditioning_subject'],b['declared_conditioning_subject']),('cuboid_a','cuboid_b'))
        self.assertIsNot(a,b); self.assertFalse(a['semantic_identity_verified'])

    def test_source_snapshot_mutation_rejected_even_with_repeated_geometry(self):
        original = self.api.describe_visible_goal
        def mutate(*a,**kw):
            out = original(*a,**kw); self.anchor['depth_m'].raw=b'MUTATED_ACTUAL_SOURCE'; return out
        self.api.describe_visible_goal = mutate
        with self.assertRaisesRegex(ValueError,'Actual source anchor changed'):
            self.provider([self.spec()]*2)(self.obs,self.make_options(2),self.anchor)

    def test_copy_snapshot_mutation_rejected_even_with_cache_hit(self):
        original = self.api.describe_visible_goal
        def mutate(rgb,*a,**kw):
            out = original(rgb,*a,**kw); rgb.raw=b'MUTATED_CALLBACK_COPY'; return out
        self.api.describe_visible_goal = mutate
        with self.assertRaises(ValueError):
            self.provider([self.spec()]*2)(self.obs,self.make_options(2),self.anchor)

    def test_numerical_mask_failure_not_hidden_by_reuse(self):
        self.api.geometry_vector = lambda proof: (0.,)*8
        with self.assertRaisesRegex(ValueError,'Exact observed plane'):
            self.provider([self.spec()]*2)(self.obs,self.make_options(2),self.anchor)

    def test_other_exception_is_not_converted_to_unknown_or_cached(self):
        def explode(*a,**kw):raise RuntimeError('EXPLICIT_SOFTWARE_FAILURE')
        self.api.describe_visible_goal = explode
        with self.assertRaisesRegex(RuntimeError,'EXPLICIT_SOFTWARE_FAILURE'):
            self.provider([self.spec()]*2)(self.obs,self.make_options(2),self.anchor)


if __name__ == '__main__':
    unittest.main()
