"""Narrow default-OFF source candidate for D3, never a live hook/dispatcher.

Only the pinned SDK PushSettled.__call__ is expanded to retain its already
computed terms. Its helper invocations, eager bitwise order, thresholds, clock
increment and returned tensor are preserved. All other source bytes stay exact.
The owner must freeze this NEW source and bind one bounded audit sink before use.
No source/file/process is modified by this module.
"""
import ast
import hashlib

SDK_SHA256 = '399aada0ee3b79af11014a22d8ba6f942e2df90f4658aa959139fc941bb59ed5'
CALL_SHA256 = 'd3cf0468608e453fd33e78fb14e635b32d30fea37b859300cd5c33eefee0c61d'
CALLBACK = '_ainav_push_settled_audit'

# Left-associated operations deliberately match the original eager '&' AST.
# Callback payload contains only copied Python scalars/tuples, never tensors/env.
_METHOD = '''    def __call__(self, env, asset_cfg=SceneEntityCfg("robot", body_names="end_effector"), hold_time=0.5):
        _audit_emit = env._ainav_push_settled_audit
        if not callable(_audit_emit):
            raise ValueError("D3 requires one bounded owner audit sink before the original predicate")
        self.contact_seen |= hand_contact(env, asset_cfg)
        box = env.scene["box"]
        _audit_error_xy = torch.linalg.vector_norm(push_target(env)[:, :2] - box.data.root_pos_w[:, :2], dim=1)
        _audit_goal_ok = _audit_error_xy < 0.12
        _audit_speed_3d = torch.linalg.vector_norm(box.data.root_lin_vel_w, dim=1)
        _audit_speed_ok = _audit_speed_3d < 0.08
        _audit_goal_speed = _audit_goal_ok & _audit_speed_ok
        _audit_with_contact = _audit_goal_speed & self.contact_seen
        _audit_not_tipped = ~box_tipped(env)
        _audit_with_tip = _audit_with_contact & _audit_not_tipped
        _audit_no_forbidden = ~forbidden_box_contact(env)
        settled = _audit_with_tip & _audit_no_forbidden
        _audit_duration_before = self.duration
        _audit_dt = env.step_dt
        self.duration = torch.where(settled, self.duration + _audit_dt, 0.0)
        _audit_result = self.duration >= hold_time
        _audit_emit(dict(
            schema="AINav-D3-original-single-predicate-components-v1",
            native_step_dt_s=float(_audit_dt), hold_time_s=float(hold_time),
            goal_xy_error_m=tuple(_audit_error_xy.tolist()),
            box_speed_3d_m_s=tuple(_audit_speed_3d.tolist()),
            goal_xy_lt_original_012=tuple(_audit_goal_ok.tolist()),
            speed_3d_lt_original_008=tuple(_audit_speed_ok.tolist()),
            contact_seen_latched=tuple(self.contact_seen.tolist()),
            not_tipped=tuple(_audit_not_tipped.tolist()),
            no_forbidden_contact=tuple(_audit_no_forbidden.tolist()),
            settled_now=tuple(settled.tolist()),
            duration_before_s=tuple(_audit_duration_before.tolist()),
            duration_after_s=tuple(self.duration.tolist()),
            returned_confirmed=tuple(_audit_result.tolist())))
        return _audit_result
'''


def instrument_push_settled_source(source, *, enabled=False):
    """Return bytes for a NEW owner-frozen SDK; never install/write/execute it.

    OFF returns the exact input unchanged. ON accepts only the original full
    source+method identity; no fuzzy patching or hot replacement is supported.
    The callback is audit-only, but its IO/conversion overhead is NOT measured
    here. Sink/conversion exceptions propagate after the original state update;
    the owner must stop/close, never roll back/reset/resume the predicate.
    """
    if type(enabled) is not bool or type(source) is not bytes:
        raise ValueError('Explicit boolean and original SDK bytes required')
    if not enabled:
        return source
    if hashlib.sha256(source).hexdigest() != SDK_SHA256:
        raise ValueError('Exact original SDK source required for independent D3 candidate')
    if CALLBACK.encode() in source:
        raise ValueError('No prior audit hook or repeated instrumentation')
    text = source.decode('utf-8')
    tree = ast.parse(text)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'PushSettled']
    if len(classes) != 1:
        raise ValueError('One original PushSettled class required')
    calls = [n for n in classes[0].body if isinstance(n, ast.FunctionDef) and n.name == '__call__']
    if len(calls) != 1 or calls[0].decorator_list:
        raise ValueError('One undecorated original stateful call required')
    node = calls[0]
    lines = source.splitlines(keepends=True)
    old = b''.join(lines[node.lineno - 1:node.end_lineno])
    normalized = old.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
    if hashlib.sha256(normalized.encode()).hexdigest() != CALL_SHA256:
        raise ValueError('Exact original single predicate body required')
    newline = b'\r\n' if old.endswith(b'\r\n') else b'\n'
    replacement = _METHOD.encode().replace(b'\n', newline)
    before = b''.join(lines[:node.lineno - 1])
    after = b''.join(lines[node.end_lineno:])
    result = before + replacement + after
    compile(result, '<new-D3-SDK-source-candidate-only>', 'exec')
    assert result.startswith(before)
    if after:
        assert result.endswith(after)
    return result
