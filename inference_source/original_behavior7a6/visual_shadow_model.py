"""RGB-D-only object perception boundary and UNTRAINED shadow-model prototype.

No simulator object state, IDs, engine physics, segmentation or labels are accepted.
This is a new model, not a feature extension of any frozen 112-D checkpoint.
"""
import torch
from torch import nn

INPUT_KEYS = frozenset(("rgb", "depth_m", "camera_K", "T_base_optical", "proprio",
                        "actions_previous", "action_valid", "timestamps_s"))
PROPRIO_FIELDS = ("joint_position_18", "joint_velocity_18", "gravity_direction_body_3",
                  "angular_velocity_body_3", "linear_velocity_body_3")
INTENT_FIELDS = ("NAV", "PUSH", "CLIMB", "goal_body_x_m", "goal_body_y_m",
                 "target_pixel_u_normalized", "target_pixel_v_normalized", "macro_distance_m")
TARGET_FIELDS = ("box_dx_query_body_m", "box_dy_query_body_m", "robot_dx_query_body_m",
                 "robot_dz_query_body_m", "support_probability", "hard_stop_probability")
HORIZONS_S = (0.4, 0.8)


def validate_visual_input(packet):
    if not isinstance(packet, dict) or set(packet) != INPUT_KEYS:
        raise ValueError("Exact visual schema required; RGB-D cannot fall back to simulator state")
    if not all(isinstance(v, torch.Tensor) for v in packet.values()):
        raise ValueError("Tensor inputs only; no nested metadata/audit payloads")
    rgb = packet["rgb"]
    if rgb.dtype != torch.uint8 or rgb.ndim != 5 or rgb.shape[-1] != 3:
        raise ValueError("rgb must be uint8 [B,T,H,W,3]")
    b, t, h, w, _ = rgb.shape
    if min(b, t) < 1 or min(h, w) < 16:
        raise ValueError("Empty or too-small visual input")
    shapes = {"depth_m": (b,t,h,w,1), "camera_K": (b,3,3), "T_base_optical": (b,4,4),
              "proprio": (b,t,45), "actions_previous": (b,t,18),
              "action_valid": (b,t), "timestamps_s": (b,t)}
    for key, shape in shapes.items():
        x = packet[key]
        if tuple(x.shape) != shape or x.device != rgb.device:
            raise ValueError(f"{key}: incorrect shape or device")
        if key == "action_valid":
            if x.dtype != torch.bool:
                raise ValueError("action_valid must be boolean")
        elif not x.is_floating_point():
            raise ValueError(f"{key}: floating-point tensor required")
        elif key != "depth_m" and not torch.isfinite(x).all():
            raise ValueError(f"{key}: nonfinite values")
    ts = packet["timestamps_s"]
    if (ts < 0).any() or (t > 1 and not (ts[:,1:] > ts[:,:-1]).all()):
        raise ValueError("Distinct increasing actual acquisition times required; no tiled fake history")
    k = packet["camera_K"]
    if not ((k[:,0,0] > 0).all() and (k[:,1,1] > 0).all()
            and ((k[:,0,2] >= 0) & (k[:,0,2] < w)).all()
            and ((k[:,1,2] >= 0) & (k[:,1,2] < h)).all()
            and torch.allclose(k[:,2], k.new_tensor([0,0,1]).expand(b,3))
            and (k[:,0,1] == 0).all() and (k[:,1,0] == 0).all()):
        raise ValueError("Invalid zero-skew calibrated camera intrinsics")
    mount = packet["T_base_optical"]
    r = mount[:,:3,:3]
    if not (torch.allclose(mount[:,3], mount.new_tensor([0,0,0,1]).expand(b,4))
            and torch.allclose(r.transpose(1,2) @ r, torch.eye(3,device=r.device,dtype=r.dtype).expand(b,3,3), atol=1e-5)
            and torch.allclose(torch.linalg.det(r), torch.ones(b,device=r.device,dtype=r.dtype), atol=1e-5)):
        raise ValueError("Invalid base-from-ROS-optical rigid calibration")
    if (packet["actions_previous"][~packet["action_valid"]] != 0).any():
        raise ValueError("Missing previous action must be explicitly zero and invalid, not a fabricated action")
    return b,t,h,w


def rgbd_channels(packet, maximum_depth_m=15.0):
    b,t,h,w = validate_visual_input(packet)
    z = packet["depth_m"].float()
    valid = torch.isfinite(z) & (z > 0) & (z <= maximum_depth_m)
    depth = torch.where(valid,z,0.0) / maximum_depth_m
    x = torch.cat((packet["rgb"].float()/255.,depth,valid.float()), dim=-1)
    return x.reshape(b*t,h,w,5).permute(0,3,1,2)


class VisualShadowModel(nn.Module):
    """Pixels -> recurrent belief -> action-conditioned short-horizon heads.

    Random initialization only in this deliverable. No efficacy/learned object
    detector is claimed. Direct RGB bypass is forbidden by input validation.
    Calibration is supplied, not privileged dynamic camera/world-object pose.
    """
    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(nn.Conv2d(5,16,5,2,2), nn.ReLU(),
            nn.Conv2d(16,24,3,2,1),nn.ReLU(),nn.Conv2d(24,32,3,2,1),nn.ReLU(),
            nn.AdaptiveAvgPool2d((3,4)),nn.Flatten(),nn.Linear(384,64),nn.ReLU())
        self.history = nn.GRU(64+45+18+1+1+4+12,96,batch_first=True)
        self.transition = nn.Sequential(nn.Linear(96+8,96),nn.ReLU(),nn.Linear(96,12))

    def encode(self, packet):
        b,t,h,w = validate_visual_input(packet)
        v = self.encoder(rgbd_channels(packet)).reshape(b,t,64)
        k = packet['camera_K'].float()
        kn = torch.stack((k[:,0,0]/w,k[:,1,1]/h,k[:,0,2]/w,k[:,1,2]/h),dim=-1)
        cal = torch.cat((kn,packet['T_base_optical'][:,:3].reshape(b,12).float()),dim=-1)
        elapsed = packet['timestamps_s'] - packet['timestamps_s'][:,:1]
        features = torch.cat((v,packet['proprio'].float(),packet['actions_previous'].float(),
            packet['action_valid'].unsqueeze(-1).float(),elapsed.unsqueeze(-1).float(),
            cal[:,None].expand(b,t,16)),dim=-1)
        _,state = self.history(features)
        return state[0]

    def forward(self, packet, macro_intent):
        belief = self.encode(packet)
        if (not isinstance(macro_intent,torch.Tensor) or tuple(macro_intent.shape) != (belief.shape[0],8)
                or macro_intent.device != belief.device or not torch.isfinite(macro_intent).all()):
            raise ValueError("Finite declared macro intent [B,8] required; no simulator target features")
        out = self.transition(torch.cat((belief,macro_intent.float()),dim=-1)).reshape(-1,2,6)
        return torch.cat((out[...,:4],out[...,4:].sigmoid()),dim=-1)
