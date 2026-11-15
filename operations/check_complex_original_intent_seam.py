#!/usr/bin/env python3
"""Original classes + live-source declarations SOFTWARE check, not a robot run.

All observations/receipts here are explicitly SOFTWARE fixtures. No image is
opened, no driver/world/capture/Actor is created, and no result is a native A/B.
The private source/existence witness is neither read nor imported.
"""
import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import sys

p = argparse.ArgumentParser(description=__doc__)
for name in ('source-root', 'public-task', 'expected-task-sha', 'finite-placements',
             'expected-placements-sha', 'output'):
    p.add_argument('--' + name, required=True)
p.add_argument('--scene-extension', help='Optional exact source extension for its public nav_declarations helper only')
a = p.parse_args()
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(a.source_root).resolve())]
blocked = []
def fence(event, args):
    if event == 'import' and str(args[0]).split('.')[0] in ('numpy', 'mujoco', 'torch', 'onnxruntime'):
        blocked.append(str(args[0])); raise RuntimeError('No native/array/Actor import in source seam check')
    if event in ('subprocess.Popen', 'socket.connect', 'socket.bind', 'socket.getaddrinfo'):
        blocked.append(event); raise RuntimeError('No child/network')
    if event == 'open' and isinstance(args[0], str) and any(x in args[0] for x in (
            'scene.json', 'scene_v2_three_choices.json', 'static_qualification', 'PRIVATE_NOMINAL',
            'private_terminal', '/query-private-')):
        blocked.append(args[0]); raise RuntimeError('No private scene/existence data')
sys.addaudithook(fence)
from ainav.contracts import Observation, Primitive, canonical
from ainav.intents import IntentBatch, ExecutionBatch, SkillIntent
from ainav.native.behavior_authority import BehaviorOption, NativeReceipt
from ainav.native.intent_execution import IntentExecutionCoordinator
from research.task_conditioned_reachability.execution_preparation.complex_source_adapter import (
    build_source_bound_planner, declared_nav_xy)

source_nav_declarations = None
source_helper_pins = {}
if a.scene_extension:
    extension=Path(a.scene_extension).resolve()
    sys.path.insert(0,str(extension))
    from scene_driver import nav_declarations as source_nav_declarations
    source_helper_pins={name:sha256((extension/name).read_bytes()).hexdigest()
                        for name in ('scene_driver.py','complex_scene.py')}

checks = []
def checked(name, condition):
    if not condition: raise AssertionError(name)
    checks.append(name)
def refuses(name, fn, text):
    try: fn()
    except (ValueError, RuntimeError) as error:
        checked(name, text in str(error)); return
    raise AssertionError('Did not refuse: ' + name)

def make_planner(method):
    rows = []
    def journal(row):
        rows.append(row); return 'SOFTWARE_ONLY_JOURNAL:' + str(len(rows))
    planner = build_source_bound_planner(public_task_path=a.public_task,
        expected_task_sha256=a.expected_task_sha, finite_placements_path=a.finite_placements,
        expected_placements_sha256=a.expected_placements_sha, method=method,
        journal=journal, terminal_target_ref='cx-goal')
    return planner, rows, journal


