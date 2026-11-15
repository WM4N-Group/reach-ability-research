#!/usr/bin/env python3
"""One new full-1 public frame; reuse pinned full-4/full-2 DEV measurements.

This is not a model, scene qualification, online proposal or causal comparison.
All medians are in each observation's own parent/body frame, not WORLD poses.
"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

p = argparse.ArgumentParser(description=__doc__)
for name in ('runs-root', 'proposer', 'component-helper', 'output'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()
runs = Path(a.runs_root)
forbidden = []

def fence(event, args):
    if event == 'import' and str(args[0]).split('.')[0] in ('torch', 'mujoco', 'onnxruntime'):
        forbidden.append(str(args[0])); raise RuntimeError('No native/Actor')
    if event in ('socket.connect', 'socket.bind', 'socket.getaddrinfo', 'subprocess.Popen'):
        forbidden.append(event); raise RuntimeError('No network/child')
    if event == 'open' and isinstance(args[0], str) and (
            '/query-private-' in args[0] or args[0].endswith(('/catalog.json', '/association.json'))):
        forbidden.append('PRIVATE_INPUT'); raise RuntimeError('Public only')
sys.addaudithook(fence)
import numpy as np
from PIL import Image
assert np.__version__ == '1.26.4'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

pins = {str(Path(__file__).resolve()): sha(__file__)}
cache_specs = (
    ('G1-pair-public-comparison-20261115-v2.json', 'c62b36c19e67e9bb65e21343935fdd189b46c4cc4e69f3d497244a9a52cadde5'),
    ('G2-full2-left-crosslayout-measurement-20261115-v1.json', '0ce3a0ff66a1459dbbe41ea41a059dcc758a5bad9c29e1804eb30654279826cb'))
caches = []
for filename, expected in cache_specs:
    path = runs / filename
    assert sha(path) == expected
    pins[str(path)] = expected
    caches.append(json.loads(path.read_bytes()))
reports = []
frames = []
for i, filename in enumerate(('G1-left-public-boundary-20261115-v2.json',
                               'G2-full2-left-public-boundary-20261115-v1.json',
                               'G2-full1-left-public-boundary-20261115-v1.json')):
    path = runs / filename
    report = json.loads(path.read_bytes())
    assert report['status'] == 'ACTUAL_FIRST_CLIMB_PREPARE_PUBLIC_QUERY_BOUND'
    assert report['role'] == 'DEV_AUDIT_ONLY_NOT_TRAIN_OR_ONLINE'
    if i < 2:
        assert caches[1]['source_pins'][str(path)] == sha(path)
    pins[str(path)] = sha(path)
    q = report['first_PREPARE']
    for key, hash_key in (('actual_query_path', 'actual_query_file_sha256'),
                           ('RGB_file', 'RGB_encoded_sha256'), ('depth_file', 'depth_file_sha256'),
                           ('calibration_file', 'calibration_file_sha256')):
        assert sha(q[key]) == q[hash_key]
        pins[q[key]] = q[hash_key]
        if i < 2:
            assert caches[1]['source_pins'][q[key]] == q[hash_key]
    with Image.open(q['RGB_file']) as image:
        rgb = np.asarray(image).copy()
    frames.append((rgb, np.load(q['depth_file'], allow_pickle=False),
                   np.asarray(q['camera_K']), np.asarray(q['T_base_optical'])))
    reports.append(report)
assert [r['scope_id'] for r in reports] == [
    'data-46308-native-prefix-left-PUSH-CLIMB-20261115-v2',
    'data-46308-G2-full2-left-PUSH-CLIMB-20261115-v1',
    'data-46308-G2-full1-left-PUSH-CLIMB-20261115-v1']
mods = []
for i, (path, expected) in enumerate(((a.proposer, '837e95ecd7bc3249154b8a53097f71fd90974a2df9fb4a35d87116d0254af304'),
                                     (a.component_helper, '0b66cbf44925722dedaea46cb3e5800cf69e7e7e39253ffb861299f837b1540b'))):
    assert sha(path) == expected and expected in caches[1]['source_pins'].values()
    pins[path] = expected
    spec = importlib.util.spec_from_file_location('Reach_full1_' + str(i), path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mods.append(mod)
original, helper = mods
q = reports[2]['first_PREPARE']
obs = json.loads(Path(q['actual_query_path']).read_bytes())
rgb, depth, K, T = frames[2]
support = helper.derive_original_component_support(original, rgb, depth, K, T,
    acquisition_time_s=obs['rgb']['time_s'], encoded_rgb_sha256=obs['rgb']['sha256'])
joins = helper.join_current_public_components(obs, support)
alias = [o for o in obs['objects'] if o['label'].startswith('cuboid-2; dimensions ')]
comp = dict(status='UNKNOWN_NO_UNIQUE_PUBLIC_ALIAS', nominal_visible_median_parent_base_m=None)
if len(alias) == 1:
    matches = [r for r in joins if r['public_target_ref'] == alias[0]['target_ref']]
    if len(matches) == 1 and matches[0]['public_bbox_component_correspondence_exact']:
        ref = matches[0]['frame_local_ref']
        c = next(c for c in support['component_support'] if c['frame_local_ref'] == ref)
        prop = next(c for c in support['original_proposals']['candidates'] if c['frame_local_ref'] == ref)
        yx = np.asarray(c['pixel_indices_yx'], dtype=np.int64)
        z = depth[yx[:, 0], yx[:, 1], 0]
        comp.update(status='EXACT_PUBLIC_COMPONENT_NOMINAL_ONLY', component_pixels=c['pixel_count'],
            valid_depth_pixels=int((np.isfinite(z) & (z >= .05) & (z <= 15.)).sum()),
            nominal_visible_median_parent_base_m=prop['visible_surface_median_base_xyz_m'])
    else:
        comp['status'] = 'UNKNOWN_NO_ACCEPTED_COMPONENT'
components = [caches[0]['component_estimates'][0], caches[1]['component_estimates'][1], comp]
comparisons = []
for i, case in enumerate(('full-4', 'full-2')):
    blocks = {}
    for name, unit in {'q': 'rad', 'dq': 'rad/s', 'gravity': '1',
                       'angular_velocity': 'rad/s', 'linear_velocity': 'm/s'}.items():
        x, y = [np.asarray(r['first_PREPARE']['public45D_vectors'][name]) for r in (reports[i], reports[2])]
        delta = y - x
        blocks[name] = dict(unit=unit, exact_numeric_equal=bool(np.array_equal(x, y)),
            different_channels=int((x != y).sum()), full1_minus_baseline_per_channel=delta.tolist(),
            max_abs_delta=float(np.max(np.abs(delta))), L2_delta=float(np.linalg.norm(delta)))
    f0, f1 = frames[i], frames[2]
    delta = None
    x, y = components[i]['nominal_visible_median_parent_base_m'], comp['nominal_visible_median_parent_base_m']
    if x is not None and y is not None:
        d = np.asarray(y) - np.asarray(x)
        delta = dict(full1_minus_baseline_XYZ_m=d.tolist(), L2_m=float(np.linalg.norm(d)),
                     physical_error_or_reference_relative_bound_m=None)
    comparisons.append(dict(baseline=case, new='full-1', public45D_blocks=blocks,
        decoded_RGB_exact_numeric_equal=bool(np.array_equal(f0[0], f1[0])),
        depth_exact_numeric_equal_NaNs_equal=bool(np.array_equal(f0[1], f1[1], equal_nan=True)),
        camera_K_exact_numeric_equal=bool(np.array_equal(f0[2], f1[2])),
        T_base_optical_exact_numeric_equal=bool(np.array_equal(f0[3], f1[3])), nominal_component_delta=delta))
for path, expected in pins.items():
    assert sha(path) == expected
assert not forbidden
out = dict(at=dt.datetime.now().astimezone().isoformat(),
    role='THREE_REGISTERED_SOURCES_MATCHED_LEFT_PREFIX_DEV_ONLY_NOT_FIT',
    source_pins=pins, conditions=[r['scope_id'] for r in reports],
    query_times_s=[r['first_PREPARE']['query_time_s'] for r in reports],
    component_estimates=components, comparisons=comparisons,
    old_frame_proposer_reexecutions=0, new_full1_original_proposer_calls=1,
    historical_attempts=5, historical_chain_PASS=4, historical_predecessor_abort=1,
    historical_first_PREPARE=4, historical_unreached=1,
    physical_error_bound_m=None, scene_family_or_training_admission=False,
    causal_effect_or_optimizer_gain_claimed=False, independent_TEST=0, model_fits=0,
    new_simulator_capture_Actor_or_model_fit=False, forbidden_attempts=forbidden)
with Path(a.output).open('x') as stream:
    json.dump(out, stream, ensure_ascii=False, indent=2, allow_nan=False)
    stream.write('\n')
print(json.dumps(dict(component=comp, comparisons=[dict(baseline=c['baseline'],
    q_max_abs_delta=c['public45D_blocks']['q']['max_abs_delta'],
    nominal_component_delta=c['nominal_component_delta']) for c in comparisons]), ensure_ascii=False))
