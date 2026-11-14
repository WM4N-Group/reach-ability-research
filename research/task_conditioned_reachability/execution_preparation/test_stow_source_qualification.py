"""New source-reader tests. Positive candidate manifests are SYNTHETIC metadata,
not a run, a physical program freeze, a selection outcome or research sample.
"""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from .stow_source_qualification import qualify_source_pair,sha,expected_consumer_adapter

DATA=Path('/home/yuanyue/main/work/data-team')
PACKAGE=Path('/home/yuanyue/main/work/ainav/consumer-deliveries/AINAV-ABSOLUTE-PLACEMENT-BASELINE-20261113-v1')
ROOT=Path(__file__).resolve().parents[3]


def encode(d):return json.dumps(d,sort_keys=True).encode()


class ExactV2SourcePairTests(unittest.TestCase):
    def fixture(self):
        inputs=dict(
            baseline_result_bytes=(DATA/'manifests/ainav-full-host-continuation-20261113-v1/raw-main/main/result.json').read_bytes(),
            baseline_freeze_bytes=(DATA/'manifests/ainav-full-host-continuation-20261113-v1/program-freeze.json').read_bytes(),
            candidate_freeze_bytes=(DATA/'manifests/ainav-stow-choice-ground-PUSH-CLIMB-20261113-v1/program-freeze.json').read_bytes(),
            fork_manifest_bytes=(DATA/'manifests/ainav-stow-choice-v2-native-CPU-intake-20261113-v1/fork-manifest.json').read_bytes(),
            baseline_release_bytes=(PACKAGE/'BASELINE_RELEASE_v1.json').read_bytes(),
            baseline_consumer_bytes=(PACKAGE/'absolute_baseline_consumer.py').read_bytes(),
            v2_bundle_manifest_bytes=(ROOT/'evidence/2026-11-13/stow-target-view-repair-v2/delta-bundle/manifest.json').read_bytes())
        freeze=json.loads(inputs['candidate_freeze_bytes']);fork=json.loads(inputs['fork_manifest_bytes'])
        bundle=json.loads(inputs['v2_bundle_manifest_bytes'])
        self.worker='/mnt/miaojigui/data-team/workspace/workers/ainav-stow-choice-ground-PUSH-CLIMB-20261113-v1/'
        freeze['scope_id']='SYNTHETIC_DECLARED_METADATA_NOT_RUN'
        freeze['current_source_fork_manifest_sha256']=sha(inputs['fork_manifest_bytes'])
        freeze['files'][self.worker+'fork-manifest.json']=sha(inputs['fork_manifest_bytes'])
        for rel,h in bundle['files_sha256'].items():
            if rel.startswith('reach_stow_choice/'):freeze['files'][self.worker+rel]=h
        inputs['candidate_freeze_bytes']=encode(freeze)
        candidate=deepcopy(json.loads(inputs['baseline_result_bytes']))
        candidate.update(scope_id=freeze['scope_id'],program_sha256=sha(inputs['candidate_freeze_bytes']),
                         source_fork_manifest_sha256=sha(inputs['fork_manifest_bytes']),new_waypoint_choice_control_enabled=True)
        inputs['candidate_result_bytes']=encode(candidate)
        return inputs

    def mutate_freeze(self,d,fn):
        f=json.loads(d['candidate_freeze_bytes']);fn(f);d['candidate_freeze_bytes']=encode(f)
        raw=json.loads(d['candidate_result_bytes']);raw['program_sha256']=sha(d['candidate_freeze_bytes']);d['candidate_result_bytes']=encode(raw)

    def test_exact_declared_v2_source_pair_not_runtime_or_success_certificate(self):
        d=self.fixture();q=qualify_source_pair(**d)
        self.assertTrue(q['source_pair_verified']);self.assertFalse(q['actual_zero_or_main_execution_authorized'])
        self.assertFalse(q['live_import_ids_or_native_safety_or_actual_success_proven'])
        self.assertEqual(q['candidate_program_sha256'],sha(d['candidate_freeze_bytes']))

    def test_consumer_adapter_independently_matches_actual_owner_adapter(self):
        d=self.fixture();f=json.loads(d['fork_manifest_bytes'])
        actual=sha(expected_consumer_adapter(d['baseline_consumer_bytes'].decode(),f['source_delta_pins']))
        self.assertEqual(actual,f['consumer_adapter_sha256'])

    def test_old_failed_v1_cannot_be_approved_as_v2(self):
        d=self.fixture();old=DATA/'manifests/ainav-stow-choice-ground-PUSH-CLIMB-20261113-v1'
        d['candidate_result_bytes']=(old/'main-result.json').read_bytes();d['candidate_freeze_bytes']=(old/'program-freeze.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'fork manifest'):qualify_source_pair(**d)

    def test_unreviewed_runtime_core_or_guard_changes_rejected(self):
        for suffix in ('reach_stow_choice/native_stow_path_binding.py','reach_stow_choice/stow_path_choice.py','source/ainav/native/placement_handoff.py'):
            with self.subTest(suffix=suffix):
                d=self.fixture();self.mutate_freeze(d,lambda f:f['files'].__setitem__(self.worker+suffix,'0'*64))
                with self.assertRaises(ValueError):qualify_source_pair(**d)

    def test_incomplete_or_mixed_source_and_lineage_as_current_rejected(self):
        for field in ('missing','mixed','lineage'):
            d=self.fixture()
            if field=='missing':self.mutate_freeze(d,lambda f:f['files'].pop(self.worker+'source/ainav/planner.py'))
            elif field=='mixed':self.mutate_freeze(d,lambda f:f['files'].__setitem__('/other/source/ainav/__init__.py','0'*64))
            else:
                raw=json.loads(d['candidate_result_bytes']);raw['source_fork_manifest_sha256']='314b6650918cbf88c6bd7166ad3f2d26f9c3b30f92094db98d6f8832f8d1fd8c';d['candidate_result_bytes']=encode(raw)
            with self.subTest(field=field),self.assertRaises(ValueError):qualify_source_pair(**d)

    def test_unknown_sdk_goal_or_noninvertible_loader_is_not_same_source(self):
        for field in ('SDK','goal','loader'):
            d=self.fixture()
            def change(f):
                if field=='SDK':
                    key=next(k for k in f['files'] if k.endswith('/native-sdk-340d7d8/MANIFEST.json'));f['files'][key]='0'*64
                else:f['files'][self.worker+('requests.json' if field=='goal' else 'overlay_consumer.py')]='0'*64
            self.mutate_freeze(d,change)
            with self.subTest(field=field),self.assertRaises(ValueError):qualify_source_pair(**d)

    def test_no_default_acceptance_for_safety_or_lifecycle_claim_missing(self):
        d=self.fixture();self.mutate_freeze(d,lambda f:f.pop('original_guards_QP_FIFO_goal_and_four_second_verification_retained'))
        with self.assertRaises(ValueError):qualify_source_pair(**d)
        d=self.fixture();raw=json.loads(d['candidate_result_bytes']);raw['phase']='zero';d['candidate_result_bytes']=encode(raw)
        with self.assertRaisesRegex(ValueError,'result/freeze'):qualify_source_pair(**d)

    def test_failed_result_stays_failed_even_when_declared_source_qualifies(self):
        d=self.fixture();raw=json.loads(d['candidate_result_bytes']);raw.update(passed=False,status='FAILED_NO_RETRY');d['candidate_result_bytes']=encode(raw)
        q=qualify_source_pair(**d)
        self.assertTrue(q['source_pair_verified']);self.assertFalse(q['method_advantage_or_generalization_proven'])
        self.assertFalse(q['live_import_ids_or_native_safety_or_actual_success_proven'])


if __name__=='__main__':unittest.main()
