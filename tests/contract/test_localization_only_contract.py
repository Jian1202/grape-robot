#!/usr/bin/env python3
# encoding: utf-8

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NODE = ROOT / "robot" / "grape_robot" / "code" / "track_and_grab.py"
LAUNCH = ROOT / "robot" / "grape_robot" / "launch" / "track_and_grab.launch.py"
RUN_SCRIPT = ROOT / "robot" / "grape_robot" / "scripts" / "run_vision.sh"


class LocalizationOnlyContractTest(unittest.TestCase):
    def test_node_has_no_actuator_channel_in_current_stage(self):
        source = NODE.read_text(encoding="utf-8")

        self.assertIn("enforce_localization_only(self.enable_arm)", source)
        self.assertNotIn("create_publisher(ServosPosition", source)
        self.assertNotIn("create_client(GetRobotPose", source)
        self.assertNotIn("create_client(SetRobotPose", source)
        self.assertNotIn("SetBool.Request", source)

    def test_detection_path_uses_explicit_rgbd_mapping(self):
        source = NODE.read_text(encoding="utf-8")

        self.assertIn("/gemini_camera/rgb/camera_info", source)
        self.assertIn("/gemini_camera/depth_to_color", source)
        self.assertIn("DurabilityPolicy.TRANSIENT_LOCAL", source)
        self.assertIn("from .grape_localization import", source)
        self.assertIn("localize_detection(", source)
        self.assertIn("# 定位结果只用于显示", source)

    def test_launch_and_runner_keep_arm_disabled(self):
        launch_source = LAUNCH.read_text(encoding="utf-8")
        run_source = RUN_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("LaunchConfiguration('enable_arm', default='false')", launch_source)
        self.assertIn("enable_arm:=false", run_source)
        self.assertIn('cp "$LOCALIZATION_FILE"', run_source)
        self.assertIn('DEPTH_SCALE_M_PER_UNIT:-0.001', run_source)


if __name__ == "__main__":
    unittest.main()
