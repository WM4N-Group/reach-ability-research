def geometry_vector(proof):
    if proof is None:return np.zeros(8,np.float32)
    p=proof['plane'];n=np.asarray(p['normal_body_xyz']);offset=p['plane_offset_body_m']
    return np.r_[n,offset,offset/n[0],p['p90_inlier_residual_m'],p['inlier_fraction'],1].astype(np.float32)
