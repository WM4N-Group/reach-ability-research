"""PIPER reachability queries and deterministic kinematic oracles."""

from .clearance import (
    ClearanceResult,
    FrozenConfigurationSafetyTube,
    PiperArmClearanceChecker,
    PiperSelfClearanceChecker,
)
from .oracle import PiperPositionReachabilityOracle
from .precontact_certificate import (
    FrozenPrecontactRegion,
    certify_frozen_precontact_region,
)
from .schema import ReachabilityQuery, ReachabilityResult
from .sampling import (
    BasePosePerturbationSample,
    BasePosePerturbationSet,
    ReachabilitySample,
    ReachabilitySampleSet,
    sample_base_pose_perturbations,
    sample_fixed_base,
)
from .support import (
    FixedContactSupportResidual,
    FixedContactSupportRegion,
    RelativeContactSupportRegion,
    PiperQuasiStaticSupportChecker,
    QuasiStaticSupportResult,
    certify_fixed_contact_support_region,
    certify_relative_contact_support_region,
    measure_fixed_contact_support_residual,
)
from .target_uncertainty import (
    StaticBoxPrecontactErrorBounds,
    StaticBoxTargetErrorBound,
    bound_static_box_precontact_errors,
    bound_static_box_target_error,
)
from .scenes import (
    STATIC_BOX_BODY,
    STATIC_BOX_GEOMETRY,
    make_static_box_navigation_runtime,
)

__all__ = (
    "PiperPositionReachabilityOracle",
    "PiperSelfClearanceChecker",
    "PiperArmClearanceChecker",
    "ClearanceResult",
    "FrozenConfigurationSafetyTube",
    "FrozenPrecontactRegion",
    "certify_frozen_precontact_region",
    "ReachabilityQuery",
    "ReachabilityResult",
    "ReachabilitySample",
    "ReachabilitySampleSet",
    "BasePosePerturbationSample",
    "BasePosePerturbationSet",
    "sample_base_pose_perturbations",
    "sample_fixed_base",
    "PiperQuasiStaticSupportChecker",
    "QuasiStaticSupportResult",
    "FixedContactSupportRegion",
    "RelativeContactSupportRegion",
    "FixedContactSupportResidual",
    "certify_fixed_contact_support_region",
    "certify_relative_contact_support_region",
    "measure_fixed_contact_support_residual",
    "StaticBoxTargetErrorBound",
    "StaticBoxPrecontactErrorBounds",
    "bound_static_box_precontact_errors",
    "bound_static_box_target_error",
    "STATIC_BOX_BODY",
    "STATIC_BOX_GEOMETRY",
    "make_static_box_navigation_runtime",
)
