# 葡萄数据集计划

## 当前数据批次

批次名称：

```text
grape_20260708
grape_20260709_hard26
grape_20260710_v3_197
```

原始数据来源：

```text
E:\图片库\手机照片云服务中转\🍇数据集
E:\图片库\手机照片云服务中转\葡萄数据集（V3）
```

当前数量：

```text
基础数据：302 张 JPG 图片
困难样本：26 张 JPG 图片
V3 场景样本：197 张 JPG 图片
合计：525 张 JPG 图片
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
yolo/data/review/grape_20260709_unseen/   hard26 新场景复查图片
yolo/data/review/hard26_export_check/      hard26 CVAT 导出检查目录
yolo/data/annotation_work/grape_20260710_v3_all197/  V3 标注工作目录
yolo/data/review/v3_export_check/          V3 CVAT 导出检查目录
yolo/data/review/                          待复查图片
```

这些目录只在本地使用，不提交到 GitHub。

## 第一版类别

```text
0 unripe_grape
1 ripe_grape
```

## 数据集划分

当前已生成第三版 YOLO 数据集划分：

```text
train: 389 张，864 个框，unripe_grape 435 个，ripe_grape 429 个，含 15 张空标签负样本
val:    60 张，127 个框，unripe_grape  61 个，ripe_grape  66 个
test:   76 张，133 个框，unripe_grape  57 个，ripe_grape  76 个，含 16 张空标签负样本
```

V3 的 197 张图片按完整拍摄场景划分：153 张追加到训练集，44 张保留到测试集，
避免连续相似照片同时进入训练和测试。

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

```powershell
python yolo/scripts/prepare_dataset_split.py `
  --extra-images yolo/data/review/grape_20260709_unseen `
  --extra-labels yolo/data/review/hard26_export_check/labels/train `
  --extra-split train `
  --extra-images yolo/data/review/v3_split/train_images `
  --extra-labels yolo/data/review/v3_split/train_labels `
  --extra-split train `
  --extra-images yolo/data/review/v3_split/test_images `
  --extra-labels yolo/data/review/v3_split/test_labels `
  --extra-split test
```

## 下一步

1. 使用 `grape_v3_sceneholdout_cpu_e20/weights/best.pt` 在机器人相机画面上做只读识别演示。
2. 重点检查空教室里的红色物体误检，以及紫红葡萄在重遮挡下的漏检。
3. 后续补拍应优先增加新的光照、真实机器人视角和不同葡萄材质，而不是同场景连拍。
4. 训练记录见 `yolo/TRAINING_NOTES.md`。
