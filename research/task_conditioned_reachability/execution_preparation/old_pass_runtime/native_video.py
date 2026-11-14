"""Encode actual native camera RGB at capture time, never state/log reconstruction."""
import hashlib,json,math,subprocess
from pathlib import Path
import numpy as np


class NativeCameraVideo:
    def __init__(self,root,width,height,fps=10.):
        self.root=Path(root);self.width=int(width);self.height=int(height);self.period=1./fps
        if self.width<=0 or self.height<=0 or not math.isfinite(fps) or fps<=0:raise ValueError('Positive native frame dimensions/rate required')
        self.frames=0;self.duplicates=0;self.first=None;self.last=None;self.closed=False;self.stream_hash=hashlib.sha256()
        self.index=(self.root/'native-camera-times.jsonl').open('x')
        self.stderr=(self.root/'native-camera-ffmpeg.log').open('xb')
        self.command=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-f','rawvideo','-pixel_format','rgb24',
                      '-video_size',f'{self.width}x{self.height}','-framerate',str(fps),'-i','pipe:0','-an',
                      '-c:v','libx264','-preset','veryfast','-crf','24','-threads','1','-pix_fmt','yuv420p',str(self.root/'native-camera-1x.mp4')]
        self.proc=subprocess.Popen(self.command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=self.stderr)
    def write(self,rgb,time_s):
        if self.closed:raise ValueError('Recorder is closed')
        rgb=np.asarray(rgb);t=float(time_s)
        if rgb.dtype!=np.uint8 or rgb.shape!=(self.height,self.width,3) or not math.isfinite(t):raise ValueError('Actual RGB/time contract mismatch')
        if self.last is not None:
            if abs(t-self.last)<=1e-9:
                self.duplicates+=1
                self.index.write(json.dumps(dict(event='duplicate_actual_epoch_not_extra_video_frame',time_s=t))+'\n');return
            if abs(t-self.last-self.period)>1e-6:raise RuntimeError('Native capture gap; do not pad/interpolate/retime missing frames')
        raw=rgb.tobytes();self.proc.stdin.write(raw);self.stream_hash.update(raw)
        self.index.write(json.dumps(dict(event='actual_native_camera_frame',index=self.frames,time_s=t,RGB_sha256=hashlib.sha256(raw).hexdigest()))+'\n')
        if self.first is None:self.first=t
        self.last=t;self.frames+=1
    def close(self):
        if self.closed:return
        self.closed=True
        self.proc.stdin.close();code=self.proc.wait(timeout=30);self.stderr.close();self.index.close()
        report=dict(schema='reach-actual-native-camera-recording-v1',frames=self.frames,first_native_time_s=self.first,last_native_time_s=self.last,
                    duplicate_same_epoch_captures=self.duplicates,width=self.width,height=self.height,source='actual OnboardObserver.capture RGB, before returning same packet',
                    raw_frame_stream_sha256=self.stream_hash.hexdigest(),encoder_exit=code,log_or_state_reconstruction=False,interpolation_or_padding=False,
                    same_packet_or_catalog_modified=False,original_speed=True)
        (self.root/'native-camera-provenance.json').write_text(json.dumps(report,indent=2)+'\n')
        if code!=0 or self.frames<1:raise RuntimeError('Actual native video failed; keep evidence, not deliver replay substitute')
