"""Decode one already recorded live RGB frame, no Runtime/render/physics calls."""
from pathlib import Path
import subprocess,shlex,json,base64,hashlib
M=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,hashlib,io,base64
import numpy as np
from PIL import Image
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/runtime/workers/data-46308-T-COMPLEX-01-v2-camera-source-components-zero-20261115-v1');v=json.loads((R/'result.json').read_bytes());assert v['passed']and v['actual_task_steps']==0 and v['actual_HD_frame']['frames']==1;d=R/'raw-third-view-preflight-frame';row=v['raw_HD_frame_closure']['chunks'][0];p=d/row['path'];sha=lambda b:hashlib.sha256(b).hexdigest();assert sha(p.read_bytes())==row['sha256']
with np.load(p,allow_pickle=False)as z:
 rgb=z['rgb'];assert rgb.dtype==np.uint8 and rgb.shape==(1,540,960,3)and z['physics_tick'].tolist()==[0]and z['actual_sim_time_s'].tolist()==[0.];assert sha(rgb.tobytes())==row['raw_RGB_bytes_sha256'];raw=rgb[0].copy()
f=io.BytesIO();Image.fromarray(raw).save(f,format='PNG');png=f.getvalue();assert np.array_equal(np.asarray(Image.open(io.BytesIO(png))),raw)
print(json.dumps(dict(PNG=base64.b64encode(png).decode(),proof=dict(actual_source_scope=R.name,source_chunk_sha256=row['sha256'],raw_RGB_bytes_sha256=row['raw_RGB_bytes_sha256'],PNG_sha256=sha(png),width=960,height=540,physics_tick=0,time_s=0.,pixel_exact_PNG_decode=True,not_video_or_AB=True,no_new_renderer_or_Runtime_calls=True))))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],capture_output=True,text=True,timeout=60);assert r.returncode==0,r.stderr;v=json.loads(r.stdout);png=base64.b64decode(v['PNG']);assert hashlib.sha256(png).hexdigest()==v['proof']['PNG_sha256'];(M/'single-live-HD-world0-preview.png').write_bytes(png);(M/'single-live-HD-world0-preview-proof.json').write_text(json.dumps(v['proof'],indent=2)+'\n');print(json.dumps(v['proof'],indent=2))
