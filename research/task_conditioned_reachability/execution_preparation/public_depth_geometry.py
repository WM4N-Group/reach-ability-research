"""Nominal body-frame visible-point geometry from EXISTING public RGBD.

No simulator/GT/localization/segmentation, training or file IO. A visible depth
sample is NOT an object center or registered approach reference. No measurement
error bound is currently supplied by the owner, so this is never a safety or
reference-relative-pose certificate, even with numerically valid calibration.
"""
import math
from .successor_aware_choice import need,number


def _matrix(value,n,m,name):
    need(type(value) in (list,tuple) and len(value)==n and
         all(type(row) in (list,tuple) and len(row)==m and all(number(x) for x in row) for row in value),
         'Finite public matrix shape: '+name)
    return tuple(tuple(float(x) for x in row) for row in value)


def visible_point(pixel_uv, optical_depth_m, camera_K, T_base_optical, *,
                  image_size_wh, acquisition_time_s, decision_time_s,
                  source_role, source_ref, depth_convention='OPTICAL_Z_METERS'):
    """Backproject one calibrated image coordinate and rigid-transform it.

    Input u/v must use the calibration's pixel-coordinate convention; integer
    array indexing does not by itself prove exact pixel-center alignment. No
    hidden half-pixel adjustment, depth interpolation or background subtraction.
    Source role is caller provenance, not authentication. Historical audit role
    is retained and cannot produce a prospective/public object-center estimate.
    """
    need(source_role in ('ONLINE_PUBLIC','AUDIT_ONLY'),'Only existing public acquisition or explicit audit measurement, never private geometry')
    need(type(source_ref) is str and bool(source_ref),'Exact public packet/calibration provenance')
    need(depth_convention=='OPTICAL_Z_METERS','Optical Z depth is not Euclidean ray range or world height')
    need(type(image_size_wh) in (tuple,list) and len(image_size_wh)==2 and
         all(type(v) is int and v>0 for v in image_size_wh),'Original positive image dimensions')
    need(type(pixel_uv) in (tuple,list) and len(pixel_uv)==2 and all(number(v) for v in pixel_uv) and
         0<=pixel_uv[0]<image_size_wh[0] and 0<=pixel_uv[1]<image_size_wh[1], 'Calibrated pixel inside actual public frame')
    need(number(acquisition_time_s) and number(decision_time_s) and
         0<=acquisition_time_s<=decision_time_s+1e-9,'Causal original acquisition time, no future frame')
    K=_matrix(camera_K,3,3,'camera_K');T=_matrix(T_base_optical,4,4,'T_base_optical')
    need(K[0][0]>0 and K[1][1]>0 and K[1][0]==0. and K[2]==(0.,0.,1.),
         'Supported original pinhole intrinsics, not arbitrary projective calibration')
    need(T[3]==(0.,0.,0.,1.),'Original rigid body-from-optical homogeneous transform')
    R=tuple(row[:3] for row in T[:3])
    # Numerical matrix validity, NOT physical calibration/measurement accuracy.
    need(all(abs(sum(R[i][k]*R[j][k] for k in range(3))-(1. if i==j else 0.))<=1e-6
             for i in range(3) for j in range(3)), 'Rigid calibration rotation, no scaling/shear')
    det=(R[0][0]*(R[1][1]*R[2][2]-R[1][2]*R[2][1])-
         R[0][1]*(R[1][0]*R[2][2]-R[1][2]*R[2][0])+
         R[0][2]*(R[1][0]*R[2][1]-R[1][1]*R[2][0]))
    need(abs(det-1.)<=1e-6,'Proper rotation, not a reflected camera frame')
    result=dict(kind='VISIBLE_SURFACE_POINT_NOT_OBJECT_CENTER',source_role=source_role,source_ref=source_ref,
        acquisition_time_s=acquisition_time_s,decision_time_s=decision_time_s,
        pixel_uv=list(pixel_uv),depth_convention=depth_convention,
        optical_xyz_m=None,body_xyz_m=None,status='UNKNOWN_NO_VALID_DEPTH',
        physical_calibration_error_bound_m=None,depth_error_bound_m=None,
        exact_pixel_center_alignment_proven=False,
        object_identity_or_center_inferred=False,registered_reference_relative_pose=None,
        public_object_geometry=dict(status='unknown',source='unavailable',values={},uncertainty={}),
        prospective_feature_from_historical_audit_allowed=False,
        native_READY_or_support_or_cost_prediction='UNKNOWN',execution_authorized=False)
    if not number(optical_depth_m) or optical_depth_m<=0:return result
    if source_role=='ONLINE_PUBLIC' and decision_time_s-acquisition_time_s>.100001:
        result['status']='UNKNOWN_STALE_PUBLIC_DEPTH';return result
    u,v=pixel_uv;z=float(optical_depth_m)
    y=(v-K[1][2])/K[1][1]
    x=(u-K[0][2]-K[0][1]*y)/K[0][0]
    optical=(x*z,y*z,z)
    body=tuple(sum(R[i][j]*optical[j] for j in range(3))+T[i][3] for i in range(3))
    need(all(number(v) for v in optical+body),'Finite nominal projection, no overflow')
    result.update(status='NOMINAL_VISIBLE_POINT_ONLY_NOT_REFERENCE_POSE',
                  optical_xyz_m=list(optical),body_xyz_m=list(body))
    return result
