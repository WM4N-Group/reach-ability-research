#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-hand-substeps-5904-20261008
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
source_root="$isaac_repo/source/LeggedManip_Lab"
nav_actor="$output_dir/nav_policy.pt"
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
protocol="$output_dir/hand-contact-substep-5904-known-state-protocol.json"
report="$output_dir/seed5904.json"
log="$output_dir/run.log"
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
if [[ -e "$report" || -e "$log" ]]; then
    echo "Output already exists; inspect it before rerunning" >&2
    exit 1
fi
verify_sha "$diagnostic" 94c8dc91693567d303a2d85cf8eca5ef0e2590f5a49ef02f5f0010e2687744c7
verify_sha "$nav_actor" 72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8
verify_sha "$push_checkpoint" b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721
verify_sha "$source_root/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/config/go2_piper/box_env_cfg.py" c1591665dcc0d2f6794a121ec131bfb86a4d600482bf879153e1b549a33a2d4f
verify_sha "$protocol" d2d595634e216f3563302d37a56204fc59f660c10ba1c90729796a0d75282390

OMNI_KIT_ACCEPT_EULA=YES CUDA_VISIBLE_DEVICES="$gpu_index" \
    PYTHONPATH="$source_root:$output_dir${PYTHONPATH:+:$PYTHONPATH}" \
    timeout 600 "$python_bin" "$diagnostic" \
    --headless --device cuda:0 --nav-actor "$nav_actor" \
    --push-checkpoint "$push_checkpoint" --isaac-repo "$isaac_repo" \
    --output-json "$report" --seed 5904 \
    --nav-start-x -0.25 --nav-goal-x -0.05 --nav-arm-home \
    --record-push-support-trace --record-push-contact-load-trace \
    --record-leg-jacobian-trace --record-base-contact-source \
    --record-invalid-hand-contact-detail --record-hand-contact-substeps >"$log" 2>&1
test -s "$report"
