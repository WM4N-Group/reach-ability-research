#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-support-response-5802-20261004
baseline=/mnt/yuanyue/tmp/reachability-support-warning-cohort-5801-5824-20261004/seed5802-baseline.json
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
protocol="$output_dir/support-response-seed5802-protocol.json"
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
verify_sha "$protocol" dee22200f7358f1fe278b7c106b30d41d541c099a1948358c8c331a21db59c97
verify_sha "$baseline" 4746bfcbbba37cfe89154447a51357c09678b4bbd58addaecf6e193739881392
verify_sha "$nav_actor" 72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8
verify_sha "$push_checkpoint" b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721

for mode in front-up front-down; do
    report="$output_dir/seed5802-${mode}.json"
    log="$output_dir/seed5802-${mode}.log"
    if [[ -e "$report" || -e "$log" ]]; then
        echo "Output already exists: $mode" >&2
        exit 1
    fi
    echo "Starting $mode at $(date -Is)"
    OMNI_KIT_ACCEPT_EULA=YES CUDA_VISIBLE_DEVICES=0 \
        PYTHONPATH="$frozen_module_root${PYTHONPATH:+:$PYTHONPATH}" \
        timeout 600 "$python_bin" "$diagnostic" \
        --headless --device cuda:0 \
        --nav-actor "$nav_actor" \
        --push-checkpoint "$push_checkpoint" \
        --isaac-repo "$isaac_repo" \
        --output-json "$report" --seed 5802 \
        --nav-start-x -0.25 --nav-goal-x -0.05 --nav-arm-home \
        --record-push-support-trace --record-push-contact-load-trace \
        --record-leg-jacobian-trace --record-base-contact-source \
        --support-response-probe "$mode" --record-support-response-velocity > "$log" 2>&1
    echo "Completed $mode at $(date -Is)"
done
