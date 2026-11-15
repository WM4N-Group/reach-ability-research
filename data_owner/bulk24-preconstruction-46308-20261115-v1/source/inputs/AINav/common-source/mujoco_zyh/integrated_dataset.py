"""Lossless ordered motor intervals plus resized real RGBD, whole-source splits.

Never reads private catalogs/capsules or world state. Terminal missing futures
are omitted, never padded. The recorded future-command condition is offline only.
"""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
from .streams import sha,write_json


def checked_chunks(root,index,key):
    for row in index[key]:
        path=root/row['path']
        if not path.resolve().is_relative_to((root/key).resolve()) or sha(path)!=row['sha256']:
            raise ValueError('Raw stream path/SHA mismatch')
        with np.load(path,allow_pickle=False) as z:yield {k:z[k].copy() for k in z.files}


def ordered_intervals(issued,physical_ticks,control_ticks):
    issued=np.asarray(issued);ticks=np.asarray(physical_ticks);visual=np.asarray(control_ticks)
    if issued.ndim!=3 or issued.shape[1:]!=(5,18) or not np.isfinite(issued).all():raise ValueError('Full finite [steps,5,18] issued PD/FF required')
    if not np.array_equal(ticks,np.arange(1,len(ticks)+1)):raise ValueError('Nonconsecutive physical motor ticks')
    if len(visual)<2 or not np.array_equal(visual,np.arange(len(visual))*5):raise ValueError('Actual10Hz visual clock required')
    needed=(len(visual)-1)*20
    if len(issued)<needed:raise ValueError('Missing intervening motor command')
    return issued[:needed].astype(np.float32).reshape(len(visual)-1,20,5,18),len(issued)-needed


