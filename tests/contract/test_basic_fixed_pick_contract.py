#!/usr/bin/env python3
# encoding: utf-8

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NODE = ROOT / "robot" / "grape_robot" / "code" / "basic_fixed_pick.py"
PLAN = ROOT / "robot" / "grape_robot" / "code" / "basic_pick_plan.py"
CONFIG = ROOT / "robot" / "grape_robot" / "config" / "basic_fixed_pick.yaml"
RUNNER = ROOT / "robot" / "grape_robot" / "scripts" / "run_basic_pick.sh"


class BasicFixedPickContractTest(unittest.TestCase):
    def setUp(self):
        self.source = NODE.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def function_node(self, name):
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == name:
                    return node
        self.fail(f"未找到函数：{name}")

    @staticmethod
    def calls_named(tree, name):
        return [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == name)
                or (isinstance(node.func, ast.Attribute) and node.func.attr == name)
            )
        ]

    def assigned_string(self, name):
        for node in self.tree.body:
            if isinstance(node, ast.Assign):
                if any(
                    isinstance(target, ast.Name) and target.id == name
                    for target in node.targets
                ):
                    self.assertIsInstance(node.value, ast.Constant)
                    return node.value.value
        self.fail(f"未找到常量：{name}")

    def test_external_endpoints_are_exact_and_bounded(self):
        self.assertEqual(
            self.assigned_string("ARM_ACTION_NAME"),
            "/arm_controller/follow_joint_trajectory",
        )
        self.assertEqual(
            self.assigned_string("GRIPPER_ACTION_NAME"),
            "/gripper_controller/follow_joint_trajectory",
        )
        self.assertEqual(
            self.assigned_string("JOINT_STATES_TOPIC"),
            "/controller_manager/joint_states",
        )
        self.assertEqual(
            self.assigned_string("SERVO_MONITOR_TOPIC"), "/servo_controller"
        )
        self.assertEqual(
            self.assigned_string("OBJECT_TRACKING_EXIT_SERVICE"),
            "/object_tracking/exit",
        )

        self.assertEqual(len(self.calls_named(self.tree, "ActionClient")), 2)
        self.assertEqual(len(self.calls_named(self.tree, "create_subscription")), 2)
        create_clients = self.calls_named(self.tree, "create_client")
        self.assertEqual(len(create_clients), 1)
        self.assertEqual(create_clients[0].args[1].id, "OBJECT_TRACKING_EXIT_SERVICE")

    def test_node_constructs_no_publishers_or_legacy_motion_interfaces(self):
        self.assertEqual(self.calls_named(self.tree, "create_publisher"), [])
        forbidden = (
            "set_servo_position",
            "set_pose_target",
            "SetRobotPose",
            "GetRobotPose",
            "cmd_vel",
        )
        for symbol in forbidden:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, self.source)

    def test_only_execute_path_can_send_goals_or_stop_tracking(self):
        inspect_tree = self.function_node("run_inspect")
        capture_tree = self.function_node("run_capture")
        execute_tree = self.function_node("run_execute")
        for tree in (inspect_tree, capture_tree):
            self.assertEqual(self.calls_named(tree, "send_trajectory"), [])
            self.assertEqual(self.calls_named(tree, "stop_object_tracking"), [])
        self.assertEqual(len(self.calls_named(execute_tree, "send_trajectory")), 4)
        self.assertEqual(len(self.calls_named(execute_tree, "stop_object_tracking")), 1)
        self.assertEqual(len(self.calls_named(execute_tree, "_require_confirmation")), 3)

    def test_cancellation_covers_active_and_late_goal(self):
        send_source = ast.unparse(self.function_node("send_trajectory"))
        late_source = ast.unparse(
            self.function_node("_cancel_goal_when_available")
        )
        wait_source = ast.unparse(self.function_node("_wait_goal_handle"))
        self.assertIn("cancel_active_goal", send_source)
        self.assertIn("cancel_goal_async", late_source)
        self.assertIn("add_done_callback", wait_source)
        self.assertIn("_cancel_goal_when_available", wait_source)

    def test_actual_position_requires_post_action_joint_state(self):
        position_source = ast.unparse(self.function_node("wait_for_positions"))
        gripper_source = ast.unparse(
            self.function_node("wait_for_gripper_motion")
        )
        for source in (position_source, gripper_source):
            self.assertIn("not_before_monotonic", source)
            self.assertIn("received >= not_before_monotonic", source)

    def test_execute_has_three_independent_permissions(self):
        execute_source = ast.unparse(self.function_node("run_execute"))
        self.assertIn("config.hardware_enabled", execute_source)
        self.assertIn("EXECUTE_ENV_NAME", execute_source)
        self.assertIn("EXECUTE_ENV_TOKEN", execute_source)
        self.assertIn("evaluate_preflight", execute_source)
        self.assertIn("servo_quiet_period_s", execute_source)

        parse_source = ast.unparse(self.function_node("parse_args"))
        self.assertIn("default='inspect'", parse_source)
        plan_source = PLAN.read_text(encoding="utf-8")
        self.assertIn('PickStage.WAIT_PICK: "PICK"', plan_source)
        self.assertIn('PickStage.WAIT_CLOSE: "CLOSE"', plan_source)
        self.assertIn('PickStage.WAIT_LIFT: "LIFT"', plan_source)

    def test_template_and_runner_fail_closed(self):
        config_source = CONFIG.read_text(encoding="utf-8")
        runner_source = RUNNER.read_text(encoding="utf-8")
        self.assertIn("hardware_enabled: false", config_source)
        self.assertGreaterEqual(config_source.count("null"), 6)
        self.assertIn('MODE="${1:-inspect}"', runner_source)
        self.assertIn('MODE" == "execute', runner_source)
        self.assertIn("GRAPE_BASIC_PICK_ENABLE", runner_source)
        self.assertIn("unset COLCON_CURRENT_PREFIX", runner_source)
        self.assertNotIn("ros2 action send_goal", runner_source)
        self.assertNotIn("ros2 topic pub", runner_source)


if __name__ == "__main__":
    unittest.main()
