"""Original pixel-only components -> current PUBLIC bbox correspondence.

Component membership is appearance-mask membership, NOT physical object truth.
No private catalogue/registry/label semantics, native authority, world pose,
reference pose, cost prediction, training or IO other than fixed source check.
Does NOT mutate the original proposer, its defaults, or public Observation.
"""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import math
from pathlib import Path

SOURCE_SHA='837e95ecd7bc3249154b8a53097f71fd90974a2df9fb4a35d87116d0254af304'
DEFAULTS=dict(minimum_pixels=64,minimum_depth_pixels=32,minimum_depth_fraction=.2,
 minimum_saturation=.18,minimum_value=.08,minimum_depth_m=.05,maximum_depth_m=15.)
FAMILIES=(('warm',.035,.16),('green',.28,.50),('violet',.70,.90),('red',.95,.035))


def need(ok,message):
 if not ok:raise ValueError(message)


def pin(x):return type(x) is str and len(x)==64 and all(c in '0123456789abcdef' for c in x)


def number(x):return type(x) in (int,float) and math.isfinite(x)


def derive_original_component_support(proposer,rgb,depth,K,T,*,acquisition_time_s,encoded_rgb_sha256):
 """Run unchanged original proposer/helpers, no alternative segmentation.

 The decoded RGB pixel SHA and encoded PNG file SHA are DIFFERENT domains.
 Caller must establish their genuine same-packet/file provenance. This function
 cannot turn an arbitrary provenance string or historical bundle into online data.
 """
 import numpy as np
 need(np.__version__=='1.26.4','This development numeric qualification pins NumPy1.26.4')
 source=Path(proposer.__file__).resolve()
 need(hashlib.sha256(source.read_bytes()).hexdigest()==SOURCE_SHA,'Exact unchanged original pixel proposer source')
 for name in ('propose_visual_candidates','single_visible_hypothesis','_hsv','_components','_validate','visual_calibration_sha'):
  f=getattr(proposer,name)
  need(callable(f) and f.__globals__ is vars(proposer) and Path(f.__code__.co_filename).resolve()==source,'Actual original proposer function namespace')
 cfg=proposer.ProposalConfig()
 need(asdict(cfg)==DEFAULTS and tuple(proposer.HUE_FAMILIES)==FAMILIES,'Original fixed segmentation defaults, no retuning')
 need(number(acquisition_time_s) and acquisition_time_s>=0 and pin(encoded_rgb_sha256),'Causal packet time and encoded public image pin')
 d=proposer._validate(rgb,depth,K,T);h,w=rgb.shape[:2]
 need(h*w<=1_000_000,'Bounded public image CPU geometry')
 before=tuple((a.shape,a.dtype.str,hashlib.sha256(a.tobytes()).hexdigest()) for a in (rgb,depth,K,T))
 result=proposer.propose_visual_candidates(rgb,depth,K,T,config=cfg)
 hue,saturation,value=proposer._hsv(rgb)
 chromatic=(saturation>=cfg.minimum_saturation)&(value>=cfg.minimum_value)
 components=[]
 for family,low,high in proposer.HUE_FAMILIES:
  inside=((hue>=low)&(hue<high)) if low<high else ((hue>=low)|(hue<high))
  for pixels in proposer._components(chromatic&inside):
   if len(pixels)<cfg.minimum_pixels:continue
   y,x=pixels[:,0],pixels[:,1];z=d[y,x]
   valid=np.isfinite(z)&(z>=cfg.minimum_depth_m)&(z<=cfg.maximum_depth_m)
   ordered=sorted((int(yy),int(xx)) for yy,xx in pixels.tolist())
   good=sorted((int(yy),int(xx)) for yy,xx in pixels[valid].tolist())
   witness=None
   if good:
    yy,xx=good[0];witness=dict(pixel_index_xy=[xx,yy],pixel_uv=[xx+.5,yy+.5],optical_Z_m=float(d[yy,xx]))
   components.append(dict(appearance_family=family,pixel_bbox_xyxy=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)],
    pixel_count=len(pixels),valid_depth_pixels=int(valid.sum()),pixel_indices_yx=ordered,
    membership_sha256=hashlib.sha256(np.asarray(ordered,dtype='<i8').tobytes()).hexdigest(),
    membership_digest_encoding='C_ORDER_INT64_LE_YX_PAIRS',first_valid_member_ray=witness))
 components.sort(key=lambda c:(c['appearance_family'],c['pixel_bbox_xyxy'][0],c['pixel_bbox_xyxy'][1]))
 need(len(components)==len(result['candidates']),'Original proposal/component count agreement')
 for component,p in zip(components,result['candidates']):
  need(all(component[k]==p[k] for k in ('appearance_family','pixel_bbox_xyxy','pixel_count','valid_depth_pixels')),'Exact original component, not bbox fill/merge/nearest')
  component['frame_local_ref']=p['frame_local_ref']
  try:
   proposer.single_visible_hypothesis(result,p['frame_local_ref'],current_RGB_sha256=result['RGB_sha256'])
   component.update(original_single_visible_hypothesis_accepted=True,original_refusal=None)
  except ValueError as error:
   component.update(original_single_visible_hypothesis_accepted=False,original_refusal=str(error))
 need(before==tuple((a.shape,a.dtype.str,hashlib.sha256(a.tobytes()).hexdigest()) for a in (rgb,depth,K,T)),'Public input arrays changed')
 return dict(acquisition_time_s=acquisition_time_s,encoded_rgb_sha256=encoded_rgb_sha256,
  raw_RGB_pixels_sha256=result['RGB_sha256'],calibration_sha256=result['calibration_sha256'],image_size_wh=[w,h],
  proposer_source_sha256=SOURCE_SHA,original_proposals=result,component_support=components,
  input_arrays_unchanged=True,source_authenticity_or_data_role_licensed_by_this_function=False)


