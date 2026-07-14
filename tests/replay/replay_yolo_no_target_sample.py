#!/usr/bin/env python3
"""离线重放无目标RGB固定样本；不创建ROS2节点，不接触硬件接口。"""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


REPO_ROOT = Path(__file__).resolve().parents[2]


def replay_sample(sample_source, model_path, repeat_count=3, device=0):
    model_path = Path(model_path)
    model_sha256 = hashlib.sha256(model_path.read_bytes()).hexdigest()
    model = YOLO(str(model_path))
    with np.load(sample_source, allow_pickle=False) as sample:
        metadata = json.loads(
            sample['metadata_json_utf8'].tobytes().decode('utf-8')
        )
        frame_count = len(metadata['frames'])
        confidence = float(metadata['confidence_threshold'])
        image_size = int(metadata['inference_image_size'])
        capture_counts = [
            len(frame['detections_at_capture']) for frame in metadata['frames']
        ]
        runs = []
        for repeat_index in range(repeat_count):
            frame_results = []
            for frame_index in range(frame_count):
                rgb = sample[f'rgb_{frame_index}']
                prediction = model.predict(
                    source=cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                    conf=confidence,
                    imgsz=image_size,
                    device=device,
                    verbose=False,
                )[0]
                detections = []
                if prediction.boxes is not None:
                    for box in prediction.boxes:
                        class_id = int(box.cls[0].item())
                        detections.append({
                            'class_id': class_id,
                            'class_name': model.names[class_id],
                            'confidence': float(box.conf[0].item()),
                            'box': box.xyxy[0].tolist(),
                        })
                frame_results.append({
                    'frame_index': frame_index,
                    'detection_count': len(detections),
                    'detections': detections,
                })
            runs.append({
                'repeat_index': repeat_index,
                'frames': frame_results,
            })

    first_counts = [
        frame['detection_count'] for frame in runs[0]['frames']
    ]
    deterministic = all(
        [frame['detection_count'] for frame in run['frames']] == first_counts
        for run in runs[1:]
    )
    all_zero = all(
        frame['detection_count'] == 0
        for run in runs
        for frame in run['frames']
    )
    model_matches_capture = model_sha256 == metadata['model_sha256']
    passed = (
        all(count == 0 for count in capture_counts)
        and all_zero
        and deterministic
        and model_matches_capture
    )
    return {
        'status': 'PASS' if passed else 'FAIL',
        'scenario': metadata['scenario'],
        'frame_count': frame_count,
        'repeat_count': repeat_count,
        'total_inferences': frame_count * repeat_count,
        'capture_detection_counts': capture_counts,
        'replay_detection_counts': [
            [frame['detection_count'] for frame in run['frames']]
            for run in runs
        ],
        'all_zero_detections': all_zero,
        'deterministic': deterministic,
        'model_sha256': model_sha256,
        'model_matches_capture': model_matches_capture,
        'confidence_threshold': confidence,
        'inference_image_size': image_size,
        'old_target_state_verified': False,
        'old_target_state_note': (
            '本脚本只重放检测器；旧目标清除需在部署后的'
            'detection-only节点上另行验证。'
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sample', type=Path)
    parser.add_argument('model', type=Path)
    parser.add_argument('--repeat', type=int, default=3)
    parser.add_argument('--device', default=0)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error('--repeat必须大于等于1')

    result = replay_sample(
        args.sample,
        args.model,
        repeat_count=args.repeat,
        device=args.device,
    )
    sample_path = args.sample.resolve()
    try:
        result['sample'] = str(sample_path.relative_to(REPO_ROOT))
    except ValueError:
        result['sample'] = str(sample_path)
    result['sample_sha256'] = hashlib.sha256(sample_path.read_bytes()).hexdigest()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
