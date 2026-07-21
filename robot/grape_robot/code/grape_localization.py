#!/usr/bin/env python3
# encoding: utf-8
"""葡萄 RGB-D 定位的纯算法实现。

本模块不依赖 ROS2，也不发布任何硬件控制消息。调用方必须显式提供
深度尺度、两路相机内参以及 depth->color 外参；缺少任一事实时失败关闭。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence, Tuple

import numpy as np


class LocalizationFailure(str, Enum):
    """定位失败原因，供日志、测试和状态机稳定判断。"""

    NONE = "NONE"
    ARM_MOTION_DISABLED = "ARM_MOTION_DISABLED"
    DEPTH_SCALE_UNKNOWN = "DEPTH_SCALE_UNKNOWN"
    INVALID_CONFIG = "INVALID_CONFIG"
    INVALID_DEPTH_IMAGE = "INVALID_DEPTH_IMAGE"
    INVALID_INTRINSICS = "INVALID_INTRINSICS"
    INVALID_EXTRINSICS = "INVALID_EXTRINSICS"
    INVALID_DETECTION_BOX = "INVALID_DETECTION_BOX"
    NO_VALID_DEPTH = "NO_VALID_DEPTH"
    INSUFFICIENT_POINTS = "INSUFFICIENT_POINTS"
    INSUFFICIENT_COVERAGE = "INSUFFICIENT_COVERAGE"
    ROBUST_FILTER_EMPTY = "ROBUST_FILTER_EMPTY"


@dataclass(frozen=True)
class CameraIntrinsics:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float

    def is_valid(self) -> bool:
        values = np.asarray((self.fx, self.fy, self.cx, self.cy), dtype=np.float64)
        return (
            self.width > 0
            and self.height > 0
            and np.all(np.isfinite(values))
            and self.fx > 0.0
            and self.fy > 0.0
        )


@dataclass(frozen=True)
class RigidTransform:
    """从深度相机坐标转换到 RGB 相机坐标的刚体变换。"""

    rotation: np.ndarray
    translation: np.ndarray

    def arrays(self) -> Tuple[np.ndarray, np.ndarray]:
        return (
            np.asarray(self.rotation, dtype=np.float64),
            np.asarray(self.translation, dtype=np.float64),
        )

    def is_valid(self) -> bool:
        rotation, translation = self.arrays()
        if rotation.shape != (3, 3) or translation.shape != (3,):
            return False
        if not np.all(np.isfinite(rotation)) or not np.all(np.isfinite(translation)):
            return False
        return bool(
            np.allclose(rotation @ rotation.T, np.eye(3), atol=1e-3)
            and np.isclose(np.linalg.det(rotation), 1.0, atol=1e-3)
        )


@dataclass(frozen=True)
class DetectionBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def clipped(self, width: int, height: int) -> Optional["DetectionBox"]:
        values = np.asarray((self.x1, self.y1, self.x2, self.y2), dtype=np.float64)
        if not np.all(np.isfinite(values)):
            return None
        x1 = float(np.clip(min(self.x1, self.x2), 0.0, float(width)))
        x2 = float(np.clip(max(self.x1, self.x2), 0.0, float(width)))
        y1 = float(np.clip(min(self.y1, self.y2), 0.0, float(height)))
        y2 = float(np.clip(max(self.y1, self.y2), 0.0, float(height)))
        if x2 <= x1 or y2 <= y1:
            return None
        return DetectionBox(x1, y1, x2, y2)

    def inset(self, ratio: float) -> Optional["DetectionBox"]:
        if not np.isfinite(ratio) or ratio < 0.0 or ratio >= 0.5:
            return None
        dx = (self.x2 - self.x1) * ratio
        dy = (self.y2 - self.y1) * ratio
        box = DetectionBox(self.x1 + dx, self.y1 + dy, self.x2 - dx, self.y2 - dy)
        return box if box.x2 > box.x1 and box.y2 > box.y1 else None

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)


@dataclass(frozen=True)
class LocalizationConfig:
    depth_scale_m_per_unit: float = 0.0
    min_valid_points: int = 20
    min_valid_ratio: float = 0.15
    box_inset_ratio: float = 0.15
    mad_scale: float = 3.5
    min_depth_m: float = 0.0
    max_depth_m: float = float("inf")


@dataclass(frozen=True)
class LocalizationResult:
    success: bool
    failure: LocalizationFailure
    message: str
    candidate_points: int = 0
    valid_points: int = 0
    valid_ratio: float = 0.0
    depth_median_m: Optional[float] = None
    point_depth_camera: Optional[Tuple[float, float, float]] = None
    point_color_camera: Optional[Tuple[float, float, float]] = None
    projected_color_pixel: Optional[Tuple[float, float]] = None


def enforce_localization_only(enable_arm: bool) -> None:
    """本阶段硬性禁止打开机械臂动作权限。"""

    if enable_arm:
        raise RuntimeError(
            "当前版本仅允许离线/检测-only定位；enable_arm=true 已被安全层拒绝"
        )


def _failure(
    reason: LocalizationFailure,
    message: str,
    *,
    candidate_points: int = 0,
    valid_points: int = 0,
    valid_ratio: float = 0.0,
) -> LocalizationResult:
    return LocalizationResult(
        success=False,
        failure=reason,
        message=message,
        candidate_points=candidate_points,
        valid_points=valid_points,
        valid_ratio=valid_ratio,
    )


def intrinsics_from_camera_info(
    width: int, height: int, k: Sequence[float]
) -> CameraIntrinsics:
    """从 CameraInfo 的宽高和 K 数组构造纯算法内参。"""

    if len(k) != 9:
        return CameraIntrinsics(width, height, np.nan, np.nan, np.nan, np.nan)
    return CameraIntrinsics(
        width=int(width),
        height=int(height),
        fx=float(k[0]),
        fy=float(k[4]),
        cx=float(k[2]),
        cy=float(k[5]),
    )


def localize_detection(
    depth_image: np.ndarray,
    depth_intrinsics: CameraIntrinsics,
    color_intrinsics: CameraIntrinsics,
    depth_to_color: RigidTransform,
    detection_box: DetectionBox,
    config: LocalizationConfig,
) -> LocalizationResult:
    """把深度点投影到 RGB 检测框，并返回稳健三维位置。

    `point_depth_camera` 和 `point_color_camera` 分别位于深度光学坐标系和
    RGB 光学坐标系。本函数不进行手眼变换，也不输出机械臂世界坐标。
    """

    if not np.isfinite(config.depth_scale_m_per_unit) or config.depth_scale_m_per_unit <= 0:
        return _failure(LocalizationFailure.DEPTH_SCALE_UNKNOWN, "深度尺度未验证")

    if (
        config.min_valid_points <= 0
        or not np.isfinite(config.min_valid_ratio)
        or config.min_valid_ratio < 0.0
        or config.min_valid_ratio > 1.0
        or not np.isfinite(config.box_inset_ratio)
        or config.box_inset_ratio < 0.0
        or config.box_inset_ratio >= 0.5
        or not np.isfinite(config.mad_scale)
        or config.mad_scale <= 0.0
        or not np.isfinite(config.min_depth_m)
        or config.min_depth_m < 0.0
        or config.max_depth_m <= config.min_depth_m
    ):
        return _failure(LocalizationFailure.INVALID_CONFIG, "定位配置超出允许范围")

    depth_array = np.asarray(depth_image)
    if depth_array.ndim != 2 or depth_array.size == 0:
        return _failure(LocalizationFailure.INVALID_DEPTH_IMAGE, "深度图必须是非空二维数组")

    if (
        not depth_intrinsics.is_valid()
        or not color_intrinsics.is_valid()
        or depth_array.shape != (depth_intrinsics.height, depth_intrinsics.width)
    ):
        return _failure(LocalizationFailure.INVALID_INTRINSICS, "内参与图像尺寸不一致")

    if not depth_to_color.is_valid():
        return _failure(LocalizationFailure.INVALID_EXTRINSICS, "depth_to_color 外参无效")

    clipped_box = detection_box.clipped(color_intrinsics.width, color_intrinsics.height)
    inset_box = clipped_box.inset(config.box_inset_ratio) if clipped_box else None
    if clipped_box is None or inset_box is None:
        return _failure(LocalizationFailure.INVALID_DETECTION_BOX, "检测框无效或收缩后为空")

    raw_depth = depth_array.astype(np.float64, copy=False)
    depth_m = raw_depth * config.depth_scale_m_per_unit
    valid_depth = np.isfinite(depth_m) & (depth_m > max(0.0, config.min_depth_m))
    if np.isfinite(config.max_depth_m):
        valid_depth &= depth_m < config.max_depth_m
    if not np.any(valid_depth):
        return _failure(LocalizationFailure.NO_VALID_DEPTH, "深度图没有有效像素")

    rows, cols = np.nonzero(valid_depth)
    z_depth = depth_m[rows, cols]
    x_depth = (cols.astype(np.float64) - depth_intrinsics.cx) * z_depth / depth_intrinsics.fx
    y_depth = (rows.astype(np.float64) - depth_intrinsics.cy) * z_depth / depth_intrinsics.fy
    points_depth = np.column_stack((x_depth, y_depth, z_depth))

    rotation, translation = depth_to_color.arrays()
    points_color = points_depth @ rotation.T + translation
    positive_z = np.isfinite(points_color).all(axis=1) & (points_color[:, 2] > 0.0)
    points_depth = points_depth[positive_z]
    points_color = points_color[positive_z]
    if points_color.size == 0:
        return _failure(LocalizationFailure.NO_VALID_DEPTH, "外参变换后没有正深度点")

    projected_x = color_intrinsics.fx * points_color[:, 0] / points_color[:, 2] + color_intrinsics.cx
    projected_y = color_intrinsics.fy * points_color[:, 1] / points_color[:, 2] + color_intrinsics.cy

    in_full_box = (
        (projected_x >= clipped_box.x1)
        & (projected_x < clipped_box.x2)
        & (projected_y >= clipped_box.y1)
        & (projected_y < clipped_box.y2)
    )
    candidate_points = int(np.count_nonzero(in_full_box))
    in_inset_box = (
        (projected_x >= inset_box.x1)
        & (projected_x < inset_box.x2)
        & (projected_y >= inset_box.y1)
        & (projected_y < inset_box.y2)
    )
    selected_depth = points_depth[in_inset_box]
    selected_color = points_color[in_inset_box]
    selected_x = projected_x[in_inset_box]
    selected_y = projected_y[in_inset_box]
    selected_count = int(selected_color.shape[0])

    if selected_count < config.min_valid_points:
        return _failure(
            LocalizationFailure.INSUFFICIENT_POINTS,
            f"有效投影点不足: {selected_count} < {config.min_valid_points}",
            candidate_points=candidate_points,
            valid_points=selected_count,
        )

    rounded_pixels = np.column_stack((np.rint(selected_x), np.rint(selected_y))).astype(np.int64)
    unique_pixel_count = int(np.unique(rounded_pixels, axis=0).shape[0])
    valid_ratio = min(1.0, unique_pixel_count / max(1.0, inset_box.area))
    if valid_ratio < config.min_valid_ratio:
        return _failure(
            LocalizationFailure.INSUFFICIENT_COVERAGE,
            f"检测框深度覆盖不足: {valid_ratio:.3f} < {config.min_valid_ratio:.3f}",
            candidate_points=candidate_points,
            valid_points=selected_count,
            valid_ratio=valid_ratio,
        )

    z_values = selected_color[:, 2]
    median_z = float(np.median(z_values))
    absolute_deviation = np.abs(z_values - median_z)
    mad = float(np.median(absolute_deviation))
    if mad > 0.0:
        robust_limit = config.mad_scale * 1.4826 * mad
        robust_mask = absolute_deviation <= robust_limit
    else:
        robust_mask = np.isclose(z_values, median_z, rtol=0.0, atol=1e-9)

    filtered_depth = selected_depth[robust_mask]
    filtered_color = selected_color[robust_mask]
    filtered_x = selected_x[robust_mask]
    filtered_y = selected_y[robust_mask]
    if filtered_color.shape[0] < config.min_valid_points:
        return _failure(
            LocalizationFailure.ROBUST_FILTER_EMPTY,
            "离群值过滤后有效点不足",
            candidate_points=candidate_points,
            valid_points=int(filtered_color.shape[0]),
            valid_ratio=valid_ratio,
        )

    point_depth = tuple(float(value) for value in np.median(filtered_depth, axis=0))
    point_color = tuple(float(value) for value in np.median(filtered_color, axis=0))
    color_pixel = (float(np.median(filtered_x)), float(np.median(filtered_y)))

    return LocalizationResult(
        success=True,
        failure=LocalizationFailure.NONE,
        message="定位成功",
        candidate_points=candidate_points,
        valid_points=int(filtered_color.shape[0]),
        valid_ratio=valid_ratio,
        depth_median_m=float(np.median(filtered_color[:, 2])),
        point_depth_camera=point_depth,
        point_color_camera=point_color,
        projected_color_pixel=color_pixel,
    )
