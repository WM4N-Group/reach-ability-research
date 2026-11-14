#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-base-contact-source-known-state-20261004
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
protocol="$output_dir/base-contact-source-known-state-protocol.json"
nav_actor=/mnt/yuanyue/data/go2-piper/2026-09-24-push-low-piper-z2O4vb/sim2real/go2-piper-low-level-policy-handoff/policies/nav/policy.pt
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
frozen_module_root="$isaac_repo/source/LeggedManip_Lab"
gpu_index=${GPU_INDEX:-0}

if [[ "$gpu_index" != 0 && "$gpu_index" != 1 ]]; then
    echo "GPU_INDEX must be 0 or 1" >&2
    exit 1
fi
if [[ "$(sha256sum "$diagnostic" | cut -d ' ' -f 1)" != 7f4dcc7e59918d5865c00f3e1cc88f02b24e0c879d0bdae4a2c31ed243965293 ]]; then
    echo "Diagnostic source differs from frozen protocol" >&2
    exit 1
fi
if [[ "$(sha256sum "$protocol" | cut -d ' ' -f 1)" != 1403ffcac2ffa3464d4d99a593d97e4fa71f180ccc48fd61b73f6dc486c38f02 ]]; then
    echo "Protocol differs from frozen registration" >&2
    exit 1
fi

for seed in 5201 5124; do
    report="$output_dir/seed${seed}-base-contact-source.json"
    log="$output_dir/seed${seed}-base-contact-source.log"
    if [[ -e "$report" || -e "$log" ]]; then
        echo "Output already exists for seed $seed" >&2
        exit 1
    fi
    echo "Starting seed $seed at $(date -Is)"
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
        > "$log" 2>&1
    if [[ ! -s "$report" ]]; then
        echo "Missing report for seed $seed" >&2
        exit 1
    fi
    echo "Completed seed $seed at $(date -Is)"
done
