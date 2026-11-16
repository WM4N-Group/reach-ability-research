"""Minimal E-only assembly over Data's ALREADY constructed fresh components.

No A--D method/backend/WM imports, credentials, model restore, new world or
launcher. Data supplies the original guarded native driver/recorder lifecycle.
Full-task attempt may end with the original explicit unsupported-domain error;
that is NOT a fabricated native CLIMB failure or high-platform success.
"""
from pathlib import Path
import hashlib
from v4_native_asset import require, load_scene, SCENE_SHA256

E_RULE_SHA = '43998a23f4e49161074658bdc26b72c47b6b501b97830b906b84b50751c98634'


def build_E_driver(components=None, *, source_root=None, bundle=None, output_root=None,
                   writer=None, journal=None, guard=None, enabled=False):
    require(type(enabled) is bool, 'Explicit E-only owner opt-in')
    if not enabled:
        return None
    require(callable(guard) and callable(journal) and guard() is not False,
            'Actual Data E owner/lease/resource guard and durable journal')
    require(type(components) is dict and components['scene_sha256'] == SCENE_SHA256
            and components['scene'] == load_scene(), 'Confirmed shared V4 scene, not an E-only easier layout')
    r = components['runtime']
    require(r.step_count == 0 and float(r.sim.data.time) == 0. and not r.sim.queue
            and getattr(writer, 'steps', None) == 0,
            'New task-zero E driver/writer only, no component/closed-root continuation')
    require(callable(getattr(writer, 'append_command', None)) and callable(getattr(writer, 'append_visual', None)),
            'Actual Data raw original command/visual writer; direct third-view recording remains required')
    path = Path(__file__).with_name('rule_baseline.py')
    require(not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == E_RULE_SHA,
            'Exact unchanged public E rule, no API0/fixed-request substitute')
    from rule_baseline import RuleBaseline
    from live_driver import driver_class
    require(Path(__import__('rule_baseline').__file__).resolve() == path.resolve(), 'No ambient E rule')
    rule = RuleBaseline(components['scene'], journal=journal, max_selections=64)
    cls = driver_class(source_root=source_root, enabled=True)
    driver = cls(components, bundle=bundle, output_root=output_root, writer=writer,
                 planner=rule, journal=journal, guard=guard, arm='E')
    from factor_scope import FactorJournal, factors
    require(driver.r is r and driver.arm == 'E' and type(driver.planner) is RuleBaseline
            and driver.planner is rule and type(driver.journal) is FactorJournal
            and driver.journal.policy == factors('E') and rule.journal is driver.journal,
            'Actual E rule and ONE original all-five common-H ledger; no method replacement')
    require(driver.loop is None and driver.tick == 0 and r.step_count == 0
            and rule.decision_count == rule.native_success_count == 0 and rule.pending is None,
            'Assembly cannot select or advance E, reset state or issue a command')
    ref = driver.journal(dict(event='V4_E_actual_unchanged_rule_driver_assembled_NOT_task_success',
        E_rule_sha256=E_RULE_SHA, E_max_semantic_selections=64,
        E_VLM_WM_new_successor_optimizer_calls=0, legacy_common_H_preserved=True,
        original_runtime_world_recorder_and_native_guards=True,
        source53_public_prior_and55_NAV_prefix_not_dependencies=True,
        direct_third_view_task0_recording_REQUIRED_but_not_certified_by_assembly=True,
        unsupported20cm_domain_is_explicit_not_native_failed_receipt=True,
        layout_or_CLIMB_safety_success_gate_relaxed=False,
        physical_action_issued=False, E_complete_or_video_delivered=False))
    require(type(ref) is str and bool(ref) and guard() is not False,
            'Durable E source assembly/actual owner required; no silent fallback')
    return driver
