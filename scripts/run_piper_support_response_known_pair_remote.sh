#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-support-response-known-pair-20261004
baseline_dir=/mnt/yuanyue/tmp/reachability-nav-push-baseline-5701-5724-20261004
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
audit="$output_dir/audit_piper_support_response_probe.py"
protocol="$output_dir/support-response-known-pair-protocol.json"
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
verify_sha "$diagnostic" 622b21dd0999439777e2470edd06d56b0907a46653e8efda0483d578c66ee43b
verify_sha "$audit" 1352bc51fe4cacee8a5fa92c7b491be0e91b6321dd9a544e1a80e14a62c3590c
verify_sha "$protocol" 296e5d6460962b3ad1ecc68cc26f14b18b0153f84b939fc26a29d458a0b44b89
verify_sha "$nav_actor" 72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8
verify_sha "$push_checkpoint" b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721
verify_sha "$baseline_dir/seed5703-baseline.json" c7725ab232462bad44652eba6e9ca6d3ac2184250a36487012dee2433de0f9db
verify_sha "$baseline_dir/seed5712-baseline.json" efd907bed8e99925a71369042ce37f6e948084796aeba8b9118abb08e035f14c

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
            --support-response-probe "$mode" > "$log" 2>&1
        "$python_bin" "$audit" --seed "$seed" --mode "$mode" \
            --baseline "$baseline_dir/seed${seed}-baseline.json" \
            --candidate "$report" --output-json "$audit_report"
        echo "Completed seed${seed} ${mode} at $(date -Is)"
    done
done
