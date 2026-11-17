"""CPU-only C/D draft preparation. NOT a scheduler, authority or Runtime entry."""
from pathlib import Path
import hashlib
import json
import cd_entry
import task_loop
import source_selection


class ProtocolError(ValueError):
    pass


def require(ok, why):
    if not ok:
        raise ProtocolError(why)


def preview(protocol, *, enabled=False):
    require(type(enabled) is bool, 'Explicit draft-only prepare')
    if not enabled:
        return None
    require(protocol['classification'] == 'DEV_ONLY_PROSPECTIVE_NOT_DISPATCH_AUTHORITY',
            'Not a physical authorization or efficacy study')
    require(protocol['arms'] == ['C', 'D'] and protocol['execution_order'] == ['C', 'D'],
            'One preregistered C then D fresh DEV attempt, no result-dependent order')
    require(protocol['own_zero_per_arm_max'] == protocol['main_per_arm_max'] == 1 and
            protocol['automatic_retry'] is False, 'Own zero/main for EACH arm; no retries')
    require(protocol['execution_enabled'] is False, 'Draft cannot enable execution')
    fairness = protocol['fairness']
    for key in ('same_public_task', 'same_skill_tree_replanning_and_safety',
                'same_backend_profile_and_caps', 'same_compute_policy',
                'full_attempt_costs_and_failures_retained', 'direct_live_1x_video_each_arm'):
        require(fairness.get(key) is True, 'Shared C/D factor required: ' + key)
    require(fairness['private_state_pair_claimed'] is False and
            fairness['DEV_is_independent_effect_estimate'] is False,
            'Fresh generated initial conditions are not exact hidden-state pairs/statistical proof')
    require(protocol['optimizer_evidence']['all_UNKNOWN_fallback_is_M1_complete'] is False,
            'Always fallback is not demonstrated working optimization')
    selected = protocol['source_paths']
    require(set(selected) == set(cd_entry.SOURCE_PINS), 'Exact selected v3 direct source selections')
    pins = {}
    for name, path in selected.items():
        p = Path(path)
        require(p.is_file() and not p.is_symlink(), 'Existing regular selected source: ' + name)
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        require(digest == cd_entry.SOURCE_PINS[name], 'Source drift: ' + name)
        pins[str(p)] = digest
    # Selected transitive Reach subset is checked BEFORE imports/factories.
    # This is not the full native dependency inventory or import qualification.
    try:
        pins.update(source_selection.verify_reach_sources(
            protocol['common']['reach_source_root_reference']))
        declarations = source_selection.read_declarations(protocol['declaration_sources'])
        source_selection.provider_config(protocol)
    except (ValueError, OSError, KeyError) as error:
        raise ProtocolError('Selected Reach/task declaration refused: ' + type(error).__name__) from error
    require(protocol['common']['task_wall_sim_caps'] ==
            declarations['NAV_DEV_DECLARATION.json']['prospective_hard_caps'],
            'Exact selected finite DEV caps, no post-result extension')
    limits = dict(protocol['common']['task_loop_limits'])
    limits['allowed_skills'] = tuple(limits['allowed_skills'])
    require(limits == dict(max_commands=12000, max_driver_calls=12064,
                          task_sim_cap_s=60, scope_wall_cap_s=1200, allowed_skills=('NAV',)),
            'Declared independent NAV DEV loop limits, not original V4 restriction')
    task_loop.MainLimits(**limits)
    # Exercise THIS entry's true disabled path, never original backend/driver/world.
    require(cd_entry.build_cd_driver('/DO_NOT_READ', enabled=False) is None and
            cd_entry.assemble_nav_dev_sources('/DO_NOT_READ', enabled=False) is None,
            'True default-off entry required')
    require(task_loop.run_task('/DO_NOT_READ', enabled=False) is None and
            task_loop.make_cd_phase_health(enabled=False) is None,
            'True default-off task-loop/health components required')
    # Common is cloned, rather than maintaining independently drifting arm copies.
    common = json.loads(json.dumps(protocol['common']))
    arms = {arm: dict(common=json.loads(json.dumps(common)), arm=arm,
                     new_successor_optimizer_enabled=arm == 'D',
                     own_zero_required=True, execution_enabled=False,
                     shared_path_cost='OWNER_BOUND_COMMON_B_D_CALLABLE' if arm == 'D' else None)
            for arm in ('C', 'D')}
    # These are concrete missing executable inputs, NOT new approvals/signatures.
    blockers = [
        dict(owner='AINav/Data', interface='independent DEV public acquisition and terminal adapter',
             missing='AINav nav_dev_task source and Data attachment are now implemented; common public acquisition and NAV receipt terminal are NOT yet native-qualified. The new parent candidate must pass its full freeze/prepare/own-zero; original V4 complete is not DEV completion'),
        dict(owner='Data', interface='fresh live backend / API fairness and accounting',
             missing='New api_accounting source now enforces 6 method queries/8 roles per query and preserves safe served-model/per-role usage/transport attempts. Actual backend/query execution and D binding to pinned genuine C result remain unqualified; no old query replay'),
        dict(owner='Data', interface='new full outer worker / native import closure / runtime qualification',
             missing='New cd-native-worker parent candidate now connects partial-finally/RNG/API accounting/disjoint phase ScopeIO/FD/video/lease and task_loop. Actual CPU prepare is recorded separately; full native authority freeze/own zeros/cleanup and external bounded launcher still required'),
        dict(owner='Data', interface='actual capacity and finite outputs',
             missing='Prospective task/seed/60sim-1200wall and output caps are selected, not null. Reconcile actual output reservation, aux/encoding/tail/RSS/GPU with fresh owned capacity before freeze; observed idle GPUs are not a lease')]
    return dict(stage='SOURCE_PREPARE_PASS_EXECUTION_NOT_READY', dispatchable=False,
                source_pins=pins, arm_config_preview=arms, blockers=blockers,
                selected_Reach_source_count=len(source_selection.REACH_PINS), selected_direct_source_count=len(selected),
                DEV_task_and_RNG_and_caps_prospectively_selected=True,
                full_native_import_closure_qualified=False,
                stepping_and_phase_health_component_available=True,
                whole_worker_lifecycle_or_runtime_qualification=False,
                original_driver_or_method_factory_calls=0, backend_or_API_calls=0,
                Runtime_Actor_renderer_or_GPU_calls=0, extra_research_signature_required=False)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol')
    args = parser.parse_args()
    print(json.dumps(preview(json.loads(Path(args.protocol).read_text()), enabled=True),
                     ensure_ascii=False, indent=2))
