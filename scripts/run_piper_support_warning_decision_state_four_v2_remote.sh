#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-support-warning-decision-state-four-20261004
baseline_dir=/mnt/yuanyue/tmp/reachability-nav-push-baseline-5701-5724-20261004
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
audit="$output_dir/audit_piper_recovery_decision_state_pilot_v2.py"
audit_dependency="$output_dir/audit_piper_nav_push_baseline_cohort.py"
protocol="$output_dir/support-warning-decision-state-four-v2-protocol.json"
nav_actor=/mnt/yuanyue/data/go2-piper/2026-09-24-push-low-piper-z2O4vb/sim2real/go2-piper-low-level-policy-handoff/policies/nav/policy.pt
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
frozen_module_root="$isaac_repo/source/LeggedManip_Lab"

verify_sha() {
    if [[ "$(sha256sum "$1" | cut -d ' ' -f 1)" != "$2" ]]; then
        echo "Frozen input differs: $1" >&2
        exit 1
    fi
}
verify_sha "$diagnostic" 944533f0069ae944a7f0203b2ab88e8f776f5169353af2f91789a8e1f7974e0b
verify_sha "$audit" c5af2be9f2d168bec8baffb7dddc8c210ec5adb6fde1d4da5ea865ff85fc9b5a
verify_sha "$audit_dependency" 7324cebf45bfa455c05991494c8111f7bdfc2dd060df4c12426eb8b1a2695cdc
verify_sha "$protocol" 100b2069d082c74b8c098bfe11b1c25f9f04d7c888cdd50c095aa9c31e5ca3ef
verify_sha "$nav_actor" 72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8
verify_sha "$push_checkpoint" b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721
verify_sha "$baseline_dir/seed5701-baseline.json" df801b27af5589f5fe7dba5088ebace8b4f6a4e0e8141be6abda96601dbf3c24
verify_sha "$baseline_dir/seed5716-baseline.json" 9ec2829e4db024506780c692770bc281be6f7856bbb9134804cafd161fa8ebca
verify_sha "$baseline_dir/seed5717-baseline.json" 6abab2e598f8885694100734756743a86caf53b9ff3a9971171d7c5c23952c25
verify_sha "$baseline_dir/seed5723-baseline.json" 1eb159b2d6df5608ab3047001871123629e7fd4232a99f4b4c6a204a857824bd
verify_sha "$output_dir/seed5701-decision-state.json" 1769ff76c1dff93a063a39bf1b20e5c287fa4b8904722a1df64d7032a7f82d77
if [[ -e "$output_dir/seed5701-decision-state-audit.json" ]]; then
    echo "Seed5701 v2 audit output already exists" >&2
    exit 1
fi
"$python_bin" "$audit" --seed 5701 \
    --baseline "$baseline_dir/seed5701-baseline.json" \
    --candidate "$output_dir/seed5701-decision-state.json" \
    --output-json "$output_dir/seed5701-decision-state-audit.json"

for seed in 5716 5717 5723; do
    report="$output_dir/seed${seed}-decision-state.json"
    log="$output_dir/seed${seed}-decision-state.log"
    audit_report="$output_dir/seed${seed}-decision-state-audit.json"
    if [[ -e "$report" || -e "$log" || -e "$audit_report" ]]; then
        echo "Output already exists: seed${seed}" >&2
        exit 1
    fi
    echo "Starting seed${seed} at $(date -Is)"
    OMNI_KIT_ACCEPT_EULA=YES CUDA_VISIBLE_DEVICES=0 \
        PYTHONPATH="$frozen_module_root${PYTHONPATH:+:$PYTHONPATH}" \
        timeout 600 "$python_bin" "$diagnostic" \
        --headless --device cuda:0 \
        --nav-actor "$nav_actor" \
        --push-checkpoint "$push_checkpoint" \
        --isaac-repo "$isaac_repo" \
        --output-json "$report" --seed "$seed" \
        --nav-start-x -0.25 --nav-goal-x -0.05 --nav-arm-home \
        --record-push-support-trace --record-push-contact-load-trace \
        --record-leg-jacobian-trace --record-base-contact-source \
        --record-recovery-decision-state > "$log" 2>&1
    "$python_bin" "$audit" --seed "$seed" \
        --baseline "$baseline_dir/seed${seed}-baseline.json" \
        --candidate "$report" --output-json "$audit_report"
    echo "Completed seed${seed} at $(date -Is)"
done
