# 06-YOLO数据集与模型

本文件长期维护，不每天新建。  
用于记录“基于移动机械臂的葡萄智能视觉夹取系统”中 YOLO 数据集、类别定义、采集规范、标注规范、训练命令、推理接口和模型版本管理。

---

## 1. 文档定位

本文件主要记录：

```text
YOLO 识别目标定义
成熟 / 未成熟类别划分
教室模拟葡萄架数据采集规范
训练集 / 验证集 / 测试集目录结构
标注规则
负样本规则
训练脚本与命令
模型权重版本
推理接口输出格式
后续接入 ROS2 的数据接口
```

不在本文件中展开：

```text
机器人远程连接方式
ROS2 节点与话题总表
机械臂控制接口
机械臂动作组文件
完整项目技术路线
每日项目进度
```

对应内容分别放入：

```text
docs/reference/02-机器人系统基础信息.md
docs/reference/03-ROS2关键节点与话题.md
docs/reference/04-机械臂控制接口.md
docs/reference/05-机械臂动作组文件.md
docs/reference/01-项目总览与技术路线.md
docs/progress/
```

---

## 2. 当前 YOLO 任务目标

当前 YOLO 模块的核心任务是：

```text
在教室模拟葡萄架场景下，识别成熟葡萄与未成熟葡萄，并输出目标检测框。
```

第一版不追求复杂农业场景泛化，优先服务现场演示闭环：

```text
机器人到达葡萄架附近
↓
相机获取图像
↓
YOLO 检测成熟 / 未成熟葡萄
↓
输出目标类别、置信度、中心点
↓
后续结合深度图和机械臂夹取
```

---

## 3. 类别定义

第一版建议只保留两个类别：

```yaml
names:
  0: unripe_grape
  1: ripe_grape
```

含义：

```text
ripe_grape：成熟葡萄，通常对应紫色 / 红色 / 深色模拟葡萄
unripe_grape：未成熟葡萄，通常对应绿色模拟葡萄
```

当前不建议第一版加入：

```text
grape_rack
leaf
stem
basket
obstacle
```

原因：

```text
类别越多，标注成本越高
类别边界越复杂，早期模型越不稳定
当前现场演示优先需要识别可夹取的目标葡萄
葡萄架位置可先通过导航点解决，不一定依赖 YOLO 识别
```

如果后续需要机器人远距离自主寻找葡萄架，再考虑加入：

```yaml
names:
  0: unripe_grape
  1: ripe_grape
  2: grape_rack
```

---

## 4. 数据采集原则

核心原则：

```text
训练图片必须尽量接近机器人最终看到的画面。
```

优先级：

```text
最高优先级：使用机器人最终识别相机采集教室模拟葡萄架图像
其次：使用同等高度、同等角度的手机 / 电脑摄像头采集
最低优先级：网络葡萄图片
```

网络图片只能作为补充，不应作为主数据源。

---

## 5. 数据采集场景

数据至少覆盖以下四层：

```text
Level 1：近距离葡萄
用途：夹取前识别成熟 / 未成熟目标

Level 2：中距离葡萄架
用途：机器人到达葡萄架附近后，确认目标大概位置

Level 3：远距离教室视角
用途：测试机器人从较远位置是否能看到葡萄 / 葡萄架

Level 4：无葡萄教室背景
用途：降低 YOLO 对教室杂物的误检
```

建议采集位置：

```text
位置 A：教室前面，机器人出发点
位置 B：教室中段，机器人行进中可能看到的画面
位置 C：葡萄架远处，刚看到葡萄架
位置 D：葡萄架前 1~2 米
位置 E：葡萄架前 0.5~1 米，准备识别和夹取
位置 F：葡萄架左右偏角
```

每个位置建议拍摄：

```text
无葡萄背景图：10~20 张
有葡萄架远景图：20~50 张
有成熟 / 未成熟葡萄图：30~80 张
```

第一轮推荐总量：

```text
葡萄目标图：200~400 张
教室负样本图：100~200 张
葡萄架中远景图：100~200 张
```

第一轮不要盲目拍太多。正确流程是：

