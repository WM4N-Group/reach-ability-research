class BehaviorQueryBuffer:
    def __init__(self,model,normalization,output):
        self.model=model;self.normalization=normalization;self.output=Path(output);self.output.mkdir(exist_ok=False)
        self.frames=deque(maxlen=3);self.commands=deque(maxlen=64)
        self.owner=None;self.observed_skill=None;self.owner_started=None

    def visual(self,packet):
        frame=resize_packet(packet)
        if self.frames and frame['time_s']<=self.frames[-1]['time_s']+1e-8:raise ValueError('No repeated or backfilled RGBD')
        self.frames.append(frame)

    def actual_motor(self,position,physical_tick,time_s,*,issued_skill,native_owner_id):
        q=np.asarray(position,np.float32)
        if (q.shape!=(18,) or not np.isfinite(q).all() or issued_skill not in SKILLS or not native_owner_id
                or physical_tick<1 or abs(physical_tick*.005-time_s)>1e-6):
            raise ValueError('Actual finite native18, owner, skill and physical clock required')
        if self.commands and physical_tick!=self.commands[-1][0]+1:raise ValueError('Actual motor history must be consecutive')
        self.commands.append((int(physical_tick),q.copy()))
        owner=(issued_skill,native_owner_id)
        if owner!=self.owner:
            self.owner=owner;self.observed_skill=issued_skill;self.owner_started=float(time_s)-.005

    def build(self,query_id,now,body45,*,body_observed_time_s,observed_geometry8=None,
              observed_geometry_time_s=None,observed_geometry_RGB_sha256=None):
        if not re.fullmatch(r'[A-Za-z0-9_-]+',query_id):raise ValueError('Safe fresh query identifier required')
        if len(self.frames)!=3 or self.observed_skill is None:raise ValueError('Three real frames and actually issued owner required')
        body=np.asarray(body45,np.float32);geometry=np.zeros(8,np.float32) if observed_geometry8 is None else np.asarray(observed_geometry8,np.float32)
        if body.shape!=(45,) or geometry.shape!=(8,) or not np.isfinite(np.r_[body,geometry]).all() or abs(now-body_observed_time_s)>1e-7:
            raise ValueError('Exact current real public body and current-image geometry required')
        if geometry[7] not in (0,1):raise ValueError('Explicit observed geometry validity required')
        if not geometry[7] and np.any(geometry[:7]!=0):raise ValueError('Missing geometry must be explicitly masked zeros')
        frames=list(self.frames);times=np.asarray([x['time_s'] for x in frames]);age=now-times[-1]
        if not np.allclose(np.diff(times),.1,atol=1e-6,rtol=0) or not -1e-7<=age<=.100001:
            raise ValueError('Actual 10Hz RGBD and bounded query-age clock required')
        if geometry[7] and (observed_geometry_time_s is None or abs(observed_geometry_time_s-times[-1])>1e-7
                or observed_geometry_RGB_sha256!=hashlib.sha256(frames[-1]['rgb'].tobytes()).hexdigest()):
            raise ValueError('Observed geometry must bind the latest actual RGB image/time')
        first,last,end=[int(round(t/.005)) for t in (times[0],times[-1],now)]
        if abs(end*.005-now)>1e-6 or not self.commands or self.commands[-1][0]!=end:
            raise ValueError('Query must match current actual motor clock, no past replay or future commands')
        refs=dict(self.commands)
        if any(t not in refs for t in range(first+1,end+1)):raise ValueError('Lossless actual native interval/tail required')
        for f in frames:
            tick=int(round(f['time_s']/.005))
            if f['action_valid'] and (tick not in refs or not np.array_equal(f['actions_previous'].astype(np.float32),refs[tick])):
                raise ValueError('Frame previous-action telemetry disagrees with actual issued reference')
        public=np.zeros(60,np.float32);public[:45]=body;public[45+SKILLS.index(self.observed_skill)]=1
        public[51]=now-self.owner_started;public[52:60]=geometry
        if public[51]<0:raise ValueError('Observed native owner cannot begin in the future')
        device=self.model.device
        history={k:torch.as_tensor(np.stack([f[k] for f in frames]),device=device)[None] for k in ('rgb','proprio','actions_previous','action_valid')}
        history.update(depth_m=torch.as_tensor(np.stack([f['depth_m'] for f in frames]),device=device).float()[None,...,None],
            timestamps_s=torch.as_tensor(times,device=device)[None],camera_K=torch.as_tensor(frames[-1]['camera_K'],device=device)[None],
            T_base_optical=torch.as_tensor(frames[-1]['T_base_optical'],device=device)[None])
        history['proprio']=(history['proprio']-history['proprio'].new_tensor(self.normalization['mean']))/history['proprio'].new_tensor(self.normalization['std'])
        native=np.stack([refs[t] for t in range(first+1,last+1)]).reshape(1,2,20,18)
        with torch.no_grad():
            belief=filter_full_native(self.model,history,torch.as_tensor(native,device=device)).last
            for tick in range(last+1,end+1):
                a=torch.cat((torch.as_tensor(refs[tick],device=device)[None],torch.ones(1,1,device=device)),-1)
                belief=self.model._advance(belief,self.model.native_action(a),torch.tensor([.005],dtype=torch.float64,device=device),(1.,0.),False)
            belief=replace(belief,time_s=torch.tensor([now],dtype=torch.float64,device=device))
        path=self.output/(query_id+'-actual-inputs.npz')
        with path.open('xb') as f:
            np.savez_compressed(f,rgb=np.stack([x['rgb'] for x in frames]),depth_m=np.stack([x['depth_m'] for x in frames]),
                raw_proprio=np.stack([x['proprio'] for x in frames]),
                actions_previous=np.stack([x['actions_previous'] for x in frames]),action_valid=np.asarray([x['action_valid'] for x in frames]),
                camera_K=frames[-1]['camera_K'],T_base_optical=frames[-1]['T_base_optical'],
                RGB_times_s=times,current_public60=public,current_body_time_s=np.float64(now),
                native18_through_query=np.stack([refs[t] for t in range(first+1,end+1)]),native_physical_ticks=np.arange(first+1,end+1))
        return belief,public,dict(query_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),input_file=str(path),query_time_s=now,
            image_time_s=float(times[-1]),observed_skill=self.observed_skill,observed_native_owner=self.owner[1],
            native_owner_started_s=self.owner_started,private_catalog_or_future_inputs=False)
