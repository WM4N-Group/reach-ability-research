"""Small RGBD recurrent dynamics baseline; offline recorded-action prediction.

This is a task adaptation of our visual recurrent baseline, not an official
DINO-WM/Dreamer reproduction. No scene truth or future observations enter rollout.
"""
import argparse,fcntl,json,os,random,time
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader
from PIL import Image,ImageDraw
from .streams import sha,write_json
from .integrated_dataset import Windows

class RecurrentWorldModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder=nn.Sequential(nn.Conv2d(5,16,5,2,2),nn.SiLU(),nn.Conv2d(16,32,3,2,1),nn.SiLU(),
            nn.Conv2d(32,48,3,2,1),nn.SiLU(),nn.AdaptiveAvgPool2d((3,4)),nn.Flatten(),nn.Linear(48*12,128),nn.LayerNorm(128))
        self.action_encoder=nn.Sequential(nn.Linear(1800,128),nn.SiLU(),nn.Linear(128,128))
        self.posterior=nn.GRUCell(128+128+45+1,128)
        self.dynamics=nn.GRUCell(128+45,128)
        self.proprio_head=nn.Linear(128,45)
        nn.init.zeros_(self.proprio_head.weight);nn.init.zeros_(self.proprio_head.bias)
        self.image_seed=nn.Linear(128,64*8*12)
        self.decoder=nn.Sequential(nn.ConvTranspose2d(64,32,4,2,1),nn.SiLU(),nn.ConvTranspose2d(32,16,4,2,1),nn.SiLU(),nn.ConvTranspose2d(16,5,4,2,1))
    def forward(self,context_visual,context_proprio,actions,rollout_frames):
        b,c= context_visual.shape[:2]
        if context_visual.shape[2:]!=(5,64,96) or context_proprio.shape!=(b,c,45) or actions.shape!=(b,c-1+rollout_frames,1800):raise ValueError('Exact public context + full ordered action intervals required')
        encoded=self.encoder(context_visual.reshape(b*c,5,64,96)).reshape(b,c,128)
        ae=self.action_encoder(actions);hidden=encoded.new_zeros(b,128)
        for t in range(c):
            a=ae[:,t-1] if t else ae.new_zeros(b,128)
            flag=encoded.new_full((b,1),float(t>0))
            hidden=self.posterior(torch.cat((encoded[:,t],a,context_proprio[:,t],flag),-1),hidden)
        p=context_proprio[:,-1];images=[];props=[]
        for k in range(rollout_frames):
            hidden=self.dynamics(torch.cat((ae[:,c-1+k],p),-1),hidden)
            p=p+.1*torch.tanh(self.proprio_head(hidden))
            image=self.decoder(self.image_seed(hidden).reshape(b,64,8,12)).sigmoid()
            images.append(image);props.append(p)
        return torch.stack(images,1),torch.stack(props,1)


def transform(batch,stats,device):
    v=batch['visual'].to(device);p=batch['proprio'].to(device);a=batch['actions'].to(device)
    pm,ps,am,ass=stats
    return v,(p-pm)/ps,((a.reshape(*a.shape[:2],20,90)-am)/ass).reshape_as(a)


def loss_terms(pred_v,pred_p,target_v,target_p):
    rgb=(pred_v[:,:,:3]-target_v[:,:,:3]).square().mean()
    valid=target_v[:,:,4:5]
    depth=((pred_v[:,:,3:4]-target_v[:,:,3:4]).square()*valid).sum()/valid.sum().clamp_min(1)
    mask=F.binary_cross_entropy(pred_v[:,:,4:5].clamp(1e-6,1-1e-6),valid)
    proprio=(pred_p-target_p).square().mean()
    return dict(loss=rgb+25*depth+.05*mask+.2*proprio,rgb_mse=rgb,depth_mse_normalized=depth,depth_valid_bce=mask,proprio_mse_standardized=proprio)


