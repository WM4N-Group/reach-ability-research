"""Causal public-input gateway for future integrated-course model decisions.

The existing rollout router is NOT wired here. This module cannot step/reset,
read a scene, create native targets, or claim task completion. The executor owns
legal candidate admission and opaque-token resolution after model selection.
"""
import hashlib,json,math
import numpy as np

PUBLIC_HISTORY_KEYS=frozenset(('rgb','depth_m','camera_K','T_base_optical','proprio','actions_previous','action_valid','timestamps_s'))
HISTORY_KEYS=frozenset(('observations','issued_commands','physical_ticks','command_times_s'))
QUERY_KEYS=frozenset(('history','candidate_tokens','macro_intents','durations_s','anchor_time_s','decision_id'))
INTENT_FIELDS=('NAV','PUSH','CLIMB','goal_body_x_m','goal_body_y_m','target_pixel_u_normalized','target_pixel_v_normalized','original_total_PUSH_distance_m')
RESPONSE_KEYS=frozenset(('selected_token','candidate_costs','model_checkpoint_sha256'))

def _array(value,shape=None,finite=True):
    if not isinstance(value,np.ndarray) or (shape is not None and value.shape!=shape):raise ValueError('Exact numpy public array shape required')
    if finite and not np.isfinite(value).all():raise ValueError('Finite public array required')
    return value


def validate_history(history,anchor):
    if not isinstance(history,dict) or set(history)!=HISTORY_KEYS:raise ValueError('Public observation/actual PAST issued-command arrays only')
    obs=history['observations']
    if not isinstance(obs,dict) or set(obs)!=PUBLIC_HISTORY_KEYS:raise ValueError('Exactly eight public observation channels required')
    rgb=_array(obs['rgb']);
    if rgb.dtype!=np.uint8 or rgb.ndim!=5 or rgb.shape[0]!=1 or rgb.shape[-1]!=3:raise ValueError('Actual RGB history [1,T,H,W,3] required')
    _,t,h,w,_=rgb.shape
    if not t or not h or not w:raise ValueError('Nonempty public history required')
    _array(obs['depth_m'],(1,t,h,w,1),finite=False)
    if np.isinf(obs['depth_m']).any():raise ValueError('Metric depth invalid pixels must use NaN, never infinity')
    _array(obs['camera_K'],(1,3,3));_array(obs['T_base_optical'],(1,4,4))
    _array(obs['proprio'],(1,t,45));_array(obs['actions_previous'],(1,t,18))
    flags=_array(obs['action_valid'],(1,t));times=_array(obs['timestamps_s'],(1,t))
    if flags.dtype!=np.bool_ or np.any(np.diff(times[0])<=0) or abs(float(times[0,-1])-anchor)>1e-7:raise ValueError('Anchor must be the latest actually acquired visual timestamp')
    physical=times[0]/.005
    if not np.allclose(physical,np.rint(physical),rtol=0,atol=1e-6):raise ValueError('Actual physics clock timestamps required')
    if not np.array_equal(flags[0],times[0]>0) or np.any(obs['actions_previous'][~flags]!=0):raise ValueError('Actual previous-action validity required')
    commands=_array(history['issued_commands']);ticks=_array(history['physical_ticks']);ctimes=_array(history['command_times_s'])
    first=int(round(times[0,0]/.005));last=int(round(anchor/.005));n=last-first
    if commands.shape!=(n,5,18) or ticks.shape!=(n,) or ctimes.shape!=(n,):raise ValueError('Complete PAST command intervals between public frames required')
    if ticks.dtype.kind not in 'iu' or not np.array_equal(ticks,np.arange(first+1,last+1)):raise ValueError('Consecutive actual command ticks required; no future prefix/gaps')
    if not np.allclose(ctimes,ticks*.005,rtol=0,atol=1e-7):raise ValueError('Command times must be actual and no later than image anchor')
    for i,stamp in enumerate(times[0]):
        index=int(round(stamp/.005))-first-1
        if index>=0 and not np.allclose(obs['actions_previous'][0,i],commands[index,0],rtol=0,atol=2e-6):raise ValueError('Image last-issued action differs from full actual history')
    return t