def pack_source(entry,output,config):
    root=Path(entry['root']);episode=root/'episode';output=Path(output)
    if sha(root/'report.json')!=entry['report_sha256']:raise ValueError('Frozen report changed')
    for name,digest in entry['files_sha256'].items():
        if sha(root/name)!=digest:raise ValueError('Frozen source file changed: '+name)
    index=json.loads((episode/'index.json').read_text());closure=json.loads((episode/'closure.json').read_text())
    if not closure['storage_complete']:raise ValueError('Cannot train on corrupt/unfinished storage')
    H,W=config['image_height'],config['image_width'];rgb=[];depth=[];valid=[];proprio=[];times=[];ticks=[];K=None;mount=None
    for z in checked_chunks(episode,index,'visual'):
        images=z['rgb'][0];d=z['depth_m'][0,...,0];h,w=images.shape[1:3]
        yy=np.minimum((np.arange(H)+.5)*h/H,h-1).astype(int);xx=np.minimum((np.arange(W)+.5)*w/W,w-1).astype(int)
        for image in images:rgb.append(np.asarray(Image.fromarray(image).resize((W,H),Image.Resampling.BILINEAR)))
        dd=d[:,yy][:,:,xx];mask=np.isfinite(dd)&(dd>=.05)&(dd<=15.)
        depth.extend(np.where(mask,dd,0).astype(np.float16));valid.extend(mask)
        proprio.extend(z['proprio'][0]);times.extend(z['timestamps_s'][0]);ticks.extend(z['control_ticks'])
        k=z['camera_K'][0].copy();k[0]*=W/w;k[1]*=H/h;m=z['T_base_optical'][0]
        if K is not None and (not np.array_equal(K,k) or not np.array_equal(mount,m)):raise ValueError('Camera calibration changed within episode')
        K,mount=k,m.copy()
    command=[];physical=[]
    for z in checked_chunks(episode,index,'commands'):
        command.append(z['issued']);physical.append(z['physical_tick'])
    intervals,tail=ordered_intervals(np.concatenate(command),np.concatenate(physical),np.asarray(ticks))
    p=np.asarray(proprio,dtype=np.float32);t=np.asarray(times,dtype=np.float64)
    if p.shape!=(len(rgb),45) or not np.isfinite(p).all() or not np.allclose(t,np.arange(len(t))*.1,atol=1e-7,rtol=0):raise ValueError('Actual proprio/time alignment differs')
    if len(rgb)!=entry['frames'] or len(rgb)!=closure['observations']:raise ValueError('Raw frame count differs')
    arrays=dict(rgb=np.stack(rgb),depth_m=np.stack(depth),depth_valid=np.stack(valid),proprio=p,
        actions=intervals,timestamps_s=t,camera_K=K,T_base_optical=mount)
    with output.open('xb') as f:np.savez_compressed(f,**arrays)
    context=config['context_frames'];rollout=config['rollout_frames'];windows=max(0,(len(rgb)-context-rollout)//5+1)
    return dict(**entry,packed=str(output),packed_sha256=sha(output),windows_stride5=windows,
        trailing_commands_without_future_visual=tail,actual_command_substeps_used=int(intervals.shape[0]*20),
        input_arrays=sorted(arrays),private_truth_read_by_packer=False)


def prepare(manifest,output,reuse_training_manifest=None):
    manifest=Path(manifest);output=Path(output);d=json.loads(manifest.read_text())
    output.mkdir(exist_ok=False);cfg=d['training'];rows=[]
    reused=json.loads(Path(reuse_training_manifest).read_text()) if reuse_training_manifest is not None else None
    old_by_root={r['root']:r for r in reused['episodes']} if reused else {}
    groups={}
    for entry in d['episodes']:
        group=entry['source_group'];role=entry['role']
        if group in groups and groups[group]!=role:raise ValueError('Source group crosses split')
        groups[group]=role
        if reused is not None and role=='train':
            row=old_by_root.get(entry['root'])
            if row is None or row['role']!='train' or row['report_sha256']!=entry['report_sha256'] or sha(row['packed'])!=row['packed_sha256']:
                raise ValueError('Immutable original training source changed during evaluation packing')
        else:row=pack_source(entry,output/(group+'.npz'),cfg)
        rows.append(row)
        print('PACKED_SOURCE',group,role,row['frames'],row['windows_stride5'],flush=True)
    # Fit every normalization statistic using training rows only.
    props=[];acts=[];Ks=[];mounts=[]
    for row in rows:
        with np.load(row['packed'],allow_pickle=False) as z:
            Ks.append(z['camera_K']);mounts.append(z['T_base_optical'])
            if reused is None and row['role']=='train':props.append(z['proprio']);acts.append(z['actions'].reshape(-1,90))
    if not all(np.array_equal(Ks[0],x) for x in Ks) or not all(np.array_equal(mounts[0],x) for x in mounts):raise ValueError('This model version requires common calibrated cameras')
    if reused is not None:
        normalization=reused['normalization']
        if reused['training']!=cfg or normalization['fit_split']!='train_only':raise ValueError('Frozen training normalization/configuration changed')
    else:
        p=np.concatenate(props);a=np.concatenate(acts)
        normalization=dict(proprio_mean=p.mean(0).tolist(),proprio_std=np.maximum(p.std(0),.05).tolist(),
            action_mean=a.mean(0).tolist(),action_std=np.maximum(a.std(0),.05).tolist(),fit_split='train_only')
    write_json(output/'packed-manifest.json',dict(schema='integrated-course-packed-RGBD-actions-v1',source_manifest=str(manifest),
        source_manifest_sha256=sha(manifest),training=cfg,episodes=rows,normalization=normalization,
        bootstrap_new_training_authorization=d['bootstrap_new_training_authorization'],
        no_private_truth_inputs=True,no_missing_future_padding=True,action_order_preserved=True,
        immutable_training_manifest_reused=str(reuse_training_manifest) if reused else None,
        condition='Given ordered recorded future issued PD/FF commands; offline prediction, never an online planning claim.'))
    print('FROZEN_PACKED_MANIFEST',str(output/'packed-manifest.json'),sha(output/'packed-manifest.json'),flush=True)

class Windows:
    def __init__(self,manifest,role):
        self.manifest=json.loads(Path(manifest).read_text());self.cfg=self.manifest['training'];self.data=[];self.keys=[]
        c=self.cfg['context_frames'];f=self.cfg['rollout_frames']
        for row in self.manifest['episodes']:
            if row['role']!=role:continue
            path=Path(row['packed'])
            if sha(path)!=row['packed_sha256']:raise ValueError('Packed source changed')
            with np.load(path,allow_pickle=False) as z:data={k:z[k].copy() for k in ('rgb','depth_m','depth_valid','proprio','actions')}
            index=len(self.data);self.data.append(data)
            self.keys.extend((index,t,row['source_group']) for t in range(0,len(data['rgb'])-c-f+1,5))
        if not self.keys:raise ValueError('No complete uncensored windows in split: '+role)
    def __len__(self):return len(self.keys)
    def __getitem__(self,index):
        episode,t,group=self.keys[index];d=self.data[episode];n=self.cfg['context_frames']+self.cfg['rollout_frames']
        v=np.concatenate([d['rgb'][t:t+n].astype(np.float32)/255.,
            (d['depth_m'][t:t+n].astype(np.float32)/15.)[...,None],d['depth_valid'][t:t+n,...,None].astype(np.float32)],axis=-1).transpose(0,3,1,2)
        return dict(visual=v,proprio=d['proprio'][t:t+n],actions=d['actions'][t:t+n-1].reshape(n-1,1800),group=group)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();prepare(a.manifest,a.output)
