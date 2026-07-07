# 07-GitHub仓库与协作规范

本文件长期维护，不每天新建。  
用于记录“基于移动机械臂的葡萄智能视觉夹取系统”项目在 GitHub 上的仓库结构、文件管理边界、分工方式、提交规范和大文件处理策略。

---

## 1. 文档定位

本文件主要记录：

```text
GitHub 仓库组织方式
目录结构
哪些文件应该提交
哪些文件不应该提交
数据集与模型权重管理方式
ROS2 代码管理方式
文档管理方式
分支与提交规范
组内协作方式
```

不在本文件中展开：

```text
项目总技术路线
机器人系统基础信息
ROS2 话题总表
机械臂控制接口
机械臂动作组
YOLO 训练细节
每日项目进度
```

对应内容分别放入：

```text
docs/reference/01-项目总览与技术路线.md
docs/reference/02-机器人系统基础信息.md
docs/reference/03-ROS2关键节点与话题.md
docs/reference/04-机械臂控制接口.md
docs/reference/05-机械臂动作组文件.md
docs/reference/06-YOLO数据集与模型.md
docs/progress/
```

---

## 2. 仓库策略

当前推荐使用一个 GitHub 仓库统一管理整个项目：

```text
monorepo：一个仓库，内部按模块分目录
```

推荐仓库名：

```text
grape-robot
```

不建议当前阶段拆成多个仓库。原因：

```text
项目规模尚未大到必须拆仓
YOLO、ROS2、机械臂、导航之间需要频繁对接
一个仓库更容易统一文档、配置和版本
新成员更容易理解项目全貌
```

后期如果数据集和模型权重过大，可以单独拆出：

```text
grape-dataset
grape-models
```

或使用 Git LFS / Release / 网盘管理。

---

## 3. 推荐目录结构

完整推荐结构：

```text
grape-robot/
├── README.md
├── .gitignore
├── docs/
│   ├── reference/
│   │   ├── 01-项目总览与技术路线.md
│   │   ├── 02-机器人系统基础信息.md
│   │   ├── 03-ROS2关键节点与话题.md
│   │   ├── 04-机械臂控制接口.md
│   │   ├── 05-机械臂动作组文件.md
│   │   ├── 06-YOLO数据集与模型.md
│   │   └── 07-GitHub仓库与协作规范.md
│   ├── progress/
│   └── reports/
│
├── data/
│   ├── README.md
│   ├── raw/
│   │   ├── classroom/
│   │   ├── grape_close/
│   │   └── grape_rack/
│   └── yolo/
│       ├── images/
│       │   ├── train/
│       │   ├── val/
│       │   └── test/
│       ├── labels/
│       │   ├── train/
│       │   ├── val/
│       │   └── test/
│       └── grape.yaml
│
├── models/
│   ├── README.md
│   └── weights/
│
├── scripts/
│   ├── collect_images.py
│   ├── split_dataset.py
│   ├── train_yolo.py
│   ├── predict_yolo.py
│   └── export_model.py
│
├── ros2/
│   └── src/
│       ├── grape_vision/
│       ├── grape_bringup/
│       ├── grape_interfaces/
│       ├── grape_pick_control/
│       └── grape_navigation/
│
├── configs/
│   ├── camera_topics.yaml
│   ├── yolo_grape.yaml
│   ├── arm_params.yaml
│   └── nav_points.yaml
│
├── tools/
│   ├── read_d6a.py
│   └── check_ros_topics.sh
│
└── tests/
    ├── test_images/
    └── test_predict.py
```

第一版可以先简化为：

```text
grape-robot/
├── README.md
├── .gitignore
├── docs/
│   └── reference/
├── data/
│   └── yolo/
│       └── grape.yaml
├── scripts/
│   ├── train_yolo.py
│   └── predict_yolo.py
└── models/
    └── README.md
```

---

## 4. docs 目录规范

```text
docs/reference/
```

长期复用资料。特点：

```text
不每天新建
随着项目推进持续更新
记录系统结构、接口、路径、命令、结论
```

```text
docs/progress/
```

每日进度资料。特点：

```text
按日期新建
只记录当天做了什么、结论、问题和下一步
不写成百科
```

