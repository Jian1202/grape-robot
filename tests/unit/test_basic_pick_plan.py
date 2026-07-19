#!/usr/bin/env python3
# encoding: utf-8

import copy
import math
import unittest

from robot.grape_robot.code.basic_pick_plan import (
    ARM_JOINT_NAMES,
    BasicPickConfig,
    PickStage,
    accept_confirmation,
    actual_pulses_to_joint_positions,
    config_from_mapping,
    evaluate_preflight,
    gripper_moved_toward_target,
    positions_within_tolerance,
)


def valid_mapping():
    return {
        "hardware_enabled": False,
        "reference_joint1_rad": 0.1,
        "poses": {
            "pregrasp": [0.0, 0.1, 0.2, 0.3],
            "grasp": [0.1, 0.2, 0.25, 0.35],
            "lift": [0.0, 0.1, 0.20, 0.30],
        },
        "gripper": {"open_rad": 0.5, "close_rad": 0.1},
        "motion": {
            "arm_duration_s": 3.0,
            "gripper_duration_s": 1.5,
            "timeout_margin_s": 2.0,
        },
        "safety": {
            "joint_state_max_age_s": 0.5,
            "joint1_tolerance_rad": 0.05,
            "arm_tolerance_rad": 0.08,
            "gripper_tolerance_rad": 0.08,
            "max_step_delta_rad": 0.20,
            "min_gripper_motion_rad": 0.02,
            "servo_quiet_period_s": 5.0,
        },
        "visual": {
            "reference_depth_m": 0.46,
            "depth_tolerance_m": 0.03,
            "min_confidence": 0.8,
            "display_max_age_s": 0.6,
        },
    }


def valid_joint_state():
    return {
        "joint1": 0.1,
        "joint2": 0.0,
        "joint3": 0.1,
        "joint4": 0.2,
        "joint5": 0.3,
        "r_joint": 0.5,
    }


