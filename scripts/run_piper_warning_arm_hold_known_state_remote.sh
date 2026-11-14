#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-warning-arm-hold-known-state-20261012
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
pair_audit="$output_dir/audit_piper_warning_arm_hold_pair.py"
observer="$output_dir/piper_scene_runtime_observation.py"
protocol="$output_dir/warning-arm-hold-known-state-protocol.json"
nav_actor=/mnt/yuanyue/data/go2-piper/2026-09-24-push-low-piper-z2O4vb/sim2real/go2-piper-low-level-policy-handoff/policies/nav/policy.pt
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
frozen_module_root="$isaac_repo/source/LeggedManip_Lab"
mdp_root="$frozen_module_root/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/mdp"
gpu_index=${GPU_INDEX:?Set an idle remote GPU index (0 or 1)}

verify_sha() {
    if [[ "$(sha256sum "$1" | cut -d ' ' -f 1)" != "$2" ]]; then
        echo "Frozen input differs: $1" >&2
        exit 1
    fi
}
if [[ "$gpu_index" != 0 && "$gpu_index" != 1 ]]; then
    echo "GPU_INDEX must be 0 or 1" >&2
    exit 1
fi
if [[ ! -d "$output_dir" ]]; then
    echo "Prepared input directory is missing: $output_dir" >&2
    exit 1
fi
if [[ -n "$(nvidia-smi -i "$gpu_index" --query-compute-apps=pid --format=csv,noheader)" ]]; then
    echo "Selected GPU has a compute job" >&2
    exit 1
fi
verify_sha "$diagnostic" 73fb03d8370171cb0d8838ccbe3532727382b458e16432c70293b7d93a4af483
verify_sha "$pair_audit" 6ef94357f1545b99d96322ed5544772ccd85061f7d276adff670a63728b3e705
verify_sha "$observer" 884bbb3350989b1b04f53efcb17b4cf369a0e3f56cb7dbd98a860e71598d26e5
verify_sha "$protocol" 8732e6d635db131e7452b151038ae2644aa534f63c9e7d3fe32ae589f56fd79b
verify_sha "$nav_actor" 72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8
verify_sha "$push_checkpoint" b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721
for name in box_push.py box_push_actions.py box_push_control.py box_push_ik.py; do
    verify_sha "$mdp_root/$name" "$(jq -r --arg name "$name" '.control_sha256[$name]' "$protocol")"
done

seed=5802
baseline=/mnt/yuanyue/tmp/reachability-support-warning-cohort-5801-5824-20261004/seed5802-baseline.json
verify_sha "$baseline" 4746bfcbbba37cfe89154447a51357c09678b4bbd58addaecf6e193739881392
report="$output_dir/seed${seed}-warning-arm-hold.json"
log="$output_dir/seed${seed}-warning-arm-hold.log"
audit_report="$output_dir/seed${seed}-warning-arm-hold-audit.json"
if [[ -e "$report" || -e "$log" || -e "$audit_report" ]]; then
    echo "Output already exists for seed $seed" >&2
    exit 1
fi

OMNI_KIT_ACCEPT_EULA=YES CUDA_VISIBLE_DEVICES="$gpu_index" \
    PYTHONPATH="$frozen_module_root${PYTHONPATH:+:$PYTHONPATH}" \
    timeout 600 "$python_bin" "$diagnostic" \
    --headless --device cuda:0 \
    --nav-actor "$nav_actor" --push-checkpoint "$push_checkpoint" \
    --isaac-repo "$isaac_repo" --output-json "$report" --seed "$seed" \
    --nav-start-x -0.25 --nav-goal-x -0.05 --nav-arm-home \
    --record-push-support-trace --record-push-contact-load-trace \
    --record-leg-jacobian-trace --record-base-contact-source \
    --hold-arm-on-support-warning > "$log" 2>&1
if [[ ! -s "$report" ]]; then
    echo "Missing report for seed $seed" >&2
    exit 1
fi
"$python_bin" "$pair_audit" --baseline "$baseline" --candidate "$report" \
    --protocol "$protocol" --output-json "$audit_report"
