"""Original model query/history port; no padding, world, training or future data.

Exact original three definitions are compiled, not their trainer/native modules.
Current-source callbacks must still be qualified by the native owner. Audit mode
is explicitly labelled and cannot supply the live raw-WM adapter's context role.
"""
from collections import deque
from dataclasses import replace
import ast
import hashlib
import json
from pathlib import Path
import re
from .v4_successor_choice import need


def checked_query_definitions(root):
    root=Path(root).resolve(strict=True);manifest=json.loads((root/'SOURCE_INVENTORY.json').read_bytes())
    need(manifest['role']=='ORIGINAL_INFERENCE_FUNCTIONS_ONLY_NOT_TRAINER_OR_RUNTIME_IMPORT', 'Exact source role')
    expected={'BehaviorQueryBuffer.py':'BehaviorQueryBuffer','filter_full_native.py':'filter_full_native','resize_packet.py':'resize_packet'}
    need(set(manifest['files'])==set(expected),'Only original query/filter/resize definitions')
    definitions={}
    for name,symbol in expected.items():
        p=root/name;need(p.is_file()and not p.is_symlink(),'Regular source definition')
        raw=p.read_bytes();row=manifest['files'][name]
        need(hashlib.sha256(raw).hexdigest()==row['extracted_bytes_sha256']and row['symbol']==symbol,'Original definition byte pin')
        tree=ast.parse(raw);need(len(tree.body)==1 and isinstance(tree.body[0],(ast.FunctionDef,ast.ClassDef))
             and tree.body[0].name==symbol,'No trainer/native module top-level execution')
        definitions[symbol]=(p,raw)
    return definitions


def build_original_buffer(model,normalization,output,*,query_source_root,software_fixture=False):
    definitions=checked_query_definitions(query_source_root)
    import numpy as np
    import torch
    from PIL import Image
    from visual_latent_world_model import ObservationTrace
    from visual_latent_behavior import SKILLS,BehaviorM
    from .v4_raw_wm_adapter import CHECKPOINT_SHA
    need(type(software_fixture)is bool,'Explicit source-function smoke fixture mode')
    if not software_fixture:
        need(isinstance(model,BehaviorM)and getattr(model,'_reach_original_checkpoint_sha256',None)==CHECKPOINT_SHA,
             'Real restored original7a6 model required; random/fake model cannot supply live IO')
    namespace=dict(deque=deque,replace=replace,hashlib=hashlib,re=re,Path=Path,np=np,torch=torch,
                   Image=Image,ObservationTrace=ObservationTrace,SKILLS=SKILLS)
    for symbol in ('filter_full_native','resize_packet','BehaviorQueryBuffer'):
        path,raw=definitions[symbol];exec(compile(raw,str(path),'exec'),namespace)
    need(model.training is False and str(model.device)=='cpu','Existing frozen CPU WM only')
    buffer=namespace['BehaviorQueryBuffer'](model,normalization,output)
    buffer._reach_query_software_fixture=software_fixture
    buffer._reach_original_query_source_pins={symbol:hashlib.sha256(raw).hexdigest()for symbol,(_,raw)in definitions.items()}
    return buffer


class WMContextUnavailable(ValueError):
    """Input/method unavailable, NOT a failed native skill or a success label."""
    def __init__(self, reason):
        self.reason = reason
        super().__init__('WM_METHOD_INPUT_UNAVAILABLE: '+reason)


