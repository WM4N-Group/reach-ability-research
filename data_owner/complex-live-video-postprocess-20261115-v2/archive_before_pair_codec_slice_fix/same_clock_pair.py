"""Post-close source-RGB pairing only. No renderer/world or time warp.
Original panels are unchanged RGB; black ENDED panels/footer are PRESENTATION,
not new experiment frames. Existing exact-RGB FFV1/decode verifier is reused.
"""
from pathlib import Path
import json,hashlib,math,os,select,subprocess,tempfile,time
from raw_third_view import raw_frames,sha,need,ACTUAL,comparison_presentation
from raw_video_encode import decoded_rgb_digest

def source_active(index,*,count,end_tick,stride):
 need(type(index)is int and index>=0 and type(stride)is int and stride>0,'Exact source tick grid')
 need(count==end_tick//stride+1,'Complete raw master including every actual capture epoch')
 if index<count:return True
 need(index*stride>end_tick,'Never silently pad a missing source frame before actual run end')
 return False

def encode_same_clock_pair(left,right,output,*,ffmpeg_path,speed=1,timeout_s=600):
 from PIL import Image,ImageDraw
 import numpy as np
 roots=[Path(left),Path(right)];out=Path(output);exe=Path(ffmpeg_path);need(exe.is_absolute()and exe.is_file(),'Existing explicit codec only; no installation')
 need(out.suffix=='.mkv'and not out.exists()and not out.with_suffix('.mkv.json').exists(),'New exclusive derived media path')
 cs=[json.loads((r/'closure.json').read_bytes())for r in roots];ms=[json.loads((r/'metadata.json').read_bytes())for r in roots]
 ends=[c['actual_run_end_time_s']for c in cs];plan=comparison_presentation(*cs,speed=speed,completion_times_s=ends);spec=ms[0]['camera_spec'];need(all(m['camera_spec']==spec for m in ms),'Same full camera/resolution/source rate, no resizing or reprojecting')
 w,h,stride=spec['width'],spec['height'],spec['stride_physics_ticks'];counts=[c['archived_frames']for c in cs];ticks=[c['final_physics_tick']for c in cs];need(all(abs(e-t*.005)<1e-7 for e,t in zip(ends,ticks)),'Actual run-end clocks are source ticks, not video durations')
 for count,tick in zip(counts,ticks):source_active(0,count=count,end_tick=tick,stride=stride)
 results=[]
 for r in roots:
  p=r.parent/'result.json';need(p.is_file(),'Literal original result/status reference for each original master');results.append(json.loads(p.read_bytes()))
 sources=[dict(root=str(r.resolve()),metadata_sha256=sha(r/'metadata.json'),closure_sha256=sha(r/'closure.json'),result_sha256=sha(r.parent/'result.json'),literal_status=v['status'],main_world_end_s=c['actual_run_end_time_s'],origin=c['origin'])for r,c,v in zip(roots,cs,results)]
 fps=1/(stride*.005);n=max(counts);footer=32;out.parent.mkdir(parents=True,exist_ok=True);mapping=out.with_suffix('.frame-map.jsonl');need(not mapping.exists(),'Never replace source-to-presentation clock map');binary=sha(exe)
 command=[str(exe),'-hide_banner','-loglevel','error','-nostdin','-n','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{2*w}x{h+footer}','-framerate',str(fps*speed),'-i','pipe:0','-an','-c:v','ffv1','-level','3','-pix_fmt','bgr0','-slices','1','-threads','1',str(out)]
 started=time.monotonic();digest=hashlib.sha256();iterators=[iter(raw_frames(r))for r in roots]
 with tempfile.TemporaryFile()as errors, mapping.open('x')as clockmap:
  process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=errors)
  try:
   fd=process.stdin.fileno();os.set_blocking(fd,False)
   for i in range(n):
    tick=i*stride;stamp=tick*.005;panels=[];labels=[];rows=[]
    for j in(0,1):
     name=('A','B')[j];active=source_active(i,count=counts[j],end_tick=ticks[j],stride=stride)
     if active:
      st,ss,rgb=next(iterators[j]);need(st==tick and abs(ss-stamp)<1e-7,'Same exact physical tick; no nearest/interpolation/retiming');need(rgb.shape==(h,w,3),'No resizing/scaling');panels.append(rgb);labels.append(f'{name}: t={ss:.3f}s\n{results[j]["status"]}');rows.append(dict(source_frame_index=i,physical_tick=st,actual_sim_time_s=ss,ended_panel=False))
     else:
      panels.append(np.zeros((h,w,3),dtype=np.uint8));labels.append(f'{name}: ENDED at {ends[j]:.6f}s\n{results[j]["status"]}');rows.append(dict(source_frame_index=None,physical_tick=None,actual_sim_time_s=None,ended_panel=True,original_run_end_s=ends[j]))
    frame=np.zeros((h+footer,2*w,3),dtype=np.uint8);frame[:h,:w]=panels[0];frame[:h,w:]=panels[1];bar=Image.new('RGB',(2*w,footer),(0,0,0))
    for j in(0,1):
     half=Image.new('RGB',(w,footer),(0,0,0));ImageDraw.Draw(half).multiline_text((2,2),labels[j],fill='white',spacing=1);bar.paste(half,(j*w,0))
    frame[h:]=np.asarray(bar)
    need(np.array_equal(frame[:h,:w],panels[0])and np.array_equal(frame[:h,w:],panels[1]),'Source panels preserved bitwise; captions never cover original pixels')
    raw=frame.tobytes();digest.update(raw);view=memoryview(raw)
    while view:
     remaining=timeout_s-(time.monotonic()-started);need(remaining>0,'Bound pure CPU presentation encoding')
     need(process.poll()is None,'Encoder ended before all source-derived frames');_,ready,_=select.select([],[fd],[],min(1.,remaining))
     if ready:
      try:view=view[os.write(fd,view):]
      except BlockingIOError:pass
    clockmap.write(json.dumps(dict(presentation_frame=i,common_physics_tick=tick,common_sim_time_s=stamp,panels=rows),separators=(',',':'))+'\n')
   for gen in iterators:
    try:next(gen)
    except StopIteration:pass
    else:raise ValueError('Extra unaccounted source frame')
   process.stdin.close();process.wait(timeout=max(.001,timeout_s-(time.monotonic()-started)));errors.seek(0);need(process.returncode==0,'Pure CPU pair codec failed: '+errors.read().decode(errors='replace')[:1000])
  except BaseException:
   if process.poll()is None:process.kill();process.wait()
   raise
 decoded,decode_cmd=decoded_rgb_digest(exe,out,expected_bytes=n*(2*w)*(h+footer)*3,timeout_s=max(.001,timeout_s-(time.monotonic()-started)));need(decoded==digest.hexdigest(),'Encoded derived RGB roundtrip differs');need(sha(exe)==binary,'Codec identity changed')
 for r,s in zip(roots,sources):need(sha(r/'metadata.json')==s['metadata_sha256']and sha(r/'closure.json')==s['closure_sha256']and sha(r.parent/'result.json')==s['result_sha256'],'Original source master/result changed')
 receipt=dict(schema='Data-same-tick-source-RGB-pair-presentation-v1',role='DERIVED_PRESENTATION_NOT_A_NEW_CAMERA_OR_METHOD_RESULT',sources=sources,output=str(out),output_sha256=sha(out),frame_map=str(mapping),frame_map_sha256=sha(mapping),source_panel_resolution=[w,h],output_resolution=[2*w,h+footer],frames=n,source_capture_fps=fps,uniform_playback_multiplier=speed,same_tick_not_nearest_or_time_warp=True,black_ENDED_panels_explicit_presentation_only=True,original_panel_pixels_preserved=True,decoded_exact_RGB_sha256=decoded,exact_RGB_codec_roundtrip_verified=True,ffmpeg_sha256=binary,command=command,decode_command=decode_cmd,new_simulation_or_renderer_calls=0,original_master_bytes_and_clocks_preserved=True,task_T_COMPLEX_result_not_inferred=True,wall_s=time.monotonic()-started,presentation_plan=plan)
 with out.with_suffix('.mkv.json').open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
 return receipt
