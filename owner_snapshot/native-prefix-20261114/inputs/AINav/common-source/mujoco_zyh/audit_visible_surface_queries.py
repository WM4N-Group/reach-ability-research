"""TRAIN-only current-frame front-plane probe; truth is separate audit labels.

Appearance requests are supplied task cues, not learned semantic selection. This
checks visible geometry, not autonomous box choice or action admission.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from visual_box_proposals import ProposalConfig,propose_visual_candidates
from .visible_surface_goal import describe_visible_goal
from .streams import sha,write_json


def quaternion_matrix(q):
    w,x,y,z=np.asarray(q,dtype=float);return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def audit(manifest,source_audit,output):
    manifest=Path(manifest);source_audit=Path(source_audit);output=Path(output);output.mkdir(exist_ok=False)
    data=json.loads(manifest.read_text());audited=json.loads(source_audit.read_text())
    if any(r['role']!='train' for r in data['episodes']):raise ValueError('TRAIN-only source manifest required')
    rows={r['source_group']:r for r in data['episodes']};records=[]
    # Frozen reviewer task cues: family is a visible appearance instruction and
    # opaque physical IDs below are used ONLY in the later error-label audit.
    tasks=[('NAV_STEP','green','middle','step_length_m'),('NAV_BRIDGE','red','heavy','bridge_length_m')]
    for macro,appearance,label_identity,length_key in tasks:
        for query in audited['action_support'][macro]['examples']:
            source=rows[query['source_group']];root=Path(source['root']);time=query['first_macro_time_s']
            if sha(source['packed'])!=source['packed_sha256']:raise ValueError('Frozen training public pack changed')
            with np.load(source['packed'],allow_pickle=False) as z:
                index=int(np.searchsorted(z['timestamps_s'],time+1e-7,side='right')-1)
                stamp=float(z['timestamps_s'][index]);rgb=z['rgb'][index].copy();depth=z['depth_m'][index].astype(np.float32)
                valid=z['depth_valid'][index];depth=np.where(valid,depth,np.nan);K=z['camera_K'].copy();mount=z['T_base_optical'].copy()
            if stamp>time+1e-7 or time-stamp>.100001:raise ValueError('Only current-or-past actual visual frames allowed')
            proposal=propose_visual_candidates(rgb,depth,K,mount)
            candidates=[p for p in proposal['candidates'] if p['appearance_family']==appearance]
            row=dict(source_group=query['source_group'],macro=macro,query_time_s=time,actual_visual_time_s=stamp,
                observed_appearance_request=appearance,appearance_candidates=len(candidates),reference_from='Explicit reviewer appearance task cue, not native object ID or detector')
            try:
                if len(candidates)!=1:raise ValueError('Selected appearance does not identify a unique visible component')
                reference=candidates[0]['frame_local_ref']
                result=describe_visible_goal(rgb,depth,K,mount,frame_local_ref=reference,current_RGB_sha256=proposal['RGB_sha256'],standoff_m=1.05)
                row.update(observable_front_plane_available=True,public_result=result)
            except ValueError as exc:
                row.update(observable_front_plane_available=False,reason=str(exc));records.append(row);continue
            # Separate diagnostic-label stage. No value below is passed to the
            # public estimator or used to correct a fitted plane/relative goal.
            closure=json.loads((root/'episode/closure.json').read_text());catalog=root/'episode/private-catalog.jsonl'
            if sha(catalog)!=closure['private_catalog_sha256']:raise ValueError('Frozen private audit catalog changed')
            label=None
            for line in catalog.open():
                entry=json.loads(line)
                if abs(entry['actual_sim_time_s']-stamp)<1e-7:label=entry;break
            if label is None or label['model_input_allowed'] is not False:raise ValueError('Audit label timestamp/permissions differ')
            obj=next(o for o in label['objects'] if o['opaque_object_id']==label_identity)
            case=json.loads((root/'protocol.json').read_text())['integrated_case'];base_R=np.array(label['R_world_from_body']);box_R=quaternion_matrix(obj['quaternion_wxyz'])
            true_n=base_R.T@box_R[:,0];front=np.array(obj['position_world_m'])-box_R[:,0]*case[length_key]/2
            front_body=base_R.T@(front-np.array(label['root_position_world_m']));true_d=float(true_n@front_body)
            plane=result['plane'];pred_n=np.array(plane['normal_body_xyz']);point=np.array(plane['visible_point_body_xyz_m'])
            angle=float(np.arccos(np.clip(abs(pred_n@true_n),-1,1)))
            # Evaluate at the SAME visible Y/Z so visible median is not treated
            # as full-box center. Units and normal directions are explicit.
            plane_error=abs(float(true_n@point)-true_d)
            row['private_audit_labels_only']=dict(front_plane_point_error_m=plane_error,front_normal_angle_rad=angle,
                private_truth_passed_to_public_estimator=False,full_box_center_claimed=False,lateral_target_validated=False)
            records.append(row)
            print('VISIBLE_PLANE_PROBE',macro,query['source_group'],plane_error,angle,flush=True)
    good=[r for r in records if r['observable_front_plane_available']]
    errors=[r['private_audit_labels_only']['front_plane_point_error_m'] for r in good]
    result=dict(schema='current-RGBD-visible-front-plane-train-audit-v1',source_manifest_sha256=sha(manifest),macro_audit_sha256=sha(source_audit),
        estimator_source_sha256=sha(Path(__file__).with_name('visible_surface_goal.py')),proposal_source_sha256=sha(Path(__file__).parents[1]/'visual_box_proposals.py'),
        query_count=len(records),front_plane_available=len(good),missing_or_rejected=len(records)-len(good),
        max_front_plane_point_error_m=max(errors) if errors else None,median_front_plane_point_error_m=float(np.median(errors)) if errors else None,
        records=records,private_truth_used_only_as_audit_labels=True,private_truth_corrected_outputs=False,
        validation_or_test_frames_read=False,model_trained=False,physics_steps_started=0,
        sensor_fixture_only_no_autonomous_target_selection=True,lateral_alignment_or_actual_action_admitted=False,
        limitation='Current visible front-plane geometry, with an explicit appearance cue. It does not solve lateral goal location, robot pose, native gate admission, persistent object binding, learned planning or full-task completion.')
    write_json(output/'visible-front-audit.json',result)
    print('VISIBLE_FRONT_AUDIT_COMPLETE',json.dumps({k:result[k] for k in ['query_count','front_plane_available','missing_or_rejected','max_front_plane_point_error_m','median_front_plane_point_error_m']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('manifest','source-audit','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();audit(a.manifest,a.source_audit,a.output)
