#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-scene-entry-pilot-5901-5904-20261008
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
source_root="$isaac_repo/source/LeggedManip_Lab"
nav_actor="$output_dir/nav_policy.pt"
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
observer="$output_dir/piper_scene_runtime_observation.py"
protocol="$output_dir/scene-entry-identification-pilot-5901-5904-protocol.json"
gpu_index=${GPU_INDEX:-0}

verify_sha() {
    local actual
    actual=$(sha256sum "$1")
    if [[ "${actual%% *}" != "$2" ]]; then
        echo "Frozen input differs: $1" >&2
        exit 1
    fi
}

if [[ "$gpu_index" != 0 && "$gpu_index" != 1 ]]; then
    echo "GPU_INDEX must be 0 or 1" >&2
    exit 1
fi
verify_sha "$diagnostic" 21812232341f3c032ec48d76720983831fdf2ad9bfa333b08769e850734659ec
verify_sha "$observer" 884bbb3350989b1b04f53efcb17b4cf369a0e3f56cb7dbd98a860e71598d26e5
verify_sha "$nav_actor" 72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8
verify_sha "$push_checkpoint" b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721
verify_sha "$source_root/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/config/go2_piper/box_env_cfg.py" c1591665dcc0d2f6794a121ec131bfb86a4d600482bf879153e1b549a33a2d4f
verify_sha "$protocol" bf60acc6cdbc74cac628b14d286e907e80d3bb4a7668ca09cf712cdf063a57c6

for seed in 5901 5902 5903 5904; do
    report="$output_dir/seed${seed}.json"
    log="$output_dir/seed${seed}.log"
    if [[ -s "$report" && -s "$log" ]]; then
        echo "Retaining completed seed${seed}"
        continue
    fi
    if [[ -e "$report" || -e "$log" ]]; then
        echo "Incomplete output for seed${seed}; inspect it before resuming" >&2
        exit 1
    fi
    OMNI_KIT_ACCEPT_EULA=YES CUDA_VISIBLE_DEVICES="$gpu_index" \
        PYTHONPATH="$source_root${PYTHONPATH:+:$PYTHONPATH}" \
        timeout 600 "$python_bin" "$diagnostic" \
        --headless --device cuda:0 --nav-actor "$nav_actor" \
        --push-checkpoint "$push_checkpoint" --isaac-repo "$isaac_repo" \
        --output-json "$report" --seed "$seed" \
        --nav-start-x -0.25 --nav-goal-x -0.05 --nav-arm-home \
        --record-push-support-trace --record-push-contact-load-trace \
        --record-leg-jacobian-trace --record-base-contact-source \
        --record-scene-runtime-observation >"$log" 2>&1
    test -s "$report"
    echo "Completed seed${seed}"
done
