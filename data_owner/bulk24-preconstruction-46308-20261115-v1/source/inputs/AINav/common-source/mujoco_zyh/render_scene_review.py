"""External-camera review from actual complete states, WITHOUT another rollout.

Only an independent display MjData is populated from recorded integration states.
No mj_step, actor import, interpolation, reconstructed root pose or task mutation.
The inset is the synchronized actual onboard RGB, not another simulated sensor.
"""
import argparse
from collections import deque
import fcntl
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import imageio.v2 as imageio
from .review_capture import state_records,load_display_model
from .streams import sha,write_json


def visual_frames(episode):
    index=json.loads((episode/'index.json').read_text())
    for row in index['visual']:
        p=episode/row['path']
        if not p.resolve().is_relative_to(episode/'visual') or sha(p)!=row['sha256']:raise ValueError('Onboard frame path/hash mismatch')
        with np.load(p,allow_pickle=False) as z:
            for i,tick in enumerate(z['control_ticks']):
                yield int(tick),float(z['timestamps_s'][0,i]),z['rgb'][0,i].copy(),z['proprio'][0,i].copy()


def load_font(size):
    for path in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']:
        if Path(path).is_file():return ImageFont.truetype(path,size)
    return ImageFont.load_default()


def render_frame(model,data,camera,renderer,*,record,meta,onboard,stage,source_id):
    import mujoco
    tick,timestamp,state=record
    spec=mujoco.mjtState.mjSTATE_INTEGRATION
    if int(spec)!=meta['state_spec'] or len(state)!=meta['state_size']:raise ValueError('Recorded integration layout differs')
    mujoco.mj_setState(model,data,state,spec)  # DISPLAY COPY ONLY; not the task world
    q=data.qpos.copy();v=data.qvel.copy()
    mujoco.mj_forward(model,data)  # derived geometry, ZERO integration steps
    if (float(data.time)!=timestamp or not np.array_equal(q,data.qpos) or not np.array_equal(v,data.qvel)):
        raise ValueError('Offline geometry render changed recorded time/pose/velocity')
    renderer.update_scene(data,camera=camera)
    frame=renderer.render().copy()
    image=Image.fromarray(frame);draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,960,61),fill=(18,25,34))
    draw.text((14,7),f'ACTUAL RECORDED COMPOSITE | t={timestamp:6.2f}s | {stage}',font=load_font(19),fill=(239,244,249))
    draw.text((14,34),meta.get('display_scene_label','Native 1kg box + 20cm platform | NO A20kg failure/recovery/B reselection'),font=load_font(14),fill=(247,196,111))
    inset=Image.fromarray(onboard)
    image.paste(inset,(754,79));draw.rectangle((752,77,947,208),outline=(235,240,245),width=2)
    draw.text((754,211),'ACTUAL ONBOARD RGB',font=load_font(12),fill=(246,249,252))
    draw.rectangle((0,464,960,512),fill=(18,25,34))
    draw.text((14,470),'Offline viewpoint from same-episode full states; no new physics or motion interpolation.',font=load_font(13),fill=(215,223,232))
    draw.text((14,489),'Engineering review only. Native completion != strict velocity/joint-range safety acceptance.',font=load_font(13),fill=(255,187,107))
    return np.asarray(image).copy()


