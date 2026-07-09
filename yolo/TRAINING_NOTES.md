# YOLO 训练记录

本文件记录本地第一版葡萄检测模型的训练结果。图片、标签、权重和 `runs/` 输出目录不提交到 Git。

## 本次训练

训练日期：2026-07-09

本地环境：

```text
Python 3.11.9
ultralytics 8.4.90
torch 2.13.0+cpu
CUDA: false
CPU: AMD Ryzen 7 7840HS with Radeon 780M Graphics
RAM: 约 27.8 GB
```

数据集：

```text
总图片：302
总标注框：625
类别 0：unripe_grape，314 个框
类别 1：ripe_grape，311 个框
标注粒度：一串葡萄一个框
```

划分：

```text
train: 210 张，430 个框
val:    60 张，127 个框
test:   32 张， 68 个框
```

## 训练命令

Windows PowerShell：

```powershell
$env:POLARS_SKIP_CPU_CHECK='1'
.\.venv\Scripts\yolo.exe detect train `
  data=yolo/data/grape.yaml `
  model=yolo11n.pt `
  epochs=20 `
  imgsz=320 `
  batch=8 `
  workers=0 `
  device=cpu `
  project=E:/grape-robot/yolo/runs `
  name=grape_v1_cpu_e20 `
  exist_ok=True
```

说明：

```text
POLARS_SKIP_CPU_CHECK=1 用于绕过当前 Windows 环境中 polars 的 CPU 特性检测问题。
workers=0 用于降低 Windows 多进程 DataLoader 出错概率。
```

## 训练结果

训练耗时：

```text
约 0.401 小时，约 24 分钟
```

本地产物：

```text
yolo/runs/grape_v1_cpu_e20/weights/best.pt
yolo/runs/grape_v1_cpu_e20/weights/last.pt
```

验证集指标：

| 类别 | P | R | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| all | 0.996 | 0.965 | 0.993 | 0.834 |
| unripe_grape | 0.992 | 0.951 | 0.991 | 0.822 |
| ripe_grape | 1.000 | 0.980 | 0.995 | 0.846 |

测试集指标：

| 类别 | P | R | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| all | 0.996 | 0.986 | 0.995 | 0.817 |
| unripe_grape | 0.998 | 0.971 | 0.994 | 0.814 |
| ripe_grape | 0.995 | 1.000 | 0.995 | 0.821 |

CPU 推理速度参考：

```text
imgsz=320 时，测试验证约 69.4 ms / image
conf=0.5 预测测试集时，约 166.9 ms / image
```

## 推理测试

建议先用 `conf=0.5`：

```powershell
$env:POLARS_SKIP_CPU_CHECK='1'
.\.venv\Scripts\yolo.exe detect predict `
  model=E:/grape-robot/yolo/runs/grape_v1_cpu_e20/weights/best.pt `
  source=yolo/data/images/test `
  imgsz=320 `
  conf=0.5 `
  save=True `
  project=E:/grape-robot/yolo/runs `
  name=grape_v1_test_pred_conf05 `
  exist_ok=True
```

本地预测结果目录：

```text
yolo/runs/grape_v1_test_pred_conf05/
```

抽查复杂叶片背景后，`conf=0.5` 比默认 `conf=0.25` 更适合作为当前第一版演示阈值。

## 配置不足时的方案

当前电脑可以完成小规模 CPU 基线训练。后续如果数据量增加、输入尺寸提高或使用更大模型，优先按以下顺序处理：

```text
1. 本地继续用 yolo11n.pt、imgsz=320、batch=4~8、epochs=20~50 做快速迭代。
2. 只在确认数据和标注没问题后，再租用云 GPU 训练更大模型或更高分辨率版本。
3. 机器人端只做推理，不在机器人上训练。
4. 如果目标是部署到 Jetson / ROSLander，后续再考虑 ONNX / TensorRT 导出。
```

不要一开始就追求大模型和高 epoch。第一阶段更重要的是用真实场景图片暴露误检、漏检和类别反转问题。

## 下一步

1. 拿 20~50 张新的、没有参与训练的真实场景图片测试。
2. 特别测试远距离、小目标、弱光、强反光、叶片遮挡和纯背景无葡萄图片。
3. 记录误检和漏检样例，决定是否补拍负样本或重新标注。
4. 如果新场景仍稳定，再把 `best.pt` 接入 Python 推理脚本。
5. Python 推理稳定后，再进入 ROS2 图像话题接入。
