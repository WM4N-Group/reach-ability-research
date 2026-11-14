#!/usr/bin/env bash
set -euo pipefail

output_dir=/mnt/yuanyue/tmp/reachability-support-warning-cohort-5801-5824-20261004
python_bin=/mnt/yuanyue/envs/go2-isaac/bin/python
diagnostic="$output_dir/diagnose_piper_nav_push_handoff.py"
protocol="$output_dir/support-warning-cohort-5801-5824-protocol.json"
resume_protocol="$output_dir/support-warning-cohort-5801-5824-resume-protocol.json"
nav_actor=/mnt/yuanyue/data/go2-piper/2026-09-24-push-low-piper-z2O4vb/sim2real/go2-piper-low-level-policy-handoff/policies/nav/policy.pt
push_checkpoint=/mnt/yuanyue/data/go2-piper/push-loadprobe-20261001-ac/selected-candidate/model_199.pt
isaac_repo=/mnt/yuanyue/data/go2-piper/push-ramptrain-20261001-aa/train
frozen_module_root="$isaac_repo/source/LeggedManip_Lab"

verify_sha() {
    if [[ "$(sha256sum "$1" | cut -d ' ' -f 1)" != "$2" ]]; then
        echo "Frozen input differs: $1" >&2
        exit 1
    fi
}
verify_sha "$diagnostic" 944533f0069ae944a7f0203b2ab88e8f776f5169353af2f91789a8e1f7974e0b
verify_sha "$protocol" 7dc46f300224453ec2a11e464a794e0394ec1f8e51258b0a5774616a23b1891a
verify_sha "$resume_protocol" 7d2d2367affc9801bee0707ba01fd4c0b8909e79067d2361762ac69448fd89df
verify_sha "$nav_actor" 72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8
verify_sha "$push_checkpoint" b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721
verify_sha "$output_dir/seed5823-baseline.json" 7e200d10711ed3f6fa48e54162e09b2175042908ed4c89c8efd481df3607ce8b
for seed in $(seq 5801 5823); do
    if [[ ! -s "$output_dir/seed${seed}-baseline.json" ]]; then
        echo "Missing previous report for seed${seed}" >&2
        exit 1
    fi
done
report="$output_dir/seed5824-baseline.json"
log="$output_dir/seed5824-baseline.log"
if [[ -e "$report" || -e "$log" ]]; then
    echo "Seed5824 output already exists" >&2
    exit 1
fi
echo "Starting seed5824 at $(date -Is)"
OMNI_KIT_ACCEPT_EULA=YES CUDA_VISIBLE_DEVICES=0 \
    PYTHONPATH="$frozen_module_root${PYTHONPATH:+:$PYTHONPATH}" \
    timeout 600 "$python_bin" "$diagnostic" \
    --headless --device cuda:0 \
    --nav-actor "$nav_actor" \
    --push-checkpoint "$push_checkpoint" \
    --isaac-repo "$isaac_repo" \
    --output-json "$report" --seed 5824 \
    --nav-start-x -0.25 --nav-goal-x -0.05 --nav-arm-home \
    --record-push-support-trace --record-push-contact-load-trace \
    --record-leg-jacobian-trace --record-base-contact-source \
    --record-recovery-decision-state > "$log" 2>&1
echo "Completed seed5824 at $(date -Is)"
