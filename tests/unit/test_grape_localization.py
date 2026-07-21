#!/usr/bin/env python3
# encoding: utf-8

import sys
import unittest
from pathlib import Path

import numpy as np


MODULE_DIR = Path(__file__).resolve().parents[2] / "robot" / "grape_robot" / "code"
sys.path.insert(0, str(MODULE_DIR))

from grape_localization import (  # noqa: E402
    CameraIntrinsics,
    DetectionBox,
    LocalizationConfig,
    LocalizationFailure,
    RigidTransform,
    enforce_localization_only,
    intrinsics_from_camera_info,
    localize_detection,
)


def identity_transform():
    return RigidTransform(np.eye(3), np.zeros(3))


class GrapeLocalizationTest(unittest.TestCase):
    def setUp(self):
        self.intrinsics = CameraIntrinsics(
            width=8,
            height=6,
            fx=100.0,
            fy=100.0,
            cx=3.5,
            cy=2.5,
        )
        self.config = LocalizationConfig(
            depth_scale_m_per_unit=0.001,
            min_valid_points=4,
            min_valid_ratio=0.1,
            box_inset_ratio=0.0,
        )

    def test_identity_projection_localizes_box(self):
        depth = np.full((6, 8), 1000, dtype=np.uint16)
        result = localize_detection(
            depth,
            self.intrinsics,
            self.intrinsics,
            identity_transform(),
            DetectionBox(2, 1, 6, 5),
            self.config,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.failure, LocalizationFailure.NONE)
        self.assertAlmostEqual(result.depth_median_m, 1.0)
        self.assertEqual(result.valid_points, 16)
        self.assertGreaterEqual(result.valid_ratio, 0.9)
        self.assertAlmostEqual(result.projected_color_pixel[0], 3.5)
        self.assertAlmostEqual(result.projected_color_pixel[1], 2.5)

    def test_different_rgb_and_depth_sizes_use_projection(self):
        depth = np.full((6, 8), 1000, dtype=np.uint16)
        color_intrinsics = CameraIntrinsics(16, 12, 200.0, 200.0, 7.5, 5.5)
        result = localize_detection(
            depth,
            self.intrinsics,
            color_intrinsics,
            identity_transform(),
            DetectionBox(4, 2, 12, 10),
            self.config,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.valid_points, 16)
        self.assertAlmostEqual(result.projected_color_pixel[0], 7.5)
        self.assertAlmostEqual(result.projected_color_pixel[1], 5.5)

    def test_translation_is_applied_in_color_frame(self):
        depth = np.full((6, 8), 1000, dtype=np.uint16)
        transform = RigidTransform(np.eye(3), np.array([0.01, 0.0, 0.0]))
        result = localize_detection(
            depth,
            self.intrinsics,
            self.intrinsics,
            transform,
            DetectionBox(3, 1, 7, 5),
            self.config,
        )

        self.assertTrue(result.success)
        self.assertAlmostEqual(result.point_color_camera[0] - result.point_depth_camera[0], 0.01)

    def test_robust_filter_rejects_far_background(self):
        depth = np.full((6, 8), 1000, dtype=np.uint16)
        depth[1, 2] = 4000
        depth[1, 3] = 4000
        original = depth.copy()
        result = localize_detection(
            depth,
            self.intrinsics,
            self.intrinsics,
            identity_transform(),
            DetectionBox(2, 1, 6, 5),
            self.config,
        )

        self.assertTrue(result.success)
        self.assertAlmostEqual(result.depth_median_m, 1.0)
        self.assertLess(result.valid_points, 16)
        np.testing.assert_array_equal(depth, original)

    def test_zero_depth_returns_failure(self):
        result = localize_detection(
            np.zeros((6, 8), dtype=np.uint16),
            self.intrinsics,
            self.intrinsics,
            identity_transform(),
            DetectionBox(2, 1, 6, 5),
            self.config,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.failure, LocalizationFailure.NO_VALID_DEPTH)

    def test_nan_depth_returns_failure(self):
        result = localize_detection(
            np.full((6, 8), np.nan, dtype=np.float64),
            self.intrinsics,
            self.intrinsics,
            identity_transform(),
            DetectionBox(2, 1, 6, 5),
            self.config,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.failure, LocalizationFailure.NO_VALID_DEPTH)

    def test_sparse_depth_fails_minimum_points(self):
        depth = np.zeros((6, 8), dtype=np.uint16)
        depth[2, 3] = 1000
        depth[2, 4] = 1000
        result = localize_detection(
            depth,
            self.intrinsics,
            self.intrinsics,
            identity_transform(),
            DetectionBox(2, 1, 6, 5),
            self.config,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.failure, LocalizationFailure.INSUFFICIENT_POINTS)

    def test_low_depth_coverage_is_rejected(self):
        depth = np.zeros((6, 8), dtype=np.uint16)
        depth[1:3, 2:4] = 1000
        config = LocalizationConfig(
            depth_scale_m_per_unit=0.001,
            min_valid_points=4,
            min_valid_ratio=0.8,
            box_inset_ratio=0.0,
        )
        result = localize_detection(
            depth,
            self.intrinsics,
            self.intrinsics,
            identity_transform(),
            DetectionBox(2, 1, 6, 5),
            config,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.failure, LocalizationFailure.INSUFFICIENT_COVERAGE)

    def test_unknown_depth_scale_fails_closed(self):
        result = localize_detection(
            np.full((6, 8), 1000, dtype=np.uint16),
            self.intrinsics,
            self.intrinsics,
            identity_transform(),
            DetectionBox(2, 1, 6, 5),
            LocalizationConfig(depth_scale_m_per_unit=0.0),
        )

        self.assertFalse(result.success)
        self.assertEqual(result.failure, LocalizationFailure.DEPTH_SCALE_UNKNOWN)

    def test_invalid_config_fails_closed(self):
        result = localize_detection(
            np.full((6, 8), 1000, dtype=np.uint16),
            self.intrinsics,
            self.intrinsics,
            identity_transform(),
            DetectionBox(2, 1, 6, 5),
            LocalizationConfig(
                depth_scale_m_per_unit=0.001,
                min_valid_points=0,
            ),
        )

        self.assertFalse(result.success)
        self.assertEqual(result.failure, LocalizationFailure.INVALID_CONFIG)

    def test_mismatched_depth_intrinsics_fail(self):
        wrong_intrinsics = CameraIntrinsics(9, 6, 100.0, 100.0, 4.0, 2.5)
        result = localize_detection(
            np.full((6, 8), 1000, dtype=np.uint16),
            wrong_intrinsics,
            self.intrinsics,
            identity_transform(),
            DetectionBox(2, 1, 6, 5),
            self.config,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.failure, LocalizationFailure.INVALID_INTRINSICS)

    def test_invalid_extrinsics_fail(self):
        invalid = RigidTransform(np.zeros((3, 3)), np.zeros(3))
        result = localize_detection(
            np.full((6, 8), 1000, dtype=np.uint16),
            self.intrinsics,
            self.intrinsics,
            invalid,
            DetectionBox(2, 1, 6, 5),
            self.config,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.failure, LocalizationFailure.INVALID_EXTRINSICS)

    def test_box_is_clipped_and_empty_box_is_rejected(self):
        depth = np.full((6, 8), 1000, dtype=np.uint16)
        clipped = localize_detection(
            depth,
            self.intrinsics,
            self.intrinsics,
            identity_transform(),
            DetectionBox(-2, -1, 4, 4),
            self.config,
        )
        empty = localize_detection(
            depth,
            self.intrinsics,
            self.intrinsics,
            identity_transform(),
            DetectionBox(20, 20, 30, 30),
            self.config,
        )

        self.assertTrue(clipped.success)
        self.assertFalse(empty.success)
        self.assertEqual(empty.failure, LocalizationFailure.INVALID_DETECTION_BOX)

    def test_intrinsics_factory_requires_nine_k_values(self):
        valid = intrinsics_from_camera_info(8, 6, [100, 0, 3.5, 0, 100, 2.5, 0, 0, 1])
        invalid = intrinsics_from_camera_info(8, 6, [1, 2])

        self.assertTrue(valid.is_valid())
        self.assertFalse(invalid.is_valid())

    def test_arm_motion_is_hard_disabled(self):
        enforce_localization_only(False)
        with self.assertRaises(RuntimeError):
            enforce_localization_only(True)


if __name__ == "__main__":
    unittest.main()
