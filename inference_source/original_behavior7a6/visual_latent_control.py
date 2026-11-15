"""M64 control successor: public declared actions and causal body/task context.

Retains M's RGBD encoder, h256/z64 and native history filter. Explicit new
contract uses the executor's declared WORLD goals, never mislabeled body goals.
The mean is public constant-velocity plus a learned action-conditioned residual.
Selected-box XYZ and robot XYZ are LABELS, not encoder inputs. Old4 fields stay
first; new fields add lateral robot and vertical box motion. Original risk heads
remain unsupervised and are NOT used for selection.
"""
from dataclasses import asdict,replace
import hashlib,json,math
import torch
from torch import nn
from torch.nn import functional as F
from visual_latent_highres import HighResolutionM,load_highres_checkpoint,highres_config
from visual_latent_world_model import Belief,config_fingerprint

ARCHITECTURE_ID='piper-M64-declared21-public77-residualXYZ-v2'
CHECKPOINT_FORMAT='piper-M64-declared-action-checkpoint-v2'
MACROS=('WAIT','PUSH_A','RECOVER_A','NAV_B','PUSH_B','NAV_STEP','CLIMB_STEP','NAV_HIGH','CLIMB_HIGH','NAV_C','PUSH_C','NAV_BRIDGE','CLIMB_BRIDGE','NAV_FAR','BRAKE_FAR')
FIELDS=('box_dx_anchor_body_m','box_dy_anchor_body_m','robot_dx_anchor_body_m','robot_dz_anchor_body_m','robot_dy_anchor_body_m','box_dz_anchor_body_m')
CONTRACT=dict(version='public-declared21-body-task77-v2',declared20='15 named macro onehot, declared world goalXY/10, declared surface height, push distance, requested prediction interval from actual duration argument (exported0.1 is only nominal metadata)',
    extra_action='NAV_STEP known world-X bias relative0.05m divided0.02m;0 outside NAV_STEP',
    context='Public69 current body/task/observed-macro state plus separate8 current-image geometry for the prospective target; observed macro never overwritten',
    maximum_query_image_age_s=.101,private_inputs=False,fields=FIELDS,displacement_std_floor_m=.002,displacement_start='latest real image acquisition; decision clock may be20ms later; horizon durations use the actual decision clock',mean='public body velocity in real-anchor axes times duration plus learned residual',
    events='Original support/hard-stop unsupervised; separate public-declaration-exit head is NOT mechanical success or risk')
CONTRACT_SHA=hashlib.sha256(json.dumps(CONTRACT,sort_keys=True).encode()).hexdigest()


def encode_declared(raw):
    if raw.ndim!=2 or raw.shape[-1]!=20 or not torch.isfinite(raw).all():raise ValueError('Finite public declared20 required')
    mode=raw[:,:15]
    if not (((mode==0)|(mode==1)).all() and (mode.sum(-1)==1).all()):raise ValueError('Exactly one known declared macro')
    scaled=raw.clone();scaled[:,15:17]*=10
    scaled[:,15]/=5;scaled[:,16]/=3;scaled[:,17]/=.6;scaled[:,18]/=.6;scaled[:,19]/=.1
    bias=(raw[:,15]*10-.05)/.02*mode[:,5]
    return torch.cat((scaled,bias[:,None]),-1)


def normalize_context(public69,geometry8,normalization):
    if public69.ndim!=2 or public69.shape[-1]!=69 or geometry8.shape!=(len(public69),8):raise ValueError('Separate current public69 and prospective target8 required')
    if not torch.isfinite(public69).all() or not torch.isfinite(geometry8).all():raise ValueError('Finite public context required')
    p=public69.clone();p[:,:45]=(p[:,:45]-p.new_tensor(normalization['mean']))/p.new_tensor(normalization['std'])
    p[:,60]/=30
    for x in (p[:,61:69],geometry8.clone()):
        if not (((x[:,-1]==0)|(x[:,-1]==1)).all()):raise ValueError('Explicit geometry validity required')
    p[:,64:66]/=3;p[:,66]/=.005
    g=geometry8.clone();g[:,3:5]/=3;g[:,5]/=.005
    return torch.cat((p,g),-1)


