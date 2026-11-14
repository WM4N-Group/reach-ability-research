#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-front-foot-response-known-state-20261004
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
audit="$output_dir/audit_piper_front_foot_response.py"
protocol="$output_dir/front-foot-response-known-state-protocol.json"
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
    echo "Diagnostic source differs from frozen protocol" >&2
    exit 1
fi
if [[ "$(sha256sum "$audit" | cut -d ' ' -f 1)" != 8b045478cf3231e3393ba92e979439ad2bcccd488a7eeaf469a80cc6b9a35625 ]]; then
    echo "Audit source differs from frozen protocol" >&2
    exit 1
fi
if [[ "$(sha256sum "$protocol" | cut -d ' ' -f 1)" != 50545b073139da75948712daa806b5a7c15dc77a98cbb0568563927c0414beac ]]; then
    echo "Protocol differs from frozen registration" >&2
    exit 1
fi

for condition in 5201:up:0.005 5201:down:-0.005 5124:up:0.005 5124:down:-0.005; do
    IFS=: read -r seed direction offset <<< "$condition"
    report="$output_dir/seed${seed}-front-${direction}.json"
    log="$output_dir/seed${seed}-front-${direction}.log"
    audit_report="$output_dir/seed${seed}-front-${direction}-audit.json"
    if [[ -e "$report" && ! -s "$report" || -e "$log" && ! -e "$report" ]]; then
        echo "Incomplete output exists for $condition" >&2
        exit 1
    fi
    if [[ ! -e "$report" ]]; then
        echo "Starting $condition at $(date -Is)"
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
            --front-foot-probe-offset-m "$offset" \
            > "$log" 2>&1
    fi
    if [[ ! -s "$report" ]]; then
        echo "Missing report for $condition" >&2
        exit 1
    fi
    audit_args=("$audit" \
        --baseline "$output_dir/seed${seed}-base-contact-source.json" \
        --probe "$report" --seed "$seed" --offset-m "$offset")
    if [[ ! -e "$audit_report" ]]; then
        audit_args+=(--output-json "$audit_report")
    fi
    "$python_bin" "${audit_args[@]}"
    echo "Completed $condition at $(date -Is)"
done
