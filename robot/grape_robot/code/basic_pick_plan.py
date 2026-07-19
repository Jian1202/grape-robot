#!/usr/bin/env python3
# encoding: utf-8
"""固定工位基本夹取的纯配置校验和安全状态判断。"""

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence, Tuple

import math


ARM_JOINT_NAMES = ("joint2", "joint3", "joint4", "joint5")
GRIPPER_JOINT_NAME = "r_joint"
REFERENCE_JOINT_NAME = "joint1"
RADIANS_PER_PULSE = 240.0 / 360.0 * (math.pi * 2.0) / 1000.0
JOINT_TO_SERVO_ID = {
    REFERENCE_JOINT_NAME: 1,
    "joint2": 2,
    "joint3": 3,
    "joint4": 4,
    "joint5": 5,
    GRIPPER_JOINT_NAME: 10,
}
JOINT_INITIAL_PULSE = {
    REFERENCE_JOINT_NAME: 500,
    "joint2": 500,
    "joint3": 500,
    "joint4": 500,
    "joint5": 500,
    GRIPPER_JOINT_NAME: 700,
}


class PickStage(str, Enum):
    WAIT_PICK = "WAIT_PICK"
    WAIT_CLOSE = "WAIT_CLOSE"
    WAIT_LIFT = "WAIT_LIFT"
    HOLDING = "HOLDING"


CONFIRMATION_TOKENS = {
    PickStage.WAIT_PICK: "PICK",
    PickStage.WAIT_CLOSE: "CLOSE",
    PickStage.WAIT_LIFT: "LIFT",
}

NEXT_STAGES = {
    PickStage.WAIT_PICK: PickStage.WAIT_CLOSE,
    PickStage.WAIT_CLOSE: PickStage.WAIT_LIFT,
    PickStage.WAIT_LIFT: PickStage.HOLDING,
}


def _finite_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} 必须是有限数字")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} 必须是有限数字")
    return result


def _positive_number(name: str, value: object) -> float:
    result = _finite_number(name, value)
    if result <= 0.0:
        raise ValueError(f"{name} 必须大于0")
    return result


def _pose(name: str, value: object) -> Tuple[float, float, float, float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"poses.{name} 必须包含4个关节位置")
    values = tuple(
        _finite_number(f"poses.{name}[{index}]", item)
        for index, item in enumerate(value)
    )
    if len(values) != len(ARM_JOINT_NAMES):
        raise ValueError(f"poses.{name} 必须包含4个关节位置")
    return values


@dataclass(frozen=True)
class BasicPickConfig:
    hardware_enabled: bool
    reference_joint1_rad: float
    pregrasp: Tuple[float, float, float, float]
    grasp: Tuple[float, float, float, float]
    lift: Tuple[float, float, float, float]
    gripper_open_rad: float
    gripper_close_rad: float
    arm_duration_s: float = 3.0
    gripper_duration_s: float = 1.5
    timeout_margin_s: float = 2.0
    joint_state_max_age_s: float = 0.5
    joint1_tolerance_rad: float = 0.05
    arm_tolerance_rad: float = 0.08
    gripper_tolerance_rad: float = 0.08
    max_step_delta_rad: float = 0.20
    min_gripper_motion_rad: float = 0.02
    servo_quiet_period_s: float = 5.0
    visual_reference_depth_m: float = 0.0
    visual_depth_tolerance_m: float = 0.03
    visual_min_confidence: float = 0.8
    visual_display_max_age_s: float = 0.6

    def __post_init__(self) -> None:
        if not isinstance(self.hardware_enabled, bool):
            raise ValueError("hardware_enabled 必须是布尔值")

        finite_fields = (
            "reference_joint1_rad",
            "gripper_open_rad",
            "gripper_close_rad",
        )
        for name in finite_fields:
            _finite_number(name, getattr(self, name))

        positive_fields = (
            "arm_duration_s",
            "gripper_duration_s",
            "timeout_margin_s",
            "joint_state_max_age_s",
            "joint1_tolerance_rad",
            "arm_tolerance_rad",
            "gripper_tolerance_rad",
            "max_step_delta_rad",
            "min_gripper_motion_rad",
            "servo_quiet_period_s",
            "visual_reference_depth_m",
            "visual_depth_tolerance_m",
            "visual_display_max_age_s",
        )
        for name in positive_fields:
            _positive_number(name, getattr(self, name))

        confidence = _finite_number(
            "visual_min_confidence", self.visual_min_confidence
        )
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError("visual_min_confidence 必须位于[0, 1]")

        for pose_name in ("pregrasp", "grasp", "lift"):
            if len(getattr(self, pose_name)) != len(ARM_JOINT_NAMES):
                raise ValueError(f"{pose_name} 必须包含4个关节位置")
            for index, value in enumerate(getattr(self, pose_name)):
                _finite_number(f"{pose_name}[{index}]", value)

        for left_name, right_name in (
            ("pregrasp", "grasp"),
            ("grasp", "lift"),
        ):
            left = getattr(self, left_name)
            right = getattr(self, right_name)
            if any(
                abs(a - b) > self.max_step_delta_rad
                for a, b in zip(left, right)
            ):
                raise ValueError(
                    f"{left_name}->{right_name} 单关节变化超过"
                    f"{self.max_step_delta_rad:.3f}rad"
                )

        if (
            abs(self.gripper_close_rad - self.gripper_open_rad)
            < self.min_gripper_motion_rad
        ):
            raise ValueError("夹爪开闭位置差小于最小可验证行程")


