#!/usr/bin/env python3
"""用本地固定样本离线重放稳定、失效、重建与代次拒绝序列。"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "robot/grape_robot/code"))

from grape_localization import (  # noqa: E402
    DetectionBox,
    LocalizationConfig,
    RigidTransform,
    intrinsics_from_camera_info,
    localize_detection,
)
from target_stability import (  # noqa: E402
    ObservationGenerationGuard,
    StabilityConfig,
    StabilityFailure,
    TargetStabilityTracker,
)


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_present_positions(sample_path):
    """从D03真实深度样本重新计算每帧RGB相机三维位置。"""

    with np.load(sample_path, allow_pickle=False) as sample:
        metadata = json.loads(sample["metadata_json_utf8"].tobytes().decode("utf-8"))
        rgb_intrinsics = intrinsics_from_camera_info(
            int(sample["rgb_width"][0]),
            int(sample["rgb_height"][0]),
            sample["rgb_k"],
        )
        transform = RigidTransform(
            sample["rotation_depth_to_color"],
            sample["translation_depth_to_color_m"],
        )
        config = LocalizationConfig(depth_scale_m_per_unit=0.001)
        positions = []
        for index in range(len(metadata["frames"])):
            depth = sample[f"depth_{index}"]
            depth_intrinsics = intrinsics_from_camera_info(
                depth.shape[1], depth.shape[0], sample[f"depth_k_{index}"]
            )
            result = localize_detection(
                depth,
                depth_intrinsics,
                rgb_intrinsics,
                transform,
                DetectionBox(*sample[f"detection_box_{index}"].tolist()),
                config,
            )
            if not result.success or result.point_color_camera is None:
                raise RuntimeError(
                    f"D03第{index}帧定位失败: {result.failure.value}"
                )
            positions.append(result.point_color_camera)
    if len(positions) < 6:
        raise RuntimeError("D03样本至少需要6个成功定位帧")
    return positions


def verify_empty_capture(sample_path):
    """确认D01采集元数据中的每帧均为无检测。"""

    with np.load(sample_path, allow_pickle=False) as sample:
        metadata = json.loads(sample["metadata_json_utf8"].tobytes().decode("utf-8"))
    counts = [len(frame["detections_at_capture"]) for frame in metadata["frames"]]
    if not counts or any(count != 0 for count in counts):
        raise RuntimeError("D01样本不是全空检测序列")
    return counts


def result_record(label, result):
    return {
        "label": label,
        "stable": result.stable,
        "failure": result.failure.value,
        "count": result.consecutive_successes,
        "target": None if result.target is None else list(result.target),
    }


def run_state_sequence(positions):
    tracker = TargetStabilityTracker(StabilityConfig(3, 0.03, 0.2))
    records = []
    timestamp = 1.0

    for index, position in enumerate(positions[:3]):
        result = tracker.update(
            observation_timestamp_s=timestamp,
            now_s=timestamp + 0.01,
            position=position,
        )
        records.append(result_record(f"present_{index + 1}", result))
        timestamp += 0.05

    missing = tracker.update(
        observation_timestamp_s=timestamp,
        now_s=timestamp + 0.01,
        position=None,
        failure=StabilityFailure.NO_DETECTION,
    )
    records.append(result_record("empty_1", missing))
    timestamp += 0.05

    for index, position in enumerate(positions[3:6]):
        result = tracker.update(
            observation_timestamp_s=timestamp,
            now_s=timestamp + 0.01,
            position=position,
        )
        records.append(result_record(f"reappear_{index + 1}", result))
        timestamp += 0.05
    return records


def run_interrupted_sequence(positions):
    tracker = TargetStabilityTracker(StabilityConfig(3, 0.03, 0.2))
    first = tracker.update(
        observation_timestamp_s=2.0, now_s=2.01, position=positions[0]
    )
    second = tracker.update(
        observation_timestamp_s=2.05, now_s=2.06, position=positions[1]
    )
    missing = tracker.update(
        observation_timestamp_s=2.10,
        now_s=2.11,
        position=None,
        failure=StabilityFailure.NO_DETECTION,
    )
    reappeared = tracker.update(
        observation_timestamp_s=2.15, now_s=2.16, position=positions[2]
    )
    return [
        result_record("present_1", first),
        result_record("present_2", second),
        result_record("empty_1", missing),
        result_record("reappear_1", reappeared),
    ]


def run_generation_sequence():
    guard = ObservationGenerationGuard()
    old_generation = guard.reset(3.0)
    queued_before_reset = guard.accepts(old_generation, 3.05)
    new_generation = guard.reset(3.10)
    return {
        "queued_before_reset_was_current": queued_before_reset,
        "inflight_old_generation_accepted": guard.accepts(old_generation, 3.15),
        "queued_old_timestamp_accepted": guard.accepts(new_generation, 3.05),
        "fresh_new_generation_accepted": guard.accepts(new_generation, 3.15),
    }


def validate_run(run):
    main = run["main_sequence"]
    interrupted = run["interrupted_sequence"]
    generation = run["generation_sequence"]
    return bool(
        [item["failure"] for item in main]
        == [
            "WARMING_UP",
            "WARMING_UP",
            "NONE",
            "NO_DETECTION",
            "WARMING_UP",
            "WARMING_UP",
            "NONE",
        ]
        and [item["count"] for item in main] == [1, 2, 3, 0, 1, 2, 3]
        and main[2]["stable"]
        and main[2]["target"] is not None
        and main[3]["target"] is None
        and main[6]["stable"]
        and [item["count"] for item in interrupted] == [1, 2, 0, 1]
        and not interrupted[-1]["stable"]
        and not generation["inflight_old_generation_accepted"]
        and not generation["queued_old_timestamp_accepted"]
        and generation["fresh_new_generation_accepted"]
    )


def replay_sequence(present_sample, empty_sample, repeat_count=3):
    positions = load_present_positions(present_sample)
    empty_counts = verify_empty_capture(empty_sample)
    runs = []
    for _ in range(repeat_count):
        runs.append(
            {
                "main_sequence": run_state_sequence(positions),
                "interrupted_sequence": run_interrupted_sequence(positions),
                "generation_sequence": run_generation_sequence(),
            }
        )
    deterministic = all(run == runs[0] for run in runs[1:])
    passed = deterministic and all(validate_run(run) for run in runs)
    return {
        "status": "PASS" if passed else "FAIL",
        "repeat_count": repeat_count,
        "deterministic": deterministic,
        "present_sample_sha256": file_sha256(present_sample),
        "empty_sample_sha256": file_sha256(empty_sample),
        "empty_capture_detection_counts": empty_counts,
        "empty_detection_source": "capture_metadata",
        "first_run": runs[0],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("present_sample", type=Path)
    parser.add_argument("empty_sample", type=Path)
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat必须大于等于1")
    result = replay_sequence(args.present_sample, args.empty_sample, args.repeat)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