```text
小批量采集
↓
小批量标注
↓
训练第一版
↓
测试误检 / 漏检
↓
针对性补拍
```

---

## 6. 拍摄变化要求

数据应覆盖：

```text
不同距离：近、中、远
不同角度：正面、左侧、右侧、略俯视
不同光照：亮、暗、背光、反光
不同遮挡：叶子遮挡、支架遮挡、葡萄互相遮挡
不同背景：墙、桌子、黑板、地面、门、窗、机器人车身边缘
不同目标组合：只有成熟、只有未成熟、成熟和未成熟混合
```

不要只拍清晰、居中、背景干净的图片。现场演示更容易出问题的是：

```text
远距离小目标
光照反光
颜色接近背景
葡萄被遮挡
背景中有彩色物体
运动模糊
```

---

## 7. 负样本规则

负样本指：

```text
没有葡萄目标的图片
```

负样本应该包含：

```text
空教室背景
葡萄架附近但没有葡萄的图
教室前方 / 中段 / 后方环境
人、桌椅、黑板、墙、地面、门窗、书包、海报等
```

负样本作用：

```text
降低模型把彩色杂物误识别成葡萄的概率
```

YOLO 数据集中可以保留无目标图片。对应 label 文件可以为空，或由标注工具按空标注处理。

---

## 8. 标注规则

第一版标注目标：

```text
只标注成熟葡萄和未成熟葡萄
```

标注原则：

```text
当前第一版数据集采用“一串葡萄 = 一个框”
一张图里有多个葡萄目标，每个都要框
成熟和未成熟必须标成不同类别
不要把叶子、支架、胶带、背景框进去
看不清成熟度的目标不要硬标
太小、太糊、无法判断的目标可以不标或丢弃该图
```

当前第一版已经采用：

```text
整串葡萄标注
```

原因：

```text
标注效率更高，适合先完成 YOLO 识别闭环
与当前 CVAT 数据集导出结果一致
先检测整串葡萄，再结合深度图选择夹取点
```

如果后续机械臂夹取必须精确到单颗葡萄球，需要重新定义标注粒度并补充单颗级别数据。

---

## 9. YOLO 数据集目录结构

推荐结构：

```text
data/yolo/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
├── labels/
│   ├── train/
│   ├── val/
│   └── test/
└── grape.yaml
```

示例 `grape.yaml`：

```yaml
path: ./yolo/data
train: images/train
val: images/val
test: images/test

names:
  0: unripe_grape
  1: ripe_grape
```

如果训练命令在项目根目录 `E:\grape-robot` 执行，`path` 使用：

```yaml
path: ./yolo/data
```

如果训练脚本在其他目录执行，需要使用绝对路径或重新确认相对路径。

---

## 10. 数据划分规则

推荐比例：

```text
train：70%~80%
val：10%~20%
test：10%
```

注意事项：

```text
不要把几乎一模一样的连拍图分别放进 train 和 val
不要让验证集只包含最简单样本
test 应保留一些模型完全没见过的位置、光照和距离
```

更稳妥的划分方式：

```text
某些角度主要放 train
某些新角度放 val
某些新距离 / 新光照专门放 test
```

这样能更真实地评估模型是否能泛化到现场。

---

## 11. 第一版训练命令

安装依赖：

```bash
pip install ultralytics
```

第一版建议使用小模型：

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

如果电脑性能不足，可以先降低：

```text
imgsz=320
epochs=10~20
batch=4
model=yolo11n.pt
```

如果有 NVIDIA GPU，可以适当提高 `imgsz`、`epochs` 和 `batch`。

当前不建议在 Jetson / 机器人上训练模型，机器人上更适合做推理。

---

## 12. 训练产物

训练完成后重点关注：

```text
yolo/runs/grape_v1_cpu_e20/weights/best.pt
yolo/runs/grape_v2_hard26_cpu_e20/weights/best.pt
yolo/runs/grape_v2_hard26_cpu_e20/weights/last.pt
yolo/runs/grape_v2_hard26_cpu_e20/results.png
yolo/runs/grape_v2_hard26_cpu_e20/confusion_matrix.png
```

应交付的核心文件：

```text
best.pt
训练结果图
测试效果截图
数据集说明
模型版本说明
```

