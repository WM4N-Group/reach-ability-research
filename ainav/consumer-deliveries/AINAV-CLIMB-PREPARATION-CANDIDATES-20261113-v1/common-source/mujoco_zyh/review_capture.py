"""Read-only complete-world-state recording for same-episode external views.

Private audit stream only. Unlike the original joint-only motor log, this keeps
actual root/object/free-joint states. It never steps or sets the task MjData.
"""
from pathlib import Path
import gzip
import hashlib
import json
import tempfile
import numpy as np
from .streams import write_json,sha


class WorldStateRecorder:
    def __init__(self,root,runtime,config,model_cache_dir=None):
        import mujoco
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=False)
        (self.root/'states').mkdir()
        self.runtime,self.config=runtime,config
        self.spec=mujoco.mjtState.mjSTATE_INTEGRATION
        self.size=mujoco.mj_stateSize(runtime.sim.model,self.spec)
        self.rows=[];self.chunks=[];self.frames=0;self.closed=False
        before=self.actual_state()
        size=mujoco.mj_sizeModel(runtime.sim.model)
        binary=np.empty(size,dtype=np.uint8)
        mujoco.mj_saveModel(runtime.sim.model,None,binary)
        binary_sha=hashlib.sha256(memoryview(binary)).hexdigest()
        cache=Path(model_cache_dir or self.root.parent/'compiled-review-models').resolve()
        cache.mkdir(parents=True,exist_ok=True)
        model_path=cache/(binary_sha+'.mjb.gz')
        cache_receipt=cache/(binary_sha+'.json')
        if model_path.exists():
            info=json.loads(cache_receipt.read_text())
            if info['binary_sha256']!=binary_sha or sha(model_path)!=info['gzip_sha256']:
                raise ValueError('Immutable shared compiled model cache is corrupt')
        else:
            with model_path.open('xb') as out:
                with gzip.GzipFile(fileobj=out,mode='wb',mtime=0) as compressed:
                    compressed.write(memoryview(binary))
            info=dict(binary_sha256=binary_sha,binary_bytes=size,gzip_sha256=sha(model_path),gzip_bytes=model_path.stat().st_size)
            write_json(cache_receipt,info)
        if info['gzip_bytes']>config['max_compiled_model_cache_bytes']:
            raise ValueError('Shared compiled model exceeds separately registered static-model quota')
        if not np.array_equal(before,self.actual_state()):raise RuntimeError('Saving compiled model changed live state')
        self.bytes=0
        self.metadata=dict(schema='mujoco-private-full-state-review-v1',model_input_allowed=False,
            source_id=config['source_id'],episode_id=config['episode_id'],source_group=config['source_group'],
            display_scene_label=(config['review_scope'] if (config.get('suite_case') or config.get('integrated_case')) else ('Research A20kg / B0.5kg / C1kg | explicit candidate context | NO CLIMB/bridge' if config['scene_recipe']=='research_threebox' else ('PUSH probe | mass='+str(config['probe_physics']['mass_kg'])+'kg | friction='+str(config['probe_physics']['friction'])+' | reviewer-only physics; NO A/B/C' if config.get('probe_physics') else 'Native 1kg box + 20cm platform | NO A20kg failure/recovery/B reselection'))),
            scene_recipe=config['scene_recipe'],selected_object_id=config['selected_object_id'],
            external_review_camera=config.get('review_camera'),mujoco_version=mujoco.__version__,state_spec=int(self.spec),state_size=self.size,
            nq=runtime.sim.model.nq,nv=runtime.sim.model.nv,nu=runtime.sim.model.nu,
            physics_dt_s=.005,control_dt_s=.02,visual_stride_control_ticks=config['visual_stride_control_ticks'],
            model_path=str(model_path),model_cache_root=str(cache),model_sha256=info['gzip_sha256'],
            shared_model_gzip_bytes=info['gzip_bytes'],shared_model_is_static_not_per_episode_dynamic_payload=True,
            binary_model_uncompressed_bytes=size,binary_model_uncompressed_sha256=binary_sha,lossless_model_compression=True,
            actual_measured_state_not_reconstructed_from_joint_only_logs=True,
            copying_states_back_to_live_task_permitted=False,
            purpose='One new user-requested composite review capture; not independent research or failed-A recovery')
        write_json(self.root/'metadata.json',self.metadata)

    def actual_state(self):
        import mujoco
        values=np.empty(self.size,dtype=np.float64)
        mujoco.mj_getState(self.runtime.sim.model,self.runtime.sim.data,values,self.spec)
        return values

    def capture(self,control_tick):
        if self.closed:raise ValueError('Review recorder closed')
        expected=self.frames*self.config['visual_stride_control_ticks']
        if control_tick!=expected:raise ValueError('No gap/replay in complete-state record')
        now=float(self.runtime.sim.data.time)
        if abs(now-control_tick*.02)>1e-7:raise ValueError('Full-state clock differs from actual acquisition')
        state=self.actual_state()
        if not np.isfinite(state).all():raise ValueError('Actual complete world state is nonfinite')
        self.rows.append((control_tick,now,state.copy()));self.frames+=1
        if len(self.rows)>=self.config['visual_chunk_frames']:self.flush()
        if not np.array_equal(state,self.actual_state()):raise RuntimeError('Review capture changed live integration state')

    def flush(self):
        if not self.rows:return
        p=self.root/'states'/f'{len(self.chunks):06d}.npz'
        with p.open('xb') as f:np.savez_compressed(f,control_ticks=np.array([r[0] for r in self.rows]),
            time_s=np.array([r[1] for r in self.rows]),full_state=np.stack([r[2] for r in self.rows]))
        self.bytes+=p.stat().st_size
        self.chunks.append(dict(path=str(p.relative_to(self.root)),sha256=sha(p),frames=len(self.rows),
            first_tick=self.rows[0][0],last_tick=self.rows[-1][0]))
        self.rows=[]
        if self.bytes>self.config['max_review_state_bytes']:raise ValueError('Private review state quota exceeded; preserve raw failure')

    def close(self):
        if self.closed:raise ValueError('Review recorder already closed')
        self.flush();self.closed=True
        result=dict(schema='mujoco-private-review-state-closure-v1',frames=self.frames,chunks=self.chunks,
            metadata_sha256=sha(self.root/'metadata.json'),model_sha256=self.metadata['model_sha256'],model_path=self.metadata['model_path'],
            shared_static_model_bytes=self.metadata['shared_model_gzip_bytes'],
            bytes=self.bytes,task_state_written=False,synthetic_or_interpolated_state=False,
            physics_started_by_recorder=0,model_input_allowed=False)
        write_json(self.root/'closure.json',result)
        return result


