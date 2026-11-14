"""Reach's offline research entrypoint on EXISTING serialized Domain/ObservedBranch.

Not a new Data logging contract. Caller uses existing source-bound result/clock
readers to produce ObservedBranch records; this command does the final research
comparison locally. File JSON alone is NOT proof of physical provenance/pairing.
"""
import argparse
import json
from pathlib import Path
from dataclasses import asdict
from .successor_aware_choice import Task,Candidate,Domain,ObservedBranch,need
from .stage_b_effect_rule import EffectRule,describe_mechanism


def evaluate_serialized(domain_document, branch_records):
    """Reuse exact existing dataclasses, no new envelope/permit schema."""
    need(type(domain_document) is dict,'Existing serialized Domain document')
    raw=domain_document.get('domain',domain_document)
    need(type(raw) is dict,'Existing serialized Domain')
    value=dict(raw);value['task']=Task(**value['task'])
    value['candidates']=tuple(Candidate(**c) for c in value['candidates'])
    domain=Domain(**value)
    need(tuple(c.candidate_id for c in domain.candidates)==
         ('original','lateral_plus_0p04','lateral_minus_0p04'),'Fixed full N=3 domain even for partial delivery')
    need(domain.role in ('AUDIT_REPLAY_ONLY','CPU_TEST_ONLY'),'Offline input domain only')
    need(type(branch_records) is list,'Existing ObservedBranch list, not future cost estimates')
    records=tuple(ObservedBranch(**r) for r in branch_records)
    ids={c.candidate_id for c in domain.candidates};received=[r.candidate_id for r in records]
    need(len(set(received))==len(received) and set(received)<=ids,
         'Unique observed candidates from the same full candidate domain')
    need(all(r.task_sha256==domain.task.sha256 for r in records) and
         len({r.pairing_ref for r in records})<=1,'Same task and declared pair identity')
    missing=[c.candidate_id for c in domain.candidates if c.candidate_id not in received]
    if missing:
        # Actual asynchronous delivery: no fake result SHA or successful/failed
        # placeholder for an unpublished branch. The complete-domain comparator
        # is deliberately not called until all real records are available.
        return dict(schema='Reach-fixed-N3-descriptive-mechanism-verdict-v1',
            role='AUDIT_HINDSIGHT_NOT_DEPLOYABLE_SELECTOR_OR_FIT',
            effect_rule_sha256=EffectRule().sha256,
            classification='NO_CONCLUSION_INCOMPLETE_TABLE',
            raw_full_domain_replay=None,received_branch_records=[asdict(r) for r in records],
            unavailable_candidate_ids=missing,
            raw_numerical_strict_reversal=None,material_strict_reversal_both_gaps_100ms=None,
            local_advantage_s=None,full_chain_penalty_s=None,
            actual_control_and_pairing_provenance_verified=False,physical_H1_proven_by_this_function=False,
            unpublished_result_or_outcome_synthesized=False,online_oracle_or_training_allowed=False,
            original_native_outcome_relabelled=False,execution_authorized=False)
    return describe_mechanism(domain,records,rule=EffectRule())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--domain-json',type=Path,required=True)
    p.add_argument('--branch-records-json',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    out=evaluate_serialized(json.loads(a.domain_json.read_text()),json.loads(a.branch_records_json.read_text()))
    with a.output.open('x') as stream:
        json.dump(out,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({k:out[k] for k in ('classification','raw_numerical_strict_reversal',
        'material_strict_reversal_both_gaps_100ms','physical_H1_proven_by_this_function')},ensure_ascii=False))


if __name__=='__main__':main()
