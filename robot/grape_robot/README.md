# 葡萄智能视觉夹取项目

基于 ROSLander 移动机械臂平台，将官方 `track_and_grab` 颜色抓取流程改造为 YOLO 葡萄检测流程。

当前阶段已经完成：

```text
官方颜色抓取闭环验证
YOLO 模型加载
成熟 / 未成熟葡萄识别
检测框、标签、置信度、中心点显示
项目代码与模型独立整理
一键安全视觉运行
Mac 本地完整备份
```

当前默认处于安全视觉模式：

```text
只进行 YOLO 检测
机械臂不跟踪
机械臂不抓取
```

---

## 1. 项目目录

机器人端项目目录：

```text
/home/ubuntu/teams/ctrlteam/grape_robot
```

Mac 本地备份目录：

```text
/Users/zhoubochun/program/grape_robot/grape-robot/robot/grape_robot
```

当前目录结构：

```text
grape_robot/
├── code/
│   └── track_and_grab.py
├── launch/
│   └── track_and_grab.launch.py
├── models/
│   ├── current.pt
│   └── archive/
│       ├── best.pt
│       ├── grape_v2_20260711_013956.pt
│       └── grape_v3_20260712_qq_best.pt
├── scripts/
│   └── run_vision.sh
└── backups/
```

说明：

```text
code/
保存 YOLO 抓取主程序

launch/
保存 ROS2 启动文件

models/archive/
保存每一版 YOLO 模型，不覆盖旧版本

models/current.pt
指向当前实际使用的模型

scripts/
保存一键运行或维护脚本

backups/
保存代码历史备份
```

---

## 2. ROS2 工作区关系

ROS2 实际运行源码位置：

```text
/home/ubuntu/ros2_ws/src/example/example/rgbd_function
```

项目主目录与 ROS2 工作区关系：

```text
grape_robot 项目主目录
↓
run_vision.sh 自动同步
↓
ros2_ws 工作区
↓
编译 example 包
↓
ros2 launch 启动
```

注意：

```text
grape_robot 是主版本
ros2_ws 是运行副本
```

不要只修改 `ros2_ws` 中的文件后就结束工作，否则下一次运行脚本时可能被项目主目录中的版本覆盖。

---

## 3. 当前模型

当前模型入口：

```text
models/current.pt
```

当前实际模型：

```text
models/archive/best.pt
```

查看当前模型指向：

```bash
readlink -f ~/teams/ctrlteam/grape_robot/models/current.pt
```

当前类别：

```text
0: unripe_grape
1: ripe_grape
```

当前模型 SHA-256：

```text
7e57e54c7e4b67d89e3a966f38e4a8923b06ed9ea66bbea9af6e1f0f8289d348
```

检查模型：

```bash
sha256sum ~/teams/ctrlteam/grape_robot/models/current.pt
```

---

## 4. 一键运行

必须在 NoMachine 图形桌面的终端中执行，因为程序会弹出 OpenCV 图像窗口。

运行：

```bash
~/teams/ctrlteam/grape_robot/scripts/run_vision.sh
```

脚本会自动完成：

```text
同步代码到 ros2_ws
检查 Python 语法
编译 example 包
停止默认 App 服务
加载 current.pt
启动 YOLO 安全视觉模式
退出后恢复 App 服务
```

当前默认参数：

```text
目标类别：ripe_grape
置信度：0.4
输入尺寸：320
机械臂控制：关闭
```

---

## 5. 临时修改运行参数

识别未成熟葡萄：

```bash
TARGET_CLASS=unripe_grape ~/teams/ctrlteam/grape_robot/scripts/run_vision.sh
```

修改置信度：

```bash
CONFIDENCE=0.5 ~/teams/ctrlteam/grape_robot/scripts/run_vision.sh
```

同时修改类别和置信度：

```bash
TARGET_CLASS=unripe_grape CONFIDENCE=0.5 ~/teams/ctrlteam/grape_robot/scripts/run_vision.sh
```

---

## 6. 退出程序

优先在图像窗口按：

```text
q
```

或：

```text
Esc
```

也可以在终端按：

```text
Ctrl + C
```

退出时可能出现：

```text
KeyboardInterrupt
rcl_shutdown already called
publisher's context is invalid
```

这些通常是多个 ROS2 节点同时退出时产生的收尾日志，不一定代表 YOLO 出错。

---

## 7. 更新代码

### 7.1 在 Mac 修改

Mac 本地源码目录：

```text
/Users/zhoubochun/program/grape_robot/grape-robot/robot/grape_robot
```

修改后必须保存：

```text
Command + S
```

### 7.2 上传到机器人

Mac 终端执行：

```bash
scp "/Users/zhoubochun/program/grape_robot/grape-robot/robot/grape_robot/code/track_and_grab.py" "/Users/zhoubochun/program/grape_robot/grape-robot/robot/grape_robot/launch/track_and_grab.launch.py" ubuntu@ubuntu.local:/tmp/
```

机器人终端先备份：

```bash
PROJECT=~/teams/ctrlteam/grape_robot
STAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$PROJECT/backups/$STAMP"

cp "$PROJECT/code/track_and_grab.py" "$PROJECT/backups/$STAMP/"

cp "$PROJECT/launch/track_and_grab.launch.py" "$PROJECT/backups/$STAMP/"
```

再更新项目主目录：

