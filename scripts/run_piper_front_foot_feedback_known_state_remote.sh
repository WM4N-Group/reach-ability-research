#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-front-foot-feedback-known-state-20261004
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
audit="$output_dir/audit_piper_front_foot_feedback_pilot.py"
protocol="$output_dir/front-foot-feedback-known-state-protocol.json"
nav_actor=/mnt/yuanyue/data/go2-piper/2026-09-24-push-low-piper-z2O4vb/sim2real/go2-piper-low-level-policy-handoff/policies/nav/policy.pt
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
frozen_module_root="$isaac_repo/source/LeggedManip_Lab"
gpu_index=${GPU_INDEX:-0}

if [[ "$gpu_index" != 0 && "$gpu_index" != 1 ]]; then
    echo "GPU_INDEX must be 0 or 1" >&2
    exit 1
fi
if [[ "$(sha256sum "$diagnostic" | cut -d ' ' -f 1)" != b16164b8bf9e6df0b91ee850d4594cfdca1eeca533880112aebc431251692642 ]]; then
    echo "Diagnostic source differs from frozen protocol" >&2
    exit 1
fi
if [[ "$(sha256sum "$audit" | cut -d ' ' -f 1)" != fbe148c5d934c22e1f7e6ff727cbf87645e912f60e10a19b80f9e1e59ad16142 ]]; then
    echo "Audit source differs from frozen protocol" >&2
    exit 1
fi
if [[ "$(sha256sum "$protocol" | cut -d ' ' -f 1)" != 145ab26cdd5949ca4f98249bb5423840fa7b932e64b2eaf4c6b852d5860ee3c4 ]]; then
    echo "Protocol differs from frozen registration" >&2
    exit 1
fi

for seed in 5503 5506 5201 5124; do
    report="$output_dir/seed${seed}-front-feedback.json"
    log="$output_dir/seed${seed}-front-feedback.log"
    audit_report="$output_dir/seed${seed}-front-feedback-audit.json"
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
        --front-foot-feedback > "$log" 2>&1
    if [[ ! -s "$report" ]]; then
        echo "Missing report for seed${seed}" >&2
        exit 1
    fi
    "$python_bin" "$audit" --seed "$seed" \
        --baseline "$output_dir/seed${seed}-baseline.json" \
        --candidate "$report" --output-json "$audit_report"
    echo "Completed seed${seed} at $(date -Is)"
done
