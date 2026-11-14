#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-front-foot-response-holdout-5501-5508-20261004
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
audit="$output_dir/audit_piper_front_foot_holdout.py"
protocol="$output_dir/front-foot-response-holdout-5501-5508-protocol.json"
nav_actor=/mnt/yuanyue/data/go2-piper/2026-09-24-push-low-piper-z2O4vb/sim2real/go2-piper-low-level-policy-handoff/policies/nav/policy.pt
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
frozen_module_root="$isaac_repo/source/LeggedManip_Lab"
gpu_index=${GPU_INDEX:-0}

if [[ "$gpu_index" != 0 && "$gpu_index" != 1 ]]; then
    echo "GPU_INDEX must be 0 or 1" >&2
    exit 1
fi
if [[ "$(sha256sum "$diagnostic" | cut -d ' ' -f 1)" != 4bcf27030f236af92ddf01df1c90955cb0cbe2884177632064610a194846f07f ]]; then
    echo "Diagnostic differs from frozen protocol" >&2
    exit 1
fi
if [[ "$(sha256sum "$audit" | cut -d ' ' -f 1)" != 10defc2e6dac6495b95ac63f5eed8e19910127a9b340b046b76a1f50955dc534 ]]; then
    echo "Audit differs from frozen protocol" >&2
    exit 1
fi
if [[ "$(sha256sum "$protocol" | cut -d ' ' -f 1)" != b95c1278ef61c40b1ecd1d0f6fbe91054dc1cece619a32fb4d763d14cfce4e52 ]]; then
    echo "Protocol differs from frozen registration" >&2
    exit 1
fi

run_case() {
    local seed=$1
    local condition=$2
    local offset=$3
    local report="$output_dir/seed${seed}-${condition}.json"
    local log="$output_dir/seed${seed}-${condition}.log"
    if [[ -e "$report" || -e "$log" ]]; then
        if [[ ! -s "$report" || ! -s "$log" ]]; then
            echo "Incomplete output for seed${seed} ${condition}" >&2
            exit 1
        fi
        echo "Reusing completed seed${seed} ${condition}"
        return
    fi
    echo "Starting seed${seed} ${condition} at $(date -Is)"
    local -a extra=()
    if [[ "$offset" != baseline ]]; then
        extra+=(--front-foot-probe-offset-m "$offset")
    fi
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
        "${extra[@]}" > "$log" 2>&1
    if [[ ! -s "$report" ]]; then
        echo "Missing report for seed${seed} ${condition}" >&2
        exit 1
    fi
    echo "Completed seed${seed} ${condition} at $(date -Is)"
}

for seed in 5501 5502 5503 5504 5505 5506 5507 5508; do
    run_case "$seed" baseline baseline
    baseline="$output_dir/seed${seed}-baseline.json"
    eligible=$("$python_bin" -c 'import json,sys; r=json.load(open(sys.argv[1])); t=r["support_trace"]; print(int(len(t)>=280 and not t[219]["motion_ready"]))' "$baseline")
    if [[ "$eligible" != 1 ]]; then
        echo "Seed${seed} ineligible from baseline; retaining denominator and skipping pulse pair"
        continue
    fi
    run_case "$seed" front-up 0.005
    run_case "$seed" front-down -0.005
    result="$output_dir/seed${seed}-pair-audit.json"
    if [[ ! -e "$result" ]]; then
        "$python_bin" "$audit" --seed "$seed" --baseline "$baseline" \
            --up "$output_dir/seed${seed}-front-up.json" \
            --down "$output_dir/seed${seed}-front-down.json" \
            --output-json "$result"
    else
        echo "Existing seed${seed} pair audit: $result"
    fi
done