```bash
cp /tmp/track_and_grab.py ~/teams/ctrlteam/grape_robot/code/track_and_grab.py

cp /tmp/track_and_grab.launch.py ~/teams/ctrlteam/grape_robot/launch/track_and_grab.launch.py
```

最后重新运行：

```bash
~/teams/ctrlteam/grape_robot/scripts/run_vision.sh
```

---

## 8. 更新 YOLO 模型

新模型不要覆盖旧模型。

### 8.1 在 Mac 本地接入新模型

假设新模型在：

```text
/Users/zhoubochun/program/grape_robot/best.pt
```

Mac 终端执行：

```bash
LOCAL="/Users/zhoubochun/program/grape_robot/grape-robot/robot/grape_robot"
MODEL_NAME="best.pt"

cp "/Users/zhoubochun/program/grape_robot/best.pt" \
"$LOCAL/models/archive/$MODEL_NAME"

ln -sfn "archive/$MODEL_NAME" \
"$LOCAL/models/current.pt"
```

检查：

```bash
readlink "$LOCAL/models/current.pt"

shasum -a 256 "$LOCAL/models/current.pt"
```

当前新模型 SHA-256：

```text
7e57e54c7e4b67d89e3a966f38e4a8923b06ed9ea66bbea9af6e1f0f8289d348
```

### 8.2 上传本地项目到机器人

机器人恢复供电并联网后，在 Mac 终端执行：

```bash
rsync -avh --progress \
"/Users/zhoubochun/program/grape_robot/grape-robot/robot/grape_robot/" \
ubuntu@ubuntu.local:/home/ubuntu/teams/ctrlteam/grape_robot/
```

上传后在机器人终端检查：

```bash
readlink -f ~/teams/ctrlteam/grape_robot/models/current.pt

sha256sum ~/teams/ctrlteam/grape_robot/models/current.pt
```

然后运行：

```bash
~/teams/ctrlteam/grape_robot/scripts/run_vision.sh
```

### 8.3 在机器人端直接更新模型

假设新模型已经上传到：

```text
/tmp/best.pt
```

执行：

```bash
PROJECT=~/teams/ctrlteam/grape_robot
MODEL_NAME="grape_$(date +%Y%m%d_%H%M%S).pt"

cp /tmp/best.pt "$PROJECT/models/archive/$MODEL_NAME"
```

验证模型：

```bash
python3 - <<PY
from ultralytics import YOLO

path = "$HOME/teams/ctrlteam/grape_robot/models/archive/$MODEL_NAME"
model = YOLO(path)

print("MODEL_OK")
print("task:", model.task)
print("classes:", model.names)
PY
```

确认正常后切换当前模型：

```bash
ln -sfn "archive/$MODEL_NAME" "$PROJECT/models/current.pt"
```

检查：

```bash
readlink -f "$PROJECT/models/current.pt"
```

---

## 9. 回滚旧模型

查看历史模型：

```bash
ls -lh ~/teams/ctrlteam/grape_robot/models/archive/
```

回滚示例：

```bash
cd ~/teams/ctrlteam/grape_robot/models

ln -sfn "archive/grape_v2_20260711_013956.pt" current.pt
```

确认：

```bash
readlink -f current.pt
```

---

## 10. 同步机器人项目到 Mac

在 Mac 终端执行：

```bash
rsync -avh --progress ubuntu@ubuntu.local:/home/ubuntu/teams/ctrlteam/grape_robot/ "/Users/zhoubochun/program/grape_robot/grape-robot/robot/grape_robot/"
```

这条命令不会自动删除 Mac 上已有但机器人上已经缺失的文件，因此适合作为日常安全备份。

---

## 11. 当前目标选择逻辑

当前检测到多个成熟葡萄时，程序优先选择：

```text
画面中最左边的目标
```

这继承了原官方颜色识别程序的最左目标选择逻辑。

因此可能出现：

```text
左侧葡萄较小或被遮挡
右侧葡萄更完整
程序仍选择左侧目标
```

这属于目标选择策略，不一定是 YOLO 模型错误。

---

## 12. 中心点修复记录

曾出现白色中心点不在检测框中心的问题。

原因：

```text
YOLO 中心点属于 RGB 图像
代码却使用深度图尺寸裁剪坐标
```

当前修复代码：

```python
rgb_h, rgb_w = result_image.shape[:2]
center_x = min(max(center_x, 0), rgb_w - 1)
center_y = min(max(center_y, 0), rgb_h - 1)
```

不要恢复成使用深度图 `w、h` 裁剪 RGB 中心点的旧逻辑。

---

## 13. 安全说明

当前只允许：

```text
enable_arm=false
```

不要直接把机械臂控制改成：

```text
enable_arm=true
```

因为原流程可能在目标稳定后继续执行：

```text
深度定位
机械臂靠近
夹爪闭合
搬运
放置
复位
```

启用机械臂前，应先增加：

```text
enable_grab=false
```

确保可以做到：

```text
允许机械臂跟踪
禁止进入 pick() 抓取流程
```

---

## 14. 下一阶段

下一阶段计划：

```text
增加 enable_grab 安全开关
只开启机械臂上下左右追踪
验证 RGB 与深度坐标对齐
验证目标三维坐标
最后再进行完整抓取
```

当前项目状态：

```text
YOLO 葡萄检测接入：完成
安全视觉模式：完成
项目目录整理：完成
模型版本管理：完成
Mac 本地备份：完成
YOLO 机械臂追踪：待完成
YOLO 完整抓取：待完成
```
