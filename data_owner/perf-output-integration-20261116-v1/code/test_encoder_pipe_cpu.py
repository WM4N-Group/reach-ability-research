"""Four synthetic color frames through real pinned FFmpeg; NOT task video."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scoped_io import ScopeIO
from controlled_process import ControlledProcess
ffmpeg=Path('/usr/bin/ffmpeg')
assert hashlib.sha256(ffmpeg.read_bytes()).hexdigest()=='36d94a605d612e4090d1b8aec889d0c0801c6eafb1593c90f5c0dfd2e2966a45'
with tempfile.TemporaryDirectory(prefix='data-encoder-CPU-not-task-')as td:
    root=Path(td);budget=ScopeIO(root,cap_bytes=4*1024**2,reserve_bytes=262144)
    argv=[str(ffmpeg),'-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
        '-s','16x16','-r','10','-i','pipe:0','-an','-c:v','libx264','-threads','1',
        '-pix_fmt','yuv420p','-movflags','frag_keyframe+empty_moov','-f','mp4','pipe:1']
    budget.begin_finalization()  # offline encoder only AFTER irreversible native seal
    process=ControlledProcess(argv,budget,stdout_path='synthetic.mp4',stderr_path='ffmpeg.stderr',
                              stdin=subprocess.PIPE,enabled=True)
    for value in (0,32,64,128):
        frame=bytes([value,value,value])*(16*16)
        offset=0
        while offset<len(frame):offset+=process.stdin.write(frame[offset:])
    process.stdin.close();capture=process.finish(timeout_s=10.)
    probe=subprocess.run(['/usr/bin/ffprobe','-v','error','-count_frames','-select_streams','v:0',
        '-show_entries','stream=nb_read_frames,width,height,avg_frame_rate','-of','json',str(root/'synthetic.mp4')],
        capture_output=True,check=True,timeout=10.)
    data=json.loads(probe.stdout);stream=data['streams'][0]
    assert stream['nb_read_frames']=='4'and stream['width']==16 and stream['height']==16
    assert budget.reconcile()==sum(p.stat().st_size for p in root.iterdir())
    print(json.dumps(dict(role='SYNTHETIC_FFMPEG_INTERFACE_ONLY_NOT_TASK_OR_RENDERING',
        frames=4,capture=capture,ffprobe=data,budget=budget.snapshot(),
        actual_live_camera_binding=False,old_E20_video_unchanged=True)))
