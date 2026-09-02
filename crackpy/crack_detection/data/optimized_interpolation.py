"""Frame-local interpolation for crack-detection model inputs."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay


def interpolate_frame(
        input_data_object: Any,
        size: int | float,
        offset: tuple[float, float] = (0.0, 0.0),
        pixels: int = 256,
        include_eps_vm: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Interpolate one DIC frame while sharing one spatial triangulation.

    The function intentionally owns no cross-frame cache because source nodes can
    change between DIC frames.

    Args:
        input_data_object: Frame with ``coor_x``, ``coor_y``, ``disp_x``,
            ``disp_y`` and ``eps_vm`` arrays.
        size: Signed physical edge length of the field of view.
        offset: Physical ``(x, y)`` offset of the field of view.
        pixels: Number of samples along each grid axis.
        include_eps_vm: Whether to interpolate ``eps_vm`` when it is available.

    Returns:
        Coordinate grid, two displacement grids and the optional von-Mises
        strain grid.

    """
    offset_x, offset_y = offset
    if size >= 0:
        x_axis = np.linspace(offset_x, size + offset_x, pixels)
        y_axis = np.linspace(-size / 2.0 + offset_y, size / 2.0 + offset_y, pixels)
    else:
        x_axis = np.linspace(size + offset_x, offset_x, pixels)
        y_axis = np.linspace(size / 2.0 + offset_y, -size / 2.0 + offset_y, pixels)
    x_grid, y_grid = np.meshgrid(x_axis, y_axis)

    source_points = np.column_stack((input_data_object.coor_x, input_data_object.coor_y))
    target_points = np.column_stack((x_grid.ravel(), y_grid.ravel()))
    field_values = [input_data_object.disp_x, input_data_object.disp_y]
    eps_vm = getattr(input_data_object, "eps_vm", None) if include_eps_vm else None
    if eps_vm is not None:
        field_values.append(eps_vm)
    values = np.column_stack(field_values)

    triangulation = Delaunay(source_points)
    # Vector-valued interpolation shares the triangulation and barycentric
    # evaluation across all requested fields.
    interpolated = LinearNDInterpolator(
        triangulation,
        values,
        fill_value=np.nan,
    )(target_points)

    fields = interpolated.reshape(pixels, pixels, values.shape[1])
    interp_disps = np.moveaxis(fields[..., :2], -1, 0)
    interp_eps_vm = fields[..., 2] if eps_vm is not None else None

    if size < 0:
        x_grid = np.fliplr(x_grid)
        y_grid = np.fliplr(y_grid)
        interp_disps = np.flip(interp_disps, axis=2)
        interp_disps[0] *= -1.0
        if interp_eps_vm is not None:
            interp_eps_vm = np.fliplr(interp_eps_vm)

    return np.asarray([x_grid, y_grid]), np.ascontiguousarray(interp_disps), interp_eps_vm
