#!/usr/bin/env python3
# encoding: utf-8
"""不依赖 ROS2 的连续目标稳定判断与旧目标失效逻辑。"""

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Deque, Optional, Sequence, Tuple

import math


class StabilityFailure(str, Enum):
    NONE = "NONE"
    WARMING_UP = "WARMING_UP"
    NO_DETECTION = "NO_DETECTION"
    LOCALIZATION_FAILED = "LOCALIZATION_FAILED"
    INVALID_POSITION = "INVALID_POSITION"
    INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
    TIMESTAMP_ROLLBACK = "TIMESTAMP_ROLLBACK"
    TARGET_EXPIRED = "TARGET_EXPIRED"
    POSITION_JUMP = "POSITION_JUMP"
    RESET = "RESET"


@dataclass(frozen=True)
class StabilityConfig:
    required_frames: int = 3
    max_position_delta_m: float = 0.03
    max_target_age_s: float = 0.2

    def __post_init__(self) -> None:
        if (
            isinstance(self.required_frames, bool)
            or not isinstance(self.required_frames, int)
            or self.required_frames <= 0
        ):
            raise ValueError("required_frames 必须为正整数")
        if (
            not math.isfinite(self.max_position_delta_m)
            or self.max_position_delta_m < 0.0
        ):
            raise ValueError("max_position_delta_m 必须为有限非负数")
        if not math.isfinite(self.max_target_age_s) or self.max_target_age_s <= 0.0:
            raise ValueError("max_target_age_s 必须为有限正数")


def stability_config_from_values(
    required_frames: object,
    max_position_delta_m: object,
    max_target_age_s: object,
) -> StabilityConfig:
    """严格校验节点参数原始类型，禁止隐式截断或布尔值冒充数字。"""

    if isinstance(required_frames, bool) or not isinstance(required_frames, int):
        raise ValueError("stability_required_frames 必须是整数，禁止隐式转换")
    numeric_values = (max_position_delta_m, max_target_age_s)
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        for value in numeric_values
    ):
        raise ValueError("稳定距离和年龄参数必须是数字，禁止隐式转换")
    return StabilityConfig(
        required_frames=required_frames,
        max_position_delta_m=float(max_position_delta_m),
        max_target_age_s=float(max_target_age_s),
    )


class ObservationGenerationGuard:
    """用代次和重置时间边界拒绝事件前排队帧与在途帧。"""

    def __init__(self) -> None:
        self._generation = 0
        self._reset_boundary_s = float("-inf")

    @property
    def generation(self) -> int:
        return self._generation

    def reset(self, boundary_timestamp_s: float) -> int:
        if not math.isfinite(boundary_timestamp_s):
            raise ValueError("重置时间边界必须为有限数")
        self._generation += 1
        self._reset_boundary_s = boundary_timestamp_s
        return self._generation

    def accepts(self, generation: int, observation_timestamp_s: float) -> bool:
        return bool(
            generation == self._generation
            and math.isfinite(observation_timestamp_s)
            and observation_timestamp_s > self._reset_boundary_s
        )


@dataclass(frozen=True)
class StabilityResult:
    stable: bool
    target: Optional[Tuple[float, float, float]]
    failure: StabilityFailure
    consecutive_successes: int
    observation_timestamp_s: Optional[float]


