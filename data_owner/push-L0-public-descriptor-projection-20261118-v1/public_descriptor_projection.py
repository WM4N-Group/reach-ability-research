"""Project CURRENT resolver RGB-only records to the ORIGINAL public ABI.

No detector replay, private catalogue, world pose/GT, geometry estimate or
admission authority. Original publisher still inserts UNKNOWN geometry.
"""
import math,re
RAW_KEYS={'target_ref','RGB_sha256','descriptor'}
VISUAL_KEYS={'appearance_family','pixel_bbox_xyxy','pixel_centroid_uv','median_observed_RGB','pixel_count','geometry_valid'}

def project(records=None,*,raw_RGB_sha256=None,width=None,height=None,enabled=False):
    if enabled is not True:return None
    if (type(raw_RGB_sha256)is not str or not re.fullmatch('[0-9a-f]{64}',raw_RGB_sha256)
            or type(width)is not int or type(height)is not int or min(width,height)<=0
            or type(records)not in(tuple,list)or len(records)>64):
        raise ValueError('Current finite public RGB hash/dimensions/descriptors required')
    result=[];seen=set()
    for row in records:
        if type(row)is not dict or set(row)!=RAW_KEYS or type(row['descriptor'])is not dict or set(row['descriptor'])!=VISUAL_KEYS:
            raise ValueError('Exact original resolver visual schema; no private/unknown extras')
        ref=row['target_ref'];visual=row['descriptor'];label=visual['appearance_family'];box=visual['pixel_bbox_xyxy']
        if row['RGB_sha256']!=raw_RGB_sha256 or type(ref)is not str or not 0<len(ref)<=160 or ref in seen:
            raise ValueError('Current RGB-bound distinct opaque target required')
        if type(label)is not str or not 0<len(label)<=160 or type(box)not in(tuple,list)or len(box)!=4:
            raise ValueError('Observed appearance label and measured pixel box required')
        if (any(type(v)not in(int,float)or not math.isfinite(v)for v in box)
                or not 0<=box[0]<box[2]<=width or not 0<=box[1]<box[3]<=height):
            raise ValueError('Measured pixel box outside current public frame')
        seen.add(ref)
        result.append(dict(target_ref=ref,label=label,bbox_xyxy=list(box),
            evidence_ref='current-public-RGB-bytes-sha256:'+raw_RGB_sha256))
    return tuple(result)
