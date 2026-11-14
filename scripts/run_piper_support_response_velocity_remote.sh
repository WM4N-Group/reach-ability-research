#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-support-response-velocity-20261004
previous_dir=/mnt/yuanyue/tmp/reachability-support-response-known-pair-20261004
decision_dir=/mnt/yuanyue/tmp/reachability-recovery-decision-state-known-pair-20261004
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
audit="$output_dir/audit_piper_support_response_velocity.py"
protocol="$output_dir/support-response-velocity-protocol.json"
manifest="$output_dir/support-response-known-pair-results.json"
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
verify_sha "$audit" ab642e1a0b129857c76998116c90533044fdeb3aafcf3e99d7e2ddaea5cc8bee
verify_sha "$protocol" 8bd6536087f52b94e83793e2c74671e0afe7918ed4a7457293a859b9a6b74856
verify_sha "$manifest" 77bf0560d7322980e3f4601e8310ac09790cec4452a176ad3a58045f7638f743
verify_sha "$nav_actor" 72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8
verify_sha "$push_checkpoint" b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721
verify_sha "$decision_dir/seed5703-decision-state.json" 27d36b18b012b76814e9a8715c6c6418a0f943317dba1fa1c80539b4ac2249a6
verify_sha "$decision_dir/seed5712-decision-state.json" 5fa840c27d9b08cb7d5952657a82d1cd27b78f06290b7229b7940d0ea9d6877a

for seed in 5703 5712; do
    for mode in front-up front-down rear-up rear-down; do
        report="$output_dir/seed${seed}-${mode}.json"
        log="$output_dir/seed${seed}-${mode}.log"
        audit_report="$output_dir/seed${seed}-${mode}-audit.json"
        if [[ -e "$report" || -e "$log" || -e "$audit_report" ]]; then
            echo "Output already exists: seed${seed} ${mode}" >&2
            exit 1
        fi
        echo "Starting seed${seed} ${mode} at $(date -Is)"
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
            --support-response-probe "$mode" --record-support-response-velocity > "$log" 2>&1
        "$python_bin" "$audit" --seed "$seed" --mode "$mode" \
            --manifest "$manifest" \
            --decision-state "$decision_dir/seed${seed}-decision-state.json" \
            --previous-candidate "$previous_dir/seed${seed}-${mode}.json" \
            --candidate "$report" --output-json "$audit_report"
        echo "Completed seed${seed} ${mode} at $(date -Is)"
    done
done
