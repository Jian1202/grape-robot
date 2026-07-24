"""生成 V3 样本属性核查清单；仅自动填写标签可确认的信息。"""

from __future__ import annotations

import csv
from pathlib import Path


SOURCE_ROOT = Path("yolo/data/review/v3_split")
OUTPUT_PATH = Path("yolo/data/tmp/v3_attribute_audit.csv")


def label_counts(label_path: Path) -> tuple[int, int, int]:
    if not label_path.exists() or not label_path.read_text(encoding="utf-8").strip():
        return 0, 0, 0

    counts = [0, 0]
    for line in label_path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) == 5 and fields[0] in {"0", "1"}:
            counts[int(fields[0])] += 1
    return sum(counts), counts[0], counts[1]


def main() -> None:
    rows: list[dict[str, str | int]] = []
    for split in ("train", "test"):
        for image_path in sorted((SOURCE_ROOT / f"{split}_images").glob("*.jpg")):
            box_count, unripe_count, ripe_count = label_counts(
                SOURCE_ROOT / f"{split}_labels" / f"{image_path.stem}.txt"
            )
            rows.append(
                {
                    "filename": image_path.name,
                    "split": split,
                    "label_status": "空景负样本" if box_count == 0 else "已标注",
                    "box_count": box_count,
                    "unripe_box_count": unripe_count,
                    "ripe_box_count": ripe_count,
                    "background_manual": "",
                    "lighting_manual": "",
                    "occlusion_manual": "",
                    "target_size_manual": "",
                    "capture_group_manual": "",
                    "review_notes_manual": "",
                }
            )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"已生成 {OUTPUT_PATH}，共 {len(rows)} 行。")


if __name__ == "__main__":
    main()
