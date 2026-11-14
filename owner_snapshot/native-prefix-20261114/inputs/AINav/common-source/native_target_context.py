"""PREPARATION ONLY: explicit per-target native reader/software-state context.

The actual Isaac scene, its object names and world env_origins are untouched.
Only functions explicitly given this context see the selected body/contact set.
A's controller caches are never silently inherited by B. No actor/SDK/controller
construction, physics writes, stepping, reset, handoff or guard certification.
Future caller MUST retain original global guards and independently verify native
entry, fresh binding, matching observations/actions and target-B guard coverage.
"""
from collections.abc import Mapping
import math
from native_candidate_contact_layout import selected_contact_keys


class _SensorView(Mapping):
    def __init__(self,original,mapping):self._original=original;self._mapping=dict(mapping)
    def __getitem__(self,key):return self._original[self._mapping.get(key,key)]
    def __iter__(self):return iter(set(self._original)|set(self._mapping))
    def __len__(self):return len(set(self._original)|set(self._mapping))


class _SceneView(Mapping):
    def __init__(self,original,body_key,sensors):
        self._original=original;self._body_key=body_key;self._sensors=dict(sensors)
        self.sensors=_SensorView(original.sensors,sensors)
    def __getitem__(self,key):
        return self._original[self._body_key if key=='box' else self._sensors.get(key,key)]
    def __iter__(self):return iter(set(self._original.keys())|set(self._sensors))
    def __len__(self):return len(set(self._original.keys())|set(self._sensors))
    @property
    def env_origins(self):
        # Do NOT shift physical world origins to fake a target-local frame.
        # Native push_target adds actual env_origins to B.default_root_state.
        return self._original.env_origins


class _ConfigSceneView:
    def __init__(self,original,body_key):object.__setattr__(self,'_original',original);object.__setattr__(self,'_body_key',body_key)
    def __getattr__(self,name):return getattr(self._original,self._body_key if name=='box' else name)
    def __setattr__(self,name,value):raise TypeError('Explicit target config view is read-only')


class _ConfigView:
    def __init__(self,original,body_key):
        object.__setattr__(self,'_original',original)
        object.__setattr__(self,'scene',_ConfigSceneView(original.scene,body_key))
        object.__setattr__(self,'_native_overrides',{})
    def __getattr__(self,name):
        if name in self._native_overrides:return self._native_overrides[name]
        return getattr(self._original,name)
    def __setattr__(self,name,value):raise TypeError('Explicit target config view is read-only')


class _ActionView:
    def __init__(self,original):self._original=original;self._terms={}
    def bind(self,name,term):
        if name!='joint_pos' or name in self._terms:raise ValueError('One explicit new target joint_pos term binding required')
        self._terms[name]=term
    def get_term(self,name):
        if name not in self._terms:raise ValueError('No fallback to previous target action term: '+name)
        return self._terms[name]
    def __getattr__(self,name):
        if name not in ('action','prev_action','prev_prev_action'):raise AttributeError(name)
        return getattr(self._original,name)  # real same-episode action history, never reset