def catalogue_and_observation(planner, seq):
    # Exact public declaration order, same as original source nav_declarations.
    goal = tuple(round(v, 12) for v in planner.model.goal_xy)
    navs = [(('cx-goal' if xy == goal else 'SOFTWARE-nav-%03d' % i), xy)
            for i, xy in enumerate(declared_nav_xy(planner.model))]
    if source_nav_declarations is not None:
        actual=source_nav_declarations(planner.model.task)  # ONLY the public blueprint passed here.
        checked(planner.method+': source NAV helper matches public domain %d'%seq,
            tuple(v['xy']for v in actual)==declared_nav_xy(planner.model))
        navs=[(v['target_ref'],v['xy'])for v in actual]
    anchors = [dict(target_ref=ref, description='SOFTWARE FIXTURE declared nav',
                    position_xyz_m=[*xy, 0.], uncertainty_xyz_m=[0., 0., 0.]) for ref, xy in navs]
    anchors.extend(dict(target_ref=o['public_ref'], description='SOFTWARE FIXTURE initial blueprint, not current pose',
                        position_xyz_m=[*o['initial_xy_m'], 0.], uncertainty_xyz_m=[0., 0., 0.]) for o in planner.model.objects)
    obs = Observation.create(dict(time_s=float(seq), rgb=dict(path='/SOFTWARE-NOT-EXPERIMENT/no-image.png',
        sha256='0'*64, time_s=float(seq), width=8, height=8), objects=[], public_state={},
        declared_map=dict(source_ref='SOFTWARE ONLY', anchors=anchors), goal='SOFTWARE ONLY', events=[]))
    options = []
    for ref, xy in navs:
        options.append(SkillIntent('software-%d-%d' % (seq,len(options)), 'NAV', ref,
            tuple(sorted(dict(goal_world_x_m=xy[0],goal_world_y_m=xy[1],surface_height_m=0.).items()))))
    for c in planner.model.placements:
        options.append(SkillIntent('software-%d-%d' % (seq,len(options)), 'PUSH', c['public_ref'],
            tuple(sorted((k,c[k])for k in ('goal_world_x_m','goal_world_y_m','surface_height_m')))))
    cap = canonical(dict(source_ref='SOFTWARE original API seam',skills=['NAV','PUSH'],constraints=[
        'Software fixture, not native qualification, successful execution, training data or an actual receipt.']))
    return IntentBatch('SOFTWARE-batch-%d'%seq, obs, tuple(options), cap)

