"""Prospective source transform ONLY. Never writes/executes frozen worker/scope.

A future assembler must assign a NEW full program/authority/own-zero after this
explicit import-order correction; this function does NOT create that program.
"""
import ast
import hashlib

FAILED_WORKER_SHA256='9607ed65cc3bd1c5cf4bc1c5cd98c2bc9a63b5ab423f4f4f988d8adcd42ffba6'
IMPORT_ANCHOR='from boundary_driver import driver_class, run_case, CaseLoopError\n'
PREPARE_ANCHOR='    return c,freeze\n'
PRELOAD_IMPORT='import registered_arm_ff  # Source-only dependency MUST exist before run helper gate.\n'
PREPARE_PROOF="""    # Source presence/order must be checked by CPU prepare, not first zero.
    helper_path=Path(registered_arm_ff.__file__)
    need(str(helper_path) in freeze['files'] and not helper_path.is_symlink() and
         sha(helper_path)==freeze['files'][str(helper_path)],
         'Prepared arm FF helper must be preloaded and exact before native phase')
"""

def derive(raw=None,*,enabled=False):
    if type(enabled)is not bool:raise ValueError('Explicit prospective source-only opt-in')
    if not enabled:return None
    if type(raw)is not bytes or hashlib.sha256(raw).hexdigest()!=FAILED_WORKER_SHA256:
        raise ValueError('Exact failed source required; never silently patch another program')
    source=raw.decode()
    if source.count(IMPORT_ANCHOR)!=1 or source.count(PREPARE_ANCHOR)!=1:
        raise ValueError('Only two exact declared source insertion sites')
    changed=source.replace(IMPORT_ANCHOR,IMPORT_ANCHOR+PRELOAD_IMPORT,1).replace(PREPARE_ANCHOR,PREPARE_PROOF+PREPARE_ANCHOR,1)
    if changed.replace(PRELOAD_IMPORT,'',1).replace(PREPARE_PROOF,'',1)!=source:
        raise ValueError('Inverse must restore entire actual failed worker')
    ast.parse(changed)
    return changed,dict(original_SHA256=FAILED_WORKER_SHA256,prospective_SHA256=hashlib.sha256(changed.encode()).hexdigest(),
        inverse_restores_original=True,only_early_dependency_import_and_prepare_presence_pin_check=True,
        physics_FF_or_safety_or_success_or_budget_changes=False,
        actual_failed_scope_still_closed=True,not_a_new_program_or_execution_permission=True)
