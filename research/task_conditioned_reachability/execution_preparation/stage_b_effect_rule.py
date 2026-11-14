"""Pre-outcome descriptive materiality supplement for the fixed N=3 pilot.

No new optimization algorithm, probability/significance estimate, controller or
native qualification. Complete observed table ONLY; never planner input or fit.
The 100ms rule is a reporting threshold, NOT any relaxed safety/success gate.
"""
from dataclasses import dataclass, asdict
from .successor_aware_choice import need, digest, replay_observed


@dataclass(frozen=True)
class EffectRule:
    reach_protocol_sha256: str = 'dfea3ec252ad995fcb9f4c0ed7f368b3b570e94dcef826bea6577ad68003371d'
    Data_preregistration_release_sha256: str = '697d72736496e1e8cc50c3932dd7c454b9bb1e0a62ecfcb55de423293cc5b59a'
    numerical_epsilon_s: float = 1e-9
    descriptive_gap_threshold_s: float = .1
    rule: str = 'BOTH_LOCAL_AND_FULL_GAPS_AT_LEAST_100MS_FOR_MATERIAL_STRICT_REVERSAL'
    variance_rule: str = 'ONE_CONFIG_ONE_REPEAT_NO_VARIANCE_OR_STATISTICAL_H1_CLAIM'
    def __post_init__(self):
        # Immutable pre-outcome agreement; changing the rule needs a NEW frozen
        # supplement, never an argument tuned after seeing an experimental table.
        need(asdict(self)==dict(reach_protocol_sha256='dfea3ec252ad995fcb9f4c0ed7f368b3b570e94dcef826bea6577ad68003371d',
            Data_preregistration_release_sha256='697d72736496e1e8cc50c3932dd7c454b9bb1e0a62ecfcb55de423293cc5b59a',
            numerical_epsilon_s=1e-9,descriptive_gap_threshold_s=.1,
            rule='BOTH_LOCAL_AND_FULL_GAPS_AT_LEAST_100MS_FOR_MATERIAL_STRICT_REVERSAL',
            variance_rule='ONE_CONFIG_ONE_REPEAT_NO_VARIANCE_OR_STATISTICAL_H1_CLAIM'),
            'Frozen pre-outcome rule; no posthoc threshold/variance/lineage override')
    @property
    def sha256(self):return digest(asdict(self))


def describe_mechanism(domain, records, *, rule):
    """Audit hindsight: evaluate ALL three branches, no success-subset deletion.

    This function cannot validate physical provenance, profile, initialization or
    distinct actual controls. Its output explicitly retains those requirements,
    even when a complete CPU table would satisfy a descriptive inequality.
    """
    need(type(rule) is EffectRule,'Explicit frozen pre-outcome reporting rule')
    need(tuple(c.candidate_id for c in domain.candidates)==
         ('original','lateral_plus_0p04','lateral_minus_0p04'), 'Fixed full N=3 candidate domain')
    raw=replay_observed(domain,records)
    result=dict(schema='Reach-fixed-N3-descriptive-mechanism-verdict-v1',
        role='AUDIT_HINDSIGHT_NOT_DEPLOYABLE_SELECTOR_OR_FIT',effect_rule_sha256=rule.sha256,
        raw_full_domain_replay=raw,raw_numerical_strict_reversal=raw['strict_current_vs_chain_cost_rank_reversal'],
        local_advantage_s=None,full_chain_penalty_s=None,
        material_strict_reversal_both_gaps_100ms=None,classification='NO_CONCLUSION_INCOMPLETE_TABLE',
        practical_threshold_is_not_native_success_gate=True,
        actual_control_and_pairing_provenance_verified=False,physical_H1_proven_by_this_function=False,
        new_hypothesis_cases_or_statistical_power_inferred=False,online_oracle_or_training_allowed=False,
        execution_authorized=False)
    if raw['status']!='COMPLETE_OBSERVED_TABLE':return result
    g=raw['choices']['current_greedy'];f=raw['choices']['successor_aware']
    table={r.candidate_id:r for r in records}
    if g is not None and f is not None:
        local=table[f].current_completion_s-table[g].current_completion_s
        result['local_advantage_s']=local
        if table[g].chain_completion_s is not None and table[f].chain_completion_s is not None:
            full=table[g].chain_completion_s-table[f].chain_completion_s
            result['full_chain_penalty_s']=full
    material=False
    if raw['strict_current_vs_chain_cost_rank_reversal']:
        material=(result['local_advantage_s']+rule.numerical_epsilon_s>=rule.descriptive_gap_threshold_s and
                  result['full_chain_penalty_s']+rule.numerical_epsilon_s>=rule.descriptive_gap_threshold_s)
        classification='STRICT_REVERSAL_BOTH_GAPS_AT_LEAST_100MS' if material else 'STRICT_BUT_SUBTHRESHOLD_REVERSAL_RETAIN_RAW'
    elif raw['failure_compatibility_switch']:
        classification='LITERAL_FAILURE_COMPATIBILITY_SWITCH_NOT_TIME_SIGNIFICANCE'
    elif raw['successor_breaks_current_cost_tie']:
        classification='CURRENT_COST_TIE_BROKEN_BY_SUCCESSOR_NOT_STRICT_REVERSAL'
    else:classification='NO_STRICT_REVERSAL_OR_FAILURE_SWITCH_IN_THIS_COMPLETE_TABLE'
    result.update(material_strict_reversal_both_gaps_100ms=material,classification=classification)
    return result
