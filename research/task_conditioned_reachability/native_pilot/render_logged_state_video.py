"""Offline measured-state visualization, NOT Isaac footage or a dynamics replay.

Only recorded robot root/q are prescribed to a PRIVATE rendering MjData.
Box center is shown only after it is recorded; orientation is schematic because
control.jsonl does not record box quaternions throughout the run. No actor,
controller, mj_step, Isaac App, source modification or original ledger update.
"""
import argparse,bisect,fcntl,hashlib,json,math,os,subprocess,sys,time
from pathlib import Path


def load(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read_lines(path):
    with path.open() as f:return [json.loads(line) for line in f]


def row_at(rows,sim_time):
    index=max(0,bisect.bisect_right([r['time_s'] for r in rows],sim_time)-1)
    return index,rows[index],sim_time>=rows[-1]['time_s']-1e-9


def box_observations(rows,geometry):
    observations=[]
    for q in geometry:
        if q.get('event')=='finite_tip_query':observations.append((q['time_s'],q['box_position_w'],'recorded_query_center'))
    for row in rows:
        position=row.get('push',{}).get('box_position')
        if position is not None:observations.append((row['time_s'],position,'recorded_control_center'))
    return sorted(observations,key=lambda p:p[0])


def box_at(observations,sim_time):
    index=bisect.bisect_right([p[0] for p in observations],sim_time)-1
    if index<0:return None
    stamp,position,origin=observations[index]
    return dict(time_s=stamp,position=position,origin=origin,orientation='SCHEMATIC_identity_NOT_measured')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--geometry-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Preserve any existing output; use a new revision')
    args.output.mkdir(parents=True)
    lock=(args.output/'render.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    # CPU-only Mesa context, explicitly reject falling back onto another team's GPU.
    os.environ.update(MUJOCO_GL='egl',LIBGL_ALWAYS_SOFTWARE='1',MESA_LOADER_DRIVER_OVERRIDE='llvmpipe',
        __EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/50_mesa.json',LP_NUM_THREADS='2')
    import numpy as np
    import mujoco
    from PIL import Image,ImageDraw,ImageFont
    from OpenGL.GL import glGetString,GL_RENDERER,GL_VENDOR
    sys.path.insert(0,str(args.geometry_root))
    from reconfigurable_navigation.piper_robot_profile import apply_piper_robot_profile,apply_piper_collision_profile
    ledger=load(args.root/'physical_ledger.json');entries={e['arm']:e for e in ledger['entries'] if e['seed']==120401}
    rows={};reports={};queries={};boxes={};hashes=[]
    for arm in ('E0','E1'):
        out=args.root/'runs'/f'seed120401-{arm}';entry=entries[arm]
        for name,key in [('control.jsonl','control_sha256'),('report.json','report_sha256'),('entry_geometry.jsonl','geometry_sha256')]:
            p=out/name;assert sha(p)==entry[key],name
            hashes.append(dict(path=str(p),sha256=sha(p)))
        rows[arm]=read_lines(out/'control.jsonl');reports[arm]=load(out/'report.json');queries[arm]=read_lines(out/'entry_geometry.jsonl')
        boxes[arm]=box_observations(rows[arm],queries[arm])
    xml=args.geometry_root/'robots/go2_piper/go2piper.xml';spec=mujoco.MjSpec.from_file(str(xml));assets=[xml]
    for mesh in spec.meshes:
        mesh.file=str(args.geometry_root/'robots/go2_piper/assets'/Path(mesh.file).name);assets.append(Path(mesh.file))
    apply_piper_robot_profile(spec);apply_piper_collision_profile(spec)
    spec.worldbody.add_geom(name='visual_ground',type=mujoco.mjtGeom.mjGEOM_PLANE,size=[6,6,.01],rgba=[.87,.89,.91,1],contype=0,conaffinity=0)
    spec.worldbody.add_geom(name='world_goal_marker',type=mujoco.mjtGeom.mjGEOM_CYLINDER,size=[.055,.002,0],pos=[-.25,0,.003],rgba=[.05,.7,.3,1],contype=0,conaffinity=0)
    spec.worldbody.add_light(pos=[0,-2,4],dir=[0,0,-1],diffuse=[.8,.8,.8])
    body=spec.worldbody.add_body(name='logged_box_center_PROXY',mocap=True,pos=[0,0,-2])
    body.add_geom(name='box_orientation_SCHEMATIC',type=mujoco.mjtGeom.mjGEOM_BOX,size=[.6,.6,.1],rgba=[.9,.45,.12,.40],contype=0,conaffinity=0)
    model=spec.compile();width,height=640,420;model.vis.global_.offwidth=width;model.vis.global_.offheight=height
    data={arm:mujoco.MjData(model) for arm in rows}
    renderer=mujoco.Renderer(model,height=height,width=width)
    gl_renderer=glGetString(GL_RENDERER).decode();gl_vendor=glGetString(GL_VENDOR).decode()
    if 'llvmpipe' not in gl_renderer.lower():raise RuntimeError('Refuse GPU renderer: '+gl_renderer)
    camera=mujoco.MjvCamera();camera.lookat[:]=[.6,0,.28];camera.distance=3.7;camera.azimuth=130;camera.elevation=-23
    option=mujoco.MjvOption();option.geomgroup[:]=[1,1,1,1,1,1]
    geom=model.geom('box_orientation_SCHEMATIC').id;mocap=model.body('logged_box_center_PROXY').mocapid[0]
    names={a:reports[a]['joint_names'] for a in rows};addresses={a:[model.joint(n).qposadr[0] for n in names[a]] for a in rows}
    fk_calls=0
    def prescribed(arm,row):
        nonlocal fk_calls
        d=data[arm];assert len(row['q'])==len(names[arm])
        d.qpos[:3]=row['root_position'];d.qpos[3:7]=row['root_quaternion'];d.qpos[addresses[arm]]=row['q']
        mujoco.mj_kinematics(model,d);mujoco.mj_comPos(model,d);mujoco.mj_camlight(model,d);fk_calls+=1
        return d
    hand_checks=[]
    for arm in rows:
        for query in queries[arm]:
            if query.get('event')!='finite_tip_query':continue
            assert query['joint_names']==names[arm]
            row=dict(q=query['q_rad'],root_position=query['root_position_w'],root_quaternion=query['root_quaternion_wxyz'])
            d=prescribed(arm,row);error=float(np.linalg.norm(d.xpos[model.body('end_effector').id]-query['source_hand_position_w']))
            if error>.0002:raise ValueError('Visual model/recorded geometry mismatch '+str(error))
            hand_checks.append(dict(arm=arm,query_id=query['query_id'],error_m=error))
    regular='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    font=lambda size,heavy=False:ImageFont.truetype(bold if heavy else regular,size)
    total_w,total_h=2*width,600;fps=20;speed=3.;horizon=max(v[-1]['time_s'] for v in rows.values());frame_count=math.ceil(horizon/speed*fps)+fps
    video=args.output/'e0-e1-logged-state-reconstruction-3x.mp4';fflog=(args.output/'ffmpeg.log').open('x')
    proc=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{total_w}x{total_h}','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart','-n',str(video)],stdin=subprocess.PIPE,stdout=fflog,stderr=subprocess.STDOUT)
    cache={};began=time.time();frame_map=[]
    try:
        for frame in range(frame_count):
            sim_time=min(horizon,frame*speed/fps);image=Image.new('RGB',(total_w,total_h),'#eef2f7');draw=ImageDraw.Draw(image)
            draw.text((18,8),'Go2 + Piper | seed 120401 | measured-state log reconstruction',font=font(25,True),fill='#182e49')
            draw.text((18,41),'NOT original Isaac camera footage  |  3x simulation speed  |  green disk = world goal',font=font(18),fill='#34465b')
            frame_record=dict(frame=frame,display_sim_time_s=sim_time,arms={})
            for a_index,arm in enumerate(('E0','E1')):
                index,row,ended=row_at(rows[arm],sim_time)
                if cache.get(arm,(-1,))[0]!=index:
                    d=prescribed(arm,row);box=box_at(boxes[arm],row['time_s'])
                    model.geom_rgba[geom,3]=.40 if box else 0.
                    if box:d.mocap_pos[mocap]=box['position'];d.mocap_quat[mocap]=[1,0,0,0]
                    else:d.mocap_pos[mocap]=[0,0,-2]
                    # Mocap visualization update is still kinematics only, never mj_step.
                    mujoco.mj_kinematics(model,d);mujoco.mj_camlight(model,d);fk_calls+=1
                    renderer.update_scene(d,camera=camera,scene_option=option)
                    cache[arm]=(index,Image.fromarray(renderer.render().copy()),box)
                x=a_index*width;image.paste(cache[arm][1],(x,80));draw=ImageDraw.Draw(image)
                phase=row.get('phase','startup / phase not recorded')
                draw.rectangle((x+8,87,x+width-8,151),fill='#f6f8fb')
                draw.text((x+18,91),f"{arm} | sim t={row['time_s']:.2f}s | step {row['step']}",font=font(21,True),fill='#182e49')
                draw.text((x+18,120),phase,font=font(19),fill='#34465b')
                box=cache[arm][2]
                if box is None:draw.text((x+18,468),'Box omitted: no pose recorded yet',font=font(17),fill='#915923')
                if ended or frame==frame_count-1:
                    label='E0 END: COMMON-GOAL SUCCESS' if arm=='E0' else 'E1 END: FINAL-PREVIEW REFUSED'
                    color='#137a53' if arm=='E0' else '#a04436'
                    draw.rectangle((x+10,417,x+width-10,467),fill='#f6f8fb')
                    draw.text((x+18,423),label,font=font(20,True),fill=color)
                    draw.text((x+18,447),'No later physical state is shown.',font=font(15),fill=color)
                frame_record['arms'][arm]=dict(control_index=index,step=row['step'],actual_sim_time_s=row['time_s'],ended=ended,box_center_record_time_s=None if box is None else box['time_s'])
            draw.text((18,510),'Robot root + all 18 joints: recorded values. Box: recorded center, orientation schematic.',font=font(20),fill='#263b53')
            draw.text((18,543),'Kinematics/render only: no controller, actor, physics integration, or new experimental outcome.',font=font(19),fill='#263b53')
            if frame==200:image.save(args.output/'preview.png')
            proc.stdin.write(image.tobytes());frame_map.append(frame_record)
            if frame%100==0:print(json.dumps(dict(frame=frame,total=frame_count,render_wall_s=time.time()-began)),flush=True)
        proc.stdin.close();rc=proc.wait(timeout=60)
        if rc:raise RuntimeError('ffmpeg failed '+str(rc))
    finally:
        renderer.close();fflog.close()
        if proc.poll() is None:
            if not proc.stdin.closed:proc.stdin.close()
            proc.wait(timeout=60)
    with (args.output/'frame-source-map.json').open('x') as f:json.dump(frame_map,f,indent=2);f.write('\n')
    asset_hashes=[]
    for p in [*assets,args.geometry_root/'deploy/piper_robot_profile.json',args.geometry_root/'deploy/piper_collision_profile.json']:
        asset_hashes.append(dict(path=str(p),sha256=sha(p)))
    metadata=dict(schema='kinematic-logged-state-video-v1',original_camera_footage=False,source_case_seed=120401,
        video=str(video),video_sha256=sha(video),frames=frame_count,fps=fps,playback_speed=3,video_duration_s=frame_count/fps,
        original_sim_end_s={a:rows[a][-1]['time_s'] for a in rows},original_outcomes={a:reports[a]['outcome'] for a in rows},
        video_has_no_new_outcome=True,new_Isaac_Apps=0,new_physical_starts=0,physics_integration_steps=0,actor_loads=0,
        private_kinematics_calls_for_render_and_visual_check=fk_calls,renderer=gl_renderer,vendor=gl_vendor,
        box_scope='Recorded centers only after observation; axis-aligned transparent proxy. Full box orientation history NOT recorded, never claimed reconstructed.',
        unlogged_environment_contacts_and_forces_NOT_reconstructed=True,frame_selection='previous measured row, no pose interpolation; terminal freeze labeled END',
        native_source_hand_checks=hand_checks,input_hashes=hashes,geometry_asset_hashes=asset_hashes,
        render_wall_s=time.time()-began,source_script_sha256=sha(Path(__file__)))
    with (args.output/'video-metadata.json').open('x') as f:json.dump(metadata,f,indent=2);f.write('\n')
    print(json.dumps(metadata,indent=2),flush=True)

if __name__=='__main__':main()
