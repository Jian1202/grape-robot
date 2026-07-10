# 07-YOLO 接入与运行维护

本文档长期维护。  
用于记录葡萄 YOLO 模型接入、项目文件保存位置、运行方式、模型更新方式和常见维护操作。

---

## 1. 当前阶段

当前已经完成：

```text
ROSLander 官方 track_and_grab 颜色抓取闭环：已跑通
YOLO 模型上传与加载：已完成
YOLO 成熟葡萄检测：已完成
检测框、标签、置信度、中心点显示：已完成
RGB 中心点显示偏移修复：已完成
项目文件独立整理：已完成
一键安全视觉启动脚本：已完成
```

当前运行模式：

```text
只运行 YOLO 检测
机械臂不跟踪
机械臂不抓取
```

关键启动参数：

```text
enable_arm=false
```

---

## 2. 必须保存的文件

项目主目录：

```text
/home/ubuntu/teams/ctrlteam/grape_robot
```

当前目录结构：

```text
/home/ubuntu/teams/ctrlteam/grape_robot/
├── code/
│   └── track_and_grab.py
├── launch/
│   └── track_and_grab.launch.py
├── models/
│   ├── current.pt
│   └── archive/
│       └── grape_v2_20260711_013956.pt
├── scripts/
│   └── run_vision.sh
└── backups/
```

必须长期保存：

```text
code/track_and_grab.py
launch/track_and_grab.launch.py
models/archive/ 中的所有模型
models/current.pt
scripts/run_vision.sh
```

其中：

```text
track_and_grab.py
YOLO 检测、中心点、深度定位和机械臂抓取主程序

track_and_grab.launch.py
ROS2 启动参数和节点启动文件

models/archive/
保存每一版 YOLO 权重，不覆盖旧模型

models/current.pt
指向当前实际使用模型的软链接

run_vision.sh
同步代码、编译并启动安全视觉模式
```

---

## 3. 项目主目录与 ROS2 工作区的关系

项目主目录：

```text
~/teams/ctrlteam/grape_robot
```

这是当前项目文件的主要保存位置。

ROS2 实际运行源码位置：

```text
/home/ubuntu/ros2_ws/src/example/example/rgbd_function
```

其中包括：

```text
track_and_grab.py
track_and_grab.launch.py
```

两者关系：

```text
项目主目录
↓
运行脚本自动复制
↓
ROS2 工作空间
↓
编译
↓
ros2 launch 启动
```

注意：

```text
不要只修改 ros2_ws 中的文件后就结束工作
确认修改有效后，应同步保存到项目主目录
否则下一次运行 run_vision.sh 时，工作区文件可能被项目主目录中的版本覆盖
```

当前建议：

```text
项目主目录是保存版本
ros2_ws 是运行副本
```

---

## 4. Mac 本地文件位置

当前 Mac 本地源码目录：

```text
/Users/zhoubochun/program/grape_robot/grape-robot/robot
```

主要文件：

```text
track_and_grab.py
track_and_grab.launch.py
```

在 VS Code 中修改后必须保存：

```text
Command + S
```

检查 Mac 文件是否保存：

```bash
grep -n "rgb_h, rgb_w" \
"/Users/zhoubochun/program/grape_robot/grape-robot/robot/ros2_ws/src/track_and_grab.py"
```

如果修改后没有保存，上传到机器人上的仍然会是旧文件。

---

## 5. 日常运行方法

必须在 NoMachine 图形桌面的终端运行，因为程序会弹出 OpenCV 图像窗口。

启动命令：

```bash
~/teams/ctrlteam/grape_robot/scripts/run_vision.sh
```

脚本会自动执行：

```text
1. 将项目主目录代码复制到 ros2_ws
2. 检查 Python 语法
3. 编译 example 包
4. 停止默认 App 服务，释放相机
5. 加载 models/current.pt
6. 启动 YOLO 安全视觉模式
7. 退出后尝试恢复默认 App 服务
```

当前默认识别类别：

```text
ripe_grape
```

当前默认置信度：

```text
0.4
```

当前默认输入尺寸：

```text
320
```

当前默认安全设置：

```text
enable_arm=false
```

因此机械臂不会动作。

---

## 6. 临时修改运行参数

临时修改置信度：

```bash
CONFIDENCE=0.5 \
~/teams/ctrlteam/grape_robot/scripts/run_vision.sh
```

临时识别未成熟葡萄：

```bash
TARGET_CLASS=unripe_grape \
~/teams/ctrlteam/grape_robot/scripts/run_vision.sh
```

同时修改类别和置信度：

```bash
TARGET_CLASS=unripe_grape CONFIDENCE=0.5 \
~/teams/ctrlteam/grape_robot/scripts/run_vision.sh
```

---

## 7. 退出程序

优先在图像窗口按：