class ControlM(HighResolutionM):
    def __init__(self):
        super().__init__();self.architecture_id=ARCHITECTURE_ID;self.profile_name='M64C'
        self.macro_action=nn.Sequential(nn.Linear(21,64),nn.SiLU())
        self.public_context=nn.Sequential(nn.Linear(77,256),nn.SiLU(),nn.Linear(256,256),nn.Tanh())
        nn.init.zeros_(self.public_context[2].weight);nn.init.zeros_(self.public_context[2].bias)
        self.consequences[-1]=nn.Linear(128,14)
        with torch.no_grad():
            self.consequences[-1].weight[:12].zero_();self.consequences[-1].bias[:6].zero_()
            self.consequences[-1].bias[6:12].fill_(math.log(math.expm1(.05)))
        self.declaration_exit=nn.Sequential(nn.Linear(320,64),nn.SiLU(),nn.Linear(64,1))

    def decode_consequences(self,state):
        raise ValueError('Use predict_declared to include the public-velocity baseline')

    def _decode_residual(self,state):
        self._validate_state(state);raw=self.consequences(state.features)
        return dict(mean=raw[:,:6],std=(F.softplus(raw[:,6:12])+.002).clamp(max=5.),event_logits=raw[:,12:14])

    def imagine_candidates(self,*args,**kwargs):
        raise ValueError('Control successor requires predict_declared(public20,public69,target8), not the old body-goal8 contract')

    def predict_declared(self,query,public69,target8,declared20,duration_s,normalization):
        b=self._validate_state(query)
        if (not query.has_observation.all() or declared20.ndim!=3 or declared20.shape[0]!=b or declared20.shape[-1]!=20):raise ValueError('Observed query and public candidates[B,N,20] required')
        n=declared20.shape[1]
        if not 1<=n<=8 or public69.shape!=(b,69) or target8.shape!=(b,n,8) or duration_s.shape!=(b,n):raise ValueError('Candidate/context shapes differ')
        if not torch.isfinite(duration_s).all() or (duration_s<=0).any() or (duration_s>2.01).any():raise ValueError('Training-supported positive horizon<=2s required')
        if ((query.time_s-query.anchor_time_s)<-1e-6).any() or ((query.time_s-query.anchor_time_s)>.101).any():raise ValueError('Current image/body anchor too old')
        repeated=Belief(**{k:getattr(query,k).repeat_interleave(n,0) for k in query.__dataclass_fields__})
        context=normalize_context(public69.repeat_interleave(n,0),target8.reshape(b*n,8),normalization)
        repeated=replace(repeated,h=repeated.h+self.public_context(context))
        requested=declared20.reshape(b*n,20).clone()
        requested[:,19]=duration_s.reshape(-1)
        action=self.macro_action(encode_declared(requested))
        prior=self._advance(repeated,action,duration_s.reshape(-1),(0.,1.),False)
        out=self._decode_residual(prior)
        # Public body velocity -> fixed last-real-image axes. Only the registered
        # boundary queries have a<=20ms body/image offset. Constant-gyro rotation
        # uses public angular rates, never a private orientation/pose.
        velocity=public69[:,42:45];omega=public69[:,39:42]
        age=(query.time_s-query.anchor_time_s).float();rot=omega*age[:,None]
        cross=lambda a,c:torch.cross(a,c,dim=-1)
        angle=rot.norm(dim=-1,keepdim=True);a=torch.sinc(angle/torch.pi);coef=.5*torch.sinc(angle/(2*torch.pi)).square()
        velocity=velocity+a*cross(rot,velocity)+coef*cross(rot,cross(rot,velocity))
        span=duration_s+age[:,None]
        cv=velocity.repeat_interleave(n,0)*span.reshape(-1,1)
        baseline=out['mean'].new_zeros((b*n,6));baseline[:,2]=cv[:,0];baseline[:,3]=cv[:,2];baseline[:,4]=cv[:,1]
        out['mean']=out['mean']+baseline
        out['declaration_exit_logits']=self.declaration_exit(prior.features).squeeze(-1)
        return {k:v.reshape(b,n,*v.shape[1:]) for k,v in out.items()},prior

    def checkpoint_payload(self,training_updates=0):
        payload=super().checkpoint_payload(training_updates)
        payload.update(checkpoint_format=CHECKPOINT_FORMAT,contract_sha256=CONTRACT_SHA,displacement_fields=list(FIELDS),
            macro_branch_trained=training_updates>0,training_stage='declared-action-residual-world-model-v1',
            displacement_std_floor_m=.002,physical_control_admitted=False,event_heads_supervised=False)
        return payload


def build_control_m(parent=None):
    model=ControlM()
    if parent is not None:
        old=load_highres_checkpoint(parent)
        copied={k:v for k,v in old.state_dict().items() if not k.startswith(('macro_action.','consequences.2.'))}
        missing,unexpected=model.load_state_dict(copied,strict=False)
        if unexpected or any(not k.startswith(('macro_action.','public_context.','consequences.2.','declaration_exit.')) for k in missing):raise ValueError('Unexpected parent transfer mismatch')
        with torch.no_grad():
            model.consequences[-1].weight[12:].copy_(old.consequences[-1].weight[8:]);model.consequences[-1].bias[12:].copy_(old.consequences[-1].bias[8:])
    return model


def load_control_checkpoint(payload):
    if (not isinstance(payload,dict) or payload.get('checkpoint_format')!=CHECKPOINT_FORMAT
        or payload.get('architecture_id')!=ARCHITECTURE_ID or payload.get('profile')!='M64C'
        or payload.get('contract_sha256')!=CONTRACT_SHA or payload.get('config')!=asdict(highres_config())
        or payload.get('config_sha256')!=config_fingerprint(highres_config()) or payload.get('displacement_fields')!=list(FIELDS)
        or payload.get('displacement_std_floor_m')!=.002 or payload.get('physical_control_admitted') is not False
        or type(payload.get('training_updates')) is not int or payload['training_updates']<=0 or payload.get('macro_branch_trained') is not True):
        raise ValueError('Trained declared-action checkpoint/contract mismatch')
    model=build_control_m();model.load_state_dict(payload['state_dict'],strict=True);return model


def upgrade_control_v1(payload):
    """Explicit transfer from the retained underfit first control checkpoint."""
    if (payload.get('architecture_id')!='piper-M64-declared21-public77-residualXYZ-v1'
        or payload.get('checkpoint_format')!='piper-M64-declared-action-checkpoint-v1'
        or payload.get('contract_sha256')!='16358853a42bc832a7a7869cc947e3070e1561d5352e99d6034e84573eafdae4'
        or payload.get('training_updates',0)<=0):raise ValueError('Explicit compatible control-v1 source required')
    model=build_control_m();model.load_state_dict(payload['state_dict'],strict=True);return model