def stats_tensors(d,device):
    n=d['normalization']
    return tuple(torch.tensor(n[k],dtype=torch.float32,device=device) for k in ('proprio_mean','proprio_std','action_mean','action_std'))


def evaluate(model,dataset,stats,device,output,split):
    cfg=dataset.cfg;c=cfg['context_frames'];f=cfg['rollout_frames'];horizons=[5,10,20];sums={}
    examples=[];model.eval()
    with torch.inference_mode():
        for batch in DataLoader(dataset,batch_size=8,shuffle=False,num_workers=0):
            v,p,a=transform(batch,stats,device);pv,pp=model(v[:,:c],p[:,:c],a,f);tv=v[:,c:];tp=p[:,c:]
            copy_v=v[:,c-1:c].expand_as(pv);copy_p=p[:,c-1:c].expand_as(pp)
            velocity=p[:,c-1]-p[:,c-2]
            linear_p=copy_p+velocity[:,None]*torch.arange(1,f+1,device=device)[None,:,None]
            for h in horizons:
                k=h-1;mask=tv[:,k,4:5];n=int(v.shape[0]);key=str(h/10);row=sums.setdefault(key,dict(windows=0,valid_depth_pixels=0.,rgb_squared=0.,copy_rgb_squared=0.,depth_abs=0.,copy_depth_abs=0.,proprio_squared=0.,copy_proprio_squared=0.,linear_proprio_squared=0.))
                row['windows']+=n;row['valid_depth_pixels']+=float(mask.sum())
                row['rgb_squared']+=float((pv[:,k,:3]-tv[:,k,:3]).square().mean((1,2,3)).sum())
                row['copy_rgb_squared']+=float((copy_v[:,k,:3]-tv[:,k,:3]).square().mean((1,2,3)).sum())
                row['depth_abs']+=float(((pv[:,k,3:4]-tv[:,k,3:4]).abs()*mask).sum())*15
                row['copy_depth_abs']+=float(((copy_v[:,k,3:4]-tv[:,k,3:4]).abs()*mask).sum())*15
                for name,pr in [('proprio_squared',pp),('copy_proprio_squared',copy_p),('linear_proprio_squared',linear_p)]:row[name]+=float((pr[:,k]-tp[:,k]).square().mean(1).sum())
            if len(examples)<3:
                examples.append((v[0,c-1].cpu().numpy(),pv[0].cpu().numpy(),tv[0].cpu().numpy(),batch['group'][0]))
    out={}
    for h,r in sums.items():
        n=r['windows'];out[h]=dict(windows=n,RGB_MSE=r['rgb_squared']/n,copy_RGB_MSE=r['copy_rgb_squared']/n,
            valid_depth_MAE_m=r['depth_abs']/max(1,r['valid_depth_pixels']),copy_valid_depth_MAE_m=r['copy_depth_abs']/max(1,r['valid_depth_pixels']),
            proprio_RMSE_standardized=(r['proprio_squared']/n)**.5,hold_proprio_RMSE_standardized=(r['copy_proprio_squared']/n)**.5,
            constant_velocity_proprio_RMSE_standardized=(r['linear_proprio_squared']/n)**.5)
    for i,(anchor,pred,true,group) in enumerate(examples):
        canvas=Image.new('RGB',(960,3*150+45),'#101820');draw=ImageDraw.Draw(canvas)
        draw.text((10,8),f'{split}: {group} | recorded-action conditional rollout; no future observations',fill='white')
        for j,k in enumerate([4,9,19]):
            y=40+j*150;draw.text((8,y+4),f'{(k+1)/10:.1f}s',fill='white')
            for col,(name,image) in enumerate([('COPY CURRENT',anchor),('MODEL PREDICTION',pred[k]),('ACTUAL FUTURE',true[k])]):
                rgb=np.clip(image[:3].transpose(1,2,0)*255,0,255).astype(np.uint8)
                canvas.paste(Image.fromarray(rgb).resize((240,128)),(65+col*290,y+17));draw.text((65+col*290,y),name,fill='white')
        canvas.save(Path(output)/f'{split}-prediction-{i}.png')
    return dict(split=split,horizons_seconds=out,windows=len(dataset),source_groups=sorted({k[2] for k in dataset.keys}),
        future_observations_used=False,condition='Actual recorded future issued 200Hz commands, all20 ordered substeps per10Hz interval; offline conditional prediction only')


