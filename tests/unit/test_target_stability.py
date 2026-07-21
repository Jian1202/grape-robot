#!/usr/bin/env python3
# encoding: utf-8

import math
import sys
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[2] / "robot" / "grape_robot" / "code"
sys.path.insert(0, str(MODULE_DIR))

from target_stability import (  # noqa: E402
    ObservationGenerationGuard,
    StabilityConfig,
    StabilityFailure,
    TargetStabilityTracker,
    stability_config_from_values,
)


class TargetStabilityTrackerTest(unittest.TestCase):
    def setUp(self):
        self.tracker = TargetStabilityTracker(StabilityConfig(3, 0.03, 0.2))

    def update(self, timestamp, position=(0.0, 0.0, 0.5), **kwargs):
        return self.tracker.update(
            observation_timestamp_s=timestamp,
            now_s=timestamp + 0.01,
            position=position,
            **kwargs,
        )

    def test_three_consistent_frames_become_stable(self):
        first = self.update(1.0)
        second = self.update(1.1, (0.01, 0.0, 0.5))
        third = self.update(1.2, (0.02, 0.0, 0.5))

        self.assertFalse(first.stable)
        self.assertFalse(second.stable)
        self.assertIsNone(second.target)
        self.assertTrue(third.stable)
        self.assertEqual(third.failure, StabilityFailure.NONE)
        self.assertEqual(third.target, (0.02, 0.0, 0.5))

    def test_single_frame_configuration_becomes_stable_immediately(self):
        tracker = TargetStabilityTracker(StabilityConfig(1, 0.0, 0.2))
        result = tracker.update(
            observation_timestamp_s=1.0,
            now_s=1.01,
            position=(0.0, 0.0, 0.5),
        )

        self.assertTrue(result.stable)
        self.assertEqual(result.target, (0.0, 0.0, 0.5))

    def test_no_detection_immediately_clears_stable_target(self):
        self.update(1.0)
        self.update(1.1)
        self.update(1.2)
        result = self.update(1.3, None)

        self.assertFalse(result.stable)
        self.assertIsNone(result.target)
        self.assertEqual(result.failure, StabilityFailure.NO_DETECTION)
        self.assertEqual(result.consecutive_successes, 0)

    def test_localization_failure_clears_and_reappearance_restarts(self):
        self.update(1.0)
        self.update(1.1)
        self.update(1.2)
        failed = self.update(
            1.3,
            None,
            failure=StabilityFailure.LOCALIZATION_FAILED,
        )
        restarted = self.update(1.4)

        self.assertEqual(failed.failure, StabilityFailure.LOCALIZATION_FAILED)
        self.assertIsNone(failed.target)
        self.assertEqual(restarted.consecutive_successes, 1)
        self.assertEqual(restarted.failure, StabilityFailure.WARMING_UP)

    def test_invalid_positions_fail_closed(self):
        for index, position in enumerate(
            ((math.nan, 0, 0), (math.inf, 0, 0), (0, 0), "bad")
        ):
            result = self.update(1.0 + index, position)
            self.assertEqual(result.failure, StabilityFailure.INVALID_POSITION)
            self.assertIsNone(result.target)

    def test_equal_or_rollback_timestamp_fails_closed(self):
        self.update(2.0)
        equal = self.update(2.0)
        rollback = self.update(1.9)

        self.assertEqual(equal.failure, StabilityFailure.TIMESTAMP_ROLLBACK)
        self.assertEqual(rollback.failure, StabilityFailure.TIMESTAMP_ROLLBACK)
        self.assertIsNone(rollback.target)

    def test_non_finite_and_future_timestamps_fail_closed(self):
        invalid = self.tracker.update(
            observation_timestamp_s=math.nan,
            now_s=1.0,
            position=(0, 0, 0.5),
        )
        future = self.tracker.update(
            observation_timestamp_s=2.0,
            now_s=1.9,
            position=(0, 0, 0.5),
        )

        self.assertEqual(invalid.failure, StabilityFailure.INVALID_TIMESTAMP)
        self.assertEqual(future.failure, StabilityFailure.INVALID_TIMESTAMP)

    def test_stale_observation_and_evaluate_expire_target(self):
        stale = self.tracker.update(
            observation_timestamp_s=1.0,
            now_s=1.21,
            position=(0, 0, 0.5),
        )
        self.assertEqual(stale.failure, StabilityFailure.TARGET_EXPIRED)

        self.tracker.reset()
        self.update(2.0)
        self.update(2.05)
        self.update(2.1)
        expired = self.tracker.evaluate(now_s=2.31)
        self.assertEqual(expired.failure, StabilityFailure.TARGET_EXPIRED)
        self.assertIsNone(expired.target)

    def test_position_jump_restarts_with_current_frame(self):
        self.update(1.0)
        self.update(1.1, (0.01, 0, 0.5))
        jumped = self.update(1.2, (0.2, 0, 0.5))
        next_frame = self.update(1.3, (0.21, 0, 0.5))

        self.assertEqual(jumped.failure, StabilityFailure.POSITION_JUMP)
        self.assertEqual(jumped.consecutive_successes, 1)
        self.assertIsNone(jumped.target)
        self.assertEqual(next_frame.consecutive_successes, 2)

    def test_sliding_window_rejects_accumulated_drift(self):
        self.update(1.0, (0.00, 0, 0.5))
        self.update(1.1, (0.02, 0, 0.5))
        result = self.update(1.2, (0.04, 0, 0.5))

        self.assertEqual(result.failure, StabilityFailure.POSITION_JUMP)
        self.assertEqual(result.consecutive_successes, 1)

    def test_reset_clears_target_and_timestamp_history(self):
        self.update(2.0)
        result = self.tracker.reset()
        restarted = self.update(1.0)

        self.assertEqual(result.failure, StabilityFailure.RESET)
        self.assertIsNone(result.target)
        self.assertEqual(restarted.consecutive_successes, 1)

    def test_input_position_is_not_modified(self):
        position = [0.0, 0.0, 0.5]
        self.update(1.0, position)
        self.assertEqual(position, [0.0, 0.0, 0.5])

    def test_invalid_configs_are_rejected(self):
        invalid_configs = (
            (0, 0.03, 0.2),
            (True, 0.03, 0.2),
            (3.5, 0.03, 0.2),
            (3, -0.01, 0.2),
            (3, math.inf, 0.2),
            (3, 0.03, 0.0),
            (3, 0.03, math.nan),
        )
        for values in invalid_configs:
            with self.assertRaises(ValueError):
                StabilityConfig(*values)

    def test_node_parameter_factory_rejects_implicit_frame_conversion(self):
        for value in (True, 3.5, "3"):
            with self.assertRaises(ValueError):
                stability_config_from_values(value, 0.03, 0.2)

        config = stability_config_from_values(3, 0.03, 0.2)
        self.assertEqual(config.required_frames, 3)

    def test_node_parameter_factory_rejects_boolean_numeric_values(self):
        with self.assertRaises(ValueError):
            stability_config_from_values(3, True, 0.2)
        with self.assertRaises(ValueError):
            stability_config_from_values(3, 0.03, False)

    def test_generation_guard_rejects_queued_and_inflight_old_frames(self):
        guard = ObservationGenerationGuard()
        first_generation = guard.reset(1.0)
        self.assertTrue(guard.accepts(first_generation, 1.1))

        second_generation = guard.reset(1.2)
        self.assertFalse(guard.accepts(first_generation, 1.3))
        self.assertFalse(guard.accepts(second_generation, 1.1))
        self.assertTrue(guard.accepts(second_generation, 1.3))

    def test_generation_guard_requires_finite_reset_boundary(self):
        guard = ObservationGenerationGuard()
        with self.assertRaises(ValueError):
            guard.reset(math.nan)


if __name__ == "__main__":
    unittest.main()
