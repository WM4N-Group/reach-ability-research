"""One explicit source inspection, no world/runtime/model or foreign tests."""
import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output); output.mkdir(parents=True, exist_ok=False)
    attempts = []
    def audit(event, values):
        if event in ('socket.connect', 'socket.getaddrinfo', 'subprocess.Popen', 'os.system', 'os.fork', 'os.posix_spawn'):
            attempts.append(event); raise RuntimeError('Offline process/network fence: '+event)
        if event == 'import' and str(values[0]).split('.')[0] in ('torch', 'numpy', 'scipy', 'mujoco', 'onnxruntime', 'requests', 'httpx', 'cv2'):
            attempts.append(str(values[0])); raise RuntimeError('No model/runtime/numeric library: '+str(values[0]))
    sys.addaudithook(audit)
    from .ainav_target_domain import evaluate, sha
    start = time.perf_counter()
    result = evaluate(args.manifest, expected_sha256=args.manifest_sha256)
    result['wall_s'] = time.perf_counter()-start
    result['fence_attempts'] = attempts
    # Verify actual owner arithmetic/schema behavior, not an invented continuum.
    from ainav.scene_intents import DeclaredScene
    manifest = json.loads(Path(args.manifest).read_text())
    raw = json.loads(Path(manifest['public_projection_path']).read_text())
    scene = DeclaredScene.from_transfer(raw)
    catalogue = scene.catalogue(0.)
    row = next(r for r in catalogue if r.skill == 'PUSH' and r.target_ref == 'o08' and dict(r.parameters)['goal_world_x_m'] == 6.15)
    from ainav.intents import SkillIntent
    from ainav.contracts import Primitive
    changed = dict(row.parameters); changed['goal_world_x_m'] += .005
    nearby = SkillIntent('EXPLICIT_OFF_CATALOGUE_SOFTWARE_CHECK', 'PUSH', row.target_ref, tuple(sorted(changed.items())))
    allowed = {Primitive.from_option(v).command_key for v in catalogue}
    result['off_catalogue_check'] = dict(nearby_goal_x_m=changed['goal_world_x_m'],
        within_native_blueprint_relaxation=0 < changed['goal_world_x_m']-5.48+.11 <= .8,
        matches_original_catalogue=Primitive.from_option(nearby).command_key in allowed,
        runtime_declaration_called=False, physical_dispatch=False)
    # Check literal constants in pinned consumer expressions; no import/runtime.
    pin = next(v for v in manifest['source_files'] if v['path'].endswith('/native/scene_placement.py'))
    text = Path(pin['path']).read_text(); tree = ast.parse(text)
    cls = next(v for v in tree.body if isinstance(v, ast.ClassDef) and v.name == 'ScenePlacementAdapter')
    declaration = next(v for v in cls.body if isinstance(v, ast.FunctionDef) and v.name == 'declaration')
    prepare = next(v for v in cls.body if isinstance(v, ast.FunctionDef) and v.name == 'prepare')
    result['consumer_source_crosscheck'] = dict(
        exact_catalogue_equality_guard="PUSH goal must preserve an actual declared placement intent" in ast.get_source_segment(text, declaration),
        native_stroke_comparison=any(isinstance(v, ast.Compare) and ast.unparse(v) == '0 < distance <= 0.8' for v in ast.walk(prepare)),
        frozen_consumer_sha256=sha(pin['path']), no_dynamic_constructor_called=True)
    assert not result['off_catalogue_check']['matches_original_catalogue']
    assert result['off_catalogue_check']['within_native_blueprint_relaxation']
    assert result['consumer_source_crosscheck']['native_stroke_comparison']
    assert result['consumer_source_crosscheck']['exact_catalogue_equality_guard']
    (output/'evaluation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    fields=['object_ref','source_ref','receiver_ref','public_goal_x_m','public_delta_m','native_drive_m',
            'blueprint_stroke_pass','next_box_approach_x_m','next_box_approach_y_m','joint_enum_agree']
    with (output/'candidates.csv').open('w') as handle:
        writer=csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for r in result['rows']:
            writer.writerow(dict(object_ref=r['object_ref'],source_ref=r['source_ref'],receiver_ref=r['receiver_ref'],
                public_goal_x_m=r['public_goal_xy_m'][0],public_delta_m=r['declared_public_translation_m'],
                native_drive_m=r['declared_native_drive_m'],blueprint_stroke_pass=r['initial_stroke_necessary_in_blueprint'],
                next_box_approach_x_m=r['nominal_successor_box_climb_approach_xy_m'][0],
                next_box_approach_y_m=r['nominal_successor_box_climb_approach_xy_m'][1],
                joint_enum_agree=r['same_problem_baselines']['goals_agree']))
    print(json.dumps(dict(rows=len(result['rows']),groups=result['source_receiver_groups'],
                         off_catalogue_check=result['off_catalogue_check'],fence_attempts=attempts),ensure_ascii=False))


if __name__ == '__main__': main()
