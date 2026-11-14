"""Read-only train/validation diagnostics of a frozen RGBD dynamics baseline.

No test frames, optimizer, physics or online action change. Motor ablations are
counterfactual offline inputs only, and do not establish causal physical validity.
"""
import argparse,bisect,json,time
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader,Subset
from PIL import Image,ImageDraw
from .streams import sha,write_json
from .integrated_dataset import Windows
from .integrated_world_model import RecurrentWorldModel,transform,stats_tensors


def motion_bucket(copy_mse):
    if copy_mse<.001:return 'near_static_RGB_mse_lt_0.001'
    if copy_mse>.01:return 'moving_RGB_mse_gt_0.01'
    return 'intermediate_RGB_motion'


def ablate_future(actions,context,mode):
    result=actions.clone();start=context-1
    if mode=='training_mean_future_commands':result[:,start:]=0.
    elif mode=='reverse_future_200Hz_substep_order':
        future=result[:,start:];result[:,start:]=future.reshape(*future.shape[:2],20,90).flip(2).reshape_as(future)
    elif mode=='swap_future_command_intervals_across_windows':result[:,start:]=result[:,start:].roll(1,0)
    else:raise ValueError('Unknown registered offline diagnostic ablation')
    return result


def stage_lookup(root):
    path=Path(root)/'episode/control-boundaries.jsonl';out={}
    for line in path.open():
        row=json.loads(line);out[int(row['control_tick'])]=row['phase'].split('/')[0]
    return out


def collect(model,dataset,stats,device,output,role,stride):
    c=dataset.cfg['context_frames'];f=dataset.cfg['rollout_frames'];groups={};stages={};examples=[];count=0
    rows={r['source_group']:r for r in dataset.manifest['episodes'] if r['role']==role}
    for group,row in rows.items():stages[group]=stage_lookup(row['root'])
    selection=list(range(0,len(dataset),stride));modes=['training_mean_future_commands','reverse_future_200Hz_substep_order','swap_future_command_intervals_across_windows']
    def add(key,record):
        row=groups.setdefault(key,dict(windows=0))
        row['windows']+=1
        for name,value in record.items():row[name]=row.get(name,0.)+float(value)
    loader=DataLoader(Subset(dataset,selection),batch_size=16,shuffle=False,num_workers=0)
    with torch.inference_mode():
        for batch in loader:
            v,p,a=transform(batch,stats,device);pv,pp=model(v[:,:c],p[:,:c],a,f)
            altered={mode:model(v[:,:c],p[:,:c],ablate_future(a,c,mode),f) for mode in modes}
            target=v[:,c:];ptarget=p[:,c:];anchor=v[:,c-1:c];panchor=p[:,c-1:c]
            for bi,group in enumerate(batch['group']):
                index=selection[count];_,frame_start,_=dataset.keys[index];count+=1
                stage=stages[group][5*(frame_start+c-1)]
                for horizon in [5,10,20]:
                    k=horizon-1;truth=target[bi,k];pred=pv[bi,k];copy=anchor[bi,0]
                    copy_mse=(copy[:3]-truth[:3]).square().mean();valid=truth[4:5];denom=valid.sum().clamp_min(1)
                    record=dict(RGB_MSE=(pred[:3]-truth[:3]).square().mean(),copy_RGB_MSE=copy_mse,
                        depth_MAE_m=((pred[3:4]-truth[3:4]).abs()*valid).sum()/denom*15,
                        copy_depth_MAE_m=((copy[3:4]-truth[3:4]).abs()*valid).sum()/denom*15,
                        proprio_MSE_standardized=(pp[bi,k]-ptarget[bi,k]).square().mean(),
                        hold_proprio_MSE_standardized=(panchor[bi,0]-ptarget[bi,k]).square().mean(),
                        predicted_RGB_change_from_anchor_MSE=(pred[:3]-copy[:3]).square().mean(),
                        target_RGB_spatial_variance=truth[:3].var((-2,-1),unbiased=False).mean(),
                        predicted_RGB_spatial_variance=pred[:3].var((-2,-1),unbiased=False).mean())
                    for mode,(av,ap) in altered.items():
                        record[mode+'_RGB_prediction_delta_MSE']=(av[bi,k,:3]-pred[:3]).square().mean()
                        record[mode+'_RGB_target_MSE']=(av[bi,k,:3]-truth[:3]).square().mean()
                        record[mode+'_proprio_target_MSE_standardized']=(ap[bi,k]-ptarget[bi,k]).square().mean()
                    for category in ['ALL','stage:'+stage,'motion:'+motion_bucket(float(copy_mse))]:add(f'{horizon/10:.1f}s|{category}',record)
                if role=='validation':
                    motion=float((anchor[bi,0,:3]-target[bi,-1,:3]).square().mean())
                    examples.append((motion,group,frame_start,anchor[bi,0].cpu().numpy(),pv[bi].cpu().numpy(),target[bi].cpu().numpy()))
                    examples=sorted(examples,key=lambda x:x[0],reverse=True)[:3]
    for row in groups.values():
        n=row['windows']
        for key in list(row):
            if key!='windows':row[key]/=n
        row['RGB_error_ratio_vs_copy']=row['RGB_MSE']/max(1e-12,row['copy_RGB_MSE'])
        row['predicted_to_target_RGB_spatial_variance_ratio']=row['predicted_RGB_spatial_variance']/max(1e-12,row['target_RGB_spatial_variance'])
    for index,(motion,group,start,anchor,pred,true) in enumerate(examples):
        image=Image.new('RGB',(960,495),'#101820');draw=ImageDraw.Draw(image)
        draw.text((8,8),f'VALIDATION moving-window diagnostic | {group} | start={start/10:.1f}s | copy2sMSE={motion:.4f}',fill='white')
        for j,k in enumerate([4,9,19]):
            y=40+j*150;draw.text((8,y),f'{(k+1)/10:.1f}s',fill='white')
            for col,(name,frame) in enumerate([('COPY CURRENT',anchor),('FROZEN MODEL',pred[k]),('ACTUAL FUTURE',true[k])]):
                draw.text((65+col*290,y),name,fill='white');rgb=(np.clip(frame[:3],0,1).transpose(1,2,0)*255).astype(np.uint8)
                image.paste(Image.fromarray(rgb).resize((240,128)),(65+col*290,y+17))
        image.save(Path(output)/f'validation-moving-{index}.png')
    return dict(split=role,available_windows=len(dataset),diagnostic_windows=count,window_stride=stride,
        groups=groups,source_groups=sorted(rows),stage_is_private_diagnostic_label_only=True,
        test_source_opened=False,ablation_modes=modes,
        cross_window_ablation_singleton_warning='Single-item last batch is unchanged by swapping; do not treat ablations as physically valid interventions.')