class CausalWMQueryPort:
    def __init__(self,buffer,*,role,target_provider=None,software_fixture=False):
        need(type(software_fixture)is bool,'Explicit software fixture mode')
        need(role in ('CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY','CLOSED_RECORDED_INPUT_AUDIT_NOT_LIVE','EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT'),
             'Explicit live or audit provenance; no role relabeling')
        fixture=software_fixture or role=='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT'
        need(fixture or getattr(buffer,'_reach_query_software_fixture',True)is False,
             'A source-function fixture buffer cannot be relabelled as live')
        if not fixture:
            need(not getattr(target_provider,'software_fixture',False),
                 'A fixture target descriptor cannot be used by a production query port')
            need(type(buffer).__name__=='BehaviorQueryBuffer'and
                 set(getattr(buffer,'_reach_original_query_source_pins',{}))=={'BehaviorQueryBuffer','filter_full_native','resize_packet'},
                 'Production query port requires the exact original constructed buffer, not a fixture')
        self.buffer=buffer;self.role='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT'if fixture else role
        self.target_provider=target_provider;self.completed_queries=0
        self._unmodelled_owner_ids=set();self._current_unmodelled_owner=None
        self._last_callback_tick=None;self.unmodelled_issued_steps=0

    def _check_accepted_clock(self,physical_tick,time_s):
        import math
        need(type(physical_tick)is int and physical_tick>=1 and type(time_s)in(int,float)
             and math.isfinite(time_s) and abs(physical_tick*.005-time_s)<=1e-6,
             'Actual accepted native tick/time, not selection or future command')
        need(self._last_callback_tick is None or physical_tick==self._last_callback_tick+1,
             'No skipped/duplicate accepted callbacks across modelled/unmodelled owners')

    def on_unmodelled_issued(self,physical_tick,time_s,*,native_owner_id,owner_kind):
        """Revoke only the model-input window for an actually issued unknown owner.

        SupportedCapture is not silently HOLD/NAV/RECOVER. Original raw recorder,
        actual owner/world/FIFO/clock and past query artifacts are NOT changed.
        A later genuine modelled owner needs three NEW real frames/full history.
        """
        need(type(native_owner_id)is str and bool(native_owner_id)
             and type(owner_kind)is str and bool(owner_kind),'Actual opaque owner ID/kind, never prospective candidate')
        self._check_accepted_clock(physical_tick,time_s)
        self._unmodelled_owner_ids.add(native_owner_id)
        self._current_unmodelled_owner=(native_owner_id,owner_kind)
        self.buffer.frames.clear();self.buffer.commands.clear()
        self.buffer.owner=None;self.buffer.observed_skill=None;self.buffer.owner_started=None
        self._last_callback_tick=physical_tick;self.unmodelled_issued_steps+=1
        return dict(status='UNMODELLED_ISSUED_OWNER_WINDOW_REVOKED_NOT_NATIVE_FAILURE',
            owner_kind=owner_kind,physical_tick=physical_tick,time_s=time_s,
            raw_recording_or_native_world_modified=False,model_forward_performed=False)

    def context_status(self):
        from .v4_raw_wm_adapter import SKILLS
        if self._current_unmodelled_owner is not None:status='CURRENT_ISSUED_OWNER_NOT_IN_ORIGINAL_GENERIC_SKILLS'
        elif getattr(self.buffer,'observed_skill',None)not in SKILLS:status='NO_ACTUALLY_ISSUED_MODELLED_OWNER'
        elif len(getattr(self.buffer,'frames',()))!=3:status='WAIT_THREE_NEW_REAL_GRID_FRAMES'
        else:status='NECESSARY_CONTEXT_PRESENT_ORIGINAL_BUILD_CHECKS_STILL_REQUIRED'
        return dict(status=status,current_observed_skill=getattr(self.buffer,'observed_skill',None),
            buffered_frames=len(getattr(self.buffer,'frames',())),
            buffered_issued_references=len(getattr(self.buffer,'commands',())),
            unmodelled_issued_steps=self.unmodelled_issued_steps,completed_queries=self.completed_queries,
            native_or_WM_inference_qualification_claimed=False)

    def _require_modelled_owner(self):
        status=self.context_status()['status']
        if self._current_unmodelled_owner is not None or (
                self.role!='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT' and
                status!='NECESSARY_CONTEXT_PRESENT_ORIGINAL_BUILD_CHECKS_STILL_REQUIRED'):
            raise WMContextUnavailable(status)

    def on_visual(self,packet):
        if self._current_unmodelled_owner is not None:
            return False  # Original native recorder still records; no unknown-owner frame enters model window.
        self.buffer.visual(packet)  # Exact original10Hz/causal ordering checks at build.

    def on_issued(self,position,physical_tick,time_s,*,actual_issued_skill,native_owner_id):
        need(type(native_owner_id)is str and bool(native_owner_id) and native_owner_id not in self._unmodelled_owner_ids,
             'An excluded actual owner cannot be renamed HOLD/NAV/RECOVER; a genuine new owner is required')
        self._check_accepted_clock(physical_tick,time_s)
        self.buffer.actual_motor(position,physical_tick,time_s,
            issued_skill=actual_issued_skill,native_owner_id=native_owner_id)
        self._last_callback_tick=physical_tick;self._current_unmodelled_owner=None

    def __call__(self,batch,options):
        """Direct query_provider for OriginalBehaviorWMAdapter, no model future head."""
        self._require_modelled_owner()
        need(self.role!='CLOSED_RECORDED_INPUT_AUDIT_NOT_LIVE','Closed audit cannot supply live WM provider')
        if self.role!='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT':
            from ainav.intents import IntentBatch
            need(isinstance(batch,IntentBatch),'Only original public semantic batch, never private ExecutionBatch')
        need(len(self.buffer.frames)==3,'Exactly original three real frame context required')
        anchor=self.buffer.frames[-1];now=batch.observation.time_s
        need(-1e-7<=now-anchor['time_s']<=.100001,'Original current WM image age')
        state=batch.observation.value['public_state'];body=[]
        for name,size in (('q',18),('dq',18),('gravity',3),('angular_velocity',3),('linear_velocity',3)):
            values=state.get(name)
            need(isinstance(values,list)and len(values)==size,'Original current public45D only, no padding')
            body.extend(values)
        anchor_sha=hashlib.sha256(anchor['rgb'].tobytes()).hexdigest()
        evidence=None
        if self.target_provider is None:
            targets={o.sha256:None for o in options}
        else:
            descriptor=self.target_provider(batch.observation,tuple(options),anchor)
            need(self.role=='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT' or
                 descriptor.get('source_role')!='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT',
                 'Fixture descriptor output cannot become live WM input')
            evidence=descriptor.get('target8_evidence_by_option_sha256')
            need(evidence is None or set(evidence)=={o.sha256 for o in options},'Same finite target evidence domain')
            need(descriptor['WM_anchor_RGB_bytes_sha256']==anchor_sha and
                 descriptor['WM_anchor_time_s']==anchor['time_s'],
                 'Target descriptors must bind WM anchor, not another off-grid image/old alias')
            targets=descriptor['target8_by_option_sha256']
            need(set(targets)=={o.sha256 for o in options},'Explicit target or missing mask for every candidate')
        return self.build('v4-wm-query-%06d'%self.completed_queries,public_observation=batch.observation,
            body45=body,body_observed_time_s=now,target8_by_option_sha256=targets,
            target8_evidence_by_option_sha256=evidence)

    def build(self,query_id,*,public_observation,body45,body_observed_time_s,
              target8_by_option_sha256,target8_evidence_by_option_sha256=None,observed_geometry8=None,
              observed_geometry_time_s=None,observed_geometry_RGB_sha256=None):
        self._require_modelled_owner()
        if self.role!='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT':
            from ainav.contracts import Observation
            need(isinstance(public_observation,Observation),'Original strict public Observation only')
        need(public_observation.time_s==body_observed_time_s,'Same original current public body clock')
        belief,public,record=self.buffer.build(query_id,public_observation.time_s,body45,
            body_observed_time_s=body_observed_time_s,observed_geometry8=observed_geometry8,
            observed_geometry_time_s=observed_geometry_time_s,
            observed_geometry_RGB_sha256=observed_geometry_RGB_sha256)
        self.completed_queries+=1
        return dict(public_observation_sha256=public_observation.sha256,
            original_query_sha256=record['query_sha256'],query_time_s=record['query_time_s'],
            image_time_s=record['image_time_s'],source_role=self.role,belief=belief,public60=public,
            target8_by_option_sha256=dict(target8_by_option_sha256),
            target8_evidence_by_option_sha256=target8_evidence_by_option_sha256,original_query_record=record,
            input_file=record['input_file'],live_policy_context_allowed=self.role=='CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY')
