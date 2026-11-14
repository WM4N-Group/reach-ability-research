#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-push-clock-6403-6415-20261009
frozen_inputs=/mnt/yuanyue/tmp/reachability-lateral-conditional-6201-6208-20261008
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
source_root="$isaac_repo/source/LeggedManip_Lab"
protocol="$output_dir/push-clock-probe-6403-6415-protocol.json"
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
observer="$output_dir/piper_scene_runtime_observation.py"
nav_actor="$frozen_inputs/nav_policy.pt"
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
framework=/mnt/yuanyue/IsaacLab/source/isaaclab/isaaclab/envs/manager_based_rl_env.py
gpu_index=${GPU_INDEX:-0}

verify_sha() {
    local actual
    actual=$(sha256sum "$1")
    if [[ "${actual%% *}" != "$2" ]]; then
        echo "Frozen input differs: $1" >&2
        exit 1
    fi
}

verify_sha "$diagnostic" "$(jq -r '.source_sha256.new_diagnostic' "$protocol")"
verify_sha "$frozen_inputs/diagnose_piper_nav_push_handoff.py" "$(jq -r '.source_sha256.frozen_diagnostic' "$protocol")"
verify_sha "$observer" "$(jq -r '.source_sha256.scene_observer' "$protocol")"
verify_sha "$framework" "$(jq -r '.source_sha256.isaac_manager_based_rl_env' "$protocol")"
verify_sha "$nav_actor" "$(jq -r '.source_sha256.nav_actor' "$protocol")"
verify_sha "$push_checkpoint" "$(jq -r '.source_sha256.push_checkpoint' "$protocol")"
if [[ "$gpu_index" != 0 && "$gpu_index" != 1 ]]; then
    echo "GPU_INDEX must be 0 or 1" >&2
    exit 1
fi
if [[ "${VERIFY_ONLY:-0}" == 1 ]]; then
    echo "Clock probe frozen inputs verified"
    exit 0
fi

run_one() {
    local seed=$1 pulse_step=$2 mode=$3 report log
    report="$output_dir/seed${seed}-${mode}.json"
    log="$output_dir/seed${seed}-${mode}.log"
    if [[ -e "$report" || -e "$log" ]]; then
        echo "Output already exists: seed${seed}-${mode}; inspect before resuming" >&2
        exit 1
    fi
    local mode_flags=()
    if [[ "$mode" != plain ]]; then
        mode_flags+=(--record-push-clock-trace)
    fi
    if [[ "$mode" == pulse ]]; then
        mode_flags+=(--push-action-pulse-step "$pulse_step" --push-action-pulse-index 0
                     --push-action-pulse-delta 0.05)
    fi
    OMNI_KIT_ACCEPT_EULA=YES CUDA_VISIBLE_DEVICES="$gpu_index" \
        PYTHONPATH="$source_root${PYTHONPATH:+:$PYTHONPATH}" \
        timeout 600 "$python_bin" "$diagnostic" \
        --headless --device cuda:0 --nav-actor "$nav_actor" \
        --push-checkpoint "$push_checkpoint" --isaac-repo "$isaac_repo" \
        --output-json "$report" --seed "$seed" --box-nominal-y-m 0.12 \
        --nav-start-x -0.25 --nav-goal-x -0.05 --nav-arm-home \
        --record-push-support-trace --record-push-contact-load-trace \
        --record-leg-jacobian-trace --record-base-contact-source \
        --record-invalid-hand-contact-detail --record-hand-contact-substeps \
        --record-hand-contact-manifold --record-scene-runtime-observation \
        "${mode_flags[@]}" >"$log" 2>&1
    test -s "$report"
    echo "Completed seed${seed}-${mode}"
}

for seed in 6403 6415; do
    if [[ "$seed" == 6403 ]]; then pulse_step=460; else pulse_step=427; fi
    for mode in plain clock pulse; do
        run_one "$seed" "$pulse_step" "$mode"
    done
done
