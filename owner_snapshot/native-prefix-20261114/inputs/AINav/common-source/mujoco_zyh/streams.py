"""Chunked sparse RGBD + lossless 200Hz motor stream; NOT the old v1 loader.

Eight public visual fields are retained. actions_previous is ONLY the last issued
substep target, never a summary of the entire visual interval. A v2 consumer MUST
also consume the complete intervening command stream. No model is trained here.
"""
import io
import json
import hashlib
from pathlib import Path
import numpy as np
import torch
from visual_shadow_model import INPUT_KEYS, validate_visual_input


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    with Path(path).open('x') as f:
        json.dump(value,f,indent=2,allow_nan=False); f.write('\n')


class ByteBudgetExceeded(RuntimeError): pass


class ChunkedEpisodeWriter:
    def __init__(self, root, metadata):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=False)
        (self.root/'visual').mkdir(); (self.root/'commands').mkdir()
        self.metadata=dict(metadata,schema='piper-mujoco-visual-action-stream-v2',
            backend='mujoco',visual_input_keys=sorted(INPUT_KEYS),
            command_stream_hz=200,control_hz=50,model_input_allowed_fields=sorted(INPUT_KEYS),
            previous_action_semantics='last_substep_issued_PD_position_target_only',
            requires_complete_intervening_action_stream_consumer=True,
            v1_visual_history_loader_compatible=False,training_allowed=bool(metadata.get('forecast_study_training_authorized') and metadata.get('role')=='train'),
            private_catalog_and_engine_provenance_not_model_input=True)
        write_json(self.root/'episode.json',self.metadata)
        self.visual=[];self.commands=[];self.visual_chunks=[];self.command_chunks=[]
        self.frames=0;self.steps=0;self.written_frames=0;self.written_steps=0;self.bytes=0;self.closed=False
        self._K=self._mount=None
        self.catalog=(self.root/'private-catalog.jsonl').open('x')
        self.trace=(self.root/'control-boundaries.jsonl').open('x')

    def save(self,folder,arrays,rows,first,last):
        out=io.BytesIO();np.savez_compressed(out,**arrays);data=out.getvalue()
        if self.bytes+len(data)>self.metadata['max_payload_bytes']:
            raise ByteBudgetExceeded('Registered compressed payload byte budget exceeded')
        path=self.root/folder/f'{len(rows):06d}.npz'
        with path.open('xb') as f:f.write(data)
        self.bytes+=len(data)
        rows.append(dict(path=str(path.relative_to(self.root)),sha256=sha(path),bytes=len(data),first=first,last=last))

    def append_command(self, *, issued, delayed, torque, raw_torque, q_before, dq_before, physical_tick, time_s):
        if self.closed or physical_tick!=self.steps+1 or abs(time_s-physical_tick*.005)>1e-7:
            raise ValueError('Actual consecutive 200Hz motor command boundary required')
        values=dict(issued=np.asarray(issued),delayed=np.asarray(delayed),torque=np.asarray(torque),raw_torque=np.asarray(raw_torque),
            q_before=np.asarray(q_before),dq_before=np.asarray(dq_before))
        for name,x in values.items():
            shape=(5,18) if name in ('issued','delayed') else (18,)
            if x.shape!=shape or not np.isfinite(x).all():raise ValueError('Invalid actual motor channel: '+name)
        self.commands.append(dict(**{k:v.copy() for k,v in values.items()},physical_tick=physical_tick,time_s=time_s))
        self.steps+=1
        if len(self.commands)>=self.metadata['command_chunk_steps']:self.flush_commands()

    def append_visual(self, packet, *, control_tick, private_catalog):
        if self.closed or control_tick!=self.frames*self.metadata['visual_stride_control_ticks']:
            raise ValueError('Actual sparse visual acquisition boundary required; no duplicates/gaps/backfill')
        validate_visual_input(packet)
        if packet['rgb'].shape[:2]!=(1,1) or abs(float(packet['timestamps_s'][0,0])-control_tick*.02)>1e-6:
            raise ValueError('Exact one-frame acquisition timestamp required')
        if bool(packet['action_valid'][0,0])!=(control_tick>0) or control_tick*4!=self.steps:
            raise ValueError('Visual action-valid/full motor-stream clock mismatch')
        K=packet['camera_K'].numpy();mount=packet['T_base_optical'].numpy()
        if self._K is not None and (not np.array_equal(K,self._K) or not np.array_equal(mount,self._mount)):
            raise ValueError('Camera calibration cannot change within a source')
        if private_catalog.get('control_tick')!=control_tick or private_catalog.get('model_input_allowed') is not False:
            raise ValueError('Exact private catalog boundary required')
        self.catalog.write(json.dumps(private_catalog,allow_nan=False)+'\n');self.catalog.flush()
        self.visual.append(dict(control_tick=control_tick,packet={k:v.numpy().copy() for k,v in packet.items()}))
        self._K,self._mount=K.copy(),mount.copy();self.frames+=1
        if len(self.visual)>=self.metadata['visual_chunk_frames']:self.flush_visual()

    def boundary(self, row):
        if self.closed:raise ValueError('Closed source')
        self.trace.write(json.dumps(row,allow_nan=False)+'\n');self.trace.flush()

    def flush_commands(self):
        if not self.commands:return
        arrays={k:np.stack([row[k] for row in self.commands]) for k in self.commands[0]}
        self.save('commands',arrays,self.command_chunks,self.commands[0]['physical_tick'],self.commands[-1]['physical_tick'])
        self.written_steps+=len(self.commands);self.commands=[]

    def flush_visual(self):
        if not self.visual:return
        arrays={k:(self.visual[0]['packet'][k] if k in ('camera_K','T_base_optical') else
            np.concatenate([row['packet'][k] for row in self.visual],axis=1)) for k in INPUT_KEYS}
        arrays['control_ticks']=np.array([row['control_tick'] for row in self.visual],dtype=np.int64)
        self.save('visual',arrays,self.visual_chunks,int(arrays['control_ticks'][0]),int(arrays['control_ticks'][-1]))
        self.written_frames+=len(self.visual);self.visual=[]

    def close(self, *, outcome, terminal_time_s, censored):
        if self.closed:raise ValueError('Source already closed, never resume an episode')
        storage_complete=True;error=None
        try:self.flush_commands();self.flush_visual()
        except Exception as exc:storage_complete=False;error=repr(exc)
        self.catalog.close();self.trace.close();self.closed=True
        index=dict(schema='piper-mujoco-chunk-index-v2',visual=self.visual_chunks,commands=self.command_chunks)
        write_json(self.root/'index.json',index)
        result=dict(schema='piper-mujoco-episode-closure-v2',caller_outcome=outcome,
            terminal_time_s=terminal_time_s,censored=censored,storage_complete=storage_complete,storage_error=error,
            observations=self.written_frames,physical_command_steps=self.written_steps,
            compressed_payload_bytes=self.bytes,episode_sha256=sha(self.root/'episode.json'),index_sha256=sha(self.root/'index.json'),
            private_catalog_sha256=sha(self.root/'private-catalog.jsonl'),control_boundaries_sha256=sha(self.root/'control-boundaries.jsonl'),
            task_success_not_inferred_from_recorder=True,no_auto_reset_or_terminal_frame_backfill=True)
        write_json(self.root/'closure.json',result)
        return result
