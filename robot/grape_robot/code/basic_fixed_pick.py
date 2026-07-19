#!/usr/bin/env python3
# encoding: utf-8
"""固定工位基本夹取执行器。

默认 ``inspect`` 和 ``capture`` 模式只读取状态。``execute`` 模式必须同时满足
配置许可、环境令牌和逐阶段人工确认，且只使用已核对的 FollowJointTrajectory
action；本文件不会向 ``/servo_controller`` 发布消息。
"""

import argparse
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence, Tuple

import rclpy
import yaml
from action_msgs.msg import GoalStatus
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState
from servo_controller_msgs.msg import ServosPosition
from std_srvs.srv import Trigger
from trajectory_msgs.msg import JointTrajectoryPoint

try:
    from .basic_pick_plan import (
        ARM_JOINT_NAMES,
        GRIPPER_JOINT_NAME,
        PickStage,
        accept_confirmation,
        config_from_mapping,
        evaluate_preflight,
        gripper_moved_toward_target,
        positions_within_tolerance,
    )
except ImportError:
    from basic_pick_plan import (
        ARM_JOINT_NAMES,
        GRIPPER_JOINT_NAME,
        PickStage,
        accept_confirmation,
        config_from_mapping,
        evaluate_preflight,
        gripper_moved_toward_target,
        positions_within_tolerance,
    )


ARM_ACTION_NAME = "/arm_controller/follow_joint_trajectory"
GRIPPER_ACTION_NAME = "/gripper_controller/follow_joint_trajectory"
JOINT_STATES_TOPIC = "/controller_manager/joint_states"
SERVO_MONITOR_TOPIC = "/servo_controller"
OBJECT_TRACKING_EXIT_SERVICE = "/object_tracking/exit"
EXECUTE_ENV_NAME = "GRAPE_BASIC_PICK_ENABLE"
EXECUTE_ENV_TOKEN = "I_UNDERSTAND_THIS_MOVES_THE_ROBOT"


def load_config(path: Path):
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    return config_from_mapping(data)


def _seconds_to_duration(seconds: float) -> Duration:
    whole = int(seconds)
    nanosec = int(round((seconds - whole) * 1_000_000_000))
    if nanosec == 1_000_000_000:
        whole += 1
        nanosec = 0
    return Duration(sec=whole, nanosec=nanosec)


