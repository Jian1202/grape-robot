# YOLO scripts

后续用于保存：

- `collect_images.py`：采集图片
- `split_dataset.py`：划分训练集 / 验证集 / 测试集
- `train_yolo.py`：训练 YOLO 模型
- `predict_yolo.py`：推理测试
- `export_model.py`：导出 ONNX / TensorRT

当前只做目录占位，不写具体脚本。

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
