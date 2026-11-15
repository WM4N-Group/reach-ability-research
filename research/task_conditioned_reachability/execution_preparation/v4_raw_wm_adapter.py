"""Actual frozen BehaviorM.predict_behavior bridge; never create a world/Actor.

Owner supplies the ALREADY LOADED original7a6 eval model, original normalization
and causal sensor/issued-history query provider. No synthetic/padded history or
checkpoint migration is performed here. New V4-context outputs are explicitly
uncalibrated raw responses, not proven successful-Finish or full-chain effects.
Missing absolute-PUSH->relative-action11 and CLIMB approach mappings stay UNKNOWN.
"""
import hashlib
import math
from pathlib import Path
from .v4_successor_choice import need

CHECKPOINT_SHA = '7a6ba61e89d824cd3e0a78f469a0925f91c784ab1f77ed4273365d6c313f569c'
SKILLS = ('NAV','PUSH','CLIMB','EXIT_PUSH','RECOVER','HOLD')


def public_action11(option):
    """Exact original public ABI only, no guessed world pose or standoff channel."""
    p=dict(option.parameters)
    if option.skill not in ('NAV','PUSH','CLIMB','HOLD'):
        return None, 'NATIVE_PROTECTION_OR_UNQUALIFIED_EXIT_NOT_A_MODEL_CANDIDATE'
    required = {'surface_height_m'}
    if option.skill in ('NAV','CLIMB'):
        required |= {'goal_world_x_m','goal_world_y_m'}
    if option.skill == 'PUSH': required |= {'push_distance_m'}
    if not required <= set(p):
        return None, ('ABSOLUTE_PUSH_HAS_NO_CAUSAL_PUBLIC_RELATIVE_ACTION11_MAPPING' if option.skill=='PUSH'
                      else 'CLIMB_OR_NAV_HAS_NO_REGISTERED_PUBLIC_APPROACH_XY')
    if not all(type(p[k]) in (int,float) and math.isfinite(p[k]) for k in required):
        raise ValueError('Original finite declared WM action parameters only')
    need(option.skill!='PUSH' or p['push_distance_m']>0, 'Positive original relative PUSH distance')
    # Extra absolute goals cannot be silently dropped when mapping relative PUSH.
    if option.skill=='PUSH' and ('goal_world_x_m' in p or 'goal_world_y_m' in p):
        return None, 'MIXED_ABSOLUTE_AND_RELATIVE_PUSH_NEEDS_ORIGINAL_SOURCE_MAPPING'
    if any(k not in required | {'requested_interval_s'} for k in p):
        return None, 'UNSUPPORTED_ADDITIONAL_ACTION_PARAMETER_NOT_SILENTLY_IGNORED'
    action=[0.]*11;action[SKILLS.index(option.skill)]=1.
    if option.skill in ('NAV','CLIMB'): action[6:8]=[p['goal_world_x_m']/10.,p['goal_world_y_m']/10.]
    action[8]=p['surface_height_m'];action[9]=p.get('push_distance_m',0.)
    action[10]=p.get('requested_interval_s',.1)
    need(type(action[10]) in (int,float) and math.isfinite(action[10]) and 0<action[10]<=60,
         'Original declared bounded interval')
    return tuple(action), None


