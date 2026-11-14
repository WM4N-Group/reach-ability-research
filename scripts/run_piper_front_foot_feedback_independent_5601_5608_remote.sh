#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-front-foot-feedback-independent-5601-5608-20261004
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
pilot_audit="$output_dir/audit_piper_front_foot_feedback_pilot.py"
pair_audit="$output_dir/audit_piper_front_foot_feedback_pair.py"
protocol="$output_dir/front-foot-feedback-independent-5601-5608-protocol.json"
nav_actor=/mnt/yuanyue/data/go2-piper/2026-09-24-push-low-piper-z2O4vb/sim2real/go2-piper-low-level-policy-handoff/policies/nav/policy.pt
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
frozen_module_root="$isaac_repo/source/LeggedManip_Lab"
gpu_index=${GPU_INDEX:-0}

if [[ "$gpu_index" != 0 && "$gpu_index" != 1 ]]; then
    echo "GPU_INDEX must be 0 or 1" >&2
    exit 1
fi
verify_sha() {
    if [[ "$(sha256sum "$1" | cut -d ' ' -f 1)" != "$2" ]]; then
        echo "Frozen source or policy differs: $1" >&2
        exit 1
    fi
}
verify_sha "$diagnostic" b16164b8bf9e6df0b91ee850d4594cfdca1eeca533880112aebc431251692642
verify_sha "$pilot_audit" fbe148c5d934c22e1f7e6ff727cbf87645e912f60e10a19b80f9e1e59ad16142
verify_sha "$pair_audit" cd28b147e2d9f2d34c262e24a97be1f97d276e1a0137d206e9defb6d4c50243f
verify_sha "$protocol" b7a3e43c7771ec37ecee0c14fea702a751264d250302ac8713d7dbaec7982194
verify_sha "$nav_actor" 72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8
verify_sha "$push_checkpoint" b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721

for seed in 5601 5602 5603 5604 5605 5606 5607 5608; do
    audit_report="$output_dir/seed${seed}-pair-audit.json"
    if [[ -s "$audit_report" ]]; then
        echo "Previously audited seed${seed}; retaining existing reports"
        continue
    fi
    for variant in baseline feedback; do
        report="$output_dir/seed${seed}-${variant}.json"
        log="$output_dir/seed${seed}-${variant}.log"
        if [[ -s "$report" && -s "$log" ]]; then
            echo "Retaining completed seed${seed} ${variant}"
            continue
        fi
        if [[ -e "$report" || -e "$log" ]]; then
            echo "Incomplete existing output for seed${seed} ${variant}" >&2
            exit 1
        fi
        options=()
        if [[ "$variant" == feedback ]]; then
            options+=(--front-foot-feedback)
        fi
        echo "Starting seed${seed} ${variant} at $(date -Is)"
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
            "${options[@]}" > "$log" 2>&1
        if [[ ! -s "$report" ]]; then
            echo "Missing report for seed${seed} ${variant}" >&2
            exit 1
        fi
    done
    "$python_bin" "$pair_audit" --seed "$seed" \
        --baseline "$output_dir/seed${seed}-baseline.json" \
        --candidate "$output_dir/seed${seed}-feedback.json" \
        --output-json "$audit_report"
    echo "Completed seed${seed} at $(date -Is)"
done