class BasicPickConfigTest(unittest.TestCase):
    def test_valid_mapping_is_accepted_without_mutation(self):
        source = valid_mapping()
        before = copy.deepcopy(source)
        config = config_from_mapping(source)
        self.assertEqual(config.pregrasp, (0.0, 0.1, 0.2, 0.3))
        self.assertFalse(config.hardware_enabled)
        self.assertEqual(source, before)

    def test_template_nulls_fail_closed(self):
        for path in (
            ("reference_joint1_rad",),
            ("poses", "pregrasp"),
            ("gripper", "open_rad"),
            ("visual", "reference_depth_m"),
        ):
            data = valid_mapping()
            target = data
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = None
            with self.subTest(path=path), self.assertRaises(ValueError):
                config_from_mapping(data)

    def test_numeric_fields_reject_bool_nan_inf_and_strings(self):
        for value in (True, False, math.nan, math.inf, "0.1"):
            data = valid_mapping()
            data["reference_joint1_rad"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                config_from_mapping(data)

    def test_hardware_enabled_is_strict_bool(self):
        for value in (1, 0, "false", None):
            data = valid_mapping()
            data["hardware_enabled"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                config_from_mapping(data)

    def test_pose_shape_and_step_delta_are_checked(self):
        data = valid_mapping()
        data["poses"]["grasp"] = [0.1, 0.2, 0.3]
        with self.assertRaises(ValueError):
            config_from_mapping(data)

        data = valid_mapping()
        data["poses"]["grasp"][0] = 0.200001
        with self.assertRaisesRegex(ValueError, "单关节变化"):
            config_from_mapping(data)

    def test_exact_step_delta_is_allowed(self):
        data = valid_mapping()
        data["poses"]["grasp"][0] = 0.2
        config_from_mapping(data)

    def test_small_gripper_span_is_rejected(self):
        data = valid_mapping()
        data["gripper"]["close_rad"] = 0.49
        with self.assertRaisesRegex(ValueError, "最小可验证行程"):
            config_from_mapping(data)

    def test_nonpositive_safety_values_are_rejected(self):
        for name in (
            "joint_state_max_age_s",
            "arm_tolerance_rad",
            "max_step_delta_rad",
            "servo_quiet_period_s",
        ):
            data = valid_mapping()
            data["safety"][name] = 0.0
            with self.subTest(name=name), self.assertRaises(ValueError):
                config_from_mapping(data)

    def test_confidence_range_is_checked(self):
        for value in (-0.01, 1.01):
            data = valid_mapping()
            data["visual"]["min_confidence"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                config_from_mapping(data)


class PreflightTest(unittest.TestCase):
    def setUp(self):
        self.config = config_from_mapping(valid_mapping())

    def test_valid_preflight(self):
        result = evaluate_preflight(self.config, valid_joint_state(), 0.1, 0)
        self.assertTrue(result.ok)
        self.assertEqual(result.failures, ())

    def test_each_safety_failure_is_reported(self):
        scenarios = []
        scenarios.append((valid_joint_state(), 0.6, 0, "JOINT_STATE_STALE"))
        scenarios.append((valid_joint_state(), 0.1, 1, "SERVO_TOPIC_NOT_QUIET"))

        joint1 = valid_joint_state()
        joint1["joint1"] = 0.2
        scenarios.append((joint1, 0.1, 0, "JOINT1_NOT_FIXED"))

        pregrasp = valid_joint_state()
        pregrasp["joint3"] = 0.3
        scenarios.append((pregrasp, 0.1, 0, "NOT_AT_PREGRASP"))

        gripper = valid_joint_state()
        del gripper["r_joint"]
        scenarios.append((gripper, 0.1, 0, "GRIPPER_STATE_MISSING"))

        for joints, age, messages, failure in scenarios:
            with self.subTest(failure=failure):
                result = evaluate_preflight(self.config, joints, age, messages)
                self.assertFalse(result.ok)
                self.assertIn(failure, result.failures)

    def test_invalid_age_is_stale(self):
        for age in (-0.1, math.nan, math.inf):
            with self.subTest(age=age):
                result = evaluate_preflight(
                    self.config, valid_joint_state(), age, 0
                )
                self.assertIn("JOINT_STATE_STALE", result.failures)


class PureHelpersTest(unittest.TestCase):
    def test_actual_pulses_are_converted_with_robot_controller_config(self):
        positions = actual_pulses_to_joint_positions(
            {1: 500, 2: 765, 3: 15, 4: 220, 5: 500, 10: 500}
        )
        self.assertAlmostEqual(positions["joint1"], 0.0)
        self.assertAlmostEqual(positions["joint2"], -1.110029404)
        self.assertAlmostEqual(positions["joint3"], 2.031563249)
        self.assertAlmostEqual(positions["joint4"], 1.172861257)
        self.assertAlmostEqual(positions["joint5"], 0.0)
        self.assertAlmostEqual(positions["r_joint"], 0.837758041)

    def test_actual_pulses_reject_missing_or_invalid_values(self):
        valid = {1: 500, 2: 765, 3: 15, 4: 220, 5: 500, 10: 500}
        for servo_id, value in ((3, None), (4, True), (5, 1001)):
            pulses = dict(valid)
            if value is None:
                del pulses[servo_id]
            else:
                pulses[servo_id] = value
            with self.subTest(servo_id=servo_id), self.assertRaises(ValueError):
                actual_pulses_to_joint_positions(pulses)

    def test_positions_tolerance(self):
        actual = dict(zip(ARM_JOINT_NAMES, (0.0, 0.1, 0.2, 0.3)))
        self.assertTrue(
            positions_within_tolerance(
                actual, ARM_JOINT_NAMES, (0.0, 0.1, 0.2, 0.38), 0.08
            )
        )
        self.assertFalse(
            positions_within_tolerance(
                actual, ARM_JOINT_NAMES, (0.0, 0.1, 0.2, 0.381), 0.08
            )
        )
        self.assertFalse(
            positions_within_tolerance(actual, ARM_JOINT_NAMES, (0.0,), 0.08)
        )

    def test_gripper_motion_supports_both_directions(self):
        self.assertTrue(gripper_moved_toward_target(0.5, 0.47, 0.1, 0.02))
        self.assertFalse(gripper_moved_toward_target(0.5, 0.49, 0.1, 0.02))
        self.assertTrue(gripper_moved_toward_target(0.1, 0.13, 0.5, 0.02))
        self.assertFalse(gripper_moved_toward_target(0.1, 0.07, 0.5, 0.02))

    def test_confirmation_state_machine_is_exact(self):
        stage = accept_confirmation(PickStage.WAIT_PICK, "PICK")
        self.assertEqual(stage, PickStage.WAIT_CLOSE)
        stage = accept_confirmation(stage, "CLOSE")
        self.assertEqual(stage, PickStage.WAIT_LIFT)
        stage = accept_confirmation(stage, "LIFT")
        self.assertEqual(stage, PickStage.HOLDING)
        for token in ("pick", " PICK ", "YES", ""):
            with self.subTest(token=token), self.assertRaises(ValueError):
                accept_confirmation(PickStage.WAIT_PICK, token)


if __name__ == "__main__":
    unittest.main()