```text
q
```

或：

```text
Esc
```

也可以在启动终端按：

```text
Ctrl + C
```

退出时可能出现：

```text
KeyboardInterrupt
rcl_shutdown already called
publisher's context is invalid
failed to terminate after receiving SIGINT
```

这些通常是多个 ROS2 节点和后台线程同时退出时产生的收尾日志。

如果检测过程正常、最终节点已经退出，这些日志暂时不视为 YOLO 故障。

---

## 8. 当前模型信息

当前模型软链接：

```text
/home/ubuntu/teams/ctrlteam/grape_robot/models/current.pt
```

当前实际模型：

```text
/home/ubuntu/teams/ctrlteam/grape_robot/models/archive/grape_v2_20260711_013956.pt
```

查看当前模型指向：

```bash
readlink -f \
~/teams/ctrlteam/grape_robot/models/current.pt
```

查看模型文件：

```bash
ls -lh \
~/teams/ctrlteam/grape_robot/models/current.pt \
~/teams/ctrlteam/grape_robot/models/archive/
```

当前模型类别：

```text
0: unripe_grape
1: ripe_grape
```

当前模型 SHA-256：

```text
7e57e54c7e4b67d89e3a966f38e4a8923b06ed9ea66bbea9af6e1f0f8289d348
```

检查：

```bash
sha256sum \
~/teams/ctrlteam/grape_robot/models/current.pt
```

---

## 9. 手动更新 YOLO 模型

新模型不要直接覆盖旧模型。

假设新模型已经上传到：

```text
/tmp/best.pt
```

先生成版本化名称：

```bash
PROJECT=~/teams/ctrlteam/grape_robot
MODEL_NAME="grape_$(date +%Y%m%d_%H%M%S).pt"

cp /tmp/best.pt \
"$PROJECT/models/archive/$MODEL_NAME"
```

测试模型能否加载：

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

确认输出正常后，切换当前模型：

```bash
ln -sfn "archive/$MODEL_NAME" \
"$PROJECT/models/current.pt"
```

确认：

```bash
readlink -f "$PROJECT/models/current.pt"
```

更新模型后不需要修改主程序路径，因为运行脚本始终加载：

```text
models/current.pt
```

---

## 10. 回滚旧模型

查看历史模型：

```bash
ls -lh \
~/teams/ctrlteam/grape_robot/models/archive/
```

假设需要回滚到：

```text
grape_v2_20260711_013956.pt
```

执行：

```bash
cd ~/teams/ctrlteam/grape_robot/models

ln -sfn \
"archive/grape_v2_20260711_013956.pt" \
current.pt
```

确认：

```bash
readlink -f current.pt
```

---

## 11. 从 Mac 上传新代码

Mac 终端执行：

```bash
scp \
"/Users/zhoubochun/program/grape_robot/grape-robot/robot/ros2_ws/src/track_and_grab.py" \
"/Users/zhoubochun/program/grape_robot/grape-robot/robot/ros2_ws/src/track_and_grab.launch.py" \
ubuntu@ubuntu.local:/tmp/
```

机器人终端先备份当前项目版本：

```bash
PROJECT=~/teams/ctrlteam/grape_robot
STAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$PROJECT/backups/$STAMP"

cp "$PROJECT/code/track_and_grab.py" \
"$PROJECT/backups/$STAMP/"

cp "$PROJECT/launch/track_and_grab.launch.py" \
"$PROJECT/backups/$STAMP/"
```

再更新项目主目录：

```bash
cp /tmp/track_and_grab.py \
~/teams/ctrlteam/grape_robot/code/track_and_grab.py

cp /tmp/track_and_grab.launch.py \
~/teams/ctrlteam/grape_robot/launch/track_and_grab.launch.py
```

检查语法：

```bash
python3 -m py_compile \
~/teams/ctrlteam/grape_robot/code/track_and_grab.py \
~/teams/ctrlteam/grape_robot/launch/track_and_grab.launch.py
```

然后运行：

```bash
~/teams/ctrlteam/grape_robot/scripts/run_vision.sh
```

---

## 12. 手动同步到 ROS2 工作区

通常由 `run_vision.sh` 自动完成，不需要手动执行。

需要手动同步时：

```bash
PROJECT=~/teams/ctrlteam/grape_robot
SRC_DIR=~/ros2_ws/src/example/example/rgbd_function

cp "$PROJECT/code/track_and_grab.py" \
"$SRC_DIR/track_and_grab.py"

cp "$PROJECT/launch/track_and_grab.launch.py" \
"$SRC_DIR/track_and_grab.launch.py"
```

检查并编译：

```bash
python3 -m py_compile \
"$SRC_DIR/track_and_grab.py" \
"$SRC_DIR/track_and_grab.launch.py"

cd ~/ros2_ws
colcon build --packages-select example --symlink-install
source ~/ros2_ws/install/setup.zsh
```

