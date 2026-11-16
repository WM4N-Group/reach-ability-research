"""Original per-guard RSS/Torch-reserved high-water/wall checks, no probe or IO."""
import math
import os
import resource
import sys
import time
from scoped_io import PolicyStop


def make_original_fast_health(torch,*,state,start_mono,wall_cap_s,rss_cap_bytes,
                              gpu_cap_bytes,teardown_reserve_s=30.,clock=time.monotonic):
    if (sys.platform!='linux' or torch is None or
        not callable(getattr(getattr(torch,'cuda',None),'is_initialized',None))):
        raise ValueError('Explicit real bound Torch module and Linux RSS contract')
    if (type(rss_cap_bytes)is not int or rss_cap_bytes<=0 or
        type(gpu_cap_bytes)is not int or gpu_cap_bytes<=0 or
        not all(type(v)in(int,float)and math.isfinite(v)for v in
                (start_mono,wall_cap_s,teardown_reserve_s)) or
        not 0<teardown_reserve_s<wall_cap_s):
        raise ValueError('Finite original wall/teardown and explicit memory caps')
    pid=os.getpid();was_initialized=False
    metrics=dict(calls=0,peak_RSS_bytes=0,peak_Torch_reserved_bytes=0,
                 CUDA_seen_initialized=False)
    def health():
        nonlocal was_initialized
        if os.getpid()!=pid:state.fail('Fast health belongs to original process')
        elapsed=clock()-start_mono
        if not math.isfinite(elapsed)or elapsed<0 or elapsed>=wall_cap_s-teardown_reserve_s:
            state.fail('Original finite wall cap with teardown reserve')
        rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if type(rss)is not int or rss<=0 or rss>rss_cap_bytes:state.fail('Original own RSS high-water cap/unknown RSS')
        metrics['peak_RSS_bytes']=max(metrics['peak_RSS_bytes'],rss)
        initialized=torch.cuda.is_initialized()
        if type(initialized)is not bool:state.fail('Unknown CUDA initialization state')
        if was_initialized and not initialized:state.fail('CUDA initialization identity regressed')
        if initialized:
            # Physical GPU is already frozen through CUDA_VISIBLE_DEVICES UUID.
            # No init/sync/model/Actor call; same per-call current/max reserved checks.
            values=(torch.cuda.memory_reserved(device=0),torch.cuda.max_memory_reserved(device=0))
            if any(type(v)is not int or v<0 or v>gpu_cap_bytes for v in values):
                state.fail('Original own GPU current/high-water cap or unknown memory')
            metrics['peak_Torch_reserved_bytes']=max(metrics['peak_Torch_reserved_bytes'],*values)
            was_initialized=True;metrics['CUDA_seen_initialized']=True
        metrics['calls']+=1
        return True
    health.metrics=metrics
    return health