```text
docs/reports/
```

汇报材料。特点：

```text
用于老师汇报、阶段汇报、比赛答辩
可以从 reference 和 progress 中提炼
```

---

## 5. data 目录规范

```text
data/raw/
```

原始图片，不修改，不直接用于训练。

```text
data/yolo/
```

整理后的 YOLO 数据集。

原则：

```text
raw 保存原始采集结果
yolo 保存训练格式数据
不要手工改乱 labels
每次数据集版本变化应记录说明
```

如果图片数量较少，可以暂时提交到 GitHub。  
如果图片数量较多，建议使用：

```text
Git LFS
外部网盘
GitHub Release
单独 dataset 仓库
```

---

## 6. models 目录规范

```text
models/weights/
```

只保留关键权重：

```text
best.pt
best.onnx
best.engine
```

不建议提交：

```text
完整 runs/ 目录
所有 epoch 权重
大量 predict 结果图
训练缓存
```

模型命名建议：

```text
yolov8n_grape_v1.pt
yolov8n_grape_v2.pt
yolov8s_grape_v1.pt
```

每个模型版本需要在 `models/README.md` 中记录：

```text
训练日期
数据集版本
类别
训练参数
测试表现
已知问题
```

---

## 7. scripts 目录规范

`scripts/` 放通用脚本，不放一次性乱试代码。

建议脚本：

```text
collect_images.py      从相机采集图片
split_dataset.py       划分 train / val / test
train_yolo.py          训练 YOLO 模型
predict_yolo.py        测试 YOLO 模型
export_model.py        导出 ONNX / TensorRT
```

脚本要求：

```text
文件名能看出用途
尽量支持命令行参数
不要把本机绝对路径写死
重要参数写到 configs 或 README
```

---

## 8. ros2 目录规范

`ros2/src/` 只放本项目自己写的 ROS2 包。

不建议把整个机器人工作空间提交到 GitHub：

```text
不要提交 /home/ubuntu/ros2_ws 整体
不要提交官方 package 的完整副本
不要提交 build / install / log
```

原因：

```text
官方代码版权不清晰
文件过多，仓库会失控
build/install/log 是生成物，不是源码
容易误改系统原始代码
```

建议自研包：

```text
grape_vision         视觉识别节点
grape_interfaces     自定义消息
grape_pick_control   夹取控制封装
grape_navigation     教室导航封装
grape_bringup        统一启动 launch
```

---

## 9. configs 目录规范

`configs/` 放可以被多个模块复用的配置。

建议配置：

```text
camera_topics.yaml   相机 RGB / depth 话题
yolo_grape.yaml      YOLO 类别、权重路径、置信度阈值
arm_params.yaml      机械臂安全参数
nav_points.yaml      教室导航点
```

配置文件原则：

```text
路径尽量相对化
不写密码和密钥
参数变更需要写明原因
```

---

## 10. 不应提交的内容

不应提交：

```text
.venv/
__pycache__/
runs/
wandb/
build/
install/
log/
*.cache
*.bag
.DS_Store
私钥
密码
机器人账号密码截图
大规模原始图片
大规模模型权重
官方 PDF 原件，除非明确允许公开
```

特别注意：

```text
不要提交 SSH 私钥
不要提交机器人登录密码
不要提交未经确认可公开的厂家资料 / 组委会资料
```

---

## 11. 推荐 .gitignore

```gitignore
# Python
__pycache__/
*.pyc
.venv/
venv/
.env

# OS
.DS_Store
Thumbs.db

# YOLO / training outputs
runs/
wandb/
*.cache

# ROS2 build outputs
build/
install/
log/

# Large data, choose whether to track with Git LFS
data/raw/
data/tmp/
data/cache/

# Model weights, use Git LFS if needed
models/weights/*.pt
models/weights/*.onnx
models/weights/*.engine

# IDE
.vscode/
.idea/

# Secrets
*.pem
*.key
*.pub
id_rsa*
id_ed25519*
```

如果决定使用 Git LFS 管理模型和图片，则不要 ignore 对应文件，而是执行：

