# YOLO scripts

目录包含以下训练与数据处理脚本：

- `collect_images.py`：采集图片
- `split_dataset.py`：划分训练集 / 验证集 / 测试集
- `train_yolo.py`：训练 YOLO 模型
- `predict_yolo.py`：推理测试
- `export_model.py`：导出 ONNX / TensorRT

## 当前脚本

- `prepare_dataset_split.py`：根据 CVAT 导出的 YOLO 标签和本地原图，生成 `train/val/test` 数据集划分。

默认输入：

```text
yolo/data/annotation_work/grape_20260708/
yolo/data/review/all_export_check/labels/train/
```

默认输出：

```text
yolo/data/images/train/
yolo/data/images/val/
yolo/data/images/test/
yolo/data/labels/train/
yolo/data/labels/val/
yolo/data/labels/test/
yolo/data/SPLIT_SUMMARY.md
```

运行：

```bash
python yolo/scripts/prepare_dataset_split.py
```

追加 hard26 困难样本到训练集：

```bash
python yolo/scripts/prepare_dataset_split.py \
  --extra-images yolo/data/review/grape_20260709_unseen \
  --extra-labels yolo/data/review/hard26_export_check/labels/train \
  --extra-split train
```

说明：

```text
extra labels 中缺失的标签文件会按空标签负样本处理。
当前用于把空景、叶片遮挡、远距离等困难样本加入 train。
```

多个附加数据目录可以分别进入 train / val / test。每个 `--extra-images`
都对应一个 `--extra-labels` 和一个 `--extra-split`：

```bash
python yolo/scripts/prepare_dataset_split.py \
  --extra-images yolo/data/review/grape_20260709_unseen \
  --extra-labels yolo/data/review/hard26_export_check/labels/train \
  --extra-split train \
  --extra-images yolo/data/review/v3_split/train_images \
  --extra-labels yolo/data/review/v3_split/train_labels \
  --extra-split train \
  --extra-images yolo/data/review/v3_split/test_images \
  --extra-labels yolo/data/review/v3_split/test_labels \
  --extra-split test
```

### 固定测试集的无增强训练

- `train_noaug.py`：以 `yolo11n.pt` 作为每轮独立起点训练。`noaug` 模式关闭
  色彩、翻转、Mosaic、MixUp、CutMix、CopyPaste 和几何增强；`geometry-small`
  模式只开启小幅旋转、平移和缩放。
- `create_v3_attribute_audit.py`：从 V3 数据划分生成仅含图片路径和已知标注统计的
  本地属性审计表，供人工填写场景属性；审计表输出位于忽略目录 `yolo/data/tmp/`。

三个无增强基线使用 `grape_noaug_v1.yaml`、`grape_noaug_v2.yaml`、
`grape_noaug_v3.yaml`。它们均将同一组 76 张图片作为 `test`，且每次训练都从
`yolo11n.pt` 开始，不继承前一版权重。

示例：

```powershell
$env:POLARS_SKIP_CPU_CHECK='1'
.\.venv\Scripts\python.exe yolo/scripts/train_noaug.py `
  --data yolo/data/grape_noaug_v3.yaml `
  --name grape_v3_geometry_small_cpu_e50 `
  --augmentation-mode geometry-small
```