def validate_query(query):
    if not isinstance(query,dict) or set(query)!=QUERY_KEYS:raise ValueError('No private object ID, mass, future motor outputs, outcomes or engine metadata in model query')
    anchor=query['anchor_time_s']
    if type(anchor) not in (int,float) or not math.isfinite(anchor) or anchor<0:raise ValueError('Finite observed anchor required')
    validate_history(query['history'],anchor)
    tokens=query['candidate_tokens']
    if not isinstance(tokens,tuple) or not tokens or len(set(tokens))!=len(tokens) or any(not isinstance(x,str) or not x for x in tokens):raise ValueError('Unique executor-issued opaque candidate tokens required')
    n=len(tokens);intents=_array(query['macro_intents'],(n,8));durations=_array(query['durations_s'],(n,))
    if np.any(durations<=0) or np.any(durations>5):raise ValueError('Declared bounded candidate duration required')
    for row in intents:
        if not any(np.array_equal(row[:3],one) for one in np.eye(3)):raise ValueError('Exactly one NAV/PUSH/CLIMB intent required')
        if np.any(row[5:7]<0) or np.any(row[5:7]>=1):raise ValueError('Normalized current-image target pixels required')
        if row[1]==1 and float(query['history']['observations']['timestamps_s'][0,0])!=0.:raise ValueError('Original-total PUSH requires real task-reset-to-query observation context; no rebased goal')
        if row[1]==1 and (np.any(row[3:5]!=0) or not math.isclose(float(row[7]),.6,abs_tol=1e-7)):
            raise ValueError('PUSH continues original0.6m task, never resets its remaining goal')
        if row[1]!=1 and row[7]!=0:raise ValueError('Non-PUSH distance field must be zero')
    if not isinstance(query['decision_id'],str) or not query['decision_id']:raise ValueError('Unique decision identity required')
    return query


def query_sha(query):
    validate_query(query);h=hashlib.sha256()
    def add(value):
        if isinstance(value,np.ndarray):
            h.update(str(value.dtype).encode());h.update(str(value.shape).encode());h.update(np.ascontiguousarray(value).tobytes())
        elif isinstance(value,dict):
            for key in sorted(value):h.update(key.encode());add(value[key])
        else:h.update(json.dumps(value,sort_keys=True).encode())
    add(query);return h.hexdigest()

class DecisionGateway:
    """Require model selection, journal it, then explicitly acknowledge execution.

    Single-candidate decisions are valid wiring checks, not selection/planning
    evidence. No fallback is returned for missing/invalid model responses.
    """
    def __init__(self,selector,journal):
        self.selector=selector;self.journal=journal;self.pending=None;self.seen=set()
    def request(self,query):
        digest=query_sha(query);decision=query['decision_id']
        if self.pending is not None or decision in self.seen:raise ValueError('Prior decision unacknowledged or duplicate request')
        result=self.selector(query)
        if query_sha(query)!=digest:raise ValueError('Model callback mutated frozen public observation/candidate query')
        if not isinstance(result,dict) or set(result)!=RESPONSE_KEYS:raise ValueError('Explicit model response required, no fixed-answer fallback')
        tokens=query['candidate_tokens'];costs=result['candidate_costs'];selected=result['selected_token'];checkpoint=result['model_checkpoint_sha256']
        if not isinstance(costs,dict) or set(costs)!=set(tokens) or any(type(x) not in (int,float) or not math.isfinite(x) for x in costs.values()):raise ValueError('Model must provide finite costs for exactly the admitted candidates')
        if selected not in tokens or costs[selected]!=min(costs.values()):raise ValueError('Chosen token must minimize model candidate cost')
        if not isinstance(checkpoint,str) or len(checkpoint)!=64 or any(c not in '0123456789abcdef' for c in checkpoint):raise ValueError('Frozen model checkpoint SHA required')
        row=dict(event='model_decision',decision_id=decision,anchor_time_s=query['anchor_time_s'],query_sha256=digest,
            candidate_tokens=list(tokens),macro_intents=query['macro_intents'].tolist(),durations_s=query['durations_s'].tolist(),
            selected_token=selected,candidate_costs=dict(costs),model_checkpoint_sha256=checkpoint,
            single_candidate_only=len(tokens)==1,selection_benefit_claimed=False,actually_dispatched=False)
        self.journal(row);self.pending=row;self.seen.add(decision)
        return selected
    def acknowledge_dispatch(self,decision_id,actual_token,actual_time_s):
        row=self.pending
        if row is None or row['decision_id']!=decision_id or row['selected_token']!=actual_token:raise ValueError('Executor did not execute the selected model candidate')
        if type(actual_time_s) not in (int,float) or not math.isfinite(actual_time_s) or actual_time_s<row['anchor_time_s']:raise ValueError('Actual causal dispatch timestamp required')
        self.journal(dict(event='actual_model_choice_dispatched',decision_id=decision_id,actual_token=actual_token,actual_time_s=actual_time_s,
            query_sha256=row['query_sha256'],model_checkpoint_sha256=row['model_checkpoint_sha256'],native_success_inferred=False))
        self.pending=None