results = {}
for method in ('greedy', 'multistep'):
    planner, rows, journal = make_planner(method)
    initial = catalogue_and_observation(planner, 1)
    refuses(method + ': private batch refused', lambda: planner.select(
        ExecutionBatch(initial.decision_id, initial.observation, tuple(BehaviorOption(
            x.token,x.skill,x.target_ref,x.parameters,60.,'SOFTWARE-NOT-ADMISSION',
            attempt_id='SOFTWARE-NOT-ATTEMPT' if x.skill=='PUSH' else '',
            original_push_goal_sha256='0'*64 if x.skill=='PUSH' else '')for x in initial.options),
            initial.capability_contract)), 'private ExecutionBatch')
    refuses(method + ': missing domain refused', lambda: planner.select(replace(initial, options=initial.options[:-1])), 'Complete ordered')
    refuses(method + ': reordered domain refused', lambda: planner.select(replace(initial, options=tuple(reversed(initial.options)))), 'Complete ordered')
    extra = replace(initial.options[-1], token='SOFTWARE-extra')
    refuses(method + ': duplicate domain refused', lambda: planner.select(replace(initial, options=initial.options+(extra,))), 'Complete ordered')
    checked(method + ': validation does not advance nominal state', planner.decision_count==0 and planner.pending is None)
    seq = 0; interactions = 0; preparations = 0; status = None; prepared = set()
    # Original coordinator, original Selection/Primitive/BehaviorOption/Receipt.
    # Only judge/bind/snapshot are explicit software fixtures, never native gates.
    state = {}
    def observe(now): return state['batch'].observation
    def catalogue(obs): return state['batch'].options
    def judge(intent, now):
        if intent.skill == 'PUSH' and intent.sha256 not in prepared:
            prepared.add(intent.sha256)
            xy=planner.nominal_context.robot_reference_xy_m
            option=BehaviorOption('SOFTWARE-entry-NAV-%d'%seq,'NAV',intent.target_ref,
                tuple(sorted(dict(goal_world_x_m=xy[0],goal_world_y_m=xy[1],surface_height_m=0.).items())),
                60.,'SOFTWARE_FAKE_NOT_ENTRY_AUTHORITY')
            return 'PREPARE',option,'SOFTWARE_FAKE_NOT_JUDGMENT'
        return 'READY', BehaviorOption('SOFTWARE-native-%d'%seq,intent.skill,intent.target_ref,
            intent.parameters,60.,'SOFTWARE_FAKE_NOT_ENTRY_AUTHORITY',
            attempt_id='SOFTWARE-NOT-ATTEMPT' if intent.skill=='PUSH' else '',
            original_push_goal_sha256='0'*64 if intent.skill=='PUSH' else ''), 'SOFTWARE_FAKE_NOT_JUDGMENT'
    coordinator = IntentExecutionCoordinator(planner=planner,observe=observe,catalogue=catalogue,
        judge=judge,bind=lambda batch: None,snapshot=lambda:'SOFTWARE-NO-WORLD',protection=lambda now:None,
        journal=journal,capability_contract=initial.capability_contract)
    while seq < 40 and not planner.awaiting_terminal:
        seq += 1; state['batch'] = catalogue_and_observation(planner,seq)
        try: native_batch = coordinator(float(seq))
        except RuntimeError:
            if planner.failed_reason is None: raise
            status = planner.failed_reason; break
        selected = coordinator.select(native_batch)
        actual = coordinator.actual_option
        checked(method+': original selection binding %d'%seq,
            selected.option_sha256 == actual.sha256 and selected.primitive_key == Primitive.from_option(actual).key)
        if seq == 1:
            refuses(method+': replay public batch refused',lambda:planner.select(state['batch']), 'Fresh')
        # Receipt literal is generated solely to test the SOFTWARE protocol seam.
        role=coordinator.phase;nominal_before=planner.nominal_context;pending_before=planner.pending
        coordinator.observe(actual,NativeReceipt(actual.sha256,float(seq)+.5,'succeeded','0'*64,
            'SOFTWARE_FAKE_NOT_NATIVE_RECEIPT'))
        if role=='preparation':
            preparations+=1
            checked(method+': preparation not a model interaction %d'%seq,
                planner.nominal_context==nominal_before and planner.pending==pending_before)
        else:interactions += 1
    if planner.awaiting_terminal:
        checked(method+': nominal goal is not native completion',not planner.complete)
        refuses(method+': empty terminal evidence refused',lambda:planner.confirm_original_task_terminal(evidence_ref=''), 'External ORIGINAL')
        # Do NOT supply fake terminal evidence to the public planner.
        status = 'SOFTWARE_AWAITING_ORIGINAL_TERMINAL_PROOF'
    decisions = [r for r in rows if r['event']=='reach_complex_public_decision']
    results[method] = dict(status=status,software_interactions=interactions,software_preparations=preparations,decision_bundles=len(decisions),
        nonforced_nominal_reconstruction_choices=sum(r['nonforced_nominal_reconstruction_choice']for r in decisions),
        actual_task_success=None,original_terminal_evidence_received=False,
        nominal_decisions=[r['nominal_action']for r in decisions])
checked('No forbidden imports/reads/network',not blocked)
source_files = ('ainav/contracts.py','ainav/intents.py','ainav/planner.py','ainav/native/behavior_authority.py',
                'ainav/native/intent_execution.py')
out = dict(role='ORIGINAL_CLASSES_SOFTWARE_SEAM_NOT_NATIVE_AB',checks=len(checks),check_names=checks,
    source_public_helper_pins=source_helper_pins,
    original_source_pins={f:sha256((Path(a.source_root)/f).read_bytes()).hexdigest()for f in source_files},
    public_source_pins=planner.source_pins,results=results,worlds=0,physical_commands=0,real_observations=0,
    real_receipts=0,training_rows=0,native_qualification=False,forbidden_attempts=blocked)
if a.scene_extension and source_helper_pins != {name:sha256((Path(a.scene_extension)/name).read_bytes()).hexdigest() for name in source_helper_pins}:
    raise RuntimeError('Source helper changed during software check; no qualified report')
with Path(a.output).open('x') as f: json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(checks=out['checks'],results={m:{k:v for k,v in r.items()if k!='nominal_decisions'}for m,r in results.items()}),ensure_ascii=False))
