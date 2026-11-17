"""Bounded metadata at the actual Actor call, for a NEW private parent only.

No torch import/forward, profiler, module monkeypatch, IO, or run authority on
import. Call-site copies preserve the original tensor construction/inference
context/output conversion. This is changed instrumentation, not unchanged code.
"""
import ast
import copy
import hashlib
from pathlib import Path
import types

INFER_SHA = '2e12846c7a7789b2f44953a12685b3d0221fbd0f9449cd704e8232916877aff5'
NAV_SHA = 'bd173adeb4d31f651f5d8d5a9c2e37c6129421aa21c39edd09e5e986ac501361'
HOOK = '_data_actual_actor_call'


class ActorTrace:
    """No observations/actions copied; counts and first/last per role/phase only.

    A call returning a tensor counts as returned even if subsequent .cpu()/numpy
    fails. Conversion or metadata failures BEFORE invocation count no Actor call.
    All counts are instrumentation-local; no historical activation inference.
    """
    def __init__(self, context, *, max_phase_keys=64):
        if not callable(context) or type(max_phase_keys) is not int or not 1 <= max_phase_keys <= 64:
            raise ValueError('Finite parent context/phase bound required')
        self.context = context
        self.max_phase_keys = max_phase_keys
        self.actors = []
        self.rows = {}
        self.resets = {}
        self.coverage_complete = False  # Only the FINAL integrated parent may qualify coverage.

    def bind_runtime(self, runtime):
        if self.actors:
            raise ValueError('No actor rebind/resync')
        roles = [('NAV_WBC', runtime.nav_actor), ('PUSH_leg', runtime.push_actors[0]),
                 ('PUSH_arm', runtime.push_actors[1]), ('CLIMB', runtime.climb_actor)]
        if len(runtime.push_actors) != 2 or any(not callable(a) for _, a in roles):
            raise ValueError('Original four deployed Actor objects required')
        if any(a is b for i, (_, a) in enumerate(roles) for _, b in roles[i + 1:]):
            raise ValueError('Distinct original Actor roles required')
        self.actors = roles

    def _context(self):
        import math
        c = self.context()
        if (type(c) is not dict or set(c) != {'root_skill', 'native_phase', 'task_step', 'task_sim_s'}
                or any(type(c[k]) is not str or not 0 < len(c[k]) <= 96 for k in ('root_skill', 'native_phase'))
                or type(c['task_step']) is not int or c['task_step'] < 0
                or type(c['task_sim_s']) not in (int, float)
                or not math.isfinite(c['task_sim_s']) or c['task_sim_s'] < 0):
            raise ValueError('Actual bounded root/native phase and physical clock required')
        return dict(c)

    def call(self, actor, prepared_tensor):
        role = next((r for r, a in self.actors if a is actor), None)
        if role is None:
            raise ValueError('Unregistered actual Actor, no guessed module label')
        c = self._context()
        key = (role, c['root_skill'], c['native_phase'])
        if key not in self.rows:
            if len(self.rows) >= self.max_phase_keys:
                raise RuntimeError('Bounded phase metadata full; do not silently lose coverage')
            self.rows[key] = dict(role=role, root_skill=key[1], native_phase=key[2],
                                  attempted=0, returned=0, raised=0, first=c, last=c,
                                  last_error_type=None)
        row = self.rows[key]
        row['last'] = c
        row['attempted'] += 1
        try:
            value = actor(prepared_tensor)  # Exactly one original Actor invocation.
        except BaseException as exc:
            row['raised'] += 1
            row['last_error_type'] = type(exc).__name__
            raise
        row['returned'] += 1
        return value  # ORIGINAL return object, not converted/reconstructed.

    def reset_call(self, name, original, instance, *args, **kwargs):
        if name not in ('reset_nav_history', 'push_enter', 'climb_enter'):
            raise ValueError('Only three original history-init boundaries')
        c = self._context()
        row = self.resets.setdefault(name, dict(attempted=0, returned=0, raised=0, first=c, last=c))
        row['last'] = c
        row['attempted'] += 1
        try:
            value = original(instance, *args, **kwargs)
        except BaseException:
            row['raised'] += 1
            raise
        row['returned'] += 1
        return value

    def snapshot(self):
        import json
        return json.loads(json.dumps(dict(schema='data-actual-actor-call-metadata-v1',
            roles_bound=[r for r, _ in self.actors], coverage_complete=self.coverage_complete,
            phase_key_cap=self.max_phase_keys, phases=list(self.rows.values()),
            original_history_initializations=self.resets,
            extra_Actor_forward_or_history_reset=0, metadata_only_not_model_input=True), allow_nan=False))