def render(root,output,resource_dir):
    import mujoco
    root=Path(root).resolve();output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    state_root=root/'review-state';meta=json.loads((state_root/'metadata.json').read_text())
    if meta['mujoco_version']!=mujoco.__version__:raise ValueError('Use same pinned MuJoCo version as recorded binary')
    close=json.loads((state_root/'closure.json').read_text())
    if sha(Path(meta['model_path']))!=close['model_sha256']:raise ValueError('Compiled model changed')
    report=json.loads((root/'report.json').read_text())
    boundaries={r['control_tick']:r for r in map(json.loads,(root/'episode/control-boundaries.jsonl').read_text().splitlines())}
    model=load_display_model(state_root);display=mujoco.MjData(model)
    protocol=json.loads((root/'protocol.json').read_text())
    episode_meta=json.loads((root/'episode/episode.json').read_text())
    qids=np.array([model.joint(n).qposadr[0] for n in episode_meta['joint_names']]);dids=np.array([model.joint(n).dofadr[0] for n in episode_meta['joint_names']])
    catalogs=iter(map(json.loads,(root/'episode/private-catalog.jsonl').read_text().splitlines()))
    max_object_pose_error=0.;joint_state_matches=True
    camera=mujoco.MjvCamera()
    fallback=(dict(lookat=[2.3,0.,.2],distance=7.5,azimuth=105.,elevation=-32.)
              if protocol.get('suite_case',{}).get('family') in ('bridge','stairs') else
              dict(lookat=[.8,-.8,.25],distance=5.6,azimuth=115.,elevation=-30.))
    view=meta.get('external_review_camera') or fallback
    camera.lookat[:]=view['lookat'];camera.distance=view['distance'];camera.azimuth=view['azimuth'];camera.elevation=view['elevation']
    handles=[];renderer=writer=None;frames=0;first=last=None
    video=output/'complete-scene-review.mp4'
    try:
        for name in ('native-observer-physics-gpu1.lock','native-observer-sdk-gpu1.lock'):
            f=(Path(resource_dir)/name).open('a+');handles.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        renderer=mujoco.Renderer(model,height=512,width=960)
        fps=50/meta['visual_stride_control_ticks']
        writer=imageio.get_writer(video,fps=fps,codec='libx264',quality=7,macro_block_size=16)
        observations=iter(visual_frames(root/'episode'))
        samples=[]
        wanted=[0.,20.,29.,111.]
        for record in state_records(state_root):
            tick,stamp,state=record
            try:vt,vs,rgb,proprio=next(observations)
            except StopIteration:raise ValueError('Full state has no synchronized onboard frame')
            if tick!=vt or abs(stamp-vs)>1e-7:raise ValueError('External/onboard actual clock mismatch')
            b=boundaries[tick];stage=b['skill'].upper()+'/'+b['phase']
            if protocol.get('integrated_case') and b.get('recovery_diagnostics'):stage=b['recovery_diagnostics']['phase']
            elif b.get('recovery_diagnostics') and b['recovery_diagnostics'].get('abort'):stage='PUSH FAILED / '+b['recovery_diagnostics']['phase']
            if report.get('nav_efficiency_adaptation') and b.get('nav_diagnostics'):stage='ENGINEERING NAV/'+b['nav_diagnostics'].get('internal_phase',b['phase'])
            if not protocol.get('integrated_case') and b['skill']=='push' and any(e['event']=='push_exit_retract' and e['time']<=stamp for e in report['native_events']):
                stage='PUSH RETRACT / STAND'
            frame=render_frame(model,display,camera,renderer,record=record,meta=meta,onboard=rgb,stage=stage,source_id=meta['source_id'])
            if (not np.array_equal(display.qpos[qids].astype(np.float32),proprio[:18]) or
                not np.array_equal(display.qvel[dids].astype(np.float32),proprio[18:36])):
                raise ValueError('Full-world state joint pose/velocity differs from actual onboard record')
            cat=next(catalogs)
            if cat['control_tick']!=tick:raise ValueError('Private actual-object catalog time mismatch')
            for obj in cat['objects']:
                position=display.xpos[model.body(obj['body_name']).id]
                err=float(np.max(abs(position-np.asarray(obj['position_world_m']))));max_object_pose_error=max(max_object_pose_error,err)
                if err>1e-10:raise ValueError('Rendered object pose differs from actual recorded object pose')
            writer.append_data(frame)
            if wanted and stamp+1e-7>=wanted[0]:
                path=output/f'scene-{wanted.pop(0):05.1f}s.png';Image.fromarray(frame).save(path);samples.append(str(path))
            frames+=1;first=stamp if first is None else first;last=stamp
        try:next(observations);raise ValueError('Onboard frames missing from full-world stream')
        except StopIteration:pass
        if frames!=close['frames']:raise ValueError('Full-state frame count mismatch')
    finally:
        if writer is not None:writer.close()
        if renderer is not None:renderer.close()
        for f in reversed(handles):f.close()
    scope=(protocol['review_scope'] if (protocol.get('suite_case') or protocol.get('integrated_case')) else ('Research A20/B0.5/C1 three-box A failure to selected B attempt; NO 40cm CLIMB/full-task acceptance'
           if meta.get('scene_recipe')=='research_threebox' else
           'Fixed PUSH probe; physics labels reviewer-only, not model input' if report.get('probe_physics_private') else
           'Native1kg/20cm composite review; NOT research A20 failure/no-reset recovery/B'))
    result=dict(schema='actual-composite-scene-review-v1',source_root=str(root),source_id=meta['source_id'],episode_id=meta['episode_id'],
        source_report_sha256=sha(root/'report.json'),source_state_closure_sha256=sha(state_root/'closure.json'),
        source_visual_index_sha256=sha(root/'episode/index.json'),frames=frames,fps=50/meta['visual_stride_control_ticks'],
        first_source_sim_s=first,last_source_sim_s=last,main_final_sim_s=report['sim_seconds'],
        review_video=str(video),review_video_sha256=sha(video),screenshots=samples,
        native_route_success=report['task_success'] if not report.get('stall_stow_recovery') else False,
        full_integrated_task_success=bool(report['task_success'] and report.get('integrated_course',{}).get('complete')) if protocol.get('integrated_case') else None,
        failed_PUSH_stow_only=report.get('stall_stow_recovery'),nav_efficiency_adaptation=report.get('nav_efficiency_adaptation'),scope=scope,
        raw_full_states=True,actual_onboard_RGB_inset=True,root_pose_reconstructed_or_interpolated=False,
        independent_display_data_only=True,new_physics_starts=0,mj_step_calls=0,actor_forwards=0,WM_forwards=0,
        model_or_actuator_control_changed_by_rendering=False,strict_safety_acceptance=False,
        full_state_joints_match_actual_proprio=True,max_object_pose_reconstruction_error_m=max_object_pose_error,
        actual_recorded_world_pose_not_inferred_from_ego_velocity=True,
        warning='Source-native strict speed/joint-range diagnostics must be reported separately. Offline mj_forward values are NOT newly measured forces.')
    write_json(output/'review-provenance.json',result)
    print(json.dumps(result))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('root','output','resource-dir'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();render(a.root,a.output,a.resource_dir)


if __name__=='__main__':main()
