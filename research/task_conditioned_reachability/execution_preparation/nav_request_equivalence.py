"""Source-bound scalar NAV request diagnostic, NOT a planner or native gate.

Characterize the pinned EfficientNav axis primitive without numpy/torch/Runtime.
The *whole* controller, latches, native profile, actor and motor dynamics are NOT
executed/qualified. Native/private errors used here must remain audit-only. Same
instantaneous body request never proves equivalent trajectories or safe arrival.
"""
from dataclasses import dataclass
import ast
import hashlib
import math

from .successor_aware_choice import need, pin, number


EXPR = 'math.copysign(max(MIN_SPEEDS[axis], 2. * abs(body_delta[axis])), body_delta[axis])'
DEADBAND = 'abs(body_delta[axis]) > cfg.position_command_deadband'
CLIP = 'np.clip(desired, -SPEED_LIMITS, SPEED_LIMITS)'


def _shape(node):return ast.dump(node,include_attributes=False)
def _expr_shape(text):return _shape(ast.parse(text,mode='eval').body)


@dataclass(frozen=True)
class Primitive:
    source_sha256: str
    minimum_speeds: tuple
    speed_limits: tuple

    def request(self, error, *, axis, deadband):
        """Only original axis primitive, CONDITIONED on warmup/drive/latch gates.

        No observation, pose, latch update, original observe/arrival or control IO.
        Scalar finite IEEE arithmetic; no rounding/tolerance widening at boundary.
        """
        need(type(axis) is int and axis in (0,1), 'Original translational axes only')
        need(number(error) and number(deadband) and deadband>=0, 'Explicit finite original-profile deadband/error')
        if abs(error)<=deadband:return 0.
        value=math.copysign(max(self.minimum_speeds[axis],2.*abs(error)),error)
        return max(-self.speed_limits[axis], min(self.speed_limits[axis],value))


def verify_primitive(source, *, expected_sha256):
    """Require exact owner file SHA and AST of the actual in-update primitive.

    Parsing is not original-class execution. Refuse unsupported source changes,
    especially changed deadband strictness, floor, clipping or slew assignment.
    """
    need(type(source) is bytes and pin(expected_sha256) and
         hashlib.sha256(source).hexdigest()==expected_sha256, 'Pinned original nav_efficiency source')
    tree=ast.parse(source)
    values={}
    for stmt in tree.body:
        if isinstance(stmt,ast.Assign) and len(stmt.targets)==1 and isinstance(stmt.targets[0],ast.Name):
            name=stmt.targets[0].id
            if name in ('SPEED_LIMITS','MIN_SPEEDS'):
                need(isinstance(stmt.value,ast.Call) and _shape(stmt.value.func)==_expr_shape('np.array') and
                     len(stmt.value.args)==1 and not stmt.value.keywords, 'Original literal np.array constants')
                value=ast.literal_eval(stmt.value.args[0])
                need(type(value) is list and len(value)==3 and all(number(v) and v>0 for v in value),
                     'Finite original axis floors/limits')
                values[name]=tuple(value)
    need(set(values)=={'SPEED_LIMITS','MIN_SPEEDS'},'Explicit original floor/limit constants')
    classes=[c for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='EfficientNav']
    need(len(classes)==1,'Exact EfficientNav class')
    methods=[m for m in classes[0].body if isinstance(m,ast.FunctionDef) and m.name=='update']
    need(len(methods)==1,'Exact original update')
    update=methods[0]
    loops=[n for n in ast.walk(update) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='axis']
    need(len(loops)==1 and ast.literal_eval(loops[0].iter)==(0,1),'Original two-axis loop')
    loop=loops[0]
    need(len(loop.body)==1 and isinstance(loop.body[0],ast.If) and not loop.body[0].orelse and
         _shape(loop.body[0].test)==_expr_shape(DEADBAND),'Exact strict original deadband')
    body=loop.body[0].body
    need(len(body)==1 and isinstance(body[0],ast.Assign) and len(body[0].targets)==1 and
         _shape(body[0].targets[0])==_shape(ast.parse('desired[axis]=0').body[0].targets[0]) and
         _shape(body[0].value)==_expr_shape(EXPR),'Exact original nonzero floor expression')
    clips=[n for n in update.body if isinstance(n,ast.Assign) and len(n.targets)==1 and
           isinstance(n.targets[0],ast.Name) and n.targets[0].id=='desired' and
           isinstance(n.value,ast.Call) and _shape(n.value)==_expr_shape(CLIP)]
    need(len(clips)==1,'Exact original post-axis clip')
    copies=[n for n in update.body if isinstance(n,ast.Assign) and len(n.targets)==1 and
            _shape(n.targets[0])==_shape(ast.parse('self.command=0').body[0].targets[0])]
    need(len(copies)==1 and _shape(copies[0].value)==_expr_shape('desired.copy()'), 'No hidden command slew accepted')
    return Primitive(expected_sha256,values['MIN_SPEEDS'],values['SPEED_LIMITS'])


def diagnose_lateral_errors(primitive, errors_by_candidate, *, deadband):
    """Same-state *axis* diagnostic. Not current public schema or candidate choice.

    Native owner supplies actual projected body-axis errors and original live
    deadband, never historical outcome calibration/default guessed profile. All
    candidates are conditional on warmup completed, position_latched=False and
    identical upstream state. No full 3D-request or motor equality conclusion.
    """
    need(type(primitive) is Primitive, 'Verified original scalar primitive')
    need(type(errors_by_candidate) is dict and set(errors_by_candidate)==
         {'original','lateral_plus_0p04','lateral_minus_0p04'}, 'Complete fixed three-candidate error row')
    need(primitive.minimum_speeds[1]==primitive.speed_limits[1],
         'Constant-amplitude lateral primitive required; do not silently generalize')
    requests={cid:primitive.request(error,axis=1,deadband=deadband) for cid,error in errors_by_candidate.items()}
    groups={}
    for cid,request in requests.items():groups.setdefault(request,[]).append(cid)
    return dict(schema='Reach-source-axis-request-equivalence-diagnostic-v1',
        role='NATIVE_PRIVATE_AUDIT_DIAGNOSTIC_NOT_SELECTOR_OR_FIT',source_sha256=primitive.source_sha256,
        deadband=deadband, supplied_native_body_axis_errors=errors_by_candidate.copy(),
        axis_requests=requests, all_lateral_axis_requests_same=len(groups)==1,
        axis_equivalence_groups=list(groups.values()),
        conditional_on=['warmup complete','position latch FALSE for every compared primitive',
                        'same physical/native snapshot; source-default floors/limits; actual profile deadband supplied'],
        whole_velocity_request_equivalence='UNKNOWN_OTHER_AXIS_YAW_AND_LATCHES_NOT_EVALUATED',
        trajectory_or_Actor_or_motor_equivalence='UNKNOWN_REQUIRES_ORIGINAL_NATIVE_AND_ACTUAL_NEW_OUTCOME',
        native_admission_or_success_or_cost_prediction=False, public_planner_input_permission=False,
        execution_authorized=False)
