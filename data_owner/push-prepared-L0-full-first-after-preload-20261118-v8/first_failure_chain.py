"""Bounded failure provenance, observation only; no changes to the thrown chain."""
AUDIT_MESSAGE='Unplanned code/import installation outside paused boundary'


def capture_failure(primary,engine,report_one):
    nodes=[];seen=set();kind='outer';depth=0;cur=primary
    while cur is not None and  id(cur) not in seen and depth<4:
        seen.add(id(cur));row=report_one(cur,max_frames=8);nodes.append(dict(link=kind,metadata=row))
        if cur.__cause__ is not None:cur=cur.__cause__;kind='cause'
        else:cur=cur.__context__;kind='context'
        depth+=1
    state=None if engine is None else engine.state
    failure=None if engine is None else engine.failure
    return dict(engine_state_at_capture=state,
        first_audit_latch_label='UNPLANNED_CODE_OR_IMPORT' if failure==AUDIT_MESSAGE else None,
        no_inference_if_first_latch_not_recorded=True,outer_then_cause_or_context=nodes,
        truncated_or_cycle=cur is not None,no_exception_text_args_locals_or_headers=True)
