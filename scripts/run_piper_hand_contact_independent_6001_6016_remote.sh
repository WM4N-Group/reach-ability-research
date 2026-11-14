#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-hand-independent-6001-6016-20261008
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
source_root="$isaac_repo/source/LeggedManip_Lab"
mdp_root="$source_root/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/mdp"
nav_actor="$output_dir/nav_policy.pt"
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
observer="$output_dir/piper_scene_runtime_observation.py"
protocol="$output_dir/hand-contact-independent-6001-6016-protocol.json"
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
verify_sha "$diagnostic" 1b2f22c7bc44835e44e8d378b42578b5459c4df7ce8f6af6faef15cd35ad0c7b
verify_sha "$observer" 884bbb3350989b1b04f53efcb17b4cf369a0e3f56cb7dbd98a860e71598d26e5
verify_sha "$nav_actor" 72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8
verify_sha "$push_checkpoint" b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721
verify_sha "$source_root/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/config/go2_piper/box_env_cfg.py" c1591665dcc0d2f6794a121ec131bfb86a4d600482bf879153e1b549a33a2d4f
verify_sha "$mdp_root/box_push.py" 889a812aa2676b8c0d3d340419af407a64dee67b8d4a07812c1ce0aa74bb1d1d
verify_sha "$mdp_root/box_push_control.py" 92d5135c09feaff66ae848709588f1d2aa75af40e55f7e4428445fb95c0c5b3d
verify_sha "$mdp_root/box_push_ik.py" 6086163efb4d64b5a812cb2cbe506bc82eaafbca6b08186151fab7a1145f9370
verify_sha "$mdp_root/box_push_actions.py" d92f8d006b1f5b74b7603501ec68a38fe88894e151c961fafcfb15adaf92d7c5
verify_sha "$protocol" b77da5b80081fed1d628f3244a7ee9b7def176dd8ab41e196f48091bb4abe0ea

for seed in {6001..6016}; do
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
        --record-invalid-hand-contact-detail --record-hand-contact-substeps \
        --record-hand-contact-manifold --record-scene-runtime-observation >"$log" 2>&1
    test -s "$report"
    echo "Completed seed${seed}"
done