不建议长期保存到 Git 的内容：

```text
完整 runs/ 目录
大量 predict 输出图
训练缓存
重复权重
```

---

## 13. 推理测试命令

使用图片文件夹测试：

```bash
yolo detect predict \
  model=yolo/runs/grape_v2_hard26_cpu_e20/weights/best.pt \
  source=tests/test_images \
  conf=0.4 \
  save=True
```

测试时重点观察：

```text
能否框住葡萄
成熟 / 未成熟是否分错
是否把教室杂物误识别为葡萄
远距离是否还能识别
遮挡时是否还能识别
目标中心点是否稳定
```

---

## 14. Python 推理接口

后续 ROS2 节点中大致需要以下输出：

```text
类别 class_id / class_name
置信度 confidence
检测框 x1, y1, x2, y2
中心点 cx, cy
框宽高 w, h
```

Python 示例：

```python
from ultralytics import YOLO

model = YOLO("yolo/runs/grape_v2_hard26_cpu_e20/weights/best.pt")

results = model(frame, conf=0.4)

for box in results[0].boxes:
    cls_id = int(box.cls[0])
    conf = float(box.conf[0])
    x1, y1, x2, y2 = box.xyxy[0].tolist()

    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    w = int(x2 - x1)
    h = int(y2 - y1)

    print(cls_id, conf, cx, cy, w, h)
```

后续与深度图结合时，需要用：

```text
(cx, cy)
```

去读取深度图对应像素区域的深度值。

---

## 15. ROS2 接入预期

YOLO 模块后续应作为 ROS2 视觉节点的一部分。

预期输入：

```text
RGB 图像话题
相机内参
可选：深度图话题
```

预期输出：

```text
检测结果图像，可选
成熟葡萄目标列表
当前最佳目标中心点
目标类别与置信度
```

后续可考虑发布自定义消息，例如：

```text
GrapeDetection.msg
GrapeDetectionArray.msg
```

可能字段：

```text
int32 class_id
string class_name
float32 confidence
float32 x1
float32 y1
float32 x2
float32 y2
float32 cx
float32 cy
float32 depth
```

当前消息格式未最终确定。

---

## 16. 模型版本命名规范

建议命名：

```text
yolo11n_grape_v1.pt
yolo11n_grape_v2.pt
yolo11s_grape_v1.pt
```

每个模型版本需要记录：

```text
训练日期
训练数据数量
类别列表
训练参数
主要改动
测试表现
已知问题
```

示例：

```markdown
## grape_v2_hard26_cpu_e20

- 日期：2026-07-09
- 数据量：328 张图片，692 个框
- 类别：0 unripe_grape / 1 ripe_grape
- 标注粒度：一串葡萄一个框
- 模型：yolo11n.pt
- imgsz：320
- epochs：20
- batch：8
- 设备：CPU
- 主要目标：加入 hard26 困难样本后的第二版识别基线
- 已知问题：数据仍偏模拟和同批次，需要用新场景图片验证泛化
```

---

## 17. 当前已知与未知

当前已知：

```text
项目需要成熟 / 未成熟葡萄识别
教室模拟葡萄架场景是重要演示环境
YOLO 第一版应优先服务现场演示闭环
当前第二版数据集为 328 张图片，类别顺序为 0 unripe_grape / 1 ripe_grape
当前标注粒度为一串葡萄一个框
负样本教室背景图有必要采集
```

当前未知：

```text
最终用于识别的相机话题名称
最终相机分辨率
最终模拟葡萄材质与颜色
最终葡萄架位置是否固定
最终是否要求远距离自主寻找葡萄架
后续是否需要从整串检测改成单颗检测
```

---

## 18. 下一步需要补充的信息

需要从机器人或组员处确认：

```text
1. 最终用于 YOLO 的相机：Gemini / Astra / 其他
2. RGB 图像话题名称
3. 图像分辨率
4. 是否能从机器人直接保存图片
5. 葡萄成熟度颜色定义
6. 后续是否继续使用整串葡萄框
7. 机器人真实视角下的测试图片
8. 第一版 best.pt 是否需要转 ONNX / TensorRT
```