def config_from_mapping(data: Mapping[str, object]) -> BasicPickConfig:
    """从YAML映射严格构造配置；模板中的空值会失败关闭。"""

    if not isinstance(data, Mapping):
        raise ValueError("基本夹取配置必须是映射")
    poses = data.get("poses")
    gripper = data.get("gripper")
    motion = data.get("motion", {})
    safety = data.get("safety", {})
    visual = data.get("visual", {})
    for name, value in (
        ("poses", poses),
        ("gripper", gripper),
        ("motion", motion),
        ("safety", safety),
        ("visual", visual),
    ):
        if not isinstance(value, Mapping):
            raise ValueError(f"{name} 必须是映射")

    hardware_enabled = data.get("hardware_enabled")
    if not isinstance(hardware_enabled, bool):
        raise ValueError("hardware_enabled 必须是布尔值")

    return BasicPickConfig(
        hardware_enabled=hardware_enabled,
        reference_joint1_rad=_finite_number(
            "reference_joint1_rad", data.get("reference_joint1_rad")
        ),
        pregrasp=_pose("pregrasp", poses.get("pregrasp")),
        grasp=_pose("grasp", poses.get("grasp")),
        lift=_pose("lift", poses.get("lift")),
        gripper_open_rad=_finite_number(
            "gripper.open_rad", gripper.get("open_rad")
        ),
        gripper_close_rad=_finite_number(
            "gripper.close_rad", gripper.get("close_rad")
        ),
        arm_duration_s=_positive_number(
            "motion.arm_duration_s", motion.get("arm_duration_s", 3.0)
        ),
        gripper_duration_s=_positive_number(
            "motion.gripper_duration_s", motion.get("gripper_duration_s", 1.5)
        ),
        timeout_margin_s=_positive_number(
            "motion.timeout_margin_s", motion.get("timeout_margin_s", 2.0)
        ),
        joint_state_max_age_s=_positive_number(
            "safety.joint_state_max_age_s",
            safety.get("joint_state_max_age_s", 0.5),
        ),
        joint1_tolerance_rad=_positive_number(
            "safety.joint1_tolerance_rad",
            safety.get("joint1_tolerance_rad", 0.05),
        ),
        arm_tolerance_rad=_positive_number(
            "safety.arm_tolerance_rad", safety.get("arm_tolerance_rad", 0.08)
        ),
        gripper_tolerance_rad=_positive_number(
            "safety.gripper_tolerance_rad",
            safety.get("gripper_tolerance_rad", 0.08),
        ),
        max_step_delta_rad=_positive_number(
            "safety.max_step_delta_rad",
            safety.get("max_step_delta_rad", 0.20),
        ),
        min_gripper_motion_rad=_positive_number(
            "safety.min_gripper_motion_rad",
            safety.get("min_gripper_motion_rad", 0.02),
        ),
        servo_quiet_period_s=_positive_number(
            "safety.servo_quiet_period_s",
            safety.get("servo_quiet_period_s", 5.0),
        ),
        visual_reference_depth_m=_positive_number(
            "visual.reference_depth_m", visual.get("reference_depth_m")
        ),
        visual_depth_tolerance_m=_positive_number(
            "visual.depth_tolerance_m", visual.get("depth_tolerance_m", 0.03)
        ),
        visual_min_confidence=_finite_number(
            "visual.min_confidence", visual.get("min_confidence", 0.8)
        ),
        visual_display_max_age_s=_positive_number(
            "visual.display_max_age_s", visual.get("display_max_age_s", 0.6)
        ),
    )


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    failures: Tuple[str, ...]


