# ROSLander 实机只读接口与源码快照

- 取证日期：2026-07-14
- 机器人时间：2026-07-14T17:31:26+08:00
- 机器人地址：`10.248.67.8`（地址可能变化）
- SSH 用户：`ubuntu`
- 主机名：`ubuntu`
- 主机 ED25519 指纹：`SHA256:zru6ibeuztJOPDxB9mSz78mwdZmBwzuC0WsCBGSxTVs`
- 本地仓库提交：`14995c7d67a127fb514fe794b4c279c009c20421`
- 取证方式：SSH 只读命令
- 硬件动作：无

## 1. 安全边界和执行情况

本次只执行系统信息、进程、ROS2 图、接口定义、参数、单条消息读取、源码读取和哈希计算。

本次没有：

- 启动或重复启动 `bringup`；
- 启动 `track_and_grab`；
- 停止或重启系统服务；
- 调用任何 ROS2 service；
- 向任何 ROS2 topic 发布消息；
- 控制底盘、机械臂或夹爪；
- 修改机器人文件；
- 重启或升级系统。

SSH 首次连接时，本机全局 `known_hosts` 校验未通过。没有使用 `StrictHostKeyChecking=no` 绕过。重新扫描得到的 ED25519 指纹与项目文档记录一致后，使用临时专用 known-hosts 文件连接，未修改全局 SSH 配置。

## 2. 系统和当前进程

| 项目 | 实机结果 | 状态 |
| --- | --- | --- |
| 用户/主机名 | `ubuntu` / `ubuntu` | `VERIFIED_ROBOT` |
| 系统架构 | Ubuntu aarch64，`5.15.148-tegra` | `VERIFIED_ROBOT` |
| ROS2 工作区 | `/home/ubuntu/ros2_ws` 存在 | `VERIFIED_ROBOT` |
| 项目主目录 | `/home/ubuntu/teams/ctrlteam/grape_robot` 存在 | `VERIFIED_ROBOT` |
| ROS2 版本 | `/opt/ros/humble` 环境可加载 | `VERIFIED_ROBOT` |
| 当前 bringup | 已有 `/opt/ros/humble/bin/ros2 launch bringup bringup.launch.py` | `VERIFIED_ROBOT` |
| `track_and_grab` 进程/节点 | 本次查询未发现 | `VERIFIED_ROBOT`（仅代表本次快照时刻） |

当前已经运行相机、`controller_manager`、`kinematics`、`servo_manager`、`object_tracking`、`hand_gesture`、`joystick_control`、`init_pose` 等节点。不得为了验证环境再次启动一套 bringup。

## 3. 当前抓取依赖的 ROS2 接口

### 3.1 相机输入

| Topic | 类型 | 发布者 | 实测消息 |
| --- | --- | --- | --- |
| `/gemini_camera/rgb/image_raw` | `sensor_msgs/msg/Image` | `/gemini_camera/orbbec_camera_node` | `640×480`，`rgb8` |
| `/gemini_camera/depth/image_raw` | `sensor_msgs/msg/Image` | `/gemini_camera/orbbec_camera_node` | `640×400`，`16UC1` |
| `/gemini_camera/depth/camera_info` | `sensor_msgs/msg/CameraInfo` | `/gemini_camera/orbbec_camera_node` | `640×400` |
| `/gemini_camera/depth_to_color` | `orbbec_camera_msgs/msg/Extrinsics` | `/gemini_camera/orbbec_camera_node` | 有发布，Transient Local |

四个 topic 在取证时均没有订阅者，因为 `track_and_grab` 未运行。

### 3.2 舵机控制

`/servo_controller`：

- 类型：`servo_controller_msgs/msg/ServosPosition`；
- 订阅者：`/controller_manager`；
- 发布端点数量：7；
- 发布节点：`line_following`、`object_tracking`、`hand_gesture`（两个端点）、`joystick_control`、`init_pose`、`lidar_app`。

消息定义：

```text
float64 duration
string position_unit
servo_controller_msgs/ServoPosition[] position
    uint16 id
    float32 position
```

结论：接口类型和当前订阅者升级为 `VERIFIED_ROBOT`。多个现存节点拥有发布能力，是否存在可靠互斥机制仍为 `UNKNOWN`。在解决互斥和动作权限前，不允许启动会发布舵机命令的抓取模式。

### 3.3 运动学服务