class TargetStabilityTracker:
    """只在连续、足够新且空间位置一致时暴露当前帧目标。"""

    def __init__(self, config: StabilityConfig):
        self.config = config
        self._observations: Deque[Tuple[float, Tuple[float, float, float]]] = deque(
            maxlen=config.required_frames
        )
        self._last_timestamp_s: Optional[float] = None
        self._last_result = self._result(StabilityFailure.RESET)

    def _result(
        self,
        failure: StabilityFailure,
        *,
        stable: bool = False,
        target: Optional[Tuple[float, float, float]] = None,
        timestamp_s: Optional[float] = None,
    ) -> StabilityResult:
        if not stable:
            target = None
        return StabilityResult(
            stable=stable,
            target=target,
            failure=failure,
            consecutive_successes=len(self._observations),
            observation_timestamp_s=timestamp_s,
        )

    def _invalidate(
        self,
        failure: StabilityFailure,
        timestamp_s: Optional[float] = None,
    ) -> StabilityResult:
        self._observations.clear()
        self._last_result = self._result(failure, timestamp_s=timestamp_s)
        return self._last_result

    @staticmethod
    def _position_tuple(
        position: Optional[Sequence[float]],
    ) -> Optional[Tuple[float, float, float]]:
        if position is None:
            return None
        try:
            values = tuple(float(value) for value in position)
        except (TypeError, ValueError):
            return None
        if len(values) != 3 or not all(math.isfinite(value) for value in values):
            return None
        return values

    @staticmethod
    def _distance(
        left: Tuple[float, float, float], right: Tuple[float, float, float]
    ) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))

    def update(
        self,
        *,
        observation_timestamp_s: float,
        now_s: float,
        position: Optional[Sequence[float]],
        failure: Optional[StabilityFailure] = None,
    ) -> StabilityResult:
        """提交一帧结果；任何失败都立即清除旧目标。"""

        if not math.isfinite(observation_timestamp_s) or not math.isfinite(now_s):
            return self._invalidate(StabilityFailure.INVALID_TIMESTAMP)
        if (
            self._last_timestamp_s is not None
            and observation_timestamp_s <= self._last_timestamp_s
        ):
            return self._invalidate(
                StabilityFailure.TIMESTAMP_ROLLBACK, observation_timestamp_s
            )
        self._last_timestamp_s = observation_timestamp_s

        age_s = now_s - observation_timestamp_s
        if age_s < 0.0:
            return self._invalidate(
                StabilityFailure.INVALID_TIMESTAMP, observation_timestamp_s
            )
        if age_s > self.config.max_target_age_s:
            return self._invalidate(
                StabilityFailure.TARGET_EXPIRED, observation_timestamp_s
            )
        if failure is not None and failure is not StabilityFailure.NONE:
            return self._invalidate(failure, observation_timestamp_s)

        point = self._position_tuple(position)
        if point is None:
            reason = (
                StabilityFailure.NO_DETECTION
                if position is None
                else StabilityFailure.INVALID_POSITION
            )
            return self._invalidate(reason, observation_timestamp_s)

        previous_count = max(0, self.config.required_frames - 1)
        recent_observations = (
            list(self._observations)[-previous_count:] if previous_count else []
        )
        candidate_points = [item[1] for item in recent_observations] + [point]
        max_distance = max(
            (
                self._distance(candidate_points[i], candidate_points[j])
                for i in range(len(candidate_points))
                for j in range(i + 1, len(candidate_points))
            ),
            default=0.0,
        )
        if max_distance > self.config.max_position_delta_m:
            self._observations.clear()
            self._observations.append((observation_timestamp_s, point))
            self._last_result = self._result(
                StabilityFailure.POSITION_JUMP,
                timestamp_s=observation_timestamp_s,
            )
            return self._last_result

        self._observations.append((observation_timestamp_s, point))
        stable = len(self._observations) == self.config.required_frames
        self._last_result = self._result(
            StabilityFailure.NONE if stable else StabilityFailure.WARMING_UP,
            stable=stable,
            target=point if stable else None,
            timestamp_s=observation_timestamp_s,
        )
        return self._last_result

    def evaluate(self, *, now_s: float) -> StabilityResult:
        """无新帧时检查最近目标是否已过期。"""

        if not math.isfinite(now_s):
            return self._invalidate(StabilityFailure.INVALID_TIMESTAMP)
        if not self._observations:
            return self._last_result
        timestamp_s = self._observations[-1][0]
        age_s = now_s - timestamp_s
        if age_s < 0.0:
            return self._invalidate(StabilityFailure.INVALID_TIMESTAMP, timestamp_s)
        if age_s > self.config.max_target_age_s:
            return self._invalidate(StabilityFailure.TARGET_EXPIRED, timestamp_s)
        return self._last_result

    def reset(self) -> StabilityResult:
        self._last_timestamp_s = None
        return self._invalidate(StabilityFailure.RESET)