class BasicFixedPickNode(Node):
    """ROS2接口适配层；不在回调中执行阻塞动作。"""

    def __init__(self) -> None:
        super().__init__("basic_fixed_pick")
        self.arm_action = ActionClient(
            self, FollowJointTrajectory, ARM_ACTION_NAME
        )
        self.gripper_action = ActionClient(
            self, FollowJointTrajectory, GRIPPER_ACTION_NAME
        )
        self.object_tracking_exit = self.create_client(
            Trigger, OBJECT_TRACKING_EXIT_SERVICE
        )
        self.create_subscription(
            JointState, JOINT_STATES_TOPIC, self._joint_state_callback, 10
        )
        self.create_subscription(
            ServosPosition, SERVO_MONITOR_TOPIC, self._servo_callback, 10
        )

        self._lock = threading.Lock()
        self._joint_positions: Dict[str, float] = {}
        self._joint_state_received_monotonic: Optional[float] = None
        self._servo_message_count = 0
        self._servo_last_received_monotonic: Optional[float] = None
        self._operator_stop = threading.Event()
        self._servo_conflict = threading.Event()
        self._active_goal = None

    def _joint_state_callback(self, message: JointState) -> None:
        if len(message.name) != len(message.position):
            return
        with self._lock:
            self._joint_positions = {
                str(name): float(position)
                for name, position in zip(message.name, message.position)
            }
            self._joint_state_received_monotonic = time.monotonic()

    def _servo_callback(self, _message: ServosPosition) -> None:
        with self._lock:
            self._servo_message_count += 1
            self._servo_last_received_monotonic = time.monotonic()
        self._servo_conflict.set()
        self.get_logger().error(
            "检测到 /servo_controller 消息，取消本次夹取并保持当前位置"
        )

    def request_stop(self) -> None:
        self._operator_stop.set()
        self.cancel_active_goal()

    def stopped(self) -> bool:
        return self._operator_stop.is_set() or self._servo_conflict.is_set()

    def clear_servo_conflict_for_preflight(self) -> None:
        self._servo_conflict.clear()

    def joint_snapshot(self) -> Tuple[Mapping[str, float], float]:
        positions, age, _received = self.joint_snapshot_with_receipt()
        return positions, age

    def joint_snapshot_with_receipt(
        self,
    ) -> Tuple[Mapping[str, float], float, Optional[float]]:
        with self._lock:
            positions = dict(self._joint_positions)
            received = self._joint_state_received_monotonic
        age = float("inf") if received is None else time.monotonic() - received
        return positions, age, received

    def servo_message_count(self) -> int:
        with self._lock:
            return self._servo_message_count

    def wait_for_joint_state(self, timeout_s: float = 5.0) -> bool:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            positions, _age = self.joint_snapshot()
            if positions:
                return True
            time.sleep(0.05)
        return False

    def wait_for_interfaces(self, timeout_s: float = 5.0) -> bool:
        return (
            self.arm_action.wait_for_server(timeout_sec=timeout_s)
            and self.gripper_action.wait_for_server(timeout_sec=timeout_s)
            and self.object_tracking_exit.wait_for_service(timeout_sec=timeout_s)
        )

    def stop_object_tracking(self, timeout_s: float = 5.0) -> None:
        request = Trigger.Request()
        future = self.object_tracking_exit.call_async(request)
        response = self._wait_future(future, timeout_s, "停止 object_tracking")
        if not response.success:
            raise RuntimeError(
                f"/object_tracking/exit 拒绝停止：{response.message}"
            )

    def observe_servo_quiet(self, seconds: float) -> int:
        start_count = self.servo_message_count()
        self.clear_servo_conflict_for_preflight()
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.stopped():
                break
            time.sleep(0.05)
        return self.servo_message_count() - start_count

    def _wait_future(self, future, timeout_s: float, description: str):
        deadline = time.monotonic() + timeout_s
        while not future.done():
            if self.stopped():
                raise RuntimeError(f"{description}被安全停止")
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{description}超时")
            time.sleep(0.02)
        exception = future.exception()
        if exception is not None:
            raise RuntimeError(f"{description}异常：{exception}") from exception
        return future.result()

    def cancel_active_goal(self) -> None:
        goal = self._active_goal
        if goal is None:
            return
        try:
            future = goal.cancel_goal_async()
            deadline = time.monotonic() + 1.0
            while not future.done() and time.monotonic() < deadline:
                time.sleep(0.01)
        except Exception as error:  # 取消失败仍不得追加恢复动作。
            self.get_logger().error(f"取消 action goal 失败：{error}")

    def _cancel_goal_when_available(self, future) -> None:
        """取消在本地超时/停止后才返回的已接受goal。"""

        try:
            goal_handle = future.result()
            if goal_handle is not None and goal_handle.accepted:
                goal_handle.cancel_goal_async()
        except Exception as error:
            self.get_logger().error(f"取消迟到action goal失败：{error}")

    def _wait_goal_handle(self, future, timeout_s: float, description: str):
        deadline = time.monotonic() + timeout_s
        while not future.done():
            if self.stopped():
                future.add_done_callback(self._cancel_goal_when_available)
                raise RuntimeError(f"{description}被安全停止；迟到goal将自动取消")
            if time.monotonic() >= deadline:
                future.add_done_callback(self._cancel_goal_when_available)
                raise TimeoutError(f"{description}超时；迟到goal将自动取消")
            time.sleep(0.02)
        exception = future.exception()
        if exception is not None:
            raise RuntimeError(f"{description}异常：{exception}") from exception
        goal_handle = future.result()
        if goal_handle.accepted and self.stopped():
            goal_handle.cancel_goal_async()
            raise RuntimeError(f"{description}接受时已触发安全停止")
        return goal_handle

    def send_trajectory(
        self,
        client: ActionClient,
        joint_names: Sequence[str],
        positions: Sequence[float],
        duration_s: float,
        timeout_margin_s: float,
        description: str,
    ) -> float:
        if self.stopped():
            raise RuntimeError(f"{description}开始前已处于停止状态")

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = list(joint_names)
        point = JointTrajectoryPoint()
        point.positions = [float(value) for value in positions]
        point.time_from_start = _seconds_to_duration(duration_s)
        goal.trajectory.points = [point]

        goal_future = client.send_goal_async(goal)
        goal_handle = self._wait_goal_handle(
            goal_future, timeout_margin_s, f"{description} goal 接收"
        )
        if not goal_handle.accepted:
            raise RuntimeError(f"{description} action goal 被拒绝")

        self._active_goal = goal_handle
        try:
            result_future = goal_handle.get_result_async()
            wrapped = self._wait_future(
                result_future,
                duration_s + timeout_margin_s,
                f"{description}执行",
            )
            if wrapped.status != GoalStatus.STATUS_SUCCEEDED:
                raise RuntimeError(
                    f"{description}未成功，action状态={wrapped.status}"
                )
            if wrapped.result.error_code != FollowJointTrajectory.Result.SUCCESSFUL:
                raise RuntimeError(
                    f"{description}错误码={wrapped.result.error_code}："
                    f"{wrapped.result.error_string}"
                )
            return time.monotonic()
        except BaseException:
            self.cancel_active_goal()
            raise
        finally:
            self._active_goal = None

    def wait_for_positions(
        self,
        joint_names: Sequence[str],
        target: Sequence[float],
        tolerance_rad: float,
        max_state_age_s: float,
        not_before_monotonic: float,
        timeout_s: float,
        description: str,
    ) -> Mapping[str, float]:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self.stopped():
                raise RuntimeError(f"{description}验证期间被安全停止")
            positions, age, received = self.joint_snapshot_with_receipt()
            if (
                received is not None
                and received >= not_before_monotonic
                and age <= max_state_age_s
                and positions_within_tolerance(
                    positions, joint_names, target, tolerance_rad
                )
            ):
                return positions
            time.sleep(0.05)
        raise RuntimeError(f"{description}未在容差内到位")

    def wait_for_gripper_motion(
        self,
        start_rad: float,
        target_rad: float,
        min_motion_rad: float,
        max_state_age_s: float,
        not_before_monotonic: float,
        timeout_s: float,
    ) -> Mapping[str, float]:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self.stopped():
                raise RuntimeError("夹爪闭合验证期间被安全停止")
            positions, age, received = self.joint_snapshot_with_receipt()
            actual = positions.get(GRIPPER_JOINT_NAME)
            if (
                received is not None
                and received >= not_before_monotonic
                and age <= max_state_age_s
                and actual is not None
                and gripper_moved_toward_target(
                    start_rad, actual, target_rad, min_motion_rad
                )
            ):
                return positions
            time.sleep(0.05)
        raise RuntimeError("夹爪未沿闭合方向达到最小可验证行程")


