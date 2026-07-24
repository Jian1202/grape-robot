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

## 第二版 hard26 微调

训练日期：2026-07-09

新增数据：

```text
grape_20260709_hard26
新增图片：26 张
新增标注框：67
类别 0：unripe_grape，38 个框
类别 1：ripe_grape，29 个框
空标签负样本：5 张
```

合并后数据集：

```text
总图片：328
总标注框：692
类别 0：unripe_grape，352 个框
类别 1：ripe_grape，340 个框
```

划分：

```text
train: 236 张，497 个框，含 5 张空标签负样本
val:    60 张，127 个框
test:   32 张， 68 个框
```

训练命令：

```powershell
$env:POLARS_SKIP_CPU_CHECK='1'
.\.venv\Scripts\yolo.exe detect train `
  data=yolo/data/grape.yaml `
  model=E:/grape-robot/yolo/runs/grape_v1_cpu_e20/weights/best.pt `
  epochs=20 `
  imgsz=320 `
  batch=8 `
  workers=0 `
  device=cpu `
  project=E:/grape-robot/yolo/runs `
  name=grape_v2_hard26_cpu_e20 `
  exist_ok=True
```

训练耗时：

```text
约 0.409 小时，约 25 分钟
```

本地产物：

```text
yolo/runs/grape_v2_hard26_cpu_e20/weights/best.pt
yolo/runs/grape_v2_hard26_cpu_e20/weights/last.pt
```

验证集指标：

| 类别 | P | R | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| all | 0.985 | 0.992 | 0.995 | 0.867 |
| unripe_grape | 0.978 | 0.984 | 0.994 | 0.867 |
| ripe_grape | 0.993 | 1.000 | 0.995 | 0.867 |

测试集指标：

| 类别 | P | R | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| all | 0.980 | 0.985 | 0.994 | 0.830 |
| unripe_grape | 0.971 | 0.969 | 0.993 | 0.787 |
| ripe_grape | 0.989 | 1.000 | 0.995 | 0.874 |

hard26 复查结论：

```text
遮挡样本 IMG_20260709_220510 已能检出。
空景样本仍保持无检测。
IMG_20260709_220703 在 conf=0.5 下漏检，但 conf=0.3 下能检出，置信度约 0.49。
原先的大范围异常框已消失。
```

## 第三版 V3 场景微调

训练日期：2026-07-11

新增数据：

```text
grape_20260710_v3_197
新增图片：197 张
新增标注框：432
类别 0：unripe_grape，201 个框
类别 1：ripe_grape，231 个框
空标签负样本：26 张
```

合并后数据集：

```text
总图片：525
总标注框：1124
类别 0：unripe_grape，553 个框
类别 1：ripe_grape，571 个框
```

划分：

```text
train: 389 张，864 个框，含 15 张空标签负样本
val:    60 张，127 个框
test:   76 张，133 个框，含 16 张空标签负样本
```

V3 图片中有 44 张按完整拍摄场景保留到测试集，未参与训练。

训练命令：

```powershell
$env:POLARS_SKIP_CPU_CHECK='1'
.\.venv\Scripts\yolo.exe detect train `
  data=yolo/data/grape.yaml `
  model=E:/grape-robot/yolo/runs/grape_v2_hard26_cpu_e20/weights/best.pt `
  epochs=20 `
  imgsz=320 `
  batch=8 `
  workers=0 `
  device=cpu `
  project=E:/grape-robot/yolo/runs `
  name=grape_v3_sceneholdout_cpu_e20 `
  exist_ok=True
```

训练耗时：

```text
约 0.418 小时，约 25 分钟
```

本地产物：

```text
yolo/runs/grape_v3_sceneholdout_cpu_e20/weights/best.pt
yolo/runs/grape_v3_sceneholdout_cpu_e20/weights/last.pt
```

验证集指标：

| 类别 | P | R | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| all | 0.991 | 1.000 | 0.995 | 0.879 |
| unripe_grape | 0.997 | 1.000 | 0.995 | 0.862 |
| ripe_grape | 0.984 | 1.000 | 0.995 | 0.895 |

同一 76 张测试集上的 v2 / v3 对比：

| 模型 | P | R | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| v2 | 0.948 | 0.797 | 0.872 | 0.633 |
| v3 | 0.965 | 0.888 | 0.917 | 0.691 |

v3 对紫红葡萄的召回从 0.697 提升到 0.829，但其 `mAP50-95` 仍为 0.598，
叶片重遮挡和目标框定位仍是后续重点。

hard26 回归检查：

```text
hard26 已参与训练，因此不作为泛化指标。
conf=0.5 下，20/26 张图片有检测；5 张空景保持无检测。
IMG_20260709_220510 的遮挡葡萄仍能检出。
IMG_20260709_220703 仍在 conf=0.5 下漏检。
```

当前推荐：

```text
演示初期可使用 grape_v3_sceneholdout_cpu_e20/weights/best.pt。
推理阈值先在 conf=0.4~0.5 之间测试。
后续抓取控制不要只依赖置信度，还需要结合目标大小、深度和可达性过滤。
```

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

1. 使用 `grape_v3_sceneholdout_cpu_e20/weights/best.pt` 做机器人相机的只读识别测试。
2. 记录空景红色物体误检、紫红葡萄重遮挡漏检和远距离小目标漏检。
3. 补拍时优先扩大视角、光照和葡萄材质的变化，不重复同一机位连拍。
4. Python 推理稳定后，再进入 ROS2 图像话题接入。

## 2026-07-18：独立无增强基线与小幅几何增强

为避免前一版权重继承干扰数据集比较，V1、V2、V3 均从 `yolo11n.pt` 独立训练
50 个 epoch。每轮使用相同的 76 张测试集（其中 16 张为空景）；数据集仅逐版增加
训练数据，不携带前一版模型参数。

无增强基线 C0 关闭了 HSV、翻转、Mosaic、MixUp、CutMix、CopyPaste 和全部几何增强。
V3 的小幅几何实验 C1 仅设置 `degrees=3`、`translate=0.05`、`scale=0.1`，其余增强
仍关闭。

同一测试集复测结果：

| V3 模型 | P | R | mAP50 | mAP50-95 | 未成熟召回 | 成熟召回 | 空景误检（conf=0.4） |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C0：无增强 | 0.884 | 0.835 | 0.869 | 0.627 | 0.965 | 0.706 | 1 / 16 |
| C1：小幅几何 | 0.889 | 0.841 | 0.855 | 0.645 | 0.961 | 0.722 | 0 / 16 |

`C1` 提升整体召回、整体定位指标和空景表现，但 `ripe_grape` 的 mAP50
从 0.772 降至 0.736，mAP50-95 从 0.523 降至 0.507。因此当前把 C0 保留为
成熟葡萄的保守基线；C1 仅作为待复验候选。后续应分别消融旋转与平移/缩放，并用
多个随机种子复测，不直接以一次结果替换部署模型。
