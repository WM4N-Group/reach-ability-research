"""Pinned CPU intake of owner candidate/protocol releases; NEVER dispatch.

Three *declared* preparation payloads, not three proven different motor traces.
No native imports, online predictor, world construction, old-outcome fit or IO
except explicitly pinned owner-release files. Stage B is a full-domain AUDIT
study, NOT Data's two-policy Stage-C comparison and NOT a deployable oracle.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from .successor_aware_choice import (
    Task, Candidate, Domain, InputSchema, InputValue, DecisionInput,
    Estimate, Costs, evaluate_shared, select_all, digest, need, pin, number,
)

IDS = ('original', 'lateral_plus_0p04', 'lateral_minus_0p04')
OFFSETS = (0., .04, -.04)
PAYLOAD_SCHEMA = 'AINav-finite-CLIMB-preparation-selection-v1'
PERMISSIONS = 'INFORMATION_PERMISSIONS_v1.json'
CONTRACT = 'CANDIDATE_CONTRACT_v1.json'
EXAMPLES = 'PUBLIC_CANDIDATES_AND_EXECUTION_PAYLOADS_v1.json'
COMMON = 'COMMON_SOURCE_FORK_MANIFEST_v1.json'
CALLER = 'ainav/native/execution_judged_course.py'


@dataclass(frozen=True)
class VerifiedRelease:
    root: str
    release_name: str
    release_sha256: str
    release_bytes: bytes
    members: tuple  # immutable (relative name, verified bytes) snapshots

    def document(self, name):
        return json.loads(dict(self.members)[name])


def verify_release(root, release_name, *, expected_release_sha256, inventory_field):
    """Verify caller-pinned release AND every declared member, capture bytes once.

    Integrity is not owner authenticity/native admission. No recursive discovery,
    imports, repair, mutable source rewrite, remote access or experiment startup.
    """
    need(pin(expected_release_sha256), 'External release SHA required')
    root = Path(root).resolve()
    def read(rel):
        path = Path(rel)
        need(not path.is_absolute() and '..' not in path.parts and str(path) == rel,
             'Canonical relative release member required')
        full = root/path
        need(full.is_file() and not full.is_symlink() and full.resolve().is_relative_to(root),
             'Regular member inside owner release')
        need(not any(p.is_symlink() for p in full.parents if p != root and root in p.parents),
             'No symlink directory in release inventory')
        return full.read_bytes()
    raw = read(release_name)
    need(hashlib.sha256(raw).hexdigest() == expected_release_sha256, 'Release SHA mismatch')
    release = json.loads(raw)
    inventory = release.get(inventory_field)
    need(type(inventory) is dict and bool(inventory), 'Nonempty explicit release inventory')
    members = []
    for name, expected in sorted(inventory.items()):
        need(pin(expected), 'Member SHA required')
        content = read(name)
        need(hashlib.sha256(content).hexdigest() == expected, 'Member SHA mismatch: '+name)
        members.append((name, content))
    return VerifiedRelease(str(root), release_name, expected_release_sha256, raw, tuple(members))


def _payload(value, target_ref):
    need(type(value) is dict and set(value) == {'schema', 'target_ref', 'candidate_id'},
         'Exact finite execution payload, no extra control/pose overrides')
    need(value['schema'] == PAYLOAD_SCHEMA and value['target_ref'] == target_ref and
         value['candidate_id'] in IDS, 'Owner same-target finite payload only')
    return dict(value)


def build_intake(ainav, data):
    """Bind real public examples to Reach CPU domain and Stage-B comparison spec.

    Source-level task/profile declaration is explicit, NOT complete native program
    identity. All cost/feasibility predictions stay UNKNOWN. Original native judge
    remains the sole admission authority; CPU domain cannot authorize execution.
    """
    need(type(ainav) is VerifiedRelease and type(data) is VerifiedRelease, 'Verified snapshot intake only')
    contract = ainav.document(CONTRACT)
    info = ainav.document(PERMISSIONS)
    example = ainav.document(EXAMPLES)
    common = ainav.document(COMMON)
    template = data.document('protocol/paired-study-template.json')
    need(tuple(contract['candidate_ids']) == IDS and tuple(contract['lateral_offsets_m']) == OFFSETS,
         'Versioned three-candidate domain, not an expanded parameter search')
    for name in ('semantic_CLIMB_intent_goal_and_READY_reference_unchanged',
                 'original_controller_guards_QP_queue_FIFO_12N_4s_unchanged',
                 'only_applies_when_original_judge_returns_PREPARE'):
        need(contract[name] is True, 'Original task/entry/safety contract changed: '+name)
    need(contract['placement_target_or_tolerances_or_CLIMB_stop_changes'] is False and
         contract['default_preparation_enabled'] is False, 'No task change or automatic enable')
    need(info['old_audit_only_data_fit_allowed'] is False and
         info['world_model_inference_allowed'] is False, 'No retrospective/model information expansion')
    need(common['changed_original_source_files'] ==
         ['mujoco_zyh/stall_stow.py', 'ainav/native/current_stall_stow.py', CALLER],
         'Common profile is the NEW three-file fork, not the old stow-only verifier')
    members = dict(ainav.members)
    for name, sha in common['source_delta_pins'].items():
        need(hashlib.sha256(members['common-source/'+name]).hexdigest() == sha,
             'Current fork delta does not match verified source')
    rows = example['candidates']
    need(len(rows) == 3 and tuple(r['candidate_id'] for r in rows) == IDS, 'Complete ordered finite public catalogue')
    target = rows[0]['target_ref']
    original = rows[0]['original_approach_xy']
    need(type(target) is str and bool(target) and type(original) is list and len(original) == 2
         and all(number(v) for v in original), 'Original finite public reference required')
    for row, offset in zip(rows, OFFSETS):
        need(all(number(v) for v in row['NAV_goal_xy']) and
             number(row['source_surface_height_m']) and number(row['lateral_offset_m']) and
             row['target_ref'] == target and row['original_approach_xy'] == original and
             row['source_surface_height_m'] == 0. and row['lateral_offset_m'] == offset and
             row['NAV_goal_xy'] == [original[0], original[1]+offset] and
             row['original_CLIMB_READY_goal_unchanged'] is True,
             'Only the published ground NAV preparation goal may differ')
        need(row['predicted_current_cost_s'] is None and row['predicted_complete_successor_cost_s'] is None,
             'Published example is not a prospective cost model')
    payloads = tuple(_payload(p, target) for p in example['execution_payloads'])
    need(tuple(p['candidate_id'] for p in payloads) == IDS, 'One exact payload per candidate')
    pins = json.loads(ainav.release_bytes)['files_sha256']
    schema = InputSchema('AINav:'+pins[PERMISSIONS]+':minimal-public-proposal-subset', (
        ('declared_map.anchors.target_ref', 'ONLINE_PUBLIC', ('HIGH_LEVEL_PLANNER',)),
        ('registered_CLIMB.approach_xy', 'ONLINE_PUBLIC', ('HIGH_LEVEL_PLANNER',)),
        ('registered_CLIMB.source_surface_height_m', 'ONLINE_PUBLIC', ('HIGH_LEVEL_PLANNER',)),
    ))
    terminal = dict(role='SOURCE_LEVEL_SHARED_TERMINAL_DECLARATION_NOT_NATIVE_QUALIFICATION',
        task='Original two-request ground PUSH then selected 20cm CLIMB; no final far-bank claim',
        target_ref=target, original_CLIMB_reference_xy=original,
        original_CLIMB_READY_and_stop_unchanged=True,
        common_source_manifest_sha256=pins[COMMON],
        terminal='Original interaction CLIMB succeeded NativeReceipt AND original two-request host endpoint; READY alone is not terminal',
        current='Original NAV preparation, its exit and fresh original CLIMB READY; every allowed preparation attempt included',
        no_goal_region_or_success_gate_relaxation=True,
        original_source_files={k:v for k,v in common['source_delta_pins'].items()},
        full_program_and_live_predicate_binding_required=True)
    gates = dict(common_source_manifest_sha256=pins[COMMON],
        unchanged_native_gates='Original identity/immutable/support/12N/guard/QP/queue/FIFO/4s/CLIMB stop',
        restore_original_reference_before_CLIMB=True,
        gate_authority='Original native controller; not candidate catalogue or Reach evaluator')
    profile = dict(common_source_manifest_sha256=pins[COMMON],
        source_delta_pins=common['source_delta_pins'],
        consumer_sha256=common['consumer_candidate_sha256'],
        common_stow_policy='EXPLICIT_REACH_V2_DIRECT_IDENTICALLY_ALL_ARMS_NOT_AUTO_INSTALLED',
        preparation_enabled='EXPLICIT_TRUE_ALL_ARMS_ORIGINAL_IS_ZERO_OFFSET',
        complete_program_frozen=False)
    task = Task('ground-PUSH-then-same-CLIMB-preparation-pilot', digest(terminal), digest(gates),
        'FIRST_ORIGINAL_CLIMB_PREPARE_BEFORE_PRIVATE_NAV_OPTION_CONSTRUCTION', schema.sha256)
    candidates = tuple(Candidate(p['candidate_id'], task.sha256, digest(profile),
        'climb_preparation_candidates:selection_from_payload->bind_to_host;payload-sha256='+digest(p),
        'DECLARED_PAYLOAD_ONLY_NOT_MOTOR_PROOF:'+digest(p),
        'original' if p['candidate_id'] == 'original' else 'owner_registered_alternative') for p in payloads)
    domain = Domain(task, candidates, 'original', None, 'CPU_TEST_ONLY')
    protocol = dict(schema='Reach-owner-bound-preparation-H1-stage-B-spec-v1',
        role='SEEN_DEV_AUDIT_ONLY_NOT_PLANNER_INPUT_OR_FIT', dispatch=False, training_allowed=False,
        AINav_release_sha256=ainav.release_sha256, Data_template_release_sha256=data.release_sha256,
        AINav_candidate_contract_sha256=pins[CONTRACT], information_permissions_sha256=pins[PERMISSIONS],
        common_source_manifest_sha256=pins[COMMON], Reach_information_subset_sha256=schema.sha256,
        common_task=terminal, common_terminal_predicate_sha256=digest(terminal),
        original_success_gates_sha256=digest(gates), declared_common_execution_profile_sha256=digest(profile),
        profile=profile, domain_sha256=domain.sha256,
        stage='B_FULL_FINITE_DOMAIN_MECHANISM_DIAGNOSIS_NOT_TWO_POLICY_DEPLOYMENT',
        candidate_ids=list(IDS), branches=[dict(candidate_id=p['candidate_id'], execution_payload=p,
            actual_control_equivalence='UNKNOWN_REQUIRES_NATIVE_PROFILE_AND_NEW_OUTCOME',
            scope_ids=None) for p in payloads],
        decision_and_cost_origin='First original CLIMB PREPARE before option construction; fixed arms bound before fresh host prefix',
        current_cost='Decision -> first fresh original CLIMB READY after actual NAV preparation/exit; include any permitted preparation repeats',
        full_cost='Same decision -> original full CLIMB/native two-request endpoint; no missing gap or stabilization dropped',
        prefix_cost='Sunk PUSH/v2-stow prefix separately reported in whole-episode totals; not added twice to remaining costs',
        original_READY_at_decision='No forced NAV: mark NONINFORMATIVE_NO_PREPARATION_INTERVENTION',
        original_BLOCKED='No bypass or synthetic branch; preserve admission outcome',
        baselines=['Original NAV goal on common v2 stow profile', 'Complete same-domain enumeration (hindsight diagnostic)',
                   'Current-only hindsight minimum', 'Full-chain hindsight minimum'],
        direct_stow='Common control substrate, not fourth candidate or separate NAV-direct arm',
        online_current_only_and_successor_aware='UNAVAILABLE_UNKNOWN_COST_MODEL_NO_POLICY_COMPARISON_CLAIM',
        initial_conditions=dict(owner='Data', manifest=None, seeds=None, repeats=None,
            selection_rule='PREDECLARE_COMMON_ADMISSIBLE_DEV_CONDITIONS_BEFORE_OUTCOMES',
            no_outcome_conditioned_selection=True, actual_hidden_state_equivalence_claimed=False),
        sampling='Freeze one or more admissible initial configurations; every declared distinct candidate once per configuration as minimum mechanism pilot, not statistical power; repetition/ordering fixed by Data before outcomes',
        candidate_equivalence_rule='Different goal is not motor difference; report actual control equivalence, stop this candidate hypothesis if aliased; do not tune delta/seed/obstacle to win',
        failure_rule='Retain every branch, refusal, binding error, native failure, timeout, NOT_RUN and censoring plus zero/main/full costs; incomplete table gives no H1 conclusion',
        rank_rule='Strict lower current cost and strictly higher full cost for current winner, or explicit failed-vs-successful complete-chain compatibility switch; ties reported separately',
        effect_rule='Numerical epsilon 1e-9s is not effect size; Data/Reach freeze practically meaningful threshold and variance rule before outcomes',
        stage_clocks='Source-level JSONL decision /payload/time_s, exact judgment_ref READY /payload/state/time_s, exact native_option receipt /payload/receipt/time_s implemented in preparation_stage_clocks.py; future original outcome/host endpoint/optional dynamics clocks still require owner binding',
        raw_third_view=dict(owner='Data', origin='DIRECT_CURRENT_LIVE_RUNTIME_ONLY',
            optional_not_native_success_gate=True, old_missing_footage_must_not_be_backfilled=True,
            live_camera_qualification_required=True),
        physical_admission=False, new_physical_H1_cases=0,
        missing_owner_bindings=['Data N=3 branch preregistration (current template hardcodes two policy arms)',
            'Data initial scene/config/Actor/seeds/repeat/order/technical-limit manifest',
            'Data JSONL hash-chain witness intake plus preparation_decision stage (current reader accepts single JSON and fixed STAGES); source-bound final two-request endpoint check',
            'Original-environment actual NavSkill/profile/controller consumption qualification',
            'Full NEW program freeze/fresh own-zero/canonical lease/watchdog',
            'If enabled: original live third-view capture qualification'])
    need(len(template['arms']) == 2 and tuple(a['arm_id'] for a in template['arms']) ==
         ('current_only_baseline', 'successor_aware'), 'Review Data template change before adapting')
    return domain, schema, protocol, payloads


def minimal_public_input(domain, schema, protocol, *, decision_time_s):
    """Static published schema example, not a fresh native observation."""
    values = (('declared_map.anchors.target_ref', protocol['common_task']['target_ref']),
        ('registered_CLIMB.approach_xy', protocol['common_task']['original_CLIMB_reference_xy']),
        ('registered_CLIMB.source_surface_height_m', 0.))
    inputs = DecisionInput(domain.task.sha256, schema.sha256, decision_time_s, 'HIGH_LEVEL_PLANNER',
        tuple(InputValue(k, v, 'ONLINE_PUBLIC', 0.,
              'STATIC_OWNER_DECLARATION_NOT_FRESH_OBSERVATION:'+protocol['AINav_release_sha256']) for k,v in values))
    schema.validate(inputs)
    return inputs


def unavailable_model_check(domain, schema, inputs):
    """Shared three-row abstention check: UNKNOWN is never zero or gate pass."""
    model_pin = digest({'role':'NO_VALIDATED_MODEL_AVAILABLE','costs':None})
    def evaluator(observation, candidate):
        return Estimate(candidate.sha256, observation.sha256, model_pin,
                        'UNKNOWN', 'CPU_TEST_ONLY', Costs())
    batch = evaluate_shared(domain, inputs, evaluator,
                            evaluator_sha256=model_pin, information_schema=schema)
    return select_all(batch)


def consume_owner_public_api(ainav, protocol, payloads):
    """Execute ONLY pinned owner's pure stdlib catalogue/payload API, not binder.

    Byte snapshot prevents path TOCTOU. No Host/Runtime creation or installation;
    this is useful source-interface consumption, not native controller proof.
    """
    import sys
    from types import ModuleType
    from dataclasses import asdict
    name='_reach_intake_owner_public_'+ainav.release_sha256
    need(name not in sys.modules, 'No replacing a loaded owner module')
    module=ModuleType(name)
    module.__file__=ainav.root+'/climb_preparation_candidates.py'
    sys.modules[name]=module
    try:
        exec(compile(dict(ainav.members)['climb_preparation_candidates.py'], module.__file__, 'exec'),vars(module))
        task=protocol['common_task']
        catalogue=module.public_candidates(target_ref=task['target_ref'],
            declared_approach_xy=task['original_CLIMB_reference_xy'],
            source_surface_height_m=0., registered_climb=True)
        selections=[asdict(module.selection_from_payload(p)) for p in payloads]
        need(tuple(r['candidate_id'] for r in catalogue)==IDS, 'Actual owner public catalogue changed')
        need(selections==[{k:v for k,v in p.items() if k!='schema'} for p in payloads],
             'Actual owner finite payload materializer mismatch')
        return dict(owner_module_sha256=hashlib.sha256(dict(ainav.members)['climb_preparation_candidates.py']).hexdigest(),
            actual_owner_API_calls=['public_candidates']+['selection_from_payload']*len(payloads),
            selections=selections,public_catalogue=list(catalogue),
            bind_to_host_called=False, Host_or_Runtime_constructed=False,
            native_admission_or_motor_consumption_proven=False, execution_authorized=False)
    finally:
        del sys.modules[name]
