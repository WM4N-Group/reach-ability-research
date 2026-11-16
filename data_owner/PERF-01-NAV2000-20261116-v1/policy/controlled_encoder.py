"""Post-seal original raw-master decode to controlled encoder/probe outputs.
No renderer/state restore/resampling. Every persisted child byte goes via parent.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import time
from controlled_process import ControlledProcess


def encode_raw_master(raw_module,root,budget,*,ffmpeg,ffmpeg_sha256,ffprobe,
                      ffprobe_sha256,timeout_s=180.,enabled=False,
                      allow_software_fixture=False):
    if enabled is not True:return None
    if not budget.state.sealed or not budget.finalizing:
        raise ValueError('Offline encoder requires irreversible native seal')
    root=Path(root);parent=root.parent;closure=json.loads((root/'closure.json').read_bytes())
    metadata=json.loads((root/'metadata.json').read_bytes());spec=metadata['camera_spec']
    if not closure['complete_for_capture_grid'] or (not allow_software_fixture and not closure['direct_from_current_live_runtime']):
        raise ValueError('Complete actual direct-live grid required; no repair/replay')
    for p,pin in((ffmpeg,ffmpeg_sha256),(ffprobe,ffprobe_sha256)):
        if Path(p).is_symlink()or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=pin:
            raise ValueError('Exact frozen encoder/probe binary required')
    fps=200/spec['stride_physics_ticks'];output=parent/'direct-live-1x.mp4'
    argv=[str(ffmpeg),'-nostdin','-v','error','-f','rawvideo','-pixel_format','rgb24',
        '-video_size',str(spec['width'])+'x'+str(spec['height']),'-framerate',str(fps),
        '-i','pipe:0','-an','-c:v','libx264','-threads','2','-preset','fast','-crf','18',
        '-pix_fmt','yuv420p','-movflags','frag_keyframe+empty_moov','-f','mp4','pipe:1']
    child=ControlledProcess(argv,budget,stdout_path=output,stderr_path=parent/'encoder.stderr',
                            stdin=subprocess.PIPE,enabled=True)
    n=0;begin=time.monotonic()
    try:
        for tick,stamp,rgb in raw_module.raw_frames(root,allow_software_fixture=allow_software_fixture):
            data=memoryview(rgb).cast('B');offset=0
            while offset<len(data):
                count=child.stdin.write(data[offset:])
                if type(count)is not int or count<=0:raise RuntimeError('Encoder input partial/failed write')
                offset+=count
            n+=1
        child.stdin.close();capture=child.finish(timeout_s=timeout_s)
    except BaseException:
        if child.process.poll()is None:child.process.kill()
        if child.stdin is not None and not child.stdin.closed:
            try:child.stdin.close()
            except BaseException:pass
        if not child.closed:
            try:child.finish(timeout_s=2.)
            except BaseException:pass
        raise
    probe_path=parent/'ffprobe.json'
    probe=ControlledProcess([str(ffprobe),'-v','error','-count_frames','-select_streams','v:0',
        '-show_entries','stream=width,height,avg_frame_rate,nb_read_frames','-of','json',str(output)],
        budget,stdout_path=probe_path,stderr_path=parent/'ffprobe.stderr',enabled=True)
    probe_capture=probe.finish(timeout_s=min(timeout_s,30.))
    if probe_path.stat().st_size>65536:raise ValueError('Unexpected unbounded probe metadata')
    info=json.loads(probe_path.read_bytes());stream=info['streams'][0]
    if (len(info['streams'])!=1 or int(stream['nb_read_frames'])!=n or n!=closure['archived_frames']
        or stream['width']!=spec['width']or stream['height']!=spec['height']):
        raise ValueError('Actual decode disagrees with original raw master')
    digest=hashlib.sha256()
    with output.open('rb')as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return dict(video_path=str(output),video_sha256=digest.hexdigest(),
        actual_raw_frames=n,width=spec['width'],height=spec['height'],fps=fps,playback_speed=1,
        native_end_time_s=closure['actual_run_end_time_s'],native_time_not_inferred_from_clip_duration=True,
        no_state_replay_renderer_interpolation_resize_or_selected_success_cut=True,
        raw_master_retained=True,encoder_wall_s=time.monotonic()-begin,
        encoder_capture=capture,ffprobe_capture=probe_capture,ffprobe=info,
        software_fixture=allow_software_fixture)