class NativeTargetContext:
    """Executor-private dependency context, NOT a model observation or live alias.

    Stateful writes are limited to local box_push_* and transition_* software
    fields. Native reader functions receive real shared robot/body/sensor handles;
    this is not a general sandbox preventing misuse of those handles.
    """
    _shared=frozenset(('device','num_envs','step_dt','physics_dt','episode_length_buf','common_step_counter'))
    def __init__(self,env,contact_receipt,*,candidate):
        keys=list(env.scene.keys())
        contacts=selected_contact_keys(contact_receipt,candidate=candidate,observed_scene_keys=keys)
        body_key=contact_receipt['scene_keys'][candidate]
        # Resolve every selected sensor from both standard native access forms.
        for sensor_key in contacts.values():
            if env.scene[sensor_key] is not env.scene.sensors[sensor_key]:
                raise ValueError('Scene and sensor dictionaries disagree on actual contact identity')
        object.__setattr__(self,'_env',env);object.__setattr__(self,'_software',{})
        object.__setattr__(self,'scene',_SceneView(env.scene,body_key,contacts))
        object.__setattr__(self,'cfg',_ConfigView(env.cfg,body_key))
        object.__setattr__(self,'action_manager',_ActionView(env.action_manager))
        object.__setattr__(self,'candidate',candidate);object.__setattr__(self,'body_key',body_key)
        object.__setattr__(self,'extras',{})
    def __getattr__(self,name):
        local=object.__getattribute__(self,'_software')
        if name in local:return local[name]
        if name=='box_push_target':
            raise ValueError('Capture an explicit measured B goal before native readers; no default-start fallback')
        if name in self._shared:return getattr(self._env,name)
        # Never forward stale target caches, reset/step methods, termination
        # ownership or unregistered SDK interfaces to the original environment.
        raise AttributeError(name)
    def __setattr__(self,name,value):
        if not name.startswith(('box_push_','transition_')):raise TypeError('Only isolated native software state may be written')
        self._software[name]=value
    def mark_actual_entry_parking(self,*,actual_planar_error_m):
        if type(actual_planar_error_m) not in (int,float) or not math.isfinite(actual_planar_error_m) or not 0<=actual_planar_error_m<.08:
            raise ValueError('Original measured80mm parking domain required')
        self._software['late_stop_requested']=True

    def set_native_prepared_hand_height(self,value,*,support_only_shift_m):
        if (value!=-.01 or type(support_only_shift_m) not in (int,float)
                or not math.isfinite(support_only_shift_m) or not 0<support_only_shift_m<=.04):
            raise ValueError('Exact original supported-preparation hand-height branch required')
        self.cfg._native_overrides['push_hand_height_offset']=value
        self.transition_native_hand_height_override=dict(value=value,support_only_shift_m=support_only_shift_m,global_cfg_changed=False)

    def capture_measured_push_goal(self):
        """Goal SOFTWARE only, equivalent to native reset goal assignment.

        Unlike a physical reset, retain B's actual current pose/velocity and all
        robot/controller histories. Native push_target's fallback to the old
        default root state must NOT erase drift/interaction before B's attempt.
        This is not a handoff gate or an authorization to execute the controller.
        """
        import torch
        if 'box_push_target' in self._software:raise ValueError('Never relabel an active target goal')
        position=self.scene['box'].data.root_pos_w
        distance=self.cfg.push_distance
        if (position.shape!=(self.num_envs,3) or not bool(torch.isfinite(position).all())
                or type(distance) not in (int,float) or not math.isfinite(distance) or abs(distance-.6)>1e-8):
            raise ValueError('Actual finite current B pose and frozen native0.6m push distance required')
        goal=position.clone();goal[:,0]+=distance
        self.box_push_target=goal
        return dict(actual_position_w=position.tolist(),target_position_w=goal.tolist(),
                    physical_state_changed=False,original_world_x_goal_rule_preserved=True)

    def capture_declared_push_goal(self, *, distance_m, declaration_id, goal_xy_m=None):
        """Bind an explicitly chosen distance ONCE for a new software attempt.

        Separate opt-in from the legacy frozen0.6m method. The caller must clone
        its prospective cfg before constructing this context/controller; this
        never modifies the original env cfg or an already running attempt.
        These software choices are not physics admission or skill certification.
        """
        import torch
        if 'box_push_target' in self._software:
            raise ValueError('Never rebase an active or retired attempt goal')
        if (type(distance_m) not in (int, float) or not math.isfinite(distance_m)
                or (not any(abs(distance_m-x)<1e-8 for x in (.2, .4, .6, .8)) if goal_xy_m is None else not 0<distance_m<=.8)
                or not isinstance(declaration_id, str) or not declaration_id
                or abs(self.cfg.push_distance-distance_m)>1e-8):
            raise ValueError('Explicit attempt ID, registered distance and matching prospective cfg required')
        position = self.scene['box'].data.root_pos_w
        if position.shape != (self.num_envs, 3) or not bool(torch.isfinite(position).all()):
            raise ValueError('Actual finite current selected pose required for new attempt')
        goal = position.clone()
        goal[:, 0] += distance_m
        if goal_xy_m is not None:
            if len(goal_xy_m)!=2 or not all(type(v) in (int,float) and math.isfinite(v) for v in goal_xy_m):
                raise ValueError('Explicit finite public absolute goal required')
            goal[:,0]=goal_xy_m[0];goal[:,1]=goal_xy_m[1]
        self.box_push_target = goal
        self.box_push_declared_attempt = dict(declaration_id=declaration_id, distance_m=distance_m)
        return dict(actual_position_w=position.tolist(), target_position_w=goal.tolist(),
                    declaration_id=declaration_id, declared_push_distance_m=distance_m,
                    physical_state_changed=False, global_cfg_changed=False,
                    original_world_x_goal_rule_preserved=goal_xy_m is None, public_absolute_goal_xy_bound=goal_xy_m is not None, physics_admission=False)

    def receipt(self):
        return dict(schema='explicit-native-target-context-v1',model_input_allowed=False,
            candidate=self.candidate,actual_scene_body_key=self.body_key,scene_aliases_modified=False,
            actual_world_origins_preserved=True,old_target_software_state_inherited=False,
            actuator_or_physical_history_reset=False,SDK_or_controller_or_handoff_certified=False)
