"""Default-OFF, unfrozen Data-only lifecycle overlay for a future program.

Two explicit receipt callbacks in a PRIVATE copy of the pinned constructor.
Original module, frozen code, guards, initialization and control remain intact.
This is changed bytecode, NOT a claim of unchanged whole-program identity.
"""
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import types

BASE_SHA = '6c3ee245cd54bfeeec0c64a53627ec2efbebba34775afcac7aab794a286b18cf'
HOOK = '_data_partial_construction_receipt'


class PartialObjects:
    """References for the future caller's sealed cleanup, NEVER planner inputs."""
    def __init__(self):
        self.runtime = None
        self.observer = None

    def capture(self, stage, value):
        if value is None:
            raise ValueError('No invented/empty partial object receipt')
        if stage == 'runtime' and self.runtime is None and self.observer is None:
            self.runtime = value
        elif stage == 'observer' and self.runtime is not None and self.observer is None:
            if getattr(value, 'r', None) is not self.runtime:
                raise ValueError('Observer must belong to the captured actual Runtime')
            self.observer = value
        else:
            raise ValueError('No duplicate/out-of-order partial lifecycle receipt')

    def usage_snapshot(self):
        value = dict(usage_known=False, actual_task_steps=None,
                     actual_task_sim_s=None, actual_auxiliary_calibration=None,
                     observer_available=self.observer is not None,
                     audit_only_not_model_input=True)
        if self.runtime is None:
            return value
        try:
            steps = self.runtime.step_count
            sim = float(self.runtime.sim.data.time)
            aux = self.runtime.wm_auxiliary_calibration
            if type(steps) is not int or steps < 0 or not math.isfinite(sim) or sim < 0:
                raise ValueError('Unknown actual Runtime counters')
            if type(aux) is not dict or not {'worlds', 'sim_seconds'} <= aux.keys():
                raise ValueError('Unknown actual auxiliary accounting')
            if type(aux['worlds']) is not int or aux['worlds'] < 0:
                raise ValueError('Unknown actual auxiliary world count')
            if type(aux['sim_seconds']) not in (int, float) or not math.isfinite(aux['sim_seconds']) or aux['sim_seconds'] < 0:
                raise ValueError('Unknown actual auxiliary clock')
            # Only read actual fields; never use reference/own-zero/default values.
            aux = json.loads(json.dumps(aux, allow_nan=False))
            value.update(usage_known=True, actual_task_steps=steps,
                         actual_task_sim_s=sim, actual_auxiliary_calibration=aux)
        except (AttributeError, TypeError, ValueError) as exc:
            value['accounting_error'] = repr(exc)
        return value


def _identity(code):
    constants = tuple(_identity(x) if isinstance(x, types.CodeType) else x
                      for x in code.co_consts)
    return (code.co_code, constants, code.co_names, code.co_varnames,
            code.co_freevars, code.co_cellvars, code.co_argcount,
            code.co_kwonlyargcount, code.co_posonlyargcount, code.co_flags)


