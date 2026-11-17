"""CPU-only C/D draft preparation. NOT a scheduler, authority or Runtime entry."""
from pathlib import Path
import hashlib
import json
import cd_entry


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
    require(set(selected) == set(cd_entry.SOURCE_PINS), 'Exact current five source selections')
    pins = {}
    for name, path in selected.items():
        p = Path(path)
        require(p.is_file() and not p.is_symlink(), 'Existing regular selected source: ' + name)
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        require(digest == cd_entry.SOURCE_PINS[name], 'Source drift: ' + name)
        pins[str(p)] = digest
    # Exercise THIS entry's true disabled path, never original backend/driver/world.
    require(cd_entry.build_cd_driver('/DO_NOT_READ', enabled=False) is None,
            'True default-off entry required')
    # Common is cloned, rather than maintaining independently drifting arm copies.
    common = json.loads(json.dumps(protocol['common']))
    arms = {arm: dict(common=json.loads(json.dumps(common)), arm=arm,
                     new_successor_optimizer_enabled=arm == 'D',
                     own_zero_required=True, execution_enabled=False,
                     shared_path_cost='OWNER_BOUND_COMMON_B_D_CALLABLE' if arm == 'D' else None)
            for arm in ('C', 'D')}
    # These are concrete missing executable inputs, NOT new approvals/signatures.
    blockers = [
        dict(owner='AINav', interface='backbone_entry._checked_backend(backend, backend_type, profile)',
             missing='Fresh original backend identity with selected model image+text capability, original caps/counters; actual response/Selection and common live caller not yet supplied'),
        dict(owner='Reach', interface='CompleteReferenceCost(initial_state, forecast, is_terminal, journal)',
             missing='A declared minimal supported multi-step public task: ReferenceState, same-query StepForecast prepare/execute/exit+next_state and terminal; at least one usable path, not global all-domain prediction or J measured-cost lookup'),
        dict(owner='Data', interface='new C/D worker.run / phase_health / termination / budget',
             missing='Original PERF worker is NAV-only/2000 commands. Do not reuse it as C/D: new arm entry, supported task termination and exact finite per-phase caps/IO/lease/video/import closure still need source assembly before freeze'),
        dict(owner='AINav+Reach+Data', interface='common.supported_DEV_task_and_initialization / result-before-freeze protocol',
             missing='Current V4 asset remains reference only. No supported smaller task is silently selected; actual domain/initialization generator/seed+global RNG policy/finite task budgets remain unresolved before any outcome')]
    require(common['supported_DEV_task_and_initialization'] is None and
            common['task_wall_sim_caps'] is None,
            'This specific draft reports unresolved task/caps, never invents a ready scene')
    return dict(stage='SOURCE_PREPARE_PASS_EXECUTION_NOT_READY', dispatchable=False,
                source_pins=pins, arm_config_preview=arms, blockers=blockers,
                original_driver_or_method_factory_calls=0, backend_or_API_calls=0,
                Runtime_Actor_renderer_or_GPU_calls=0, extra_research_signature_required=False)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol')
    args = parser.parse_args()
    print(json.dumps(preview(json.loads(Path(args.protocol).read_text()), enabled=True),
                     ensure_ascii=False, indent=2))