`/kinematics` 节点当前提供：

- `/kinematics/get_current_pose`：`kinematics_msgs/srv/GetRobotPose`；
- `/kinematics/set_pose_target`：`kinematics_msgs/srv/SetRobotPose`；
- `/kinematics/init_finish`：`std_srvs/srv/Trigger`；
- 订阅 `/controller_manager/servo_states`；
- 客户端依赖 `/controller_manager/init_finish`。

`GetRobotPose`：

```text
---
bool success
bool solution
geometry_msgs/Pose pose
```

`SetRobotPose`：

```text
float64[] position
float64 pitch
float64[] pitch_range
float64 resolution
float64 duration
---
bool success
uint16[] pulse
uint16[] current_pulse
float64[] rpy
float64 min_variation
```

服务名称、类型和字段升级为 `VERIFIED_ROBOT`。本次没有调用服务，因此具体数值结果没有通过调用实验验证。

## 4. 外部 Python 函数定义

### 4.1 `set_pose_target`

实机安装位置：

```text
/home/ubuntu/ros2_ws/install/kinematics/lib/python3.10/site-packages/kinematics/kinematics_control.py
```

源码确认其签名为：

```python
set_pose_target(position, pitch, pitch_range=[-180.0, 180.0], resolution=1.0, duration=1.0)
```

定义确认：

- `position` 为 `[x, y, z]`，注释单位为米；
- `pitch` 和 `pitch_range` 注释单位为度；
- `resolution` 为角度搜索分辨率；
- 第五个参数才是 `duration`；
- 函数只构造并返回 `SetRobotPose.Request`，不直接调用服务。

当前抓取代码调用：

```python
set_pose_target(position, yaw, [-180.0, 180.0], 1.0)
```

其中 `1.0` 实际绑定 `resolution`，`duration` 使用默认值 `1.0`。

### 4.2 `set_servo_position`

实机安装位置：

```text
/home/ubuntu/ros2_ws/install/servo_controller/lib/python3.10/site-packages/servo_controller/bus_servo_control.py
```

源码确认：

- `duration` 转为 `float`；
- 每个 `(id, position)` 转为 `ServoPosition`；
- `position_unit` 固定为 `"pulse"`；
- 最后通过传入的 publisher 发布 `ServosPosition`。

因此该函数会产生真实舵机控制消息，不是纯数据转换函数。

### 4.3 `sdk.common` 与 PID

实机安装位置：

```text
/home/ubuntu/ros2_ws/install/sdk/lib/python3.10/site-packages/sdk/common.py
/home/ubuntu/ros2_ws/install/sdk/lib/python3.10/site-packages/sdk/pid.py
/home/ubuntu/ros2_ws/install/sdk/lib/python3.10/site-packages/sdk/fps.py
```

源码确认：

- `xyz_quat_to_mat(xyz, quat)` 将输入四元数直接传入 `transforms3d.quaternions.quat2mat`；
- 当前抓取代码传入顺序为 `[w, x, y, z]`，与该库调用一致；
- `xyz_euler_to_mat(..., degrees=True)` 默认把欧拉角按度转为弧度后计算；
- `mat_to_xyz_euler(..., degrees=True)` 默认输出角度；
- `PID.update()` 使用 `SetPoint - feedback_value` 作为误差。

这些函数的当前实机定义升级为 `VERIFIED_ROBOT`。坐标轴的实际物理方向仍需安全实验验证。

### 4.4 Ultralytics

```text
版本：8.3.182
路径：/home/ubuntu/.local/lib/python3.10/site-packages/ultralytics/__init__.py
```

版本和安装路径为 `VERIFIED_ROBOT`。本次没有加载模型或运行推理。

## 5. IK 服务端失败行为

服务端源码：

```text
/home/ubuntu/ros2_ws/src/driver/kinematics/kinematics/kinematics/search_kinematics_solutions_node.py
```

源码显示：

1. `set_pose_target()` 调用 `get_ik(...)`；
2. 只有存在 IK 解且已经收到当前1至5号舵机位置时，才选择总 pulse 变化量最小的解；
3. 每个输出 pulse 会被裁剪到 `[0, 1000]`；
4. 没有解或当前舵机位置为空时，返回 `[True, [], [], [], 0.0]`；
5. service callback 无条件设置 `response.success = True`；
6. 调用方必须使用 `response.pulse` 是否为空判断是否有可用解，不能只检查 `success`。

