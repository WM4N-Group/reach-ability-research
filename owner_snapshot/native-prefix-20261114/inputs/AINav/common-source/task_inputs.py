import numpy as np
MACROS = ('WAIT', 'PUSH_A', 'RECOVER_A', 'NAV_B', 'PUSH_B', 'NAV_STEP', 'CLIMB_STEP', 'NAV_HIGH', 'CLIMB_HIGH', 'NAV_C', 'PUSH_C', 'NAV_BRIDGE', 'CLIMB_BRIDGE', 'NAV_FAR', 'BRAKE_FAR')
STATE_DIM = 124

def action(macro, dx=0.0, dt=0.1):
    if macro not in MACROS or (macro != 'NAV_STEP' and dx != 0) or (not any((abs(dx - v) < 1e-08 for v in (-0.02, 0.0, 0.02)))) or (not 0 < dt <= 0.100001):
        raise ValueError('Registered declared offset action required')
    x = np.zeros(20, np.float32)
    x[MACROS.index(macro)] = 1.0
    x[15] = dx / 0.1
    x[18] = 0.6 if macro.startswith('PUSH_') else 0.0
    x[19] = dt
    return x

def state_input(raw69, mean, scale, *, fresh_body=None, body_age=0.0, rgb_age=0.0, candidate_front=None):
    raw69 = np.asarray(raw69, np.float32)
    if raw69.shape != (69,) or not np.isfinite(raw69).all():
        raise ValueError('Observed69D state required')
    if raw69[68] == 0 and np.any(raw69[61:68] != 0):
        raise ValueError('Missing geometry must not be imputed')
    front = raw69[61:69] if candidate_front is None else np.asarray(candidate_front, np.float32)
    body = raw69[:45] if fresh_body is None else np.asarray(fresh_body, np.float32)
    if front.shape != (8,) or body.shape != (45,) or (not np.isfinite(front).all()) or (not np.isfinite(body).all()) or (min(body_age, rgb_age) < -1e-08) or (rgb_age > 0.100001) or (body_age > 0.020001):
        raise ValueError('Finite actual mixed-rate context required')
    if front[7] == 0 and np.any(front[:7] != 0):
        raise ValueError('Candidate front invalid0 must retain zero measurement')
    x = np.zeros(STATE_DIM, np.float32)
    x[:69] = raw69
    x[:45] = (raw69[:45] - mean) / scale
    x[60] = np.log1p(raw69[60])
    x[69:114] = (body - mean) / scale
    x[114] = max(0.0, body_age)
    x[115] = max(0.0, rgb_age)
    x[116:124] = front
    return x