def build_receipted_constructor(bound_original=None, receipt=None, *,
                                 source_path=None, enabled=False):
    """Prepare BEFORE seal; no constructor or native method is called here.

    Future caller must supply native_entry._bound_original('construct_cold_components'),
    preserving its private V4 registry/scene globals, and retain the original
    native_entry postchecks. Returning this function grants no run authority.
    """
    if type(enabled) is not bool:
        raise ValueError('Explicit future new-program opt-in')
    if not enabled:
        return None
    if type(receipt) is not PartialObjects or not isinstance(bound_original, types.FunctionType):
        raise ValueError('Exact Data receipt object and original bound function required')
    if receipt.runtime is not None or receipt.observer is not None:
        raise ValueError('Fresh per-program partial receipt required')
    path = Path(source_path)
    raw = path.read_bytes()
    if path.is_symlink() or hashlib.sha256(raw).hexdigest() != BASE_SHA:
        raise ValueError('Exact frozen original constructor source required')
    if bound_original.__code__.co_filename != str(path):
        raise ValueError('Original code must come from that exact pinned source')
    tree = ast.parse(raw.decode(), filename=str(path))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
              and n.name == 'construct_cold_components')
    expected_kwdefaults = {arg.arg: ast.literal_eval(value)
                           for arg, value in zip(fn.args.kwonlyargs, fn.args.kw_defaults)
                           if value is not None}
    if bound_original.__defaults__ is not None or bound_original.__kwdefaults__ != expected_kwdefaults:
        raise ValueError('Original constructor default-OFF arguments changed')
    original_module = ast.Module(body=[copy.deepcopy(fn)], type_ignores=[])
    baseline = compile(original_module, str(path), 'exec', dont_inherit=True)
    original_code = next(x for x in baseline.co_consts if isinstance(x, types.CodeType))
    if _identity(bound_original.__code__) != _identity(original_code):
        raise ValueError('Changed constructor cannot be silently overlaid')
    if HOOK in bound_original.__globals__:
        raise ValueError('No layered lifecycle overlay or callback replacement')
    patched = copy.deepcopy(fn)
    found = []
    body = []
    for node in patched.body:
        body.append(node)
        stage = None
        # Match only the two exact already-reviewed assignment locations.
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = ast.unparse(node.targets[0])
            if target == '(runtime, construction)' and isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == 'construct_cold_runtime':
                stage = 'runtime'
            elif target == 'observer' and isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == 'RegisteredObserver':
                stage = 'observer'
        if stage:
            hook = ast.Expr(ast.Call(ast.Name(HOOK, ast.Load()),
                                    [ast.Constant(stage), ast.Name(stage, ast.Load())], []))
            body.append(ast.copy_location(hook, node))
            found.append(stage)
    if found != ['runtime', 'observer']:
        raise ValueError('Exact original two construction handoff sites changed')
    patched.body = body
    # Removing the TWO hook statements must exactly recover the original AST.
    stripped = copy.deepcopy(patched)
    stripped.body = [n for n in stripped.body if not (
        isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
        and isinstance(n.value.func, ast.Name) and n.value.func.id == HOOK)]
    if ast.dump(stripped, include_attributes=False) != ast.dump(fn, include_attributes=False):
        raise ValueError('No other constructor AST changes allowed')
    private = dict(bound_original.__globals__)
    private[HOOK] = receipt.capture
    module = ast.fix_missing_locations(ast.Module(body=[patched], type_ignores=[]))
    exec(compile(module, str(path), 'exec', dont_inherit=True), private)
    result = private['construct_cold_components']
    result.__defaults__ = bound_original.__defaults__
    result.__kwdefaults__ = dict(bound_original.__kwdefaults__ or {})
    return result


def build_receipted_entry(entry_module=None, receipt=None, *, source_path=None,
                         entry_sha256=None, enabled=False):
    """Private outer entry copy: retain original goal/terrain postchecks too.

    Future worker catches construction exceptions and hands receipt.runtime /
    receipt.observer to its EXISTING sealed cleanup and actual accounting.
    No imported module/function is replaced. No run, lease or AUTH is granted.
    """
    if type(enabled) is not bool:
        raise ValueError('Explicit future new-program opt-in')
    if not enabled:
        return None
    if type(receipt) is not PartialObjects or receipt.runtime is not None or receipt.observer is not None:
        raise ValueError('Fresh per-program receipt required')
    path = Path(entry_module.__file__)
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != entry_sha256:
        raise ValueError('Exact future-freeze original outer entry source required')
    original = entry_module.construct_cold_components
    if not isinstance(original, types.FunctionType) or original.__code__.co_filename != str(path):
        raise ValueError('Original outer entry code/file binding required')
    tree = ast.parse(path.read_text(), filename=str(path))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
              and n.name == 'construct_cold_components')
    check = compile(ast.Module(body=[fn], type_ignores=[]), str(path), 'exec', dont_inherit=True)
    expected = next(x for x in check.co_consts if isinstance(x, types.CodeType))
    if _identity(original.__code__) != _identity(expected) or original.__kwdefaults__ != {'enabled': False}:
        raise ValueError('No changed/default-enabled outer constructor')
    old_factory = original.__globals__['_bound_original']
    def private_factory(name):
        if name != 'construct_cold_components':
            raise ValueError('Only the pinned cold-construction path is overlaid')
        return build_receipted_constructor(old_factory(name), receipt,
                                          source_path=source_path, enabled=True)
    namespace = dict(original.__globals__)
    namespace['_bound_original'] = private_factory
    result = types.FunctionType(original.__code__, namespace, original.__name__,
                                original.__defaults__, original.__closure__)
    result.__kwdefaults__ = dict(original.__kwdefaults__)
    return result
