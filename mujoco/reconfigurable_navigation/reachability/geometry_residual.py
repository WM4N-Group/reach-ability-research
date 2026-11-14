"""Rigid collision-geometry residuals in a common moving anchor frame."""

from __future__ import annotations

import mujoco
import numpy as np


def anchored_geometry_displacement_bounds(model, reference_data, observed_data, *,
                                         geometry_ids, anchor_geometry):
    """Bound every geometry point's motion after removing the anchor SE(3).

    Inputs must be forward-computed data for the same unchanged model. Shapes
    must be rigid: this does not account for deformation or model error.
    Outputs are observed displacement bounds, not prospective policy budgets.
    """
    geometries = tuple(geometry_ids)
    if (len(set(geometries)) != len(geometries)
            or any(not isinstance(g, (int, np.integer)) or not 0 <= g < model.ngeom
                   for g in (*geometries, anchor_geometry))):
        raise ValueError("Geometry IDs must be unique valid model indices")
    for data in (reference_data, observed_data):
        selected = list(set((*geometries, anchor_geometry)))
        if (not np.isfinite(data.geom_xpos[selected]).all()
                or not np.isfinite(data.geom_xmat[selected]).all()):
            raise ValueError("Geometry poses must be finite")
    anchor_reference = reference_data.geom_xmat[anchor_geometry].reshape(3, 3)
    anchor_observed = observed_data.geom_xmat[anchor_geometry].reshape(3, 3)
    common_rotation = anchor_observed @ anchor_reference.T
    common_translation = (observed_data.geom_xpos[anchor_geometry]
                          - common_rotation @ reference_data.geom_xpos[anchor_geometry])
    result = {}
    for geometry in geometries:
        radius = float(model.geom_rbound[geometry])
        if not np.isfinite(radius) or radius <= 0:
            raise ValueError("Geometry needs a finite positive bounding sphere radius")
        if geometry == anchor_geometry:
            result[geometry] = 0.0
            continue
        expected_position = common_rotation @ reference_data.geom_xpos[geometry] + common_translation
        expected_rotation = common_rotation @ reference_data.geom_xmat[geometry].reshape(3, 3)
        relative_rotation = observed_data.geom_xmat[geometry].reshape(3, 3) @ expected_rotation.T
        quaternion = np.empty(4)
        mujoco.mju_mat2Quat(quaternion, relative_rotation.ravel())
        # sin(theta/2) is ||q_xyz||; stable near zero without arccos.
        displacement = (np.linalg.norm(observed_data.geom_xpos[geometry] - expected_position)
                        + 2 * radius * np.linalg.norm(quaternion[1:]))
        if not np.isfinite(displacement):
            raise ValueError("Geometry poses must be finite")
        result[geometry] = float(displacement)
    return result


def anchored_clearance_lower_bound(model, reference_data, geometry_pairs, displacement_radii):
    """Conditional distance lower bound given point-motion budgets for both sides.

    All budgets must refer to one common anchor rigid transform. This checks
    the selected geometry pairs only, not joint limits or contact/support.
    """
    pairs = tuple(geometry_pairs)
    if not pairs:
        raise ValueError("At least one geometry pair is required")
    lower = []
    for first, second in pairs:
        for geometry in (first, second):
            if (not isinstance(geometry, (int, np.integer)) or not 0 <= geometry < model.ngeom
                    or geometry not in displacement_radii):
                raise ValueError("Every valid geometry must have a displacement radius")
            radius = displacement_radii[geometry]
            if not np.isfinite(radius) or radius < 0:
                raise ValueError("Displacement radii must be finite and nonnegative")
        distance = mujoco.mj_geomDistance(model, reference_data, first, second, float("inf"), None)
        if not np.isfinite(distance):
            raise ValueError("Nominal geometry distance must be finite")
        lower.append(distance - displacement_radii[first] - displacement_radii[second])
    return float(min(lower))


def conditioned_geometry_poses(model, reference_initial, reference_current,
                               observed_initial, observed_current, *,
                               geometry_ids, anchor_geometry):
    """Predict geometry poses from observed initial state and reference motion.

    All geometry poses are expressed in their respective anchor frames. The
    prediction applies the reference geometry's relative SE(3) motion to the
    observed initial geometry pose. It does not use observed future geometry
    poses; those are read only to calculate diagnostic residuals.
    """
    geometries = tuple(geometry_ids)
    if (len(set(geometries)) != len(geometries)
            or any(not isinstance(g, (int, np.integer)) or not 0 <= g < model.ngeom
                   for g in (*geometries, anchor_geometry))):
        raise ValueError("Geometry IDs must be unique valid model indices")
    samples = (reference_initial, reference_current, observed_initial, observed_current)
    selected = list(set((*geometries, anchor_geometry)))
    for data in samples:
        if (not np.isfinite(data.geom_xpos[selected]).all()
                or not np.isfinite(data.geom_xmat[selected]).all()):
            raise ValueError("Geometry poses must be finite")

    def in_anchor(data, geometry):
        anchor_rotation = data.geom_xmat[anchor_geometry].reshape(3, 3)
        return (anchor_rotation.T @ (data.geom_xpos[geometry] - data.geom_xpos[anchor_geometry]),
                anchor_rotation.T @ data.geom_xmat[geometry].reshape(3, 3))

    predicted = {}
    residuals = {}
    for geometry in geometries:
        initial_position, initial_rotation = in_anchor(reference_initial, geometry)
        current_position, current_rotation = in_anchor(reference_current, geometry)
        observed_position, observed_rotation = in_anchor(observed_initial, geometry)
        actual_position, actual_rotation = in_anchor(observed_current, geometry)
        rotation_change = current_rotation @ initial_rotation.T
        predicted_rotation = rotation_change @ observed_rotation
        predicted_position = current_position + rotation_change @ (observed_position - initial_position)
        radius = float(model.geom_rbound[geometry])
        if not np.isfinite(radius) or radius <= 0:
            raise ValueError("Geometry needs a finite positive bounding sphere radius")
        relative_rotation = actual_rotation @ predicted_rotation.T
        quaternion = np.empty(4)
        mujoco.mju_mat2Quat(quaternion, relative_rotation.ravel())
        residual = (np.linalg.norm(actual_position - predicted_position)
                    + 2 * radius * np.linalg.norm(quaternion[1:]))
        if not np.isfinite(residual):
            raise ValueError("Geometry residual must be finite")
        predicted[geometry] = (predicted_position, predicted_rotation)
        residuals[geometry] = float(residual)
    return predicted, residuals
