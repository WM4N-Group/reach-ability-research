"""Bind an actual observed query to native target/entry evidence before VLM."""
from ..contracts import Observation, DecisionBatch, ProtectionRequest


class NativeDecisionGateway:
    def __init__(self, *, runtime, observe_public, admitted_options, bind_native, snapshot, journal, capability_contract, protection_provider=None):
        self.runtime, self.observe_public, self.admitted_options = runtime, observe_public, admitted_options
        self.bind_native, self.snapshot, self.journal = bind_native, snapshot, journal
        self.capability_contract = capability_contract
        self.protection_provider = protection_provider
        self.sequence = 0

    def __call__(self, now):
        before = self.snapshot(self.runtime)
        if self.protection_provider is not None:
            safety = self.protection_provider(now)
            if safety is not None:
                if not isinstance(safety, ProtectionRequest) or safety.time_s != now:
                    raise ValueError('Actual current native-only protection request required')
                if self.snapshot(self.runtime) != before:
                    raise RuntimeError('Native safety admission modified physical world/FIFO')
                return safety
        observation = self.observe_public(now)
        if not isinstance(observation, Observation) or observation.time_s != now:
            raise ValueError('Actual current public sensor observation required')
        # Native safety/geometry may filter entries, but does not select a task.
        options = tuple(self.admitted_options(observation))
        self.sequence += 1
        batch = DecisionBatch('ainav-decision-%06d' % self.sequence, observation, options, self.capability_contract)
        # The host may freeze private targets/attempt binding, never return them
        # to the planner. Existing BehaviorSessionFactory.bind_query fits here.
        result = self.bind_native(batch)
        if result is not None:
            raise ValueError('Native private binding must not leak into public query')
        if self.snapshot(self.runtime) != before:
            raise RuntimeError('Acquisition/entry binding modified physical world/FIFO')
        self.journal(dict(event='ainav_current_public_query_bound', query_sha256=batch.sha256,
                          observation_sha256=observation.sha256,
                          exact_native_options=[x.sha256 for x in options],
                          private_binding_returned=False, automatic_next_skill=False))
        return batch