当前抓取代码第一轮 `res.pulse` 为空时仍会继续发送夹爪和后续固定动作。这是已经由仓库调用链与实机服务端源码共同确认的高风险缺陷。

`get_current_pose` 服务端源码显示：

- 使用当前舵机位置做正运动学；
- `response.success` 同样固定为 `True`；
- 是否获得有效解由 `response.solution` 表示；
- 当前抓取代码直接读取 `.pose`，没有检查 `solution`。

## 6. RGB-D 对齐证据

实机参数：

| 参数 | 当前值 |
| --- | --- |
| `color_width` / `color_height` | `640 / 480` |
| `depth_width` / `depth_height` | `640 / 400` |
| `depth_registration` | `false` |
| `align_mode` | `HW` |
| `align_target_stream` | `COLOR` |
| `enable_frame_sync` | `false` |
| `enable_depth_scale` | `true` |
| `enable_colored_point_cloud` | `false` |

相机发布了 `depth_to_color` 外参：

```text
rotation:
  [0.9999837279, -0.0032465258,  0.0046826247,
   0.0032455940,  0.9999946952,  0.0002065851,
  -0.0046832711, -0.0001913839,  0.9999890327]
translation:
  [-0.0098447027, 0.0000437419, -0.0004593794]
```

RGB 内参：

```text
frame: gemini_camera_color_optical_frame
size: 640x480
fx=453.38818359375 fy=453.38818359375
cx=325.9556884765625 cy=242.73870849609375
```

深度内参：

```text
frame: gemini_camera_depth_optical_frame
size: 640x400
fx=476.67559814453125 fy=476.67559814453125
cx=327.14422607421875 cy=200.98683166503906
```

深度单位追加取证：

```text
/home/ubuntu/third_party/orbbec_ws/src/OrbbecSDK_ROS2/orbbec_camera/src/ob_camera_node.cpp
```

该驱动在发布深度图前读取 `DepthFrame::getValueScale()` 并执行
`image = image * depth_scale`。Orbbec SDK接口注释明确该scale换算后的深度单位为毫米；
当前节点参数同时确认`enable_depth_scale=true`。因此当前发布图像使用
`0.001 m/单位`，状态升级为`VERIFIED_ROBOT`。驱动关键源码哈希：

```text
2b30fb7aeef3d806970ceac5974e13be1acde628d0ffa7cc5e613d8dc9d75751  ob_camera_node.cpp
77db1912ed54a62577d4c068aded281d265631ea50df40bf26fbe4eb91f8f84d  constants.h
```

外参单位追加取证确认，驱动`obExtrinsicsToMsg()`将SDK的毫米平移量除以1000后
写入ROS消息，因此`/gemini_camera/depth_to_color.translation`单位为米；rotation
按SDK九元素顺序写入消息。对应源码哈希：

```text
e06b4f9c358c7937b8ac0d7ec8f3bdec5276bb85db4625f8c7095ea07de00d6c  utils.cpp
```

结论：

- RGB 与深度分辨率、主点和焦距不同；
- `depth_registration=false`，且实际深度消息仍为 `640×400`；
- 尽管存在 `align_mode=HW`、`align_target_stream=COLOR` 和外参 topic，仅凭当前参数不能证明 `/gemini_camera/depth/image_raw` 已经与 RGB 像素一一对齐；
- 当前代码把 RGB 检测中心直接裁剪到深度图并使用深度内参反投影，缺少显式的 RGB→深度映射；
- RGB-D 空间对应关系继续标记为 `UNKNOWN`，未解决前不得由当前深度结果触发机械臂动作。

## 7. 代码一致性

| 文件 | SHA-256 |
| --- | --- |
| 本地、机器人项目主目录、ROS2运行副本 `track_and_grab.py` | `3b6f7c9ed7fc95320cd07841ec45fdb4b19fea8c20dd83606d58d198b61c0928` |
| 本地、机器人项目主目录、ROS2运行副本 `track_and_grab.launch.py` | `2ee78fea2af83499630a848565421cc153938efc1ca109f350b1924ac75a06bf` |
| 本地与机器人项目主目录 `run_vision.sh` | `4ce119dcf85ee4da3f101cbd7ee375a4e19dd9845c42694fc15c4202b01c1489` |

