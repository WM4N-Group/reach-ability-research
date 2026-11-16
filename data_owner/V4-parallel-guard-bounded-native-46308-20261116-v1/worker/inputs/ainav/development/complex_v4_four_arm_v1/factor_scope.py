"""Separate fixed legacy-common stow H from the V4 successor treatment.

Do not weaken C (or silently change E's shared execution layer) to make a broad
'optimizer=0' caption literally true. H is identical for A--E. Only B/D enables
Reach's NEW successor selector. This is source policy before any five-arm main,
not an assertion that a selector or old H has actually run or improved a task.
"""
from pathlib import Path
import hashlib
import importlib
import sys
import types
from v4_native_asset import require

POLICY_ID = 'V4_FIXED_LEGACY_COMMON_H_NEW_SUCCESSOR_TREATMENT_SEPARATE_v1'
BINDER_SHA = '23c1d6b5d160de10259d469d43c57bf7c6d6e1616d4568b895ab8fdf76ac65a5'
KERNEL_SHA = 'f330cd5facba98922e995730ebd48ba4eb7a51a789b0ca9041a78758f2a97383'
NEW_CHOICE_EVENT = 'reach_v4_shared_optimizer_choice'
LEGACY_CHOICE_EVENT = 'reach_selected_ground_confirmed_stow_path_choice'


def factors(arm):
    require(arm in ('A', 'B', 'C', 'D', 'E'), 'Explicit frozen five-arm identity')
    return dict(policy=POLICY_ID, arm=arm, legacy_common_stow_H_enabled=True,
        new_successor_optimizer_enabled=arm in ('B', 'D'),
        legacy_H_is_not_new_treatment=True, legacy_H_costs_included_in_all_arms=True,
        E_zero_VLM_WM_and_new_optimizer_not_zero_all_legacy_algorithms=True)


class FactorJournal:
    """Persist attempts before H invocation; count outcomes, not hypothetical gain."""
    def __init__(self, arm, journal):
        self.policy = factors(arm)
        require(callable(journal), 'Original Data evidence journal')
        self.original = journal
        self.counts = dict(legacy_kernel_attempts=0, legacy_kernel_completed=0,
            legacy_kernel_failed=0, legacy_kernel_result_changed=0,
            legacy_callback_choice_events=0, new_successor_choice_events=0,
            new_successor_choice_changed_events=0)

    def __call__(self, row):
        require(type(row) is dict, 'Original structured event required')
        event = row.get('event')
        if event == NEW_CHOICE_EVENT:
            require(self.policy['new_successor_optimizer_enabled'], 'A/C/E cannot emit a new successor treatment choice')
            require(row.get('software_fixture') is not True, 'No fixture optimizer event in a live driver')
            self.counts['new_successor_choice_events'] += 1
            if row.get('choice_changed') is True:
                self.counts['new_successor_choice_changed_events'] += 1
        elif event == LEGACY_CHOICE_EVENT:
            self.counts['legacy_callback_choice_events'] += 1
        value = dict(row)
        require('v4_factor_scope' not in value, 'No replacement of frozen factor identity')
        value['v4_factor_scope'] = dict(self.policy)
        return self.original(value)

    def kernel(self, original):
        """Exact original H call arguments/return and exceptions pass unchanged."""
        require(callable(original), 'Original finite waypoint kernel required')
        def counted(*args, **kwargs):
            self.counts['legacy_kernel_attempts'] += 1
            attempt = self.counts['legacy_kernel_attempts']
            self(dict(event='V4_legacy_common_H_kernel_attempt', attempt=attempt,
                      new_successor_optimizer_call=False, model_input=False))
            try:
                result = original(*args, **kwargs)
            except BaseException:
                # No exception text/arguments can leak private data/credentials.
                self.counts['legacy_kernel_failed'] += 1
                self(dict(event='V4_legacy_common_H_kernel_raised', attempt=attempt,
                          new_successor_optimizer_call=False, model_input=False))
                raise
            self.counts['legacy_kernel_completed'] += 1
            if isinstance(result, dict) and result.get('changed') is True:
                self.counts['legacy_kernel_result_changed'] += 1
            self(dict(event='V4_legacy_common_H_kernel_returned', attempt=attempt,
                proposed_waypoint_path_changed=isinstance(result, dict) and result.get('changed') is True,
                actual_motor_change_or_task_gain_inferred=False,
                new_successor_optimizer_call=False, model_input=False))
            return result
        return counted


