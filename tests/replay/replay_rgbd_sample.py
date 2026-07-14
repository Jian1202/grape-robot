#!/usr/bin/env python3
"""离线重放固定RGB-D样本，不创建ROS2节点，不接触任何硬件接口。"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / 'robot/grape_robot/code'))

from grape_localization import (  # noqa: E402
    DetectionBox,
    LocalizationConfig,
    RigidTransform,
    intrinsics_from_camera_info,
    localize_detection,
)


def replay_once(sample, metadata):
    rgb_intrinsics = intrinsics_from_camera_info(
        int(sample['rgb_width'][0]),
        int(sample['rgb_height'][0]),
        sample['rgb_k'],
    )
    transform = RigidTransform(
        sample['rotation_depth_to_color'],
        sample['translation_depth_to_color_m'],
    )
    config = LocalizationConfig(depth_scale_m_per_unit=0.001)
    manual_min = float(sample['manual_distance_min_m'][0])
    manual_max = float(sample['manual_distance_max_m'][0])
    frames = []

    for index, expected in enumerate(metadata['frames']):
        depth = sample[f'depth_{index}']
        depth_intrinsics = intrinsics_from_camera_info(
            depth.shape[1], depth.shape[0], sample[f'depth_k_{index}']
        )
        box_values = sample[f'detection_box_{index}'].tolist()
        result = localize_detection(
            depth,
            depth_intrinsics,
            rgb_intrinsics,
            transform,
            DetectionBox(*box_values),
            config,
        )
        projected = (
            None
            if result.projected_color_pixel is None
            else list(result.projected_color_pixel)
        )
        frames.append({
            'index': index,
            'success': result.success,
            'failure': result.failure.value,
            'depth_m': result.depth_median_m,
            'inside_manual_interval': bool(
                result.depth_median_m is not None
                and manual_min <= result.depth_median_m <= manual_max
            ),
            'inside_detection_box': bool(
                projected is not None
                and box_values[0] <= projected[0] <= box_values[2]
                and box_values[1] <= projected[1] <= box_values[3]
            ),
            'depth_matches_capture': bool(
                result.depth_median_m is not None
                and abs(result.depth_median_m - expected['expected_depth_m'])
                <= 1e-12
            ),
            'valid_ratio': result.valid_ratio,
            'valid_points': result.valid_points,
            'projected_pixel': projected,
        })
    return frames


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sample', type=Path)
    parser.add_argument('--repeat', type=int, default=3)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error('--repeat必须大于等于1')

    sample_path = args.sample.resolve()
    sample_sha256 = hashlib.sha256(sample_path.read_bytes()).hexdigest()
    try:
        sample_display = str(sample_path.relative_to(REPO_ROOT))
    except ValueError:
        sample_display = str(sample_path)
    with np.load(sample_path, allow_pickle=False) as sample:
        metadata = json.loads(
            sample['metadata_json_utf8'].tobytes().decode('utf-8')
        )
        runs = [replay_once(sample, metadata) for _ in range(args.repeat)]
        first_run = runs[0]
        deterministic = all(run == first_run for run in runs[1:])
        frame_pass = all(
            frame['success']
            and frame['inside_manual_interval']
            and frame['inside_detection_box']
            and frame['depth_matches_capture']
            for frame in first_run
        )
        depths = [frame['depth_m'] for frame in first_run]
        passed = frame_pass and deterministic
        output = {
            'status': 'PASS' if passed else 'FAIL',
            'sample': sample_display,
            'sample_sha256': sample_sha256,
            'sample_schema_version': int(sample['schema_version'][0]),
            'model_sha256_at_capture': metadata['model_sha256'],
            'frame_count': len(first_run),
            'repeat_count': args.repeat,
            'deterministic': deterministic,
            'manual_distance_m': [
                float(sample['manual_distance_min_m'][0]),
                float(sample['manual_distance_max_m'][0]),
            ],
            'mean_depth_m': float(np.mean(depths)),
            'depth_range_m': float(np.max(depths) - np.min(depths)),
            'frames': first_run,
        }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
