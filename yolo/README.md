# YOLO 模块

本目录用于管理葡萄检测模型相关内容。

当前目标类别建议为：

names:
  0: unripe_grape
  1: ripe_grape

## 目录说明

data/      数据集说明与 YOLO 配置
scripts/   训练、推理、数据划分脚本
models/    模型权重说明

训练记录：

TRAINING_NOTES.md

## 注意事项

- 不要直接提交大量原始图片。
- 不要直接提交大型模型权重。
- 训练输出 `runs/` 不进入 Git。
- 第一版目标是先在教室模拟葡萄架场景中稳定识别成熟 / 未成熟葡萄。
