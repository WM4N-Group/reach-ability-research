#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-lateral-conditional-6201-6208-20261008
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
source_root="$isaac_repo/source/LeggedManip_Lab"
task_root="$source_root/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab"
mdp_root="$task_root/mdp"
protocol="$output_dir/lateral-layout-conditional-6201-6208-protocol.json"
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
observer="$output_dir/piper_scene_runtime_observation.py"
nav_actor="$output_dir/nav_policy.pt"
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
gpu_index=${GPU_INDEX:-0}

verify_sha() {
    local actual
    actual=$(sha256sum "$1")
    if [[ "${actual%% *}" != "$2" ]]; then
        echo "Frozen input differs: $1" >&2
        exit 1
    fi
}

verify_source() {
    verify_sha "$2" "$(jq -r --arg key "$1" '.source_sha256[$key]' "$protocol")"
}

if [[ "$gpu_index" != 0 && "$gpu_index" != 1 ]]; then
    echo "GPU_INDEX must be 0 or 1" >&2
    exit 1
fi
verify_sha "$protocol" 78a6adf13446475769f7eae0b7bc26d6abeeeca7c4aa5e719a7ba09c29f75f7a
verify_source diagnostic "$diagnostic"
verify_source scene_observer "$observer"
verify_source piper_box_env_cfg "$task_root/config/go2_piper/box_env_cfg.py"
verify_source arx5_box_push_env_cfg "$task_root/config/go2_arx5/box_push_env_cfg.py"
verify_source flat_env_cfg "$task_root/config/go2_arx5/flat_env_cfg.py"
verify_source parent_env_cfg "$task_root/leggedmanip_lab_env_cfg.py"
verify_source box_push_reset "$mdp_root/box_push.py"
verify_source safe_approach_resource "$isaac_repo/mujoco/deploy/piper_push_safe_approach.json"
for name in box_push.py box_push_control.py box_push_ik.py box_push_actions.py; do
    verify_sha "$mdp_root/$name" "$(jq -r --arg key "$name" '.control_sha256[$key]' "$protocol")"
done
verify_sha "$nav_actor" "$(jq -r '.nav_actor_sha256' "$protocol")"
verify_sha "$push_checkpoint" "$(jq -r '.push_checkpoint_sha256' "$protocol")"

run_one() {
    local seed=$1 tag=$2 nominal_y=$3 report log
    report="$output_dir/seed${seed}-${tag}.json"
    log="$output_dir/seed${seed}-${tag}.log"
    if [[ -s "$report" && -s "$log" ]]; then
        if ! grep -q 'NAV_PUSH_HANDOFF_DIAGNOSTIC=' "$log"; then
            echo "Missing completion marker for seed${seed}-${tag}" >&2
            exit 1
        fi
        echo "Retaining completed seed${seed}-${tag}"
        return
    fi
    if [[ -e "$report" || -e "$log" ]]; then
        echo "Incomplete output for seed${seed}-${tag}; inspect before resuming" >&2
        exit 1
    fi
    OMNI_KIT_ACCEPT_EULA=YES CUDA_VISIBLE_DEVICES="$gpu_index" \
        PYTHONPATH="$source_root${PYTHONPATH:+:$PYTHONPATH}" \
        timeout 600 "$python_bin" "$diagnostic" \
        --headless --device cuda:0 --nav-actor "$nav_actor" \
        --push-checkpoint "$push_checkpoint" --isaac-repo "$isaac_repo" \
        --output-json "$report" --seed "$seed" --box-nominal-y-m "$nominal_y" \
        --nav-start-x -0.25 --nav-goal-x -0.05 --nav-arm-home \
        --record-push-support-trace --record-push-contact-load-trace \
        --record-leg-jacobian-trace --record-base-contact-source \
        --record-invalid-hand-contact-detail --record-hand-contact-substeps \
        --record-hand-contact-manifold --record-scene-runtime-observation >"$log" 2>&1
    test -s "$report"
    echo "Completed seed${seed}-${tag}"
}

for seed in {6201..6208}; do
    run_one "$seed" center 0.0
done
for seed in {6201..6208}; do
    center="$output_dir/seed${seed}-center.json"
    if jq -e '.outcome == "push_terminated" and .terminal.reasons.box_settled == true and any(.hand_contact_substeps[]; .hand_contact.force_norm_n > 1.0)' "$center" >/dev/null; then
        run_one "$seed" minus012 -0.12
        run_one "$seed" plus012 0.12
    else
        echo "Unqualified center seed${seed}; retaining screen outcome"
    fi
done
