#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-hand-substeps-success-5901-5903-20261008
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
source_root="$isaac_repo/source/LeggedManip_Lab"
nav_actor="$output_dir/nav_policy.pt"
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
protocol="$output_dir/hand-contact-substep-success-controls-5901-5903-protocol.json"
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
verify_sha "$diagnostic" 94c8dc91693567d303a2d85cf8eca5ef0e2590f5a49ef02f5f0010e2687744c7
verify_sha "$nav_actor" 72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8
verify_sha "$push_checkpoint" b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721
verify_sha "$source_root/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/config/go2_piper/box_env_cfg.py" c1591665dcc0d2f6794a121ec131bfb86a4d600482bf879153e1b549a33a2d4f
verify_sha "$protocol" 5f9e0de2e59162cf7a6bd8d0650bdf7e3d61782c320de80514d38560f5c75a4a

for seed in 5901 5902 5903; do
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
        PYTHONPATH="$source_root:$output_dir${PYTHONPATH:+:$PYTHONPATH}" \
        timeout 600 "$python_bin" "$diagnostic" \
        --headless --device cuda:0 --nav-actor "$nav_actor" \
        --push-checkpoint "$push_checkpoint" --isaac-repo "$isaac_repo" \
        --output-json "$report" --seed "$seed" \
        --nav-start-x -0.25 --nav-goal-x -0.05 --nav-arm-home \
        --record-push-support-trace --record-push-contact-load-trace \
        --record-leg-jacobian-trace --record-base-contact-source \
        --record-invalid-hand-contact-detail --record-hand-contact-substeps >"$log" 2>&1
    test -s "$report"
    echo "Completed seed${seed}"
done
