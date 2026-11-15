def resize_packet(packet):
    """Exactly the public-export bilinear RGB/center-nearest quantized depth."""
    rgb=packet['rgb'][0,0].numpy();depth=packet['depth_m'][0,0,...,0].numpy();h,w=rgb.shape[:2]
    yy=np.minimum((np.arange(64)+.5)*h/64,h-1).astype(int);xx=np.minimum((np.arange(96)+.5)*w/96,w-1).astype(int)
    dd=depth[yy][:,xx];valid=np.isfinite(dd)&(dd>=.05)&(dd<=15)
    dd=np.where(valid,dd,0).astype(np.float16).astype(np.float32)
    K=packet['camera_K'][0].numpy().copy();K[0]*=96/w;K[1]*=64/h
    return dict(rgb=np.asarray(Image.fromarray(rgb).resize((96,64),Image.Resampling.BILINEAR)).copy(),depth_m=dd,
        proprio=packet['proprio'][0,0].numpy().copy(),time_s=float(packet['timestamps_s'][0,0]),camera_K=K,
        T_base_optical=packet['T_base_optical'][0].numpy().copy(),actions_previous=packet['actions_previous'][0,0].numpy().copy(),
        action_valid=bool(packet['action_valid'][0,0]))