def positions_within_tolerance(
    actual: Mapping[str, float],
    joint_names: Sequence[str],
    target: Sequence[float],
    tolerance_rad: float,
) -> bool:
    if (
        len(joint_names) != len(target)
        or not math.isfinite(tolerance_rad)
        or tolerance_rad < 0.0
    ):
        return False
    try:
        return all(
            math.isfinite(float(actual[name]))
            and (
                abs(float(actual[name]) - float(expected)) <= tolerance_rad
                or math.isclose(
                    abs(float(actual[name]) - float(expected)),
                    tolerance_rad,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            )
            for name, expected in zip(joint_names, target)
        )
    except (KeyError, TypeError, ValueError):
        return False


def actual_pulses_to_joint_positions(
    pulses_by_servo_id: Mapping[int, int],
) -> Mapping[str, float]:
    """按机器人控制器配置把真实总线pulse转换为关节rad。"""

    positions = {}
    for joint_name in (
        REFERENCE_JOINT_NAME,
        *ARM_JOINT_NAMES,
        GRIPPER_JOINT_NAME,
    ):
        servo_id = JOINT_TO_SERVO_ID[joint_name]
        try:
            pulse = pulses_by_servo_id[servo_id]
        except (KeyError, TypeError) as error:
            raise ValueError(f"缺少舵机ID{servo_id}真实位置") from error
        pulse_value = _finite_number(f"servo[{servo_id}].pulse", pulse)
        if pulse_value < 0.0 or pulse_value > 1000.0:
            raise ValueError(f"舵机ID{servo_id}真实位置超出[0, 1000]")
        positions[joint_name] = (
            JOINT_INITIAL_PULSE[joint_name] - pulse_value
        ) * RADIANS_PER_PULSE
    return positions


def evaluate_preflight(
    config: BasicPickConfig,
    joint_positions: Mapping[str, float],
    joint_state_age_s: float,
    servo_messages_during_quiet_period: int,
) -> PreflightResult:
    failures = []
    if (
        not math.isfinite(joint_state_age_s)
        or joint_state_age_s < 0.0
        or joint_state_age_s > config.joint_state_max_age_s
    ):
        failures.append("JOINT_STATE_STALE")
    if servo_messages_during_quiet_period != 0:
        failures.append("SERVO_TOPIC_NOT_QUIET")
    if not positions_within_tolerance(
        joint_positions,
        (REFERENCE_JOINT_NAME,),
        (config.reference_joint1_rad,),
        config.joint1_tolerance_rad,
    ):
        failures.append("JOINT1_NOT_FIXED")
    if not positions_within_tolerance(
        joint_positions,
        ARM_JOINT_NAMES,
        config.pregrasp,
        config.arm_tolerance_rad,
    ):
        failures.append("NOT_AT_PREGRASP")
    if GRIPPER_JOINT_NAME not in joint_positions:
        failures.append("GRIPPER_STATE_MISSING")
    return PreflightResult(not failures, tuple(failures))


def gripper_moved_toward_target(
    start_rad: float,
    actual_rad: float,
    target_rad: float,
    min_motion_rad: float,
) -> bool:
    values = (start_rad, actual_rad, target_rad, min_motion_rad)
    if not all(math.isfinite(value) for value in values) or min_motion_rad <= 0.0:
        return False
    direction = target_rad - start_rad
    if abs(direction) < min_motion_rad:
        return False
    return (actual_rad - start_rad) * math.copysign(1.0, direction) >= min_motion_rad


def accept_confirmation(stage: PickStage, token: str) -> PickStage:
    expected = CONFIRMATION_TOKENS.get(stage)
    if expected is None or token != expected:
        raise ValueError(f"{stage.value} 只接受确认词 {expected}")
    return NEXT_STAGES[stage]
