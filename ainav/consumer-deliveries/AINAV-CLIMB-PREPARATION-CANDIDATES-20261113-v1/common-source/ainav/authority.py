"""AINav-native dispatch authority. No world-model forecasts or fake checkpoint."""
from dataclasses import asdict
from .contracts import DecisionBatch, ProtectionRequest, NativeReceipt
from .planner import Selection

TERMINAL = {'succeeded', 'failed', 'protected_exit_complete', 'budget_expired', 'hard_stop'}


class AinavAuthority:
    def __init__(self, planner, dispatcher, journal):
        self.planner, self.dispatcher, self.journal = planner, dispatcher, journal
        self.active = None
        self.started_at = None
        self.last_time = -1.
        self.blocked = False
        self.protection_latched = False
        self.decisions = set()
        self.goals = {}
        self.retired = set()
        self.selected_by_planner = False

    def decide(self, batch):
        if self.blocked or self.active is not None:
            raise RuntimeError('Dispatch revoked or actual interval still owns control')
        if not isinstance(batch, (DecisionBatch, ProtectionRequest)):
            raise ValueError('A typed task batch or native-only protection request required')
        if getattr(batch,'semantic_intents_only',False):
            raise ValueError('Semantic intents are not native entry admission; independent execution judgment required')
        query_time_s = batch.time_s if isinstance(batch, ProtectionRequest) else batch.observation.time_s
        if batch.decision_id in self.decisions or query_time_s < self.last_time:
            raise ValueError('Fresh current immutable decision required')
        mandatory = [x for x in batch.options if x.mandatory_protection]
        if self.protection_latched and not mandatory:
            raise RuntimeError('Actual failure requires native protected handling, not a task action')
        for option in batch.options:
            if option.skill == 'PUSH' and option.attempt_id in self.retired:
                raise ValueError('Retired PUSH attempt cannot be revived')
            if option.skill == 'EXIT_PUSH' and option.attempt_id not in self.goals:
                raise ValueError('Protected exit must bind a genuinely admitted prior PUSH')
            if option.attempt_id in self.goals and self.goals[option.attempt_id] != option.original_push_goal_sha256:
                raise ValueError('Original PUSH goal cannot be rebased')
        self.decisions.add(batch.decision_id)
        try:
            if mandatory:
                chosen = mandatory[0]
                self.selected_by_planner = False
                self.journal(dict(event='mandatory_native_protection', counts_as_model_decision=False,
                                  query_sha256=batch.sha256, option=asdict(chosen)))
            else:
                result = self.planner.select(batch)
                if (not isinstance(result, Selection) or result.query_sha256 != batch.sha256
                        or not result.evidence_ref):
                    raise ValueError('AINav selection must bind current public query and evidence')
                matches = [x for x in batch.options if x.token == result.token and x.sha256 == result.option_sha256]
                if len(matches) != 1:
                    raise ValueError('Exact selected option is not in native-admitted catalogue')
                chosen = matches[0]
                self.selected_by_planner = True
            receipt = self.dispatcher.start(chosen, batch.decision_id, query_time_s)
            if (not isinstance(receipt, NativeReceipt) or receipt.status != 'admitted'
                    or receipt.option_sha256 != chosen.sha256 or receipt.time_s != query_time_s):
                raise ValueError('Exact current native admission receipt required; not an issued command')
        except Exception as error:
            self.blocked = True
            self.journal(dict(event='ainav_dispatch_failed', error=str(error), fixed_route_fallback=False,
                              native_safety_handling_required=True, physical_success_claimed=False))
            raise
        if chosen.skill == 'PUSH':
            self.goals[chosen.attempt_id] = chosen.original_push_goal_sha256
        self.active = chosen
        self.started_at = None
        self.last_time = receipt.time_s
        self.journal(dict(event='ainav_native_admitted', option=asdict(chosen), receipt=asdict(receipt),
                          query_sha256=batch.sha256, physical_command_issued=False))
        return chosen

    def observe(self, receipt):
        if (self.active is None or not isinstance(receipt, NativeReceipt)
                or receipt.option_sha256 != self.active.sha256 or receipt.time_s < self.last_time):
            self.blocked = True
            raise ValueError('Monotonic receipt for the actual active native option required')
        if receipt.status == 'started':
            if self.started_at is not None:
                self.blocked = True
                raise ValueError('One first-issued-command receipt per interval required')
            self.started_at = receipt.time_s
        elif receipt.status == 'running':
            if self.started_at is None:
                raise ValueError('No running execution before a real issued command')
        elif receipt.status in TERMINAL:
            if self.started_at is None and receipt.status != 'hard_stop':
                self.blocked = True
                raise ValueError('No execution outcome before an actual motor-command receipt')
            if receipt.status == 'budget_expired' and receipt.time_s + 1e-7 < self.started_at + self.active.budget_s:
                self.blocked = True
                raise ValueError('Cannot expire a native interval before its bound')
            if receipt.status == 'protected_exit_complete' and self.active.skill not in ('EXIT_PUSH', 'RECOVER', 'HOLD'):
                self.blocked = True
                raise ValueError('Task skill cannot manufacture a protected-exit acknowledgement')
            if receipt.status in ('failed', 'hard_stop'):
                self.protection_latched = True
                if self.active.attempt_id:
                    self.retired.add(self.active.attempt_id)
            elif receipt.status == 'protected_exit_complete':
                self.protection_latched = False
                if self.active.attempt_id:
                    self.retired.add(self.active.attempt_id)
            if receipt.status == 'hard_stop':
                self.blocked = True
            if self.selected_by_planner:
                self.planner.observe(self.active, receipt)
        else:
            raise ValueError('Unexpected active receipt status')
        self.last_time = receipt.time_s
        self.journal(dict(event='ainav_native_receipt', receipt=asdict(receipt), task_success_inferred=False))
        if receipt.status in TERMINAL:
            self.active = None
            self.started_at = None
