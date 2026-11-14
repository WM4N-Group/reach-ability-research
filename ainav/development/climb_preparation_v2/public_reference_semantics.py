"""Source-specific PUBLIC semantic alias -> declared CLIMB reference link.

Only the selected FullCourse publisher's explicit `cuboid-N; dimensions ...`
label format is supported. No color/UUID/nearest/initial-pose heuristic. This is
semantic correspondence, NOT physical identity or reference-relative geometry.
The existing label/anchor is a declaration, not an authentication certificate.
"""
from copy import deepcopy
import math
import re


def need(ok,message):
 if not ok:raise ValueError(message)


def number(v):return type(v) in (int,float) and math.isfinite(v)


def link_public_CLIMB_reference(observation,component_rows,requested_reference):
 """Use an original explicit public alias, without rewriting Observation.

 Zero uncertainty on a declared static map reference is NOT a measured relative
 pose/tracking bound. Adjacent-boundary text is NOT admission or future success.
 Retired/initial anchors are never substituted for a registered skill reference.
 """
 need(type(observation) is dict and type(component_rows) is list,'Existing public value and current component sidecars')
 need(type(requested_reference) is str,'Explicit declared task reference')
 out=dict(requested_reference=requested_reference,status='UNKNOWN_UNSUPPORTED_PUBLIC_REFERENCE',
  declared_object_alias=None,public_target_ref=None,frame_local_component_ref=None,
  declared_skill_reference_world_xyz_m=None,declared_reference_uncertainty_xyz_m=None,
  nominal_component_member_ray=None,semantic_public_correspondence_only=False,
  physical_object_identity_or_point_ownership_verified=False,reference_relative_pose_body=None,
  robot_world_pose=None,current_object_world_pose=None,measured_relative_pose_error_bound_m=None,
  native_admission=False,CLIMB_READY_or_success_inferred=False,successor_cost_or_failure_predicted=False,
  public_map_zero_uncertainty_is_NOT_tracking_bound=True,source_authenticity_verified_by_this_function=False)
 match=re.fullmatch(r'(cuboid-[1-9][0-9]*):upper-entry',requested_reference)
 if match is None:return out
 alias=match.group(1)
 anchors=observation['declared_map']['anchors'];need(type(anchors) is list,'Existing declared map anchors')
 exact=[a for a in anchors if a.get('target_ref')==requested_reference]
 if len(exact)!=1:
  out['status']='UNKNOWN_NO_UNIQUE_DECLARED_SKILL_REFERENCE';return out
 anchor=exact[0]
 description=anchor['description']
 if (type(description) is not str or not description.startswith('Declared skill reference: NAV source/support z=')
     or '; CLIMB destination z=' not in description):
  out['status']='UNKNOWN_NOT_ORIGINAL_DECLARED_CLIMB_REFERENCE';return out
 # Only declared-coordinate validity; never use :initial position as current GT.
 for name in ('position_xyz_m','uncertainty_xyz_m'):
  v=anchor[name]
  need(type(v) is list and len(v)==3 and all(number(x) for x in v),'Finite original declared reference coordinate')
 need(all(v>=0 for v in anchor['uncertainty_xyz_m']),'Nonnegative declared-coordinate uncertainty')
 objects=observation['objects'];need(type(objects) is list and all(type(o) is dict and type(o.get('target_ref')) is str and type(o.get('label')) is str for o in objects)
      and len({o['target_ref'] for o in objects})==len(objects),'Unique original public descriptor identities')
 visible=[o for o in objects if type(o.get('label')) is str and o['label'].startswith(alias+'; dimensions ')]
 if len(visible)!=1:
  out['status']='UNKNOWN_NO_UNIQUE_EXPLICIT_PUBLIC_ALIAS';return out
 obj=visible[0]
 linked=[r for r in component_rows if r.get('public_target_ref')==obj['target_ref']]
 if len(linked)!=1:
  out['status']='UNKNOWN_NO_UNIQUE_CURRENT_COMPONENT_SUPPORT';return out
 row=linked[0];rgb=observation['rgb']
 need(number(rgb['time_s']) and number(observation['time_s']) and 0<=observation['time_s']-rgb['time_s']<=.100001,
      'Original causal current-query acquisition age; no stale/future association')
 need(row['acquisition_time_s']==rgb['time_s'] and row['encoded_rgb_sha256']==rgb['sha256'],
      'Same current public component image/clock; no past-frame re-identification')
 if not (row['public_bbox_component_correspondence_exact'] is True and row['appearance_component_membership_reproduced'] is True):
  out['status']='UNKNOWN_COMPONENT_ORIGINAL_REFUSAL';return out
 out.update(status='PUBLIC_ALIAS_TO_DECLARED_REFERENCE_ONLY_NOT_RELATIVE_POSE',
  declared_object_alias=alias,public_target_ref=obj['target_ref'],frame_local_component_ref=row['frame_local_ref'],
  acquisition_time_s=row['acquisition_time_s'],encoded_rgb_sha256=row['encoded_rgb_sha256'],
  calibration_sha256=row['calibration_sha256'],
  declared_skill_reference_world_xyz_m=deepcopy(anchor['position_xyz_m']),
  declared_reference_uncertainty_xyz_m=deepcopy(anchor['uncertainty_xyz_m']),
  nominal_component_member_ray=deepcopy(row['first_valid_component_member_ray']),semantic_public_correspondence_only=True)
 return out
