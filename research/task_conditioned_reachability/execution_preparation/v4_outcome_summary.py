"""Five-arm result summary after owner-specific original result consumption.

Pure scalar reader, not a native result verifier or publisher. Source adapter must
supply SHA-bound original facts. Missing arms and method-unavailable runs are not
wins; API/resource censor is separate from native failure. No statistical claim
from one DEV run/arm. Does not evaluate, fit or read the frozen critic/heldout.

Comparison only: the source consumer supplies common_execution_profile_sha256
and common_execution_profile_ref from the ORIGINAL frozen shared execution
configuration (performance/audit/detection policy, common brake/control and
resource/recording policy). Do not hash the whole arm program: method-specific
VLM/WM/optimizer differences are the intended treatments. This scalar reader
cannot authenticate the referenced bytes; source consumption must do that.
Missing/malformed profiles preserve result rows but withhold method contrasts.
These fields are NOT new runtime/zero/E-dispatch prerequisites.
"""
import math
from .v4_successor_choice import need

ARMS=tuple('ABCDE')


def _common_execution_profile(row):
    digest = row.get('common_execution_profile_sha256')
    ref = row.get('common_execution_profile_ref')
    if (type(digest) is str and len(digest) == 64 and
            all(c in '0123456789abcdef' for c in digest) and
            type(ref) is str and bool(ref.strip())):
        return digest
    return None


def summarize(rows, *, scene_sha256):
    by_arm={}
    for row in rows:
        # Component probes can carry an internal arm flag solely to configure
        # the shared execution layer. They are NEVER one of the five mains,
        # including failed probes with zero VLM/WM/commands or an E-like flag.
        need(row.get('run_role') == 'V4_FIVE_ARM_TASK_MAIN' and row.get('source_phase') == 'main'
             and type(row.get('source_task_main_dispatch_count')) is int
             and row['source_task_main_dispatch_count'] == 1
             and row.get('component_not_C_or_E_method') is not True,
             'Actual five-arm task-main source role/dispatch required; component zero is not C or E')
        arm=row['arm'];need(arm in ARMS and arm not in by_arm, 'One original new main per arm; no duplicates/retries')
        need(row['scene_sha256']==scene_sha256 and len(row['source_result_sha256'])==64 and bool(row['source_result_ref']),
             'Exact common frozen scene and original result identity')
        need(type(row['task_success']) is bool and type(row['resource_censored']) is bool and
             type(row['api_censored']) is bool, 'Literal terminal flags, not inferred from process exit')
        for k in ('VLM_calls','WM_forward_batches','effective_optimizer_choices'):
            need(type(row[k]) is int and row[k]>=0, 'Actual counts, not enabled flags')
        if arm in 'CD': need(row['WM_forward_batches']==0, 'No undisclosed WM on C/D')
        if arm=='E': need(row['VLM_calls']==row['WM_forward_batches']==row['effective_optimizer_choices']==0,
                          'E has no API/WM/proposed optimizer, not an oracle route')
        if arm in 'ACE': need(row['effective_optimizer_choices']==0, 'Optimizer-off baseline is not optimized')
        if row['task_success']:
            proof=row.get('complete_elevated_task_evidence',{})
            need(not row['resource_censored'] and not row['api_censored'] and
                 proof.get('three_original_placements_verified') is True and
                 proof.get('original_CLIMB_receipts_verified') is True and
                 proof.get('goal_deck_actual_support_verified') is True and
                 proof.get('original_final_stop_and_stow_verified') is True and
                 proof.get('same_world_native_guards_intact') is True,
                 'Ground XY/native exit/partial placement is not full elevated task completion')
            need(type(row.get('success_elapsed_sim_s')) in (int,float) and math.isfinite(row['success_elapsed_sim_s']) and row['success_elapsed_sim_s']>=0,
                 'Verified actual complete-task success clock')
        else:
            need(row.get('success_elapsed_sim_s') is None, 'Failure/censor elapsed cannot become success cost')
        copy=dict(row)
        copy['method_identity_established']=(row['VLM_calls']>0 and row['WM_forward_batches']>0 if arm in 'AB'
                                             else row['VLM_calls']>0 if arm in 'CD' else True)
        copy['optimizer_effective']=(row['effective_optimizer_choices']>0 if arm in 'BD' else False)
        by_arm[arm]=copy
    contrasts={}
    for treatment,baseline in (('B','A'),('D','C')):
        key=treatment+'-'+baseline
        if treatment not in by_arm or baseline not in by_arm:
            contrasts[key]=dict(status='MISSING_ORIGINAL_ARM_NOT_COMPARABLE');continue
        t,b=by_arm[treatment],by_arm[baseline]
        method_valid=t['method_identity_established'] and b['method_identity_established'] and t['optimizer_effective']
        tp, bp = _common_execution_profile(t), _common_execution_profile(b)
        profile_match = None if tp is None or bp is None else tp == bp
        valid = method_valid and profile_match is True
        status = ('METHOD_CONTRAST_NOT_ESTABLISHED' if not method_valid else
                  'COMMON_EXECUTION_PROFILE_UNVERIFIED' if profile_match is None else
                  'COMMON_EXECUTION_PROFILE_MISMATCH' if not profile_match else
                  'SINGLE_DEV_DESCRIPTIVE_ONLY')
        contrasts[key]=dict(status=status, common_execution_profile_match=profile_match,
            treatment_actual_success=t['task_success'],baseline_actual_success=b['task_success'],
            treatment_censored=t['resource_censored'] or t['api_censored'],
            baseline_censored=b['resource_censored'] or b['api_censored'],
            successful_sim_delta=(t['success_elapsed_sim_s']-b['success_elapsed_sim_s']
                if valid and t['task_success'] and b['task_success'] else None),
            no_statistical_or_generalization_claim=True)
    return dict(original_arm_count=len(by_arm),missing_arms=[a for a in ARMS if a not in by_arm],
        arms=by_arm,primary_contrasts=contrasts,all_five_original_results_available=len(by_arm)==5,
        E_is_independent_rule_baseline_not_WM_factor=True,process_exit_not_task_success=True,
        full_five_video_delivery_complete=len(by_arm)==5 and all(r.get('complete_live_video_verified') is True for r in by_arm.values()),
        statistical_or_WM_causal_advantage_established=False)
