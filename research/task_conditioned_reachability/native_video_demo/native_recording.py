"""Stream the LIVE Isaac RGB render to MP4; never reconstruct robot state."""
import hashlib
import json
from pathlib import Path
import subprocess
import time


def configure_view(cfg):
    cfg.viewer.eye=(3.0,-4.0,2.5)
    cfg.viewer.lookat=(.65,0.,.25)
    cfg.viewer.resolution=(960,640)


class NativeRecording:
    def __init__(self,env,output):
        self.env=env;self.output=Path(output);self.fps=10;self.count=0;self.last_step=None;self.last_row=None
        self.nonblack=0;self.render_wall_s=0.;self.closed=False
        self.log=(self.output/'native-video-frames.jsonl').open('x')
        self.stderr=(self.output/'native-video-encoder.log').open('x')
        self.video=self.output/'native-run-original-speed.mp4'
        self.proc=subprocess.Popen(['/usr/bin/ffmpeg','-hide_banner','-loglevel','error','-f','rawvideo','-pixel_format','rgb24',
            '-video_size','960x640','-framerate','10','-i','-','-an','-c:v','libx264','-threads','2','-preset','veryfast',
            '-crf','22','-pix_fmt','yuv420p','-movflags','+faststart','-n',str(self.video)],
            stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=self.stderr)

    def capture(self,row,force=False):
        import numpy as np
        import torch
        step=row['step'];self.last_row=row
        if self.last_step==step:return
        if not force and self.last_step is not None and step%5:return
        b=self.env.unwrapped;r=b.scene['robot'];stamp=int(b.episode_length_buf[0]);q=r.data.joint_pos.clone();root=r.data.root_state_w.clone()
        started=time.perf_counter();image=None
        for _ in range(12 if self.count==0 else 1):
            image=self.env.render()
            if image is not None and image.size and image.max()>0:break
        self.render_wall_s+=time.perf_counter()-started
        if int(b.episode_length_buf[0])!=stamp or not torch.equal(q,r.data.joint_pos) or not torch.equal(root,r.data.root_state_w):
            raise RuntimeError('Rendering changed physical state or clock')
        if image is None or image.shape!=(640,960,3) or image.dtype!=np.uint8:raise RuntimeError('Invalid live RGB render')
        image=np.ascontiguousarray(image);self.nonblack+=int(image.max()>0)
        self.proc.stdin.write(image.tobytes())
        phase=('return_navigation' if row.get('return_nav_actor_input') is not None else
               'push' if row.get('push_active') else row.get('entry_center_stage',row.get('phase','initial_navigation')))
        self.log.write(json.dumps(dict(frame=self.count,control_step=step,sim_time_s=row['time_s'],phase=phase,
            rgb_sha256=hashlib.sha256(image.tobytes()).hexdigest(),source='LIVE_Isaac_env.render_rgb_array'))+'\n');self.log.flush()
        self.last_step=step;self.count+=1

    def close(self,report):
        if self.closed:return
        self.closed=True
        self.proc.stdin.close();rc=self.proc.wait(timeout=90);self.log.close();self.stderr.close()
        metadata=dict(schema='native-live-Isaac-video-v1',original_simulator_footage=True,log_reconstruction=False,
            video=str(self.video),fps=self.fps,frames=self.count,nonblack_frames=self.nonblack,
            playback_speed=1,control_sampling='first, every fifth 50Hz control step, and final logged state; final timing tolerance<0.1s',
            rendering_without_physics_step_verified=True,render_wall_s=self.render_wall_s,
            actual_task_outcome=report.get('outcome'),task_success_not_inferred_from_video=True,
            continuous_single_episode=True,encoder_returncode=rc)
        if self.video.exists():metadata['video_sha256']=hashlib.sha256(self.video.read_bytes()).hexdigest()
        (self.output/'native-video.json').write_text(json.dumps(metadata,indent=2)+'\n')
        if rc or self.count<2 or self.nonblack<self.count*.9:raise RuntimeError('Native video encoding or visibility check failed; do not retry automatically')
