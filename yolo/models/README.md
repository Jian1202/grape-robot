# YOLO models

本目录用于记录模型权重说明。

不要直接提交大型权重文件，例如：

- `*.pt`
- `*.onnx`
- `*.engine`

如果确实需要管理权重，应考虑 Git LFS 或 GitHub Release。

## 当前本地基线模型

```text
yolo/runs/grape_v2_hard26_cpu_e20/weights/best.pt
```

该文件只保存在本地训练输出目录中，不提交到 Git。

上一版基线：

```text
yolo/runs/grape_v1_cpu_e20/weights/best.pt
```

训练记录见：

```text
yolo/TRAINING_NOTES.md
```
