"""使用真实数据、关闭随机数据增强的 YOLO 检测训练入口。"""

from __future__ import annotations

import argparse

from ultralytics import YOLO


NO_AUGMENTATION = {
    "hsv_h": 0.0,
    "hsv_s": 0.0,
    "hsv_v": 0.0,
    "degrees": 0.0,
    "translate": 0.0,
    "scale": 0.0,
    "shear": 0.0,
    "perspective": 0.0,
    "flipud": 0.0,
    "fliplr": 0.0,
    "bgr": 0.0,
    "mosaic": 0.0,
    "mixup": 0.0,
    "cutmix": 0.0,
    "copy_paste": 0.0,
    "close_mosaic": 0,
    # 显式传空列表，避免 Ultralytics 为检测任务注入默认 Albumentations 变换。
    "augmentations": [],
}

# 仅模拟实际拍摄中可能出现的轻微取景偏差；不改颜色、不拼接图像。
SMALL_GEOMETRIC_AUGMENTATION = {
    **NO_AUGMENTATION,
    "degrees": 3.0,
    "translate": 0.05,
    "scale": 0.1,
}


TRAINING_MODES = {
    "noaug": ("不使用随机数据增强", NO_AUGMENTATION),
    "geometry-small": (
        "仅使用小角度旋转、轻微平移和缩放；颜色与合成增强保持关闭",
        SMALL_GEOMETRIC_AUGMENTATION,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="训练葡萄检测模型，并显式记录增强策略。")
    parser.add_argument("--data", required=True, help="数据集 YAML 路径。")
    parser.add_argument("--name", required=True, help="本次训练输出目录名。")
    parser.add_argument("--model", default="yolo11n.pt", help="所有独立实验共用的初始权重。")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--project", default="E:/grape-robot/yolo/runs")
    parser.add_argument("--augmentation-mode", choices=TRAINING_MODES, default="noaug")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mode_description, augmentation = TRAINING_MODES[args.augmentation_mode]
    print("初始权重：", args.model)
    print("数据集：", args.data)
    print("增强策略：", mode_description)
    YOLO(args.model).train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        device=args.device,
        seed=args.seed,
        deterministic=True,
        patience=args.patience,
        project=args.project,
        name=args.name,
        exist_ok=True,
        **augmentation,
    )


if __name__ == "__main__":
    main()