```bash
git lfs track "*.pt"
git lfs track "*.onnx"
git lfs track "*.jpg"
git lfs track "*.png"
git add .gitattributes
```

---

## 12. 提交信息规范

推荐格式：

```text
<type>: <summary>
```

常用 type：

```text
docs: 文档更新
data: 数据集相关
vision: YOLO / 视觉代码
ros2: ROS2 节点与 launch
arm: 机械臂控制
nav: 导航与地图
config: 配置文件
fix: 修复问题
refactor: 重构
```

示例：

```text
docs: add yolo dataset reference
vision: add yolov8 grape training script
data: add first classroom negative samples
ros2: add grape vision node skeleton
arm: wrap gripper open close command
config: add camera topic config
```

---

## 13. 分支策略

当前项目可以简单使用：

```text
main：稳定可运行版本
feature/*：个人开发分支
```

示例：

```text
feature/yolo-dataset-v1
feature/grape-vision-node
feature/nav-map-classroom
feature/arm-wrapper
```

如果组内 Git 经验不足，也可以先全部提交到 main，但必须保持：

```text
每次提交小而清楚
不要一次提交大量无关文件
不要把临时文件提交进去
```

---

## 14. Issue 分工建议

建议用 GitHub Issues 管任务。

标签示例：

```text
data
vision
ros2
arm
nav
docs
bug
experiment
```

任务示例：

```text
[data] 采集第一批教室葡萄图像
[data] 标注 ripe_grape / unripe_grape
[vision] 训练 yolov8n_grape_v1
[vision] 测试远中近距离检测效果
[ros2] 确认 Gemini / Astra 图像话题
[ros2] 编写 grape_vision 节点
[arm] 封装夹爪开合接口
[nav] 建教室地图并保存导航点
[docs] 整理阶段汇报材料
```

---

## 15. 当前推荐分工

可以按模块分工：

```text
YOLO / 数据负责人：数据采集、标注、训练、推理接口
ROS2 / 机器人负责人：连接、话题、节点、相机输入
机械臂负责人：夹爪、动作组、控制接口、安全测试
导航负责人：建图、路径点、从起点到葡萄架
文档负责人：reference、progress、reports 整理
```

这只是职责边界，不代表不能交叉协作。

---

## 16. 仓库初始化命令

```bash
mkdir grape-robot
cd grape-robot

git init

mkdir -p docs/reference docs/progress docs/reports
mkdir -p data/yolo/images/train data/yolo/images/val data/yolo/images/test
mkdir -p data/yolo/labels/train data/yolo/labels/val data/yolo/labels/test
mkdir -p scripts models ros2/src configs tools tests

touch README.md .gitignore
touch data/README.md models/README.md
touch data/yolo/grape.yaml

git add .
git commit -m "init project structure"
```

绑定 GitHub 远程仓库：

```bash
git remote add origin git@github.com:你的用户名/grape-robot.git
git branch -M main
git push -u origin main
```

---

## 17. README 第一版建议内容

```markdown
# Grape Robot

基于 ROSLander 移动机械臂平台的葡萄智能视觉夹取系统。

## 项目目标

实现教室模拟葡萄架场景下的：

- 成熟 / 未成熟葡萄检测
- 葡萄目标中心点输出
- 深度定位
- 移动底盘导航到葡萄架附近
- 机械臂夹取演示

## 当前阶段

当前优先完成 YOLO 葡萄检测模型。

## 目录结构

- docs/: 项目文档
- data/: 数据集说明与 YOLO 配置
- scripts/: 训练和推理脚本
- models/: 模型权重说明
- ros2/: 后续 ROS2 接入代码

## YOLO 类别

```yaml
names:
  0: ripe_grape
  1: unripe_grape
```

## 快速开始

```bash
pip install ultralytics
python scripts/train_yolo.py
python scripts/predict_yolo.py
```
```

---

## 18. 当前决策

当前仓库管理决策：

```text
使用一个 GitHub 仓库管理整个项目
不提交整个机器人 ros2_ws
不提交 build / install / log
不提交私钥和密码
数据集与模型权重视规模决定是否使用 Git LFS
reference 文档长期维护
progress 文档按日期新建
```
