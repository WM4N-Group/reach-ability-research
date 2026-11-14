#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-recovery-decision-state-known-pair-20261004
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
audit="$output_dir/audit_piper_recovery_decision_state_pilot.py"
audit_dependency="$output_dir/audit_piper_nav_push_baseline_cohort.py"
protocol="$output_dir/recovery-decision-state-known-pair-protocol.json"
nav_actor=/mnt/yuanyue/data/go2-piper/2026-09-24-push-low-piper-z2O4vb/sim2real/go2-piper-low-level-policy-handoff/policies/nav/policy.pt
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
frozen_module_root="$isaac_repo/source/LeggedManip_Lab"
gpu_index=${GPU_INDEX:-0}

verify_sha() {
    if [[ "$(sha256sum "$1" | cut -d ' ' -f 1)" != "$2" ]]; then
        echo "Frozen source, baseline or policy differs: $1" >&2
        exit 1
    fi
}
if [[ "$gpu_index" != 0 && "$gpu_index" != 1 ]]; then
    echo "GPU_INDEX must be 0 or 1" >&2
    exit 1
fi
verify_sha "$diagnostic" 293c1323e7fc9f4678f501ed9519a457b15a77b5e8e7702f8e051332ad164fe0
verify_sha "$audit" 2cdf07ab084531237b163b84305f6e086096a4cb1cc05acf164e918b01eff197
verify_sha "$audit_dependency" 7324cebf45bfa455c05991494c8111f7bdfc2dd060df4c12426eb8b1a2695cdc
verify_sha "$protocol" 2096a7db122910944d53a38ccaf4981e153cc938dd17767658be629a47e4d7d5
verify_sha "$nav_actor" 72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8
verify_sha "$push_checkpoint" b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721
verify_sha "$output_dir/seed5703-baseline.json" c7725ab232462bad44652eba6e9ca6d3ac2184250a36487012dee2433de0f9db
verify_sha "$output_dir/seed5712-baseline.json" efd907bed8e99925a71369042ce37f6e948084796aeba8b9118abb08e035f14c

for seed in 5703 5712; do
    report="$output_dir/seed${seed}-decision-state.json"
    log="$output_dir/seed${seed}-decision-state.log"
    audit_report="$output_dir/seed${seed}-decision-state-audit.json"
    if [[ -e "$report" || -e "$log" || -e "$audit_report" ]]; then
        echo "Output already exists for seed${seed}" >&2
        exit 1
    fi
    echo "Starting seed${seed} at $(date -Is)"
    OMNI_KIT_ACCEPT_EULA=YES CUDA_VISIBLE_DEVICES="$gpu_index" \
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
        --baseline "$output_dir/seed${seed}-baseline.json" \
        --candidate "$report" --output-json "$audit_report"
    echo "Completed seed${seed} at $(date -Is)"
done
