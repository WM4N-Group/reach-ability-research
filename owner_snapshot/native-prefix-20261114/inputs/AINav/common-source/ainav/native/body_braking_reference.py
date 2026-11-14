"""Per-selected-context immutable body reference; original native code reused.

Only the REQUESTED velocity term in the original 226D observation is sourced
from the public placement reference. Measured sensors, original arm/NN drive,
set_action, native algorithms, gains and global module/scene aliases stay intact.
No actor/physics, copied state, reset, command-history rewrite or route selector.
"""
from dataclasses import asdict,dataclass
import hashlib
import inspect
import json
import math
from types import FunctionType,MethodType


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class BodyBrakingDeclaration:
    body_goal_xy_m: tuple
    original_native_drive_goal_sha256: str
    def __post_init__(self):
        if type(self.body_goal_xy_m) is not tuple or len(self.body_goal_xy_m)!=2 or not all(type(v) in (float,int) and math.isfinite(v) for v in self.body_goal_xy_m):
            raise ValueError('Finite immutable declared public body XY required')
        h=self.original_native_drive_goal_sha256
        if not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):raise ValueError('Actual original native goal identity required')
    @property
    def sha256(self):return digest(asdict(self))


def clone_with_globals(fn,**rebindings):
    if not isinstance(fn,FunctionType):raise ValueError('Original Python native function required')
    scope=dict(fn.__globals__)
    if not set(rebindings)<=set(scope):raise ValueError('Only existing declared native global names may be rebound')
    scope.update(rebindings)
    result=FunctionType(fn.__code__,scope,fn.__name__,fn.__defaults__,fn.__closure__)
    result.__kwdefaults__=fn.__kwdefaults__;result.__module__=fn.__module__;result.__qualname__=fn.__qualname__
    return result


class _BoxVelocityView:
    def __init__(self,original,velocity):self.original,self.push_velocity_commands=original,velocity
    def __getattr__(self,name):return getattr(self.original,name)


class BodyBrakingBinding:
    def __init__(self,view,box_push,*,body_goal_xy_m,goal_fingerprint=None,journal=None):
        if view.history is not None or hasattr(view,'controller'):
            raise ValueError('Bind both references before target controller/history construction')
        if goal_fingerprint is None:
            from mujoco_zyh.native_behavior_executor import array_sha
            goal_fingerprint=lambda:array_sha(view.box_push_target.detach().cpu().numpy())
        self.view,self.original,self.goal_fingerprint=view,box_push,goal_fingerprint
        self.data,self.box=view.data,view.scene['box']
        self.journal=journal
        self.declaration=BodyBrakingDeclaration(tuple(body_goal_xy_m),goal_fingerprint())
        self.initial_sha=self.declaration.sha256
        self.functions={n:getattr(box_push,n) for n in ('nominal_push_velocity_commands','push_velocity_commands','push_control_at_goal')}
        self.original_observation=view.observation.__func__
        if self.original_observation.__globals__.get('box_push') is not box_push:
            raise ValueError('Original native observation must reference this actual SDK box_push module')
        def remaining(env):
            self.assert_immutable()
            if env is not self.view:raise RuntimeError('Body reference used on another target context')
            return self.declaration.body_goal_xy_m[0]-env.scene['box'].data.root_pos_w[:,0]
        self.remaining=remaining
        self.nominal=clone_with_globals(self.functions['nominal_push_velocity_commands'],push_remaining_distance=remaining)
        self.at_goal=clone_with_globals(self.functions['push_control_at_goal'],push_remaining_distance=remaining)
        self.velocity=clone_with_globals(self.functions['push_velocity_commands'],
            nominal_push_velocity_commands=self.nominal,push_control_at_goal=self.at_goal)
        self.proxy=_BoxVelocityView(box_push,self.velocity)
        self.observation=clone_with_globals(self.original_observation,box_push=self.proxy)
        binding=self
        def guarded_observation(env):
            binding.assert_immutable()
            observation=binding.observation(env)
            if binding.journal is not None:
                from mujoco_zyh.native_behavior_executor import array_sha
                if observation.shape!=(226,):raise RuntimeError('Original body-reference policy observation must remain 226D')
                binding.journal(dict(event='body_reference_native_observation_proposed',
                    time_s=float(binding.data.time),body_reference_sha256=binding.initial_sha,
                    observation_sha256=array_sha(observation),
                    requested_velocity_history=observation[180:189].reshape(3,3).tolist(),
                    original_native_goal_sha256=binding.declaration.original_native_drive_goal_sha256,
                    actuator_command_not_yet_issued=True,model_input=False))
            return observation
        self.guarded_observation=guarded_observation
        view.observation=MethodType(guarded_observation,view)
        self.source_receipt=dict(schema='ainav-native-body-reference-code-binding-v1',
            declaration=asdict(self.declaration),declaration_sha256=self.initial_sha,
            native_function_source_sha256={n:hashlib.sha256(inspect.getsource(f).encode()).hexdigest() for n,f in self.functions.items()},
            original_observation_source_sha256=hashlib.sha256(inspect.getsource(self.original_observation).encode()).hexdigest(),
            original_code_objects_reused=True,original_global_functions_or_scene_aliases_replaced=False,
            inverse_is_original_functions_and_observation=True,
            measured_observation_fields_unchanged=True,native_set_action_unmodified=True,
            native_arm_and_NN_goal_unchanged=True,body_reference_bound_before_controller=True,
            algorithms_or_gains_or_thresholds_changed=False,actors_forwarded=0,physics_steps=0,model_input=False)
        self.assert_immutable()
    @property
    def sha256(self):self.assert_immutable();return self.initial_sha
    def assert_immutable(self):
        if self.declaration.sha256!=self.initial_sha or self.goal_fingerprint()!=self.declaration.original_native_drive_goal_sha256:
            raise RuntimeError('Declared body or original native drive reference changed')
        if self.view.data is not self.data or self.view.scene['box'] is not self.box:
            raise RuntimeError('Body-braking world/object binding changed')
        if any(getattr(self.original,n) is not f for n,f in self.functions.items()):raise RuntimeError('Original global native velocity functions replaced')
        if (self.nominal.__code__ is not self.functions['nominal_push_velocity_commands'].__code__
                or self.nominal.__globals__['push_remaining_distance'] is not self.remaining
                or self.at_goal.__code__ is not self.functions['push_control_at_goal'].__code__
                or self.at_goal.__globals__['push_remaining_distance'] is not self.remaining
                or self.velocity.__code__ is not self.functions['push_velocity_commands'].__code__
                or self.velocity.__globals__['nominal_push_velocity_commands'] is not self.nominal
                or self.velocity.__globals__['push_control_at_goal'] is not self.at_goal
                or self.observation.__code__ is not self.original_observation.__code__
                or self.observation.__globals__['box_push'] is not self.proxy
                or self.proxy.push_velocity_commands is not self.velocity
                or self.proxy.original is not self.original):
            raise RuntimeError('Original native body-reference code bindings changed')
    def receipt(self):self.assert_immutable();return json.loads(json.dumps(self.source_receipt))
