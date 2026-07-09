# YOLO 数据集说明

本目录用于保存数据集配置和少量说明文件。

大量原始图片不建议直接提交到 Git。

推荐数据类型：

- 近距离葡萄图片
- 中距离葡萄架图片
- 教室背景负样本
- 成熟 / 未成熟混合样本

推荐类别：

names:
  0: unripe_grape
  1: ripe_grape

## 当前本地数据批次

当前本地准备的数据批次为：

```text
grape_20260708
```

本地原图备份目录：

```text
yolo/data/raw/grape_20260708/
```

标注工作目录：

```text
yolo/data/annotation_work/grape_20260708/
```

以上目录只在本地使用，不提交到 GitHub。

标注前先阅读：

- `ANNOTATION_GUIDE.md`
- `DATASET_PLAN.md`

## 当前正式 YOLO 数据目录

第一版数据集已经整理到：

```text
yolo/data/images/train/
yolo/data/images/val/
yolo/data/images/test/
yolo/data/labels/train/
yolo/data/labels/val/
yolo/data/labels/test/
```

划分记录：

```text
yolo/data/SPLIT_SUMMARY.md
```

以上图片和标签目录只在本地使用，不提交到 GitHub。
