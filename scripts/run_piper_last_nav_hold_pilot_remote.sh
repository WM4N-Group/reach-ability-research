#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-last-nav-hold-pilot-20261003
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
nav_actor=/mnt/yuanyue/data/go2-piper/2026-09-24-push-low-piper-z2O4vb/sim2real/go2-piper-low-level-policy-handoff/policies/nav/policy.pt
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
frozen_module_root="$isaac_repo/source/LeggedManip_Lab"

mkdir -p "$output_dir"
for seed in 5201 5124; do
    report="$output_dir/seed${seed}-last-nav-hold.json"
    log="$output_dir/seed${seed}-last-nav-hold.log"
    if [[ -e "$report" || -e "$log" ]]; then
        echo "Output already exists for seed $seed" >&2
        exit 1
    fi
    echo "Starting seed $seed at $(date -Is)"
    OMNI_KIT_ACCEPT_EULA=YES CUDA_VISIBLE_DEVICES=1 \
        PYTHONPATH="$frozen_module_root${PYTHONPATH:+:$PYTHONPATH}" \
        timeout 600 "$python_bin" "$diagnostic" \
        --headless --device cuda:0 \
        --nav-actor "$nav_actor" \
        --push-checkpoint "$push_checkpoint" \
        --isaac-repo "$isaac_repo" \
        --output-json "$report" --seed "$seed" \
        --nav-start-x -0.25 --nav-goal-x -0.05 --nav-arm-home \
        --record-push-support-trace --record-push-contact-load-trace \
        --handoff-settle-stable-s 0.4 --handoff-settle-timeout-s 3.0 \
        --handoff-settle-control hold_last_nav > "$log" 2>&1
    if [[ ! -s "$report" ]]; then
        echo "Missing report for seed $seed" >&2
        exit 1
    fi
    echo "Completed seed $seed at $(date -Is)"
done
