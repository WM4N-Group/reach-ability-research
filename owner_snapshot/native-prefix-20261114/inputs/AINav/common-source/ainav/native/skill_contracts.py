"""Public meaning of current skill admission, not new motion/route policy.

Admission checks current necessary conditions; it does not certify a future
trajectory. Keep this description separate from motor guards and task order.
"""

ENTRY_PREPARATION_CONSTRAINTS = (
    'Current native admission checks necessary entry conditions only; it does not certify a collision-free approach or successful future skill trajectory.',
    'Native internal preparation is not a guarantee of safe entry from every admitted pose. Choose or omit NAV using current visual clearance, public approach references and actual outcomes; admission alone is not evidence that extra positioning is unnecessary.',
    'Completion of one skill does not certify the next skill READY or safe approach. There is no mandatory predecessor or successor skill; use current observations and the declared skill contract.',
)