---

## 13. 当前 YOLO 目标选择逻辑

当前程序检测到多个成熟葡萄时，会优先选择：

```text
画面中最左边的目标
```

这继承了官方颜色识别程序选择最左轮廓的逻辑。

因此可能出现：

```text
左边葡萄较小或被遮挡
右边葡萄更大、更完整
程序仍选择左边目标
```

这不是 YOLO 模型故障，而是当前代码的目标选择策略。

后续可以修改为：

```text
选择面积最大目标
选择最靠近画面中心目标
排除靠近图像边缘的目标
综合面积、置信度和位置进行选择
```

当前尚未修改。

---

## 14. 中心点修复记录

曾出现：

```text
绿色检测框正确
白色中心点不在检测框几何中心
```

原因：

```text
YOLO 中心点来自 RGB 图像
代码却使用深度图宽高限制 RGB 坐标
导致靠近图像边缘的中心点被错误裁剪
```

已改为：

```python
rgb_h, rgb_w = result_image.shape[:2]
center_x = min(max(center_x, 0), rgb_w - 1)
center_y = min(max(center_y, 0), rgb_h - 1)
```

因此后续不要恢复成：

```python
center_x = min(max(center_x, 0), w - 1)
center_y = min(max(center_y, 0), h - 1)
```

---

## 15. 默认 App 服务

服务名称：

```text
start_app_node.service
```

停止：

```bash
sudo systemctl stop start_app_node.service
```

恢复：

```bash
sudo systemctl start start_app_node.service
```

查看状态：

```bash
systemctl status start_app_node.service
```

运行视觉程序前需要停止该服务，避免相机被占用。

`run_vision.sh` 已经自动处理停止和恢复。

---

## 16. 故障排查

### 16.1 找不到模型

检查：

```bash
ls -lh \
~/teams/ctrlteam/grape_robot/models/current.pt

readlink -f \
~/teams/ctrlteam/grape_robot/models/current.pt
```

如果软链接指向不存在的文件，需要重新切换模型。

---

### 16.2 编译成功但代码没有变化

先检查项目主目录：

```bash
grep -n "rgb_h, rgb_w" \
~/teams/ctrlteam/grape_robot/code/track_and_grab.py
```

再检查 ROS2 工作区：

```bash
grep -n "rgb_h, rgb_w" \
~/ros2_ws/src/example/example/rgbd_function/track_and_grab.py
```

如果两边不同，重新运行：

```bash
~/teams/ctrlteam/grape_robot/scripts/run_vision.sh
```

---

### 16.3 相机启动失败

先停止默认 App 服务：

```bash
sudo systemctl stop start_app_node.service
```

确认没有旧的抓取程序仍在运行：

```bash
ps aux | grep track_and_grab
```

不要重复启动多个 `track_and_grab`。

---

### 16.4 VS Code 修改没有生效

Mac 修改后必须：

```text
Command + S
```

再用 `grep` 检查本地文件，确认内容已经写入磁盘，然后重新上传。

---

## 17. 安全注意事项

当前只允许使用：

```text
enable_arm=false
```

在没有单独增加“允许跟踪但禁止抓取”的安全开关前，不要直接设置：

```text
enable_arm=true
```

因为原抓取流程可能在目标稳定后进入：

```text
深度定位
机械臂靠近
夹爪闭合
搬运
放置
复位
```

启用机械臂前必须：

```text
清空机械臂周围空间
确认急停或断电方式
确认目标在机械臂安全工作范围
先实现只跟踪、不抓取
再单独测试深度坐标
最后才允许完整抓取
```

---

## 18. 当前推荐工作流程

每次修改代码：

```text
在 Mac 修改并保存
↓
上传到机器人 /tmp
↓
备份项目主目录旧版本
↓
更新项目主目录
↓
运行 run_vision.sh
↓
观察结果
↓
确认稳定后保留
```

每次更新模型：

```text
上传新模型
↓
保存到 models/archive
↓
测试模型能否加载
↓
切换 current.pt
↓
运行 run_vision.sh
↓
出现问题时回滚旧模型
```

---

## 19. 下一阶段

下一阶段目标：

```text
增加 enable_grab 安全开关
enable_arm=true 时只允许机械臂跟踪
enable_grab=false 时禁止执行 pick()
验证 YOLO 中心点驱动机械臂上下、左右追踪
确认追踪稳定后，再验证 RGB 与深度坐标对齐
最后才允许完整抓取
```

当前阶段结论：

```text
YOLO 葡萄检测接入：成功
安全视觉模式：可运行
项目文件独立整理：完成
模型版本化保存：完成
机械臂 YOLO 追踪：待完成
YOLO 完整抓取：待完成
```