def train(manifest,output,defer_evaluation=False):
    manifest=Path(manifest);d=json.loads(manifest.read_text());cfg=d['training'];output=Path(output)
    output.mkdir(exist_ok=False)
    lock=(output.parent/'integrated-world-model-training-gpu0.lock').open('a+')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if not torch.cuda.is_available():raise RuntimeError('Registered GPU training device unavailable')
    device=torch.device(cfg['device']);torch.set_num_threads(4)
    random.seed(cfg['seed']);np.random.seed(cfg['seed']);torch.manual_seed(cfg['seed']);torch.cuda.manual_seed_all(cfg['seed'])
    torch.backends.cudnn.benchmark=False
    source={p.name:sha(p) for p in (Path(__file__),Path(__file__).with_name('integrated_dataset.py'))}
    write_json(output/'training-freeze.json',dict(schema='integrated-world-model-training-freeze-v1',packed_manifest=str(manifest),packed_manifest_sha256=sha(manifest),
        source_sha256=source,configuration=cfg,optimizer_selection='fixed in collection plan before new physics',
        model_input='RGBD/proprio history, fixed calibrated sensor, ordered full issued commands; no catalogs/capsules/world state',
        source_groups_are_independent=True,test_loaded_after_checkpoint_freeze=True,bootstrap_only_training=True,
        model_type='Our small recurrent RGBD baseline; no official DINO-WM/Dreamer reproduction claim',WM_control=False))
    # Train split is the ONLY split loaded before the immutable checkpoint exists.
    dataset=Windows(manifest,'train');stats=stats_tensors(d,device)
    model=RecurrentWorldModel().to(device);optimizer=torch.optim.AdamW(model.parameters(),lr=cfg['learning_rate'],weight_decay=1e-4)
    loader=DataLoader(dataset,batch_size=cfg['batch_size'],shuffle=True,num_workers=0,drop_last=True)
    iterator=iter(loader);started=time.monotonic();last={};updates=0
    with (output/'training-log.jsonl').open('x') as log:
        for step in range(1,cfg['updates']+1):
            if time.monotonic()-started>cfg['max_wall_seconds']:break
            try:batch=next(iterator)
            except StopIteration:iterator=iter(loader);batch=next(iterator)
            v,p,a=transform(batch,stats,device);c=cfg['context_frames']
            model.train();pred_v,pred_p=model(v[:,:c],p[:,:c],a,cfg['rollout_frames'])
            terms=loss_terms(pred_v,pred_p,v[:,c:],p[:,c:])
            if not torch.isfinite(terms['loss']):raise RuntimeError('Nonfinite training loss')
            optimizer.zero_grad(set_to_none=True);terms['loss'].backward();torch.nn.utils.clip_grad_norm_(model.parameters(),10.);optimizer.step();updates=step
            if step==1 or step%50==0:
                last=dict(update=step,wall_seconds=time.monotonic()-started,**{k:float(x.detach()) for k,x in terms.items()})
                log.write(json.dumps(last)+'\n');log.flush();print('WORLD_MODEL_TRAIN',json.dumps(last),flush=True)
    checkpoint=output/'world-model-final.pt'
    with checkpoint.open('xb') as f:torch.save(dict(model=model.state_dict(),normalization=d['normalization'],configuration=cfg,updates=updates,source_sha256=source,packed_manifest_sha256=sha(manifest)),f)
    digest=sha(checkpoint)
    write_json(output/'checkpoint-freeze.json',dict(checkpoint=str(checkpoint),sha256=digest,updates=updates,planned_updates=cfg['updates'],
        complete=updates==cfg['updates'],model_selection='fixed last checkpoint; no validation/test selection'))
    print('WORLD_MODEL_CHECKPOINT_FROZEN',str(checkpoint),digest,flush=True)
    if updates!=cfg['updates']:raise RuntimeError('Training budget censored; checkpoint retained; no automatic continuation')
    del dataset,loader,iterator
    if defer_evaluation:
        write_json(output/'training-only-completion.json',dict(complete=True,updates=updates,checkpoint_sha256=digest,training_manifest_sha256=sha(manifest),heldout_loaded=False))
        print('TRAINING_COMPLETE_HELDOUT_DATA_UNREAD',digest,flush=True);lock.close();return
    validation=Windows(manifest,'validation');metrics=[evaluate(model,validation,stats,device,output,'validation')];del validation
    test=Windows(manifest,'test');metrics.append(evaluate(model,test,stats,device,output,'test'))
    if sha(checkpoint)!=digest or sha(manifest)!=json.loads((output/'training-freeze.json').read_text())['packed_manifest_sha256']:raise ValueError('Frozen model/data changed during evaluation')
    write_json(output/'evaluation.json',dict(schema='integrated-world-model-offline-evaluation-v1',checkpoint_sha256=digest,updates=updates,
        metrics=metrics,test_evaluation_runs=1,test_used_for_selection=False,WM_control=False,
        predictions_do_not_read_future_visuals_or_proprio=True,recorded_future_commands_are_offline_condition_only=True,
        task_or_planning_benefit_claimed=False,independent_hardware_or_broad_generalization_claimed=False))
    print('WORLD_MODEL_TRAINING_AND_FIXED_EVALUATION_COMPLETE',json.dumps(dict(updates=updates,checkpoint_sha256=digest,output=str(output))),flush=True)
    lock.close()

