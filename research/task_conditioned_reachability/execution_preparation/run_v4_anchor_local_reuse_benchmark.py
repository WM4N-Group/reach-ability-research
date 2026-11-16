"""Bounded CPU SOFTWARE benchmark of per-call geometry reuse, not simulation.

Uses exact original geometry algorithms and synthetic64x96 pixels, no sensor,
model inference, world or closed-run data. Baseline is this repo's c6bccd1 source.
Reports whole provider time and geometry inclusive subtime separately. Never
multiply this isolated ratio into an E/control/Actor/WM-forward speedup claim.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import types
from .v4_anchor_target8 import AnchorTarget8Provider, load_original_geometry

BASELINE_COMMIT = 'c6bccd1'
RELATIVE_SOURCE = 'research/task_conditioned_reachability/execution_preparation/v4_anchor_target8.py'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.rounds <= 5:
        parser.error('At most five paired rounds; no sustained load or parameter search')
    # Local pure NumPy CPU only. Avoid the native worker CPUs36/37 where possible.
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else []
    candidates = [c for c in affinity if c not in (36,37)]
    if candidates:
        os.sched_setaffinity(0,{candidates[-1]})
    import numpy as np
    root = Path(__file__).resolve().parents[3]
    source = root/'inference_source/original_behavior7a6_geometry'
    api = load_original_geometry(source)  # Hash checked; no trainer/WM/native.
    baseline = subprocess.check_output(['git','show',BASELINE_COMMIT+':'+RELATIVE_SOURCE],cwd=root)
    module = types.ModuleType(__package__+'._explicit_anchor_baseline_benchmark')
    module.__package__ = __package__
    exec(compile(baseline,'<SOFTWARE_BASELINE_'+BASELINE_COMMIT+'>','exec'),module.__dict__)
    old_class = module.AnchorTarget8Provider
    rgb = np.full((64,96,3),8,dtype=np.uint8)
    rgb[20:44,32:64] = [220,150,50]
    depth = np.ones((64,96),dtype=np.float32)
    K = np.array([[60.,0.,48.],[0.,60.,32.],[0.,0.,1.]])
    mount = np.array([[0.,0.,1.,.2],[-1.,0.,0.,0.],[0.,-1.,0.,.4],[0.,0.,0.,1.]])
    anchor = dict(rgb=rgb,depth_m=depth,camera_K=K,T_base_optical=mount,time_s=1.)
    obs = types.SimpleNamespace(time_s=1.015)
    candidates_found = api.propose_visual_candidates(rgb,depth,K,mount)['candidates']
    assert len(candidates_found)==1 and candidates_found[0]['geometry_valid']
    ref = candidates_found[0]['frame_local_ref']
    cases = [('16_candidates_one_geometry',[1.05]*16),
             ('16_candidates_four_geometries',[.58,.8,1.05,1.2]*4),
             ('four_unique_geometries_control',[.58,.8,1.05,1.2])]
    report = []
    for name, standoffs in cases:
        options = tuple(types.SimpleNamespace(sha256=hashlib.sha256(str(i).encode()).hexdigest())
                        for i in range(len(standoffs)))
        def associate(observation, opts, current):
            return dict(WM_anchor_RGB_bytes_sha256=hashlib.sha256(current['rgb'].tobytes()).hexdigest(),
                WM_anchor_time_s=current['time_s'],
                WM_anchor_calibration_sha256=api.visual_calibration_sha(current['camera_K'],current['T_base_optical']),
                frame_local_ref_by_option_sha256={o.sha256:dict(frame_local_ref=ref,declared_standoff_m=v)
                                                  for o,v in zip(opts,standoffs)})
        stats = {}; providers = {}
        for kind, cls in [('baseline',old_class),('per_call_reuse',AnchorTarget8Provider)]:
            stats[kind] = dict(plane_calls=0,vector_calls=0,geometry_inclusive_wall_s=0.)
            counter = stats[kind]
            def describe(*a,_counter=counter,**kw):
                _counter['plane_calls'] += 1; start=time.perf_counter()
                try:return api.describe_visible_goal(*a,**kw)
                finally:_counter['geometry_inclusive_wall_s']+=time.perf_counter()-start
            def vector(proof,_counter=counter):
                _counter['vector_calls'] += 1
                return api.geometry_vector(proof)
            wrapped=types.SimpleNamespace(**vars(api))
            wrapped.describe_visible_goal=describe;wrapped.geometry_vector=vector
            providers[kind]=cls(association_provider=associate,software_fixture=True,fixture_api=wrapped)
        # One warmup each; verify entire public descriptor/evidence result, not
        # just final numeric vector or a rounded approximation.
        expected=providers['baseline'](obs,options,anchor)
        actual=providers['per_call_reuse'](obs,options,anchor)
        assert actual==expected
        output_sha=hashlib.sha256(json.dumps(expected,sort_keys=True,allow_nan=False).encode()).hexdigest()
        assert all(v is not None for v in expected['target8_by_option_sha256'].values())
        timings={kind:[]for kind in providers}; call_counts={kind:[]for kind in providers}
        geometry_times={kind:[]for kind in providers}
        for iteration in range(args.rounds):
            order=('baseline','per_call_reuse')if iteration%2==0 else ('per_call_reuse','baseline')
            for kind in order:
                before=dict(stats[kind]); start=time.perf_counter()
                result=providers[kind](obs,options,anchor)
                timings[kind].append(time.perf_counter()-start)
                assert result==expected
                call_counts[kind].append(stats[kind]['plane_calls']-before['plane_calls'])
                geometry_times[kind].append(stats[kind]['geometry_inclusive_wall_s']-before['geometry_inclusive_wall_s'])
        oldmedian=statistics.median(timings['baseline']);newmedian=statistics.median(timings['per_call_reuse'])
        report.append(dict(case=name,candidates=len(options),unique_geometry_requests=len(set(standoffs)),
            rounds=args.rounds,provider_wall_s_by_round=timings,
            geometry_inclusive_subtime_s_by_round=geometry_times,geometry_subtime_not_additive_to_provider=True,
            original_plane_calls_by_round=call_counts,all_public_output_and_evidence_exactly_equal=True,
            output_sha256=output_sha,baseline_median_s=oldmedian,reuse_median_s=newmedian,
            isolated_provider_ratio=oldmedian/newmedian))
    print(json.dumps(dict(role='SYNTHETIC_SOFTWARE_ORIGINAL_GEOMETRY_CPU_ONLY_NOT_SIMULATION',
        baseline_commit=BASELINE_COMMIT,baseline_source_sha256=hashlib.sha256(baseline).hexdigest(),
        candidate_source_sha256=hashlib.sha256((root/RELATIVE_SOURCE).read_bytes()).hexdigest(),
        original_geometry_pins=api.source_pins,synthetic_rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),
        actual_affinity=sorted(os.sched_getaffinity(0))if affinity else [],rounds=args.rounds,cases=report,
        current_E20_uses_WM=False,current_E20_or_physics_or_WM_inference_speedup_claimed=False,
        model_native_renderer_physics_API_fit_calls=0,no_source_array_or_sensor_frame_read=True,
        no_cross_query_reuse=True),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