def _require_confirmation(stage: PickStage) -> PickStage:
    expected = {
        PickStage.WAIT_PICK: "PICK",
        PickStage.WAIT_CLOSE: "CLOSE",
        PickStage.WAIT_LIFT: "LIFT",
    }[stage]
    print(f"请输入 {expected} 并回车；其他输入将安全退出：", end="", flush=True)
    token = input()
    return accept_confirmation(stage, token)


def run_inspect(node: BasicFixedPickNode) -> int:
    if not node.wait_for_joint_state():
        raise RuntimeError("5秒内未收到 /controller_manager/joint_states")
    arm_ready = node.arm_action.wait_for_server(timeout_sec=2.0)
    gripper_ready = node.gripper_action.wait_for_server(timeout_sec=2.0)
    positions, age = node.joint_snapshot()
    print("inspect为只读模式，不会发送action goal或停止现有节点。")
    print(f"arm_action_ready={arm_ready}")
    print(f"gripper_action_ready={gripper_ready}")
    print(f"joint_state_age_s={age:.3f}")
    for name in ("joint1", *ARM_JOINT_NAMES, GRIPPER_JOINT_NAME):
        print(f"{name}={positions.get(name, 'MISSING')}")
    return 0


def run_capture(node: BasicFixedPickNode, item: str) -> int:
    if not node.wait_for_joint_state():
        raise RuntimeError("5秒内未收到 /controller_manager/joint_states")
    positions, age = node.joint_snapshot()
    if age > 0.5:
        raise RuntimeError("关节状态已过期，拒绝记录")
    required = ("joint1", *ARM_JOINT_NAMES, GRIPPER_JOINT_NAME)
    missing = [name for name in required if name not in positions]
    if missing:
        raise RuntimeError(f"缺少关节状态：{missing}")
    print("capture为只读模式；请将以下片段人工复制到配置并独立复核。")
    if item in ("pregrasp", "grasp", "lift"):
        values = [positions[name] for name in ARM_JOINT_NAMES]
        print(f"{item}: [{', '.join(f'{value:.9f}' for value in values)}]")
    elif item == "reference_joint1":
        print(f"reference_joint1_rad: {positions['joint1']:.9f}")
    else:
        key = "open_rad" if item == "gripper_open" else "close_rad"
        print(f"{key}: {positions[GRIPPER_JOINT_NAME]:.9f}")
    return 0