def evaluate_frozen(checkpoint,manifest,output):
    checkpoint=Path(checkpoint);manifest=Path(manifest);output=Path(output)
    frozen=json.loads((output/'checkpoint-freeze.json').read_text());digest=sha(checkpoint)
    if digest!=frozen['sha256'] or not frozen['complete']:raise ValueError('Complete frozen checkpoint required')
    lock=(output.parent/'integrated-world-model-training-gpu0.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    data=json.loads(manifest.read_text());device=torch.device(data['training']['device']);torch.set_num_threads(4)
    saved=torch.load(checkpoint,map_location=device,weights_only=True)
    if saved['normalization']!=data['normalization'] or saved['configuration']!=data['training']:raise ValueError('Training statistics/configuration changed after checkpoint freeze')
    model=RecurrentWorldModel().to(device);model.load_state_dict(saved['model']);stats=stats_tensors(data,device)
    results=[]
    for role in ('validation','test'):
        dataset=Windows(manifest,role);results.append(evaluate(model,dataset,stats,device,output,role));del dataset
    if sha(checkpoint)!=digest:raise ValueError('Checkpoint changed during heldout evaluation')
    write_json(output/'evaluation.json',dict(schema='integrated-world-model-offline-evaluation-v1',checkpoint_sha256=digest,
        training_manifest_sha256=saved['packed_manifest_sha256'],evaluation_manifest_sha256=sha(manifest),updates=saved['updates'],
        metrics=results,test_evaluation_runs=1,test_used_for_selection=False,WM_control=False,
        predictions_do_not_read_future_visuals_or_proprio=True,recorded_future_commands_are_offline_condition_only=True,
        task_or_planning_benefit_claimed=False,independent_hardware_or_broad_generalization_claimed=False))
    print('FIXED_CHECKPOINT_HELDOUT_EVALUATION_COMPLETE',digest,flush=True);lock.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();train(a.manifest,a.output)
