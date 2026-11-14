"""Causal task-skill vocabulary; input is declared intent, never recorded future PD.

Known task-map/waypoint instructions are explicit common inputs. This is not an
unknown-map or hidden-physics estimator. Phase labels describe commands that were
already issued by the training executor, not what an online planner should pick.
"""
import math,json,hashlib
VOCAB=('WAIT','PUSH_A','RECOVER_A','NAV_B','PUSH_B','NAV_STEP','CLIMB_STEP','NAV_HIGH','CLIMB_HIGH','NAV_C','PUSH_C','NAV_BRIDGE','CLIMB_BRIDGE','NAV_FAR','BRAKE_FAR')
ACTION_SCHEMA={'version':'task-declared-skill-intent-v1','onehot':list(VOCAB),'tail':['declared_goal_world_x_over10','declared_goal_world_y_over10','declared_goal_world_z','declared_push_distance_m','requested_prediction_interval_s'],'hidden_mass_or_friction':False,'future_recorded_motor_commands':False,'known_static_task_map':True}
SCHEMA_SHA256=hashlib.sha256(json.dumps(ACTION_SCHEMA,sort_keys=True).encode()).hexdigest()
class IntentError(ValueError):pass

def encode_intent(name,goal_xyz=(0,0,0),push_distance=0.,interval_s=.1):
 if name not in VOCAB or len(goal_xyz)!=3:raise IntentError('Unknown skill intent/goal shape')
 vals=[*goal_xyz,push_distance,interval_s]
 if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in vals) or interval_s<=0:raise IntentError('Finite declared parameters required')
 out=[0.]*len(VOCAB);out[VOCAB.index(name)]=1.
 return out+[float(goal_xyz[0])/10,float(goal_xyz[1])/10,float(goal_xyz[2]),float(push_distance),float(interval_s)]

class CausalPhaseDecoder:
 """Stateful decoder consumes control rows in order; no future row lookup."""
 patterns={'B_STEP_HIGH_PLATFORM':(('nav','NAV_STEP'),('climb','CLIMB_STEP'),('nav','NAV_HIGH'),('climb','CLIMB_HIGH'),('nav','NAV_C')),'BRIDGE_CLIMB_AND_CROSS':(('nav','NAV_BRIDGE'),('climb','CLIMB_BRIDGE'),('nav','NAV_FAR'))}
 def __init__(self):self.time=-1.;self.stage=None;self.index=-1;self.last_kind=None
 def push(self,row):
  t=float(row['time_s'])
  if t<=self.time:raise IntentError('Control rows must increase in time')
  self.time=t;phase=row['phase'];kind=row['skill'];stage,_,suffix=phase.partition('/')
  if stage!=self.stage:self.stage=stage;self.index=-1;self.last_kind=None
  if stage=='A_FAIL_RECOVER_RESELECT_B':
   if suffix.startswith('B_PUSH'):return 'PUSH_B'
   if suffix.startswith('ARRIVAL_') or suffix=='RESUME_NAV':return 'NAV_B'
   if suffix in ['UNLOAD_CAPTURE','PROTECTED_STOW','STOW_VERIFY','COMPACT_READY_CAPTURE']:return 'RECOVER_A'
   if kind=='startup':return 'WAIT'
   if kind=='push' and suffix in ['prepare','blend','run']:return 'PUSH_A'
   raise IntentError('Unmapped A-prefix declaration: '+phase)
  if stage in self.patterns:
   pattern=self.patterns[stage]
   if kind!=self.last_kind:self.index+=1;self.last_kind=kind
   if self.index>=len(pattern) or kind!=pattern[self.index][0]:raise IntentError('Native task order differs from pinned declaration')
   return pattern[self.index][1]
  if stage=='C_BRIDGE_PUSH_STOW':
   if kind!='push':raise IntentError('C push declaration differs')
   return 'PUSH_C'
  if stage=='FAR_BANK_BRAKE':return 'BRAKE_FAR'
  if stage=='FAR_BANK_COMPLETE':return 'WAIT'
  raise IntentError('Unmapped current declared task stage: '+stage)

def declared_goal(name,case,layout):
 lane=case['lane_y_m'];g=layout(case)
 targets={'PUSH_A':(1.7,0,.1),'NAV_B':(-.08,lane,0),'PUSH_B':(g['step_initial_center']+.6,lane,.1),'NAV_STEP':(g['step_docked_front']-1.05,lane,0),'CLIMB_STEP':(g['step_docked_front']-1.05,lane,.2),'NAV_HIGH':(g['high_front']-.95,lane,.2),'CLIMB_HIGH':(g['high_front']-.95,lane,.4),'NAV_C':(g['bridge_initial_front']-.58,lane,.4),'PUSH_C':(g['bridge_initial_center']+.6,lane,.5),'NAV_BRIDGE':(g['bridge_initial_front']+.6-1.05,lane,.4),'CLIMB_BRIDGE':(g['bridge_initial_front']+.6-1.05,lane,.6),'NAV_FAR':(g['finish_x'],lane,.6),'BRAKE_FAR':(g['finish_x'],lane,.6)}
 return targets.get(name,(0.,0.,0.))