def _function_node(text, name, class_name=None):
    tree = ast.parse(text)
    body = tree.body if class_name is None else next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name).body
    return next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == name)


def instrument_callsite(original, *, source_path, source_sha256, function_name,
                        actor_expression, trace, class_name=None):
    """PRIVATE function copy; only one exact Actor call AST node is changed.

    The full original module is compiled (not executed) to check code identity.
    No shared imported function/class/global is changed, no class is downcast.
    """
    from types import CodeType
    path = Path(source_path)
    raw = path.read_bytes()
    if path.is_symlink() or hashlib.sha256(raw).hexdigest() != source_sha256:
        raise ValueError('Exact original source required')
    if type(original) is not types.FunctionType or original.__closure__:
        raise ValueError('Exact non-closure original callsite required')
    text = raw.decode()
    fn = _function_node(text, function_name, class_name)
    compiled = compile(text, str(path), 'exec', dont_inherit=True)
    if class_name:
        compiled = next(c for c in compiled.co_consts if isinstance(c, CodeType) and c.co_name == class_name)
    expected = next(c for c in compiled.co_consts if isinstance(c, CodeType) and c.co_name == function_name)
    def identity(code):
        return (code.co_code, tuple(identity(c) if isinstance(c, CodeType) else c for c in code.co_consts),
                code.co_names, code.co_varnames, code.co_freevars, code.co_cellvars,
                code.co_argcount, code.co_kwonlyargcount, code.co_posonlyargcount, code.co_flags)
    if identity(original.__code__) != identity(expected) or HOOK in original.__globals__:
        raise ValueError('Changed or layered callsite refused')
    node = copy.deepcopy(fn)
    calls = [n for n in ast.walk(node) if isinstance(n, ast.Call) and ast.unparse(n.func) == actor_expression]
    if len(calls) != 1 or len(calls[0].args) != 1 or calls[0].keywords:
        raise ValueError('One original single-argument Actor call required')
    selected = calls[0]
    before = ast.dump(fn, include_attributes=False)
    old_func = selected.func
    selected.func = ast.Name(HOOK, ast.Load())
    selected.args.insert(0, copy.deepcopy(old_func))
    # Inverse identity check before compilation, preserving every other AST node.
    inverse = copy.deepcopy(node)
    changed = next(n for n in ast.walk(inverse) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Name) and n.func.id == HOOK)
    changed.func = changed.args.pop(0)
    if ast.dump(inverse, include_attributes=False) != before:
        raise ValueError('Callsite inverse mismatch')
    namespace = dict(original.__globals__)
    namespace[HOOK] = trace.call
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                 str(path) + '[actual-actor-call-only]', 'exec', dont_inherit=True), namespace)
    result = namespace[function_name]
    result.__defaults__ = original.__defaults__
    result.__kwdefaults__ = original.__kwdefaults__
    return result


def copy_infer_method(original, traced_infer):
    """Copy the ORIGINAL method bytecode with ONLY private infer binding.

    Intended for a fresh generated Machine BEFORE subclass/session creation.
    Never assign this as an instance/base update over a registered derived type.
    """
    if type(original) is not types.FunctionType or original.__closure__ or 'infer' not in original.__code__.co_names:
        raise ValueError('Expected original simple Machine inference method')
    namespace = dict(original.__globals__)
    namespace['infer'] = traced_infer
    result = types.FunctionType(original.__code__, namespace, original.__name__, original.__defaults__)
    result.__kwdefaults__ = original.__kwdefaults__
    return result
