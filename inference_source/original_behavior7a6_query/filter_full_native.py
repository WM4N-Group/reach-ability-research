def filter_full_native(model,history,commands):
    """Assimilate real RGBD once per frame, all intervening native18 in order."""
    embedding=model.encoder(history);b,t=history['rgb'].shape[:2]
    if tuple(commands.shape)!=(b,t-1,20,18):raise ValueError('Lossless native18 intervals required')
    state=model.initial_state(history['timestamps_s'][:,0]);states=[];pm=[];ps=[];qm=[];qs=[]
    for i in range(t):
        if i:
            previous=history['timestamps_s'][:,i-1];end=history['timestamps_s'][:,i]
            dt=(end-previous)/20
            for j in range(20):
                a=torch.cat((commands[:,i-1,j],commands.new_ones((b,1))),-1)
                state=model._advance(state,model.native_action(a),dt,(1.,0.),False)
            state=replace(state,time_s=end.double())
        pm.append(state.mean);ps.append(state.std)
        mean,std=model._normal(model.posterior(torch.cat((state.h,embedding[:,i]),-1)))
        state=replace(state,z=mean,mean=mean,std=std,time_s=history['timestamps_s'][:,i].double(),
            anchor_time_s=history['timestamps_s'][:,i].double(),has_observation=torch.ones(b,dtype=torch.bool,device=model.device),is_posterior=torch.ones(b,dtype=torch.bool,device=model.device))
        states.append(state);qm.append(mean);qs.append(std)
    return ObservationTrace(tuple(states),torch.stack(pm,1),torch.stack(ps,1),torch.stack(qm,1),torch.stack(qs,1))