def run_execute(node: BasicFixedPickNode, config_path: Path) -> int:
    config = load_config(config_path)
    if not config.hardware_enabled:
        raise RuntimeError("配置 hardware_enabled=false，拒绝执行")
    if os.environ.get(EXECUTE_ENV_NAME) != EXECUTE_ENV_TOKEN:
        raise RuntimeError(
            f"缺少执行令牌：{EXECUTE_ENV_NAME}={EXECUTE_ENV_TOKEN}"
        )
    if not node.wait_for_interfaces():
        raise RuntimeError("动作服务器或 /object_tracking/exit 不可用")
    if not node.wait_for_joint_state():
        raise RuntimeError("5秒内未收到关节状态")

    node.clear_servo_conflict_for_preflight()
    node.stop_object_tracking()
    quiet_messages = node.observe_servo_quiet(config.servo_quiet_period_s)
    positions, age = node.joint_snapshot()
    preflight = evaluate_preflight(config, positions, age, quiet_messages)
    if not preflight.ok:
        raise RuntimeError(f"启动前安全检查失败：{preflight.failures}")

    print(
        "人工视觉核对参数："
        f"reference_depth={config.visual_reference_depth_m:.3f}m，"
        f"tolerance=±{config.visual_depth_tolerance_m:.3f}m，"
        f"confidence≥{config.visual_min_confidence:.2f}，"
        f"display_age≤{config.visual_display_max_age_s:.3f}s。"
    )
    print("这些参数只供人工查看检测画面，未接入动作坐标。")
    stage = _require_confirmation(PickStage.WAIT_PICK)
    open_completed = node.send_trajectory(
        node.gripper_action,
        (GRIPPER_JOINT_NAME,),
        (config.gripper_open_rad,),
        config.gripper_duration_s,
        config.timeout_margin_s,
        "打开夹爪",
    )
    node.wait_for_positions(
        (GRIPPER_JOINT_NAME,),
        (config.gripper_open_rad,),
        config.gripper_tolerance_rad,
        config.joint_state_max_age_s,
        open_completed,
        config.timeout_margin_s,
        "夹爪打开",
    )
    grasp_completed = node.send_trajectory(
        node.arm_action,
        ARM_JOINT_NAMES,
        config.grasp,
        config.arm_duration_s,
        config.timeout_margin_s,
        "移动到夹取位",
    )
    node.wait_for_positions(
        ARM_JOINT_NAMES,
        config.grasp,
        config.arm_tolerance_rad,
        config.joint_state_max_age_s,
        grasp_completed,
        config.timeout_margin_s,
        "夹取位",
    )

    stage = _require_confirmation(stage)
    before_close, _age = node.joint_snapshot()
    start_gripper = before_close[GRIPPER_JOINT_NAME]
    close_completed = node.send_trajectory(
        node.gripper_action,
        (GRIPPER_JOINT_NAME,),
        (config.gripper_close_rad,),
        config.gripper_duration_s,
        config.timeout_margin_s,
        "闭合夹爪",
    )
    node.wait_for_gripper_motion(
        start_gripper,
        config.gripper_close_rad,
        config.min_gripper_motion_rad,
        config.joint_state_max_age_s,
        close_completed,
        config.timeout_margin_s,
    )

    stage = _require_confirmation(stage)
    lift_completed = node.send_trajectory(
        node.arm_action,
        ARM_JOINT_NAMES,
        config.lift,
        config.arm_duration_s,
        config.timeout_margin_s,
        "抬升",
    )
    node.wait_for_positions(
        ARM_JOINT_NAMES,
        config.lift,
        config.arm_tolerance_rad,
        config.joint_state_max_age_s,
        lift_completed,
        config.timeout_margin_s,
        "抬升位",
    )
    if stage is not PickStage.HOLDING:
        raise RuntimeError("内部状态机未进入HOLDING")
    print("已到达HOLDING：保持当前位置，不自动回位、不自动张开夹爪。")
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("inspect", "capture", "execute"), nargs="?", default="inspect"
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument(
        "--capture",
        choices=(
            "reference_joint1",
            "pregrasp",
            "grasp",
            "lift",
            "gripper_open",
            "gripper_close",
        ),
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.mode == "execute" and args.config is None:
        raise SystemExit("execute模式必须提供 --config")
    if args.mode == "capture" and args.capture is None:
        raise SystemExit("capture模式必须提供 --capture")

    rclpy.init(args=None)
    node = BasicFixedPickNode()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    def handle_signal(_signum, _frame):
        node.request_stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    try:
        if args.mode == "inspect":
            return run_inspect(node)
        if args.mode == "capture":
            return run_capture(node, args.capture)
        return run_execute(node, args.config)
    except (EOFError, KeyboardInterrupt):
        node.request_stop()
        print("人工取消：已请求取消当前goal，不执行自动恢复动作。", file=sys.stderr)
        return 130
    except Exception as error:
        node.request_stop()
        print(f"安全退出：{error}", file=sys.stderr)
        return 1
    finally:
        executor.shutdown(timeout_sec=2.0)
        node.destroy_node()
        rclpy.shutdown()
        spin_thread.join(timeout=2.0)


if __name__ == "__main__":
    raise SystemExit(main())
