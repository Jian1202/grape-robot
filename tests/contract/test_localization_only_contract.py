#!/usr/bin/env python3
# encoding: utf-8

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NODE = ROOT / "robot" / "grape_robot" / "code" / "track_and_grab.py"
LAUNCH = ROOT / "robot" / "grape_robot" / "launch" / "track_and_grab.launch.py"
RUN_SCRIPT = ROOT / "robot" / "grape_robot" / "scripts" / "run_vision.sh"


class LocalizationOnlyContractTest(unittest.TestCase):
    def setUp(self):
        self.source = NODE.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def method_node(self, method_name):
        node_class = next(
            node
            for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "TrackAndGrabNode"
        )
        for node in node_class.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == method_name:
                    return node
        self.fail(f"未找到方法: {method_name}")

    @staticmethod
    def called_attributes(node):
        return {
            child.func.attr
            for child in ast.walk(node)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
        }

    def test_node_has_no_actuator_channel_in_current_stage(self):
        self.assertIn("enforce_localization_only(self.enable_arm)", self.source)
        called = self.called_attributes(self.tree)
        self.assertNotIn("create_publisher", called)
        self.assertNotIn("create_client", called)
        self.assertNotIn("SetBool.Request", self.source)

    def test_detection_path_uses_explicit_rgbd_mapping(self):
        self.assertIn("/gemini_camera/rgb/camera_info", self.source)
        self.assertIn("/gemini_camera/depth_to_color", self.source)
        self.assertIn("DurabilityPolicy.TRANSIENT_LOCAL", self.source)
        self.assertIn("from .grape_localization import", self.source)
        self.assertIn("localize_detection(", self.source)
        self.assertIn("# 定位结果只用于显示", self.source)

    def test_stability_path_invalidates_missing_and_failed_targets(self):
        self.assertIn("from .target_stability import", self.source)
        main_calls = self.called_attributes(self.method_node("main"))
        self.assertIn("_update_stability_for_generation", main_calls)
        self.assertIn("evaluate", main_calls)

        for callback in (
            "start_srv_callback",
            "stop_srv_callback",
            "set_color_srv_callback",
        ):
            callback_calls = self.called_attributes(self.method_node(callback))
            self.assertIn("_invalidate_target_state_locked", callback_calls)

        invalidate_calls = self.called_attributes(
            self.method_node("_invalidate_target_state_locked")
        )
        self.assertIn("reset", invalidate_calls)
        self.assertIn("_clear_image_queue_locked", invalidate_calls)

        target_reads = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Attribute)
            and node.attr == "target"
            and isinstance(node.ctx, ast.Load)
        ]
        self.assertEqual(target_reads, [])

    def test_launch_and_runner_keep_arm_disabled(self):
        launch_source = LAUNCH.read_text(encoding="utf-8")
        run_source = RUN_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("LaunchConfiguration('enable_arm', default='false')", launch_source)
        self.assertIn("enable_arm:=false", run_source)
        self.assertIn('cp "$LOCALIZATION_FILE"', run_source)
        self.assertIn('DEPTH_SCALE_M_PER_UNIT:-0.001', run_source)
        self.assertIn(
            "LaunchConfiguration('stability_required_frames', default='3')",
            launch_source,
        )
        self.assertIn(
            "'stability_max_position_delta_m', default='0.03'",
            launch_source,
        )
        self.assertIn(
            "'stability_max_target_age_s', default='0.2'",
            launch_source,
        )


if __name__ == "__main__":
    unittest.main()