def state_records(root):
    """Stream verified actual states; no simulator import, no frame synthesis."""
    import json
    root=Path(root);meta=json.loads((root/'metadata.json').read_text());close=json.loads((root/'closure.json').read_text())
    if sha(root/'metadata.json')!=close['metadata_sha256'] or sha(Path(meta['model_path']))!=close['model_sha256']:
        raise ValueError('Full-state metadata/model changed')
    count=0
    for row in close['chunks']:
        path=root/row['path']
        if not path.resolve().is_relative_to(root/'states') or sha(path)!=row['sha256']:raise ValueError('Full-state chunk path/hash mismatch')
        with np.load(path,allow_pickle=False) as z:
            if set(z.files)!={'control_ticks','time_s','full_state'}:raise ValueError('Unknown full-state record fields')
            if z['full_state'].shape!=(len(z['control_ticks']),meta['state_size']):raise ValueError('Full-state width mismatch')
            for tick,stamp,state in zip(z['control_ticks'],z['time_s'],z['full_state']):
                if int(tick)!=count*meta['visual_stride_control_ticks'] or abs(float(stamp)-int(tick)*.02)>1e-7:
                    raise ValueError('Actual review-state history gap')
                count+=1
                yield int(tick),float(stamp),state.copy()
    if count!=close['frames']:raise ValueError('Full-state closure frame count mismatch')


def load_display_model(root):
    """Decode a lossless compiled-model copy, never touch a task world."""
    import mujoco
    root=Path(root);meta=json.loads((root/'metadata.json').read_text())
    if meta['mujoco_version']!=mujoco.__version__:raise ValueError('Compiled model requires the pinned MuJoCo version')
    path=Path(meta['model_path'])
    if path.resolve().parent!=Path(meta['model_cache_root']).resolve() or sha(path)!=meta['model_sha256']:raise ValueError('Compiled model source/hash differs')
    with tempfile.TemporaryDirectory(prefix='mujoco-display-model-') as directory:
        decoded=Path(directory)/'model.mjb';hasher=hashlib.sha256();count=0
        with gzip.open(path,'rb') as src,decoded.open('xb') as dst:
            for block in iter(lambda:src.read(1024*1024),b''):
                dst.write(block);hasher.update(block);count+=len(block)
        if count!=meta['binary_model_uncompressed_bytes'] or hasher.hexdigest()!=meta['binary_model_uncompressed_sha256']:
            raise ValueError('Compiled model decompression integrity failure')
        model=mujoco.MjModel.from_binary_path(str(decoded))
    return model
