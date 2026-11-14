"""Publish real OnboardObserver packets without its private object catalogue."""
from pathlib import Path
from ..contracts import Observation, file_sha, canonical


class AcquisitionPublisher:
    def __init__(self, root):
        self.root = Path(root).absolute()
        self.root.mkdir(parents=True, exist_ok=False)
        self.count = 0

    def publish(self, packet, *, now, descriptors, declared_map, goal, events,
                current_public_proprio=None, public_status=None):
        """packet is ONLY the real public packet returned by OnboardObserver.

        descriptors must come from the current RGB detector/association, not
        the observer's second return value (private_catalog). Geometry is
        unknown until a separate audited RGBD measurement provides estimates.
        """
        import numpy as np
        from PIL import Image
        def array(value):
            if hasattr(value, 'detach'):
                value = value.detach().cpu().numpy()
            return np.asarray(value)
        required = {'rgb', 'depth_m', 'camera_K', 'T_base_optical', 'proprio',
                    'actions_previous', 'action_valid', 'timestamps_s'}
        if not isinstance(packet, dict) or set(packet) != required:
            raise ValueError('Exact actual OnboardObserver public packet required, never a private catalogue')
        rgb = array(packet['rgb'])
        depth = array(packet['depth_m'])
        times = array(packet['timestamps_s'])
        proprio = array(packet['proprio']) if current_public_proprio is None else array(current_public_proprio)
        if proprio.shape == (45,):
            proprio = proprio[None, None]
        if (rgb.ndim != 5 or rgb.shape[:2] != (1, 1) or rgb.shape[-1] != 3 or rgb.dtype != np.uint8
                or depth.shape != (*rgb.shape[:-1], 1) or times.shape != (1, 1)
                or proprio.shape != (1, 1, 45) or not np.isfinite(proprio).all()):
            raise ValueError('Real RGBD and original public 45D proprioception required')
        camera_time = float(times[0, 0])
        if not np.isfinite(camera_time) or not 0 <= now-camera_time <= .100001:
            raise ValueError('Actual causal recent acquisition required; no timestamp padding')
        k, mount = array(packet['camera_K']), array(packet['T_base_optical'])
        if k.shape != (1, 3, 3) or mount.shape != (1, 4, 4) or not np.isfinite(k).all() or not np.isfinite(mount).all():
            raise ValueError('Actual public camera calibration required')
        self.count += 1
        frame_dir = self.root/('frame-%06d' % self.count)
        frame_dir.mkdir()
        image = frame_dir/'rgb.png'
        Image.fromarray(rgb[0, 0]).save(image)
        np.save(frame_dir/'depth_m.npy', depth[0, 0], allow_pickle=False)
        calibration = dict(camera_K=k[0].tolist(), T_base_optical=mount[0].tolist(),
                           acquisition_time_s=camera_time, public_packet_only=True)
        (frame_dir/'calibration.json').write_text(canonical(calibration)+'\n')
        values = proprio[0, 0]
        observed = []
        for descriptor in descriptors:
            if not isinstance(descriptor, dict) or set(descriptor) != {'target_ref', 'label', 'bbox_xyxy', 'evidence_ref'}:
                raise ValueError('Detector-only measured descriptor fields required')
            observed.append(dict(descriptor, geometry=dict(status='unknown', source='unavailable', values={}, uncertainty={})))
        value = dict(time_s=now, rgb=dict(path=str(image), sha256=file_sha(image), time_s=camera_time,
                    width=int(rgb.shape[3]), height=int(rgb.shape[2])), objects=observed,
                    public_state=dict(q=values[:18].tolist(), dq=values[18:36].tolist(),
                        gravity=values[36:39].tolist(), angular_velocity=values[39:42].tolist(),
                        linear_velocity=values[42:45].tolist()),
                    declared_map=declared_map, goal=goal, events=events)
        if public_status is not None:
            if not isinstance(public_status,dict) or not set(public_status)<= {'support_surface','task_status','skill_status'}:
                raise ValueError('Only public categorical status fields accepted')
            value['public_state'].update(public_status)
        observation = Observation.create(value)
        (frame_dir/'observation.json').write_text(observation.encoded+'\n')
        return observation
