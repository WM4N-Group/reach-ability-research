"""CPU snapshot has NO SDK or physical execution authority.

A future immutable release must add a source-bound SDK gate and an explicit
8-of-14 budget allocation launcher. Never reuse the stopped16-start supervisor.
"""

def require_execution_authority():
    raise PermissionError('CPU-only pose-entry source snapshot: no SDK/physical admission or budget allocation is implemented/approved; no App may start')