class OriginalBehaviorWMAdapter:
    def __init__(self, model, normalization, *, checkpoint_path, loaded_checkpoint_sha256, query_provider):
        path=Path(checkpoint_path)
        need(path.is_file() and not path.is_symlink(), 'Explicit existing remote checkpoint, no automatic download')
        h=hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
        need(h.hexdigest()==loaded_checkpoint_sha256==CHECKPOINT_SHA, 'Same actually loaded original7a6 weights')
        need(getattr(model,'training',True) is False and callable(getattr(model,'predict_behavior',None)),
             'Original frozen eval BehaviorM, no training')
        self.model=model;self.normalization=normalization;self.provider=query_provider
        self.forward_batches=0

    @classmethod
    def from_checkpoint(cls, checkpoint_path, *, source_root, query_provider):
        """Owner calls once in a fresh qualified run; no synthetic query fallback."""
        from .v4_original_wm_loader import restore_original_cpu
        model,normalization,report=restore_original_cpu(checkpoint_path,source_root=source_root)
        adapter=cls(model,normalization,checkpoint_path=checkpoint_path,
                    loaded_checkpoint_sha256=report['checkpoint_sha256'],query_provider=query_provider)
        adapter.restore_report=report
        return adapter

    def evaluate(self,batch):
        from ainav.intents import IntentBatch
        need(isinstance(batch,IntentBatch),'Public semantic WM candidates only, not private ExecutionBatch')
        actions=[];supported=[];unknown=[]
        need(1<=len(batch.options)<=128, 'Same finite source candidate capability; do not drop roots')
        for option in batch.options:
            action,reason=public_action11(option)
            if action is None:
                unknown.append(dict(option_sha256=option.sha256,status='UNKNOWN',reason=reason))
            else:
                actions.append(action);supported.append(option)
        base=dict(query_sha256=batch.sha256,checkpoint_sha256=CHECKPOINT_SHA,
                  actual_model_forward_batches=0,known_raw_predictions=0,unknown=unknown,raw=[],
                  output_scope='UNCALIBRATED_RAW_NATIVE_EVENT_RESPONSE_NOT_SUCCESSFUL_FINISH',
                  successful_Finish_cost_s=None,successor_READY=None,success_probability=None,
                  world_exit_pose=None,native_admission_or_safety=False)
        if not supported: return base
        # Provider MUST link original live query/actual native-history to the same
        # public observation. This interface alone is NOT its native qualification.
        context=self.provider(batch,tuple(supported))
        need(context['public_observation_sha256']==batch.observation.sha256 and
             context['query_time_s']==batch.observation.time_s and
             isinstance(context['original_query_sha256'],str) and len(context['original_query_sha256'])==64,
             'Original causal query bound to THIS public observation')
        age=context['query_time_s']-context['image_time_s']
        need(0<=age<=.101 and context['source_role']=='CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY',
             'No stale/imagined/audit query or padded history')
        import torch
        device=self.model.device
        public=torch.as_tensor(context['public60'],device=device,dtype=torch.float32)
        need(tuple(public.shape)==(60,), 'Unchanged current public60, not candidate-overwritten observed mode')
        targets=context['target8_by_option_sha256'];records=[];actual_batches=0
        need(set(targets)=={o.sha256 for o in supported}, 'Each current candidate has a separate original target8')
        valid_options=[];valid_actions=[]
        for option,action in zip(supported,actions):
            raw_target=targets[option.sha256]
            if raw_target is None:
                unknown.append(dict(option_sha256=option.sha256,status='UNKNOWN',reason='CURRENT_TARGET8_UNAVAILABLE'))
                continue
            target=torch.as_tensor(raw_target,device=device,dtype=torch.float32)
            need(tuple(target.shape)==(8,) and bool(torch.isfinite(target).all()) and
                 float(target[7]) in (0.,1.), 'Original explicit target8 validity, no imputation')
            if float(target[7])==0.:
                unknown.append(dict(option_sha256=option.sha256,status='UNKNOWN',reason='CURRENT_TARGET8_MASKED_UNRESOLVED'))
                continue
            valid_options.append(option);valid_actions.append(action)
        supported=valid_options;actions=valid_actions
        for start in range(0,len(supported),16):
            opts=supported[start:start+16];a=actions[start:start+16]
            target=torch.as_tensor([targets[o.sha256] for o in opts],device=device,dtype=torch.float32)
            need(tuple(target.shape)==(len(opts),8) and bool(torch.isfinite(target).all()) and
                 bool((target[:,7]==1).all()), 'Observed target8 required; missing geometry cannot become zeros')
            durations=torch.as_tensor([[o.budget_s for o in opts]],device=device,dtype=torch.float32)
            with torch.inference_mode():
                prediction,_ = self.model.predict_behavior(context['belief'],public[None],target[None],
                    torch.as_tensor([a],device=device,dtype=torch.float32),durations,self.normalization,terminal=True)
            actual_batches+=1;self.forward_batches+=1
            expected={'mean','std','elapsed_s','elapsed_std_s','option_success_logits'}
            need(set(prediction)==expected and all(bool(torch.isfinite(v).all()) for v in prediction.values()),
                 'Exact actual finite raw original WM heads')
            need(tuple(prediction['mean'].shape)==tuple(prediction['std'].shape)==(1,len(opts),6), 'Original six translations, not6D pose')
            for i,option in enumerate(opts):
                row={k:v[0,i].detach().cpu().tolist() for k,v in prediction.items()}
                need(all(x>0 for x in row['std']) and row['elapsed_s']>0 and row['elapsed_std_s']>0,
                     'Raw model dispersion/time, not calibrated uncertainty')
                records.append(dict(option_sha256=option.sha256,original_query_sha256=context['original_query_sha256'],
                    actual_action11=list(a[i]),raw_anchor_translation6_m=row['mean'],raw_learned_std6_m=row['std'],
                    raw_native_success_or_failure_event_elapsed_s=row['elapsed_s'],raw_elapsed_std_s=row['elapsed_std_s'],
                    raw_uncalibrated_option_success_logit=row['option_success_logits'],
                    successful_Finish_or_READY_unsupported=True))
        base.update(actual_model_forward_batches=actual_batches,known_raw_predictions=len(records),raw=records)
        return base