def join_current_public_components(observation,support):
 """Exact current-frame bbox join, not re-identification or native association.

 Even a one-to-one published-bbox/component match is only correspondence to an
 existing public descriptor. No private engine identity or object center is
 recovered. Never pick largest/nearest or resolve same-family source refusal.
 """
 need(type(observation) is dict and type(support) is dict,'Existing public Observation.value and derived component support')
 need(support['proposer_source_sha256']==SOURCE_SHA and pin(support['raw_RGB_pixels_sha256']), 'Exact derived original source/pixel pin')
 rgb=observation['rgb'];t=support['acquisition_time_s']
 need(number(t) and rgb['time_s']==t and number(observation['time_s']) and 0<=observation['time_s']-t<=.100001,
      'Same causal acquisition, no stale/future component join')
 need(rgb['sha256']==support['encoded_rgb_sha256'] and [rgb['width'],rgb['height']]==support['image_size_wh'],
      'Exact encoded-image identity, not confused with raw RGB pixel SHA')
 proposals=support['original_proposals']
 need(proposals['RGB_sha256']==support['raw_RGB_pixels_sha256'] and proposals['calibration_sha256']==support['calibration_sha256'],
      'Derived proposal pixel/calibration identity')
 objects=observation['objects'];components=support['component_support']
 need(type(objects) is list and all(type(o) is dict and set(o)=={'target_ref','label','bbox_xyxy','geometry','evidence_ref'}
      and type(o['target_ref']) is str and bool(o['target_ref']) for o in objects)
      and len({o['target_ref'] for o in objects})==len(objects),'Unique original public descriptor fields/target refs, not private catalogue')
 need(len({c['frame_local_ref'] for c in components})==len(components),'Unique original frame-local components')
 rows=[]
 for obj in objects:
  bbox=obj['bbox_xyxy']
  need(type(bbox) is list and len(bbox)==4 and all(number(v) for v in bbox),'Finite original public bbox')
  w,h=support['image_size_wh'];need(0<=bbox[0]<bbox[2]<=w and 0<=bbox[1]<bbox[3]<=h,'Current public bbox inside image')
  row=dict(public_target_ref=obj['target_ref'],acquisition_time_s=t,
   encoded_rgb_sha256=support['encoded_rgb_sha256'],raw_RGB_pixels_sha256=support['raw_RGB_pixels_sha256'],
   calibration_sha256=support['calibration_sha256'],status='UNKNOWN_NO_EXACT_COMPONENT',
   frame_local_ref=None,appearance_component_membership_reproduced=False,
   public_bbox_component_correspondence_exact=False,physical_object_identity_or_point_ownership_verified=False,
   full_object_center_xyz_m=None,registered_reference_relative_pose=None,validated_metric_error_bound_m=None,
   native_admission=False,successor_prediction_available=False,public_object_geometry_modified=False)
  matches=[c for c in components if c['pixel_bbox_xyxy']==bbox]
  if sum(o['bbox_xyxy']==bbox for o in objects)!=1:row['status']='UNKNOWN_MULTIPLE_PUBLIC_DESCRIPTORS_SAME_BBOX'
  elif len(matches)!=1:row['status']='UNKNOWN_NO_UNIQUE_EXACT_COMPONENT'
  elif matches[0]['original_single_visible_hypothesis_accepted'] is not True:
   row.update(status='UNKNOWN_ORIGINAL_COMPONENT_REFUSED',original_refusal=matches[0]['original_refusal'])
  else:
   c=matches[0]
   row.update(status='EXACT_CURRENT_PUBLIC_BBOX_COMPONENT_NOT_PHYSICAL_OBJECT_PROOF',frame_local_ref=c['frame_local_ref'],
    appearance_component_membership_reproduced=True,public_bbox_component_correspondence_exact=True,
    component_pixel_count=c['pixel_count'],bbox_pixel_area=(bbox[2]-bbox[0])*(bbox[3]-bbox[1]),
    membership_sha256=c['membership_sha256'],first_valid_component_member_ray=deepcopy(c['first_valid_member_ray']))
  rows.append(row)
 return rows
