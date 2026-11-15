"""Post-close CPU codec of ONLY directly captured raw RGB. No renderer/replay.
Original raw frames stay immutable. Optional output is never a native-run gate.
"""
from pathlib import Path
import hashlib,json,math,os,select,subprocess,tempfile,time
from raw_third_view import raw_frames,sha,need


def decoded_rgb_digest(exe, output, *, expected_bytes, timeout_s):
    """Bounded CPU decode verification; no renderer, no new experiment frames."""
    command=[str(exe),'-hide_banner','-loglevel','error','-nostdin','-threads','1',
             '-i',str(output),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','pipe:1']
    started=time.monotonic();total=0;digest=hashlib.sha256()
    with tempfile.TemporaryFile() as errors:
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stdin=subprocess.DEVNULL,stderr=errors)
        try:
            fd=process.stdout.fileno();os.set_blocking(fd,False)
            while True:
                remaining=timeout_s-(time.monotonic()-started)
                need(remaining>0,'Bound optional decoder wall time')
                ready,_,_=select.select([fd],[],[],min(1.,remaining))
                if not ready:continue
                try:chunk=os.read(fd,65536)
                except BlockingIOError:continue
                if not chunk:break
                total+=len(chunk);need(total<=expected_bytes,'Decoded extra bytes/frames')
                digest.update(chunk)
            process.stdout.close();process.wait(timeout=max(.001,timeout_s-(time.monotonic()-started)))
            errors.seek(0)
            need(process.returncode==0,'CPU decode failure: '+errors.read().decode(errors='replace')[:1000])
            need(total==expected_bytes,'Decoded missing bytes/frames')
        except BaseException:
            if process.poll() is None:process.kill();process.wait()
            raise
    return digest.hexdigest(),command


def encode_ffv1(root, output, *, ffmpeg_path, speed=1, timeout_s=1200,
                allow_software_fixture=False):
    root,output,exe=Path(root),Path(output),Path(ffmpeg_path)
    need(exe.is_file() and exe.is_absolute(), 'Existing explicitly pinned CPU ffmpeg; do not install')
    need(not output.exists() and not output.with_suffix(output.suffix+'.json').exists(), 'Never overwrite old media')
    need(output.suffix=='.mkv' and type(speed) in (int,float) and math.isfinite(speed) and speed>0,
         'Explicit Matroska FFV1 and uniformly labelled speed')
    need(type(timeout_s) in (int,float) and math.isfinite(timeout_s) and timeout_s>0, 'Bound CPU encoder wall time')
    c=json.loads((root/'closure.json').read_bytes());m=json.loads((root/'metadata.json').read_bytes())
    need(c['complete_for_capture_grid'] is True, 'Do not hide missing raw epochs by CFR encoding')
    spec=m['camera_spec'];fps=1/(spec['stride_physics_ticks']*.005)
    need(spec['width']>=4 and spec['height']>=2,
         'Pinned FFV1 wrapper requires width>=4 height>=2; raw master still valid independently')
    binary_before=sha(exe)
    source_before=dict(metadata=sha(root/'metadata.json'),closure=sha(root/'closure.json'))
    output.parent.mkdir(parents=True,exist_ok=True)
    command=[str(exe),'-hide_banner','-loglevel','error','-nostdin','-n',
        '-f','rawvideo','-pixel_format','rgb24','-video_size',str(spec['width'])+'x'+str(spec['height']),
        '-framerate',str(fps*speed),'-i','pipe:0','-an','-c:v','ffv1','-level','3',
        '-pix_fmt','bgr0','-slices','4','-threads','1',str(output)]
    started=time.monotonic();pixels=hashlib.sha256();count=0
    with tempfile.TemporaryFile() as errors:
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=errors)
        try:
            fd=process.stdin.fileno();os.set_blocking(fd,False)
            for tick,stamp,rgb in raw_frames(root,allow_software_fixture=allow_software_fixture):
                need(tick==count*spec['stride_physics_ticks'] and abs(stamp-tick*.005)<1e-7,
                     'No time warp/gap fill/nearest frame')
                raw=rgb.tobytes();pixels.update(raw);view=memoryview(raw)
                while view:
                    remaining=timeout_s-(time.monotonic()-started)
                    need(remaining>0,'Bound optional encoder timeout; no native retry')
                    need(process.poll() is None,'CPU ffmpeg exited before all source frames')
                    _,ready,_=select.select([], [fd], [], min(1.,remaining))
                    if ready:
                        try:view=view[os.write(fd,view):]
                        except BlockingIOError:pass
                count+=1
            process.stdin.close();process.wait(timeout=max(.001,timeout_s-(time.monotonic()-started)))
            errors.seek(0);error=errors.read().decode(errors='replace')
            need(process.returncode==0, 'CPU FFV1 failure: '+error[:1000])
        except BaseException:
            if process.poll() is None:process.kill();process.wait()
            raise  # Never touch/delete a native run; retain any failed output.
    need(count==c['archived_frames'] and count>0,'One video frame per original raw frame')
    decoded_sha,decode_command=decoded_rgb_digest(exe,output,
        expected_bytes=count*spec['width']*spec['height']*3,
        timeout_s=max(.001,timeout_s-(time.monotonic()-started)))
    need(decoded_sha==pixels.hexdigest(),'Actual encoded RGB differs from raw master; retain failed clip, never publish as lossless')
    need(sha(exe)==binary_before,'CPU codec binary changed during encode/decode')
    need(source_before==dict(metadata=sha(root/'metadata.json'),closure=sha(root/'closure.json')),
         'Raw master changed during optional encoding')
    out=dict(schema='Data-direct-source-raw-RGB-FFV1-codec-receipt-v1',origin=c['origin'],
        role=c['role'],source_master_root=str(root.resolve()),source_master_SHA=source_before,
        output=str(output.resolve()),output_sha256=sha(output),ffmpeg_binary_sha256=binary_before,
        command=command,decode_verification_command=decode_command,frames=count,
        source_RGB_all_bytes_sha256=pixels.hexdigest(),decoded_RGB_all_bytes_sha256=decoded_sha,
        actual_encoded_output_exact_RGB_roundtrip_verified=True,
        original_acquisition_fps=fps,uniform_playback_multiplier=speed,
        actual_sim_end_time_s=c['actual_run_end_time_s'],new_renderer_or_state_replay_or_physics_calls=0,
        interpolated_or_synthesized_frames=0,raw_master_preserved=True,
        presentation_not_a_new_experiment_or_native_success_gate=True,
        completion_time_must_come_from_original_events_not_container_duration=True)
    with output.with_suffix(output.suffix+'.json').open('x') as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write(chr(10))
    return out