三处核心代码一致，状态升级为 `VERIFIED_ROBOT`。本次没有上传或覆盖任何机器人文件。

外部源码哈希：

```text
aa40b2d40bdb3265ebd261f3d01d108b8e27cb76bec164273b589447da24bac7  kinematics_control.py
40e1f70b2100517ec87b85544a2aa55ca8cf2c781c1c52f65a81d98e537a2093  search_kinematics_solutions_node.py
90886966d34438a3138192621b5188560b02cf0947bfcce53fd1d7a0d0888b79  bus_servo_control.py
```

## 8. 状态更新对照

### `VERIFIED_ROBOT`

- 机器人身份、系统架构、ROS2工作区和项目目录；
- 当前节点、topic、service 列表；
- 相机消息类型、分辨率和 encoding；
- 深度发布值单位为毫米；
- `depth_to_color.translation`单位为米；
- `/servo_controller` 类型、当前发布端点和订阅者；
- 运动学服务类型和字段；
- `set_pose_target`、`set_servo_position`、关键 `sdk.common` 函数的当前实机源码；
- Ultralytics 版本；
- 本地、机器人项目目录、ROS2运行副本的核心代码一致性；
- IK无解时 pulse 为空但 success 仍为 true的服务端实现。

### `UNKNOWN`

- RGB像素到当前深度图像素的可靠映射；
- `depth_registration=false` 与 `align_mode=HW` 的驱动组合在当前发布链中的准确语义；
- 深度无效值的完整规则；
- 当前 `hand2cam_tf_matrix` 的标定来源和误差；
- 机械臂世界坐标轴的实际物理方向；
- id1至id5完整安全范围；
- id10各 pulse 的准确张开、闭合、保持和归位语义；
- 多个 `/servo_controller` 发布者之间的互斥机制；
- ROS2 service 无响应时的超时和取消行为；
- 底盘真实控制入口和坐标方向；
- 任何抓取动作在当前实车上的安全性和效果。

## 9. 直接影响修改方案的结论

1. 暂时不能进入机械臂跟踪或抓取测试。RGB-D映射尚未成立，且舵机topic存在多个发布者。
2. 第一项代码修复应是纯离线的RGB-D映射与稳健深度模块，而不是修改固定Z偏移。
3. 运动学适配层必须检查 `GetRobotPose.solution` 和 `SetRobotPose.pulse`，不能只检查 `success`。
4. 所有 service wait/call 必须增加超时；IK无解后必须停止，禁止继续夹爪和固定动作。
5. 后续运行抓取节点前，必须先建立 `/servo_controller` 发布者互斥方案，并把跟踪、夹爪、脱离、底盘权限拆分为独立默认关闭开关。

## 10. 最小可验证下一步

下一步只做离线任务：

1. 根据 RGB、深度 CameraInfo 和 `depth_to_color` 外参，调查 Orbbec 当前驱动提供的标准对齐输出或映射API；
2. 保存一组严格同步的 RGB、深度、两路 CameraInfo 和外参样本；
3. 实现不依赖 ROS2 publisher/service 的 RGB→深度映射与框内稳健深度纯函数；
4. 用已知距离标定物验证像素映射和三维误差；
5. 仅在检测-only模式显示映射点、有效深度比例、三维坐标和误差，不发送任何控制消息。

在这一步通过前，`enable_arm` 必须保持 `false`。

## 11. 本次主要只读命令

```bash
ros2 node list
ros2 topic list -t
ros2 service list -t
ros2 node info /kinematics
ros2 node info /controller_manager
ros2 topic info -v /servo_controller
ros2 topic info -v /gemini_camera/rgb/image_raw
ros2 topic info -v /gemini_camera/depth/image_raw
ros2 topic info -v /gemini_camera/depth/camera_info
ros2 topic info -v /gemini_camera/depth_to_color
ros2 interface show servo_controller_msgs/msg/ServosPosition
ros2 interface show kinematics_msgs/srv/GetRobotPose
ros2 interface show kinematics_msgs/srv/SetRobotPose
ros2 interface show orbbec_camera_msgs/msg/Extrinsics
ros2 param get /gemini_camera/orbbec_camera_node ...
ros2 topic echo --once ...
python3 -c 'import inspect; ...'
find ~/ros2_ws/src ...
sha256sum ...
```

本次命令均为查询或读取，没有调用改变状态的接口。