def run(checkpoint,manifest,output,stride=5):
    checkpoint=Path(checkpoint);manifest=Path(manifest);output=Path(output);output.mkdir(exist_ok=False)
    d=json.loads(manifest.read_text());digest=sha(checkpoint);manifest_digest=sha(manifest)
    write_json(output/'diagnostic-freeze.json',dict(schema='integrated-world-model-readonly-diagnostic-v1',
        checkpoint_sha256=digest,manifest_sha256=manifest_digest,source_sha256=sha(Path(__file__)),
        split_allowlist=['train','validation'],window_stride=stride,test_pixels_or_metrics_loaded=False,
        training_updates=0,physics_steps=0,model_or_actor_weights_modified=False,
        motion_thresholds=dict(near_static_below=.001,moving_above=.01),horizons_seconds=[.5,1.,2.]))
    torch.set_num_threads(4);device=torch.device('cuda:0');saved=torch.load(checkpoint,map_location=device,weights_only=True)
    if saved['normalization']!=d['normalization']:raise ValueError('Frozen normalization mismatch')
    model=RecurrentWorldModel().to(device);model.load_state_dict(saved['model']);model.eval();stats=stats_tensors(d,device)
    started=time.monotonic();results=[]
    for role in ('train','validation'):
        dataset=Windows(manifest,role);results.append(collect(model,dataset,stats,device,output,role,stride));del dataset
    if sha(checkpoint)!=digest or sha(manifest)!=manifest_digest:raise ValueError('Frozen model/data changed')
    write_json(output/'diagnostic.json',dict(schema='integrated-world-model-readonly-diagnostic-results-v1',
        complete=True,checkpoint_sha256=digest,manifest_sha256=manifest_digest,wall_seconds=time.monotonic()-started,
        results=results,test_data_loaded=False,training_updates=0,physics_steps=0,weights_changed=False,
        interpretation_limit='Ablation sensitivity alone is not action usefulness. Static/dynamic categories use actual future RGB only as offline diagnostic labels; never model input.'))
    for split in results:
        print(split['split'],json.dumps({k:v for k,v in split['groups'].items() if k.endswith('|ALL')}),flush=True)
    print('DIAGNOSTIC_COMPLETE',str(output/'diagnostic.json'),sha(output/'diagnostic.json'),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('checkpoint','manifest','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--stride',type=int,default=5);a=p.parse_args()
    if a.stride<1:raise ValueError('Positive diagnostic stride required')
    run(a.checkpoint,a.manifest,a.output,a.stride)
