"""One fixed PUBLIC observation NAV before ANY V4 arm's method, opt-in only.

This is a proposed shared engineering prefix, NOT an A/B VLM-only fallback,
optimizer, source integration, WM-ready certificate or native launcher. Keep the
real arm planner installed at task0; a source-owned coordinator may use this
auxiliary policy once, then return to that SAME method after a genuine receipt.
"""
from .v4_successor_choice import need

POLICY_ID = 'V4_COMMON_PUBLIC_NAV_OBSERVATION_PRELUDE_v1'
TARGET_REF = 'v4-ground-nav-007'
PARAMETERS = (('goal_world_x_m', .22), ('goal_world_y_m', 0.), ('surface_height_m', 0.))


class CommonNavObservationPrelude:
    decision_source = 'V4_COMMON_NAV_OBSERVATION_PRELUDE_NOT_ARM_METHOD'

    def __init__(self, *, arm, journal, enabled=False, software_fixture=False):
        need(arm in ('A', 'B', 'C', 'D', 'E') and callable(journal), 'Exact arm and original shared journal')
        need(type(enabled) is bool and type(software_fixture) is bool, 'Explicit opt-in and fixture provenance')
        self.arm, self.journal = arm, journal
        self.prelude_enabled, self.software_fixture = enabled, software_fixture
        self.status = 'NEW'
        self.pending = None
        self.initial_observation_sha256 = None
        self.selected_query_sha256 = None
        self.selected_time_s = None
        self.completed_time_s = None
        self.receipt_ref = None

    def _record(self, event, **values):
        ref = self.journal(dict(event=event, policy_id=POLICY_ID, arm=self.arm,
            common_all_five_arms=True, software_fixture=self.software_fixture,
            counts_as_arm_method_or_optimizer_decision=False,
            task_success_or_WM_input_ready_claimed=False, **values))
        need(type(ref) is str and bool(ref), 'Durable original common-prefix evidence')
        return ref

    def select(self, batch):
        from ainav.intents import IntentBatch
        from ainav.contracts import Primitive
        from ainav.planner import Selection
        need(self.prelude_enabled and self.status == 'NEW', 'Prelude opt-in once only; no retry or task-method replacement')
        need(type(batch) is IntentBatch, 'Only the current original public semantic batch')
        # Fail closed even if catalogue/image/journal validation refuses below.
        self.status = 'UNAVAILABLE'
        batch.observation.verify_image()
        anchors = [a for a in batch.observation.value['declared_map']['anchors'] if a['target_ref'] == TARGET_REF]
        need(len(anchors) == 1 and tuple(anchors[0]['position_xyz_m']) == (.22, 0., 0.),
             'Exact existing COMMON public NAV declaration, not a private approach or fabricated waypoint')
        candidates = [o for o in batch.options if o.skill == 'NAV' and o.target_ref == TARGET_REF
                      and tuple(sorted(o.parameters)) == PARAMETERS]
        need(len(candidates) == 1, 'Exact unique shared public NAV; no alternate target/view scan')
        option = candidates[0]
        ref = self._record('reach_v4_common_observation_NAV_selected', query_sha256=batch.sha256,
            public_observation_sha256=batch.observation.sha256, option_sha256=option.sha256,
            target_ref=TARGET_REF, parameters=dict(PARAMETERS), physical_action_issued=False)
        self.initial_observation_sha256 = batch.observation.sha256
        self.selected_query_sha256 = batch.sha256
        self.selected_time_s = batch.observation.time_s
        self.pending = option
        self.status = 'PENDING'
        return Selection(batch.sha256, option.token, option.sha256, Primitive.from_option(option).key, 0, ref)

    def observe_intent(self, intent, actual, receipt, binding_ref):
        from ainav.native.behavior_authority import BehaviorOption, NativeReceipt
        need(self.status == 'PENDING' and self.pending is intent and
             type(actual) is BehaviorOption and type(receipt) is NativeReceipt and
             actual.skill == intent.skill == 'NAV' and actual.target_ref == intent.target_ref == TARGET_REF and
             actual.parameters == intent.parameters and receipt.option_sha256 == actual.sha256 and
             receipt.status in ('succeeded', 'failed', 'hard_stop', 'budget_expired') and
             receipt.time_s >= self.selected_time_s and
             type(binding_ref) is str and bool(binding_ref),
             'Exact pending common NAV and its original bound actual terminal/expiry receipt')
        self.status = 'UNAVAILABLE'  # Never silently retry an unsuccessful/uncertain prefix.
        ref = self._record('reach_v4_common_observation_NAV_outcome',
            intent_sha256=intent.sha256, native_option_sha256=actual.sha256,
            native_receipt_status=receipt.status, native_receipt_time_s=receipt.time_s,
            native_receipt_evidence_ref=receipt.evidence_ref, binding_ref=binding_ref,
            prefix_succeeded=receipt.status == 'succeeded')
        self.pending = None
        if receipt.status == 'succeeded':
            self.completed_time_s = receipt.time_s
            self.receipt_ref = ref
            self.status = 'SUCCEEDED'

    def reject_intent(self, intent, reason, evidence_ref):
        need(self.status == 'PENDING' and self.pending is intent and bool(reason) and bool(evidence_ref),
             'Only the real pending prefix judgment rejection, not a fabricated physical failure')
        self.status = 'UNAVAILABLE'
        self._record('reach_v4_common_observation_NAV_rejected', intent_sha256=intent.sha256,
            reason=str(reason), evidence_ref=evidence_ref, native_failed_receipt_created=False)
        self.pending = None

    def require_fresh_method_observation(self, observation):
        """Source calls at handoff. WM's ORIGINAL causal build remains separate."""
        from ainav.contracts import Observation
        need(self.status == 'SUCCEEDED' and type(observation) is Observation and
             observation.time_s >= self.completed_time_s and
             observation.sha256 != self.initial_observation_sha256,
             'Genuine prefix success and a NEW original public acquisition before arm method')
        observation.verify_image()
        return dict(common_prefix_succeeded=True, common_prefix_receipt_ref=self.receipt_ref,
            fresh_public_observation_sha256=observation.sha256,
            WM_ready_or_task_success_not_inferred=True)
