"""Publish Stage-A contracts and replay ONLY the consumed legacy DEV table.

No raw stream audit, native import, geometry query, training or experiment.
The old two-policy table is a negative ranking check, never an online model.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from .successor_aware_choice import Task,Candidate,Domain,ObservedBranch,replay_observed,digest

ROOT=Path(__file__).resolve().parents[3]
EFFECT_SHA='4e74c8a111ce0e8ee7d13b9596b42cdd332e4b512c4f2eae300707bcaf65193f'
SUMMARY_SHA='1612e248e0e21b0386c58fd49db92e18a8cc829cc8c4a5e24fedc567a79bc4fa'
P2_LEDGER_SHA='30e1cbc85fa6aa28176192752a471a71fedf1cd5d6bd8647358d39c28751e325'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def publish(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=False);refs=[]
    def read(p,expected):
        if sha(p)!=expected:raise ValueError('Frozen consumed evidence drift: '+str(p))
        refs.append(dict(path=str(p),sha256=expected));return json.loads(p.read_text())
    old=ROOT/'evidence/2026-11-13/stow-v2-actual-control-consumption-v1'
    effects=read(old/'effects-and-source-bound-prefix.json',EFFECT_SHA)
    summary=read(old/'ACTUAL_CONTROL_AND_NET_COST_CONSUMED.json',SUMMARY_SHA)
    p2=read(Path('/home/yuanyue/main/work/data-team/manifests/ainav-full-host-continuation-20261113-v1/raw-main/accounting/ledger.json'),P2_LEDGER_SHA)
    task=Task('legacy-observed-two-intent-stow-case-not-new-H1-trial',
        digest(dict(requests=effects['baseline']['selected_requests'],terminal='original current stow and requested CLIMB full success; no broadened goal')),
        digest(dict(original_success_contract='unchanged native gates',source=effects['declared_source_pair_qualification'])),
        'ORIGINAL_PROTECTED_STOW_CAPTURE',digest(dict(role='AUDIT_ONLY_NO_PROSPECTIVE_STATE_SCHEMA')))
    # A SYMBOLIC audit domain. A shared source-family label is explicitly not a
    # claim that the two historical executions used a single identical program.
    family=digest(dict(role='LEGACY_ALLOWLISTED_CONTROL_FAMILY_NOT_EXECUTION_PACKAGE',source=effects['declared_source_pair_qualification']))
    candidates=(Candidate('original',task.sha256,family,'closed-P2:original-ordered-stow','ORIGINAL_ORDERED_STOW','original'),
                Candidate('direct',task.sha256,family,'closed-v2:guard-approved-direct','DIRECT_SAME_COMPACT','direct'))
    domain=Domain(task,candidates,'original','direct','AUDIT_REPLAY_ONLY')
    records=[]
    for cid,key,spent in [('original','baseline',sum(r['sim_s'] for r in p2['rows'])),('direct','candidate',summary['scope_final_sim_s'])]:
        value=effects[key];cost=value['actual_costs_s']
        records.append(ObservedBranch(cid,task.sha256,'LEGACY_EXACT_PAIR_13750_PREFIX_NOT_FULL_STATE_PROOF',value['input_result_sha256'],
            'SUCCESS' if value['original_stow_verified_literal'] else 'UNKNOWN',
            'SUCCESS' if value['owner_literal_task_passed'] else 'UNKNOWN',
            cost['capture_to_stow'],cost['capture_to_CLIMB_success'],spent))
    replay=replay_observed(domain,tuple(records))
    assert replay['choices']['current_greedy']==replay['choices']['successor_aware']=='direct'
    assert replay['strict_current_vs_chain_cost_rank_reversal'] is False
    assert replay['positive_recorded_preference_change'] is False
    replay.update(source_inputs=refs,legacy_different_full_programs_explicit=True,
        new_common_frozen_executable_domain_qualified=False,new_physical_H1_cases=0,
        spent_sim_scope='old own-zero plus main including auxiliary calibration; old integration failure retained separately',
        comparison_cost_origin='remaining from original capture; past NN/current operation is already completed',
        no_legacy_outcome_passed_to_prospective_evaluator=True,
        conclusion='Local and whole-chain winners are both direct; +0.560 successor penalty alone is NOT an observed ranking reversal.',
        all_old_closed_sources_and_failure_costs_preserved=True)
    (out/'LEGACY_DEV_NO_RANK_REVERSAL.json').write_text(json.dumps(replay,ensure_ascii=False,indent=2)+'\n')
    plan=Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md')
    (out/'CONSUMED_MAIN_PLAN.md').write_bytes(plan.read_bytes())
    (out/'SOURCE_AND_ROLE.json').write_text(json.dumps(dict(
        schema='reach-successor-choice-stage-A-software-delivery-v1',consumed_plan_sha256=sha(plan),
        no_native_or_raw_stream_replay=True,new_physics_Actor_GPU_API_or_training=0,
        positive_toy_tests_are_not_H1_evidence=True,
        next_owner_fields=['fixed common task terminal region/predicate and original success gates',
          'at least two prospectively materialized distinct legal candidate plans in one profile',
          'module:function consumer and default original candidate',
          'owner InputSchema with explicit current-field visibility/audience permissions',
          'common evaluator source/scope/unknown heads and per-candidate budget',
          'frozen initial-state selection/paired execution manifest before outcome exposure'],
        online_dynamic_successor_cost_model_available=False,
        candidate_domain_binding_and_physical_qualification_not_inferred=True),ensure_ascii=False,indent=2)+'\n')
    return replay


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    def fence(event,args):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.fork','os.posix_spawn'):
            raise RuntimeError('Stage-A metadata only, no remote/process launcher')
        if event=='import' and str(args[0]).split('.')[0] in ('numpy','torch','mujoco','scipy','onnxruntime','requests','httpx'):
            raise RuntimeError('No native/model/array/fit')
    sys.addaudithook(fence);r=publish(a.output)
    print(json.dumps(dict(legacy_choices=r['choices'],rank_reversal=r['strict_current_vs_chain_cost_rank_reversal'],new_H1_physics=0),ensure_ascii=False))


if __name__=='__main__':main()
