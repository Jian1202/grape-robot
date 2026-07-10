from __future__ import annotations

import argparse
import random
import shutil
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare YOLO train/val/test split for grape dataset.")
    parser.add_argument(
        "--images",
        default="yolo/data/annotation_work/grape_20260708",
        help="Source image directory.",
    )
    parser.add_argument(
        "--labels",
        default="yolo/data/review/all_export_check/labels/train",
        help="Source YOLO label directory exported from CVAT.",
    )
    parser.add_argument("--out", default="yolo/data", help="Output YOLO data root.")
    parser.add_argument("--seed", type=int, default=20260709, help="Deterministic random seed.")
    parser.add_argument("--train", type=int, default=210, help="Number of training images.")
    parser.add_argument("--val", type=int, default=60, help="Number of validation images.")
    parser.add_argument("--test", type=int, default=32, help="Number of test images.")
    parser.add_argument(
        "--extra-images",
        action="append",
        default=[],
        help="Extra image directory to append after the base split. Can be passed multiple times.",
    )
    parser.add_argument(
        "--extra-labels",
        action="append",
        default=[],
        help="Extra label directory matching --extra-images. Missing labels are treated as empty labels.",
    )
    parser.add_argument(
        "--extra-split",
        action="append",
        choices=["train", "val", "test"],
        default=[],
        help="Split to receive each extra image directory. Repeat once per --extra-images; defaults to train.",
    )
    return parser.parse_args()


def label_counts(label_path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not label_path.exists():
        return counts
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 5:
            counts[parts[0]] += 1
    return counts


def split_items(items: list[dict], train_count: int, val_count: int, test_count: int, seed: int) -> dict[str, list[dict]]:
    if len(items) != train_count + val_count + test_count:
        raise ValueError(f"Split counts do not match item count: {len(items)}")

    rng = random.Random(seed)
    shuffled = items[:]
    rng.shuffle(shuffled)

    targets = {"train": train_count, "val": val_count, "test": test_count}
    splits: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    split_boxes: dict[str, Counter[str]] = {"train": Counter(), "val": Counter(), "test": Counter()}
    total_boxes = Counter()
    for item in shuffled:
        total_boxes.update(item["classes"])

    def score(split: str, item: dict) -> tuple[float, int]:
        size_after = len(splits[split]) + 1
        size_target = targets[split]
        if size_after > size_target:
            return (float("inf"), size_after)

        projected = split_boxes[split] + item["classes"]
        expected_ratio = size_after / size_target
        class_penalty = 0.0
        for cls, total in total_boxes.items():
            expected = total * expected_ratio * (size_target / len(shuffled))
            class_penalty += abs(projected[cls] - expected)
        remaining = size_target - size_after
        return (class_penalty, remaining)

    for item in shuffled:
        best_split = min(targets, key=lambda split: score(split, item))
        splits[best_split].append(item)
        split_boxes[best_split].update(item["classes"])

    return splits


def clean_output(out_root: Path) -> None:
    for subdir in [
        out_root / "images" / "train",
        out_root / "images" / "val",
        out_root / "images" / "test",
        out_root / "labels" / "train",
        out_root / "labels" / "val",
        out_root / "labels" / "test",
    ]:
        if subdir.exists():
            shutil.rmtree(subdir)
        subdir.mkdir(parents=True, exist_ok=True)


def copy_label(label: Path, destination: Path) -> None:
    if label.exists():
        shutil.copy2(label, destination)
    else:
        destination.write_text("", encoding="utf-8")


def write_manifest(out_root: Path, splits: dict[str, list[dict]], seed: int) -> None:
    lines = [
        "# 本地 YOLO 数据集划分记录",
        "",
        f"随机种子：`{seed}`",
        "",
        "## 划分结果",
        "",
        "| split | images | boxes | class 0 unripe_grape | class 1 ripe_grape |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for split in ["train", "val", "test"]:
        class_counts = Counter()
        for item in splits[split]:
            class_counts.update(item["classes"])
        lines.append(
            f"| {split} | {len(splits[split])} | {sum(class_counts.values())} | {class_counts['0']} | {class_counts['1']} |"
        )

    lines.extend(
        [
            "",
            "## 文件列表",
            "",
        ]
    )
    for split in ["train", "val", "test"]:
        lines.append(f"### {split}")
        lines.append("")
        for item in sorted(splits[split], key=lambda entry: entry["stem"]):
            suffix = "，空标签负样本" if not item["classes"] else ""
            lines.append(f"- `{item['image'].name}`{suffix}")
        lines.append("")

    (out_root / "SPLIT_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    if len(args.extra_images) != len(args.extra_labels):
        raise ValueError("--extra-images and --extra-labels must be provided in pairs.")
    if args.extra_split and len(args.extra_split) != len(args.extra_images):
        raise ValueError("--extra-split must be omitted or provided once for each --extra-images.")

    extra_splits = args.extra_split or ["train"] * len(args.extra_images)

    image_dir = Path(args.images)
    label_dir = Path(args.labels)
    out_root = Path(args.out)

    images = sorted(image_dir.glob("*.jpg"))
    items = []
    for image in images:
        label = label_dir / f"{image.stem}.txt"
        if not label.exists():
            raise FileNotFoundError(f"Missing label for {image.name}")
        counts = label_counts(label)
        if not counts:
            raise ValueError(f"Empty label file: {label}")
        items.append({"stem": image.stem, "image": image, "label": label, "classes": counts})

    clean_output(out_root)
    splits = split_items(items, args.train, args.val, args.test, args.seed)

    for extra_image_dir, extra_label_dir, target_split in zip(
        args.extra_images, args.extra_labels, extra_splits
    ):
        extra_image_path = Path(extra_image_dir)
        extra_label_path = Path(extra_label_dir)
        for image in sorted(extra_image_path.glob("*.jpg")):
            label = extra_label_path / f"{image.stem}.txt"
            counts = label_counts(label)
            splits[target_split].append({"stem": image.stem, "image": image, "label": label, "classes": counts})

    for split, split_items_ in splits.items():
        for item in split_items_:
            shutil.copy2(item["image"], out_root / "images" / split / item["image"].name)
            copy_label(item["label"], out_root / "labels" / split / f"{item['stem']}.txt")

    write_manifest(out_root, splits, args.seed)

    for split in ["train", "val", "test"]:
        class_counts = Counter()
        for item in splits[split]:
            class_counts.update(item["classes"])
        print(
            f"{split}: images={len(splits[split])}, boxes={sum(class_counts.values())}, "
            f"unripe={class_counts['0']}, ripe={class_counts['1']}"
        )


if __name__ == "__main__":
    main()
