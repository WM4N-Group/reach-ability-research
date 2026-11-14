#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-front-foot-hold-known-state-20261004
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
audit="$output_dir/audit_piper_front_foot_hold_pilot.py"
protocol="$output_dir/front-foot-hold-known-state-protocol.json"
nav_actor=/mnt/yuanyue/data/go2-piper/2026-09-24-push-low-piper-z2O4vb/sim2real/go2-piper-low-level-policy-handoff/policies/nav/policy.pt
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
frozen_module_root="$isaac_repo/source/LeggedManip_Lab"
gpu_index=${GPU_INDEX:-0}

if [[ "$gpu_index" != 0 && "$gpu_index" != 1 ]]; then
    echo "GPU_INDEX must be 0 or 1" >&2
    exit 1
fi
if [[ "$(sha256sum "$diagnostic" | cut -d ' ' -f 1)" != 7ec75ce01fc101a70db41d721b71e8795dd0d8c2a93661c96c3a93675f63634c ]]; then
    echo "Diagnostic source differs from frozen protocol" >&2
    exit 1
fi
if [[ "$(sha256sum "$audit" | cut -d ' ' -f 1)" != 9816e28279854091029d637450e2a86fdad309e547d745ba571b388d25a0c103 ]]; then
    echo "Audit source differs from frozen protocol" >&2
    exit 1
fi
if [[ "$(sha256sum "$protocol" | cut -d ' ' -f 1)" != 3b949fa83ffddea2136e72c0dd0f296b9648dc568a833b2a56f40de32e46a89d ]]; then
    echo "Protocol differs from frozen registration" >&2
    exit 1
fi

for seed in 5503 5506 5201 5124; do
    report="$output_dir/seed${seed}-front-hold.json"
    log="$output_dir/seed${seed}-front-hold.log"
    if [[ -e "$report" || -e "$log" ]]; then
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
        --front-foot-hold-offset-m -0.005 \
        > "$log" 2>&1
    if [[ ! -s "$report" ]]; then
        echo "Missing report for seed${seed}" >&2
        exit 1
    fi
    "$python_bin" "$audit" --seed "$seed" \
        --baseline "$output_dir/seed${seed}-baseline.json" \
        --hold "$report" --output-json "$output_dir/seed${seed}-front-hold-audit.json"
    echo "Completed seed${seed} at $(date -Is)"
done