def _binding(source_root, ledger):
    root = Path(source_root).resolve(strict=True)
    package = root.parent / 'reach_stow_choice'
    for name, pin in [('native_stow_path_binding.py', BINDER_SHA), ('stow_path_choice.py', KERNEL_SHA)]:
        path = package / name
        require(not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == pin,
                'Exact fixed legacy-common H dependency: ' + name)
    sys.path.insert(0, str(root.parent))
    module = importlib.import_module('reach_stow_choice.native_stow_path_binding')
    require(Path(module.__file__).resolve() == package / 'native_stow_path_binding.py', 'No ambient H binder')
    original = module.bind_to_host
    namespace = dict(vars(module))
    namespace['optimize'] = ledger.kernel(module.optimize)
    # A PRIVATE function-globals copy. No monkeypatch of Reach module/kernel or
    # native source. The original callback's actual capture/queue/owner/goal/
    # unchanged-state/full-path/native 4s guards and return all stay unchanged.
    bound = types.FunctionType(original.__code__, namespace, original.__name__,
                               original.__defaults__, original.__closure__)
    bound.__kwdefaults__ = dict(original.__kwdefaults__ or {})
    return module, bound


def install_legacy_common(host, *, arm, planner, journal):
    """New fresh-worker binding, never replace/uninstall an existing callback."""
    require(not hasattr(host, '_v4_factor_journal'), 'One immutable task-zero factor installation only')
    runtime = host.r
    require(type(runtime.step_count) is int and runtime.step_count == 0
            and float(runtime.sim.data.time) == 0. and not runtime.sim.queue,
            'Fresh task-zero runtime/FIFO only; no post-capture/live switch')
    policy = factors(arm)
    require(getattr(planner, 'journal', None) is journal, 'One exact original shared method/native journal sink')
    if arm == 'E':
        from rule_baseline import RuleBaseline
        require(type(planner) is RuleBaseline, 'Actual fixed E rule, not a VLM/optimizer adapter')
    else:
        require(getattr(planner, 'enabled', None) is policy['new_successor_optimizer_enabled']
                and getattr(planner, 'software_fixture', None) is False,
                'Original Reach method adapter must match the frozen new treatment flag; not a fixture')
    ledger = FactorJournal(arm, journal)
    module, bind = _binding(host.source_root, ledger)
    root = Path(host.source_root).resolve(strict=True)
    allowed = {root / 'mujoco_zyh/stall_stow.py', root / 'ainav/native/current_stall_stow.py'}
    modules, seen = [], set()
    for value in tuple(sys.modules.values()):
        name = getattr(value, '__file__', None)
        if name is not None and id(value) not in seen and Path(name).resolve() in allowed:
            seen.add(id(value)); modules.append(value)
    require(any(Path(v.__file__).resolve() == root / 'mujoco_zyh/stall_stow.py' for v in modules),
            'Selected original transformed stow module must already be loaded')
    # Validate ALL aliases before installing ANY callback; never partly install
    # then silently turn the remainder OFF or remove an earlier active hook.
    for value in modules:
        path = Path(value.__file__)
        require(not path.is_symlink(), 'Regular native stow alias')
        module.restore_stall_source(path.read_text())
        ns = vars(value)
        require(module.CALLBACK not in ns and ns['ProtectedStow'].update.__globals__ is ns
                and module.CALLBACK in ns['ProtectedStow'].update.__code__.co_consts,
                'Fresh original stow alias without a prior callback')
    host.common_choice_records, host.common_stow_bindings = [], []
    host._stow_callback_name, host._stow_allowed, host._stow_installed = module.CALLBACK, allowed, {}
    host._v4_factor_journal, host.journal = ledger, ledger
    # This is a NEW, task-zero adapter instance, never a running method/profile.
    planner.journal = ledger
    def emit(row):
        ledger(row)
        value = dict(row)
        value.update(legacy_common_H=True, new_successor_optimizer_call=False, v4_arm=arm)
        host.common_choice_records.append(value)
    for value in modules:
        result = bind(host, value, enabled=True, emit=emit)
        require(result['installed'] is True, 'Exact original common H binding required for every arm')
        key = str(Path(value.__file__).resolve())
        host._stow_installed[key] = vars(value)[module.CALLBACK]
        host.common_stow_bindings.append(dict(path=key, **result))
    ledger(dict(event='V4_two_factor_policy_bound_at_task_zero', policy=policy,
        legacy_common_H_callbacks=len(modules), counts=dict(ledger.counts),
        kernel_execution_or_success_not_implied_by_installation=True, model_input=False))
    return ledger
