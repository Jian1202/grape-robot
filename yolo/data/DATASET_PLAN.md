# 葡萄数据集计划

## 当前数据批次

批次名称：

```text
grape_20260708
```

原始数据来源：

```text
E:\图片库\手机照片云服务中转\🍇数据集
```

当前数量：

```text
302 张 JPG 图片
```

## 拍摄覆盖情况

本批次图片已覆盖：

- 白色桌子背景
- 橙色椅子背景
- 黑色椅子背景
- 灰色地板背景
- 单串紫色葡萄
- 单串绿色葡萄
- 一株两串紫色和绿色葡萄
- 四个目标组合场景
- 亮光环境
- 弱光环境

## 本地工作目录

当前项目内本地数据目录：

```text
yolo/data/raw/grape_20260708/              原图备份
yolo/data/annotation_work/grape_20260708/  标注工作目录
yolo/data/review/                          待复查图片
```

这些目录只在本地使用，不提交到 GitHub。

## 第一版类别

```text
0 unripe_grape
1 ripe_grape
```

## 数据集划分

当前已生成第一版 YOLO 数据集划分：

```text
train: 210 张，430 个框，unripe_grape 218 个，ripe_grape 212 个
val:    60 张，127 个框，unripe_grape  61 个，ripe_grape  66 个
test:   32 张， 68 个框，unripe_grape  35 个，ripe_grape  33 个
```

划分记录见：

```text
yolo/data/SPLIT_SUMMARY.md
```

正式 YOLO 数据目录为：

```text
yolo/data/images/train/
yolo/data/images/val/
yolo/data/images/test/
yolo/data/labels/train/
yolo/data/labels/val/
yolo/data/labels/test/
```

这些图片和标签目录只在本地使用，不提交到 GitHub。

如需重新生成划分，运行：

```bash
python yolo/scripts/prepare_dataset_split.py
```

## 下一步

1. 使用没有参与训练的新图片测试第一版模型。
2. 重点检查叶子、椅子、地面、桌面等背景误检。
3. 根据新场景测试结果决定是否补拍负样本或增强数据。
4. 训练记录见 `yolo/TRAINING_NOTES.md`。
