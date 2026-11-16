"""Encode actual direct-live raw master only. No renderer/world/state replay/interpolation."""
from pathlib import Path
import os,json,hashlib,subprocess,time,sys
import numpy as np
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encode(root,*,ffmpeg,expected_sha):
 root=Path(root);out=root.parent/'E-direct-live-1x.mp4';need=lambda x,m:None if x else(_ for _ in()).throw(ValueError(m));need(not out.exists(),'No overwrite');need(sha(ffmpeg)==expected_sha,'Frozen encoder binary');cl=json.loads((root/'closure.json').read_bytes());meta=json.loads((root/'metadata.json').read_bytes());spec=meta['camera_spec'];fps=200/spec['stride_physics_ticks'];need(cl['direct_from_current_live_runtime']and cl['complete_for_capture_grid'],'Actual complete direct-live grid required');n=0;begin=time.monotonic()
 command=[ffmpeg,'-nostdin','-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size',f"{spec['width']}x{spec['height']}",'-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264','-threads','2','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart','-n',str(out)]
 with (root.parent/'encoder.stderr').open('xb')as err:
  child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=err)
  try:
   for row in cl['chunks']:
    p=root/row['path'];need(sha(p)==row['sha256'],'Original raw chunk SHA')
    with np.load(p,allow_pickle=False)as a:
     rgb=a['rgb'];ticks=a['physics_tick'];times=a['actual_sim_time_s'];need(np.array_equal(ticks,np.arange(n,n+len(ticks))*spec['stride_physics_ticks'])and np.allclose(times,ticks*.005,atol=1e-7,rtol=0),'Original direct grid, no resampling');need(hashlib.sha256(rgb.tobytes()).hexdigest()==row['raw_RGB_bytes_sha256'],'Original RGB bytes');child.stdin.write(rgb.tobytes());n+=len(ticks)
   child.stdin.close();need(child.wait(timeout=180)==0,'Encoder failure')
  except BaseException:
   child.kill();child.wait();raise
 return dict(video_path=str(out),video_sha256=sha(out),actual_raw_frames=n,width=spec['width'],height=spec['height'],fps=fps,playback_speed=1,source='actual direct-live raw master',native_end_time_s=cl['actual_run_end_time_s'],native_time_not_inferred_from_clip_duration=True,no_state_replay_renderer_interpolation_resize_or_selected_success_cut=True,raw_master_retained=True,encoder_wall_s=time.monotonic()-begin)
if __name__=='__main__':
 root=Path(sys.argv[1]);v=encode(root,ffmpeg=sys.argv[2],expected_sha=sys.argv[3]);p=root.parent/'video-encoding-result.json'
 with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
 print(json.dumps(v))
