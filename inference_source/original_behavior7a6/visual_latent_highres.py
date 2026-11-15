"""Explicit64x96 decoder successor of M; historical S/M formats stay intact.

Only observation_decoder changes. The body/box consequence heads, encoders,
latent state and dynamics retain the original M shapes and values on transfer.
This profile does not imply that a source's untrained macro branch is usable.
"""
from dataclasses import asdict,replace
import torch
from torch import nn
from visual_latent_world_model import (VisualLatentWorldModel,model_config,
    config_fingerprint,load_profile_checkpoint)

ARCHITECTURE_ID='piper-visual-latent-rssm-M-rgbd64x96-v1'
CHECKPOINT_FORMAT='piper-visual-latent-highres-checkpoint-v1'
DECODER_ID='linear-grid4x6-convtranspose-four-stages-v1'


def highres_config():
    return replace(model_config('M'),reconstruction_height=64,reconstruction_width=96)


class HighResolutionM(VisualLatentWorldModel):
    def __init__(self):
        super().__init__(highres_config())
        self.architecture_id=ARCHITECTURE_ID;self.profile_name='M64'
        self.observation_decoder=nn.Sequential(
            nn.Linear(320,96*4*6),nn.SiLU(),nn.Unflatten(1,(96,4,6)),
            nn.ConvTranspose2d(96,64,4,2,1),nn.SiLU(),
            nn.ConvTranspose2d(64,48,4,2,1),nn.SiLU(),
            nn.ConvTranspose2d(48,32,4,2,1),nn.SiLU(),
            nn.ConvTranspose2d(32,5,4,2,1))

    def checkpoint_payload(self,training_updates=0):
        result=super().checkpoint_payload(training_updates)
        result.update(checkpoint_format=CHECKPOINT_FORMAT,decoder_id=DECODER_ID,
            macro_branch_trained=False,event_heads_supervised=False,
            physical_control_admitted=False,training_stage='decoder-only-64x96-v1')
        return result


def build_highres_m(parent_payload=None):
    model=HighResolutionM()
    if parent_payload is not None:
        parent=load_profile_checkpoint(parent_payload,'M')
        copied={k:v for k,v in parent.state_dict().items() if not k.startswith('observation_decoder.')}
        missing,unexpected=model.load_state_dict(copied,strict=False)
        if unexpected or any(not k.startswith('observation_decoder.') for k in missing):raise ValueError('Unexpected M transfer mismatch')
    return model


def load_highres_checkpoint(payload):
    config=highres_config()
    if (not isinstance(payload,dict) or payload.get('checkpoint_format')!=CHECKPOINT_FORMAT
        or payload.get('architecture_id')!=ARCHITECTURE_ID or payload.get('profile')!='M64'
        or payload.get('decoder_id')!=DECODER_ID or payload.get('config')!=asdict(config)
        or payload.get('config_sha256')!=config_fingerprint(config)
        or type(payload.get('training_updates')) is not int or payload['training_updates']<0
        or payload.get('physical_control_admitted') is not False
        or payload.get('macro_branch_trained') is not False):
        raise ValueError('High-resolution checkpoint/version mismatch')
    model=build_highres_m();model.load_state_dict(payload['state_dict'],strict=True)
    return model
