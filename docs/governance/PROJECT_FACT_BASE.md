# 项目事实基线

最后整理：2026-07-13

本文件是当前项目事实的集中入口。后续 Codex、组员、README 和实施方案不得把本文件中的 `UNKNOWN`、`INFERRED` 或 `REFERENCE_ONLY` 内容写成已经实现或已经验证。

## 1. 状态定义

| 状态 | 含义 |
| --- | --- |
| `VERIFIED_REPO` | 已在当前仓库源码、配置或提交中确认，只证明仓库内容 |
| `DOCUMENTED_ROBOT` | 项目文档记录为实机观察结果，本轮未重新连接实车复核 |
| `VERIFIED_ROBOT` | 本轮通过实机只读命令或安全实验确认，并保存了证据 |
| `REFERENCE_ONLY` | 来自厂商资料、官方示例或 ROS1 旧案例，只能参考 |
| `INFERRED` | 从材料推断，尚未验证 |
| `UNKNOWN` | 没有足够证据，禁止作为代码前提 |

## 2. 项目与环境基线

| 编号 | 事实 | 状态 | 证据 |
| --- | --- | --- | --- |
| F-001 | 项目目标是教室模拟葡萄架场景下的视觉检测、深度定位、移动对准和机械臂采摘演示 | `VERIFIED_REPO` | 根 [README](../../README.md) |
| F-002 | 当前平台记录为 ROSLander Mecanum，机器人系统记录为 ROS2 Humble | `DOCUMENTED_ROBOT` | [机器人系统基础信息](../reference/02-机器人系统基础信息-已更新.md) |
| F-003 | 当前自研运行代码位于 `robot/grape_robot/`，官方示例备份位于 `official_examples/` | `VERIFIED_REPO` | 当前目录结构 |
| F-004 | 当前 launch 的 `enable_arm` 默认值为 `false` | `VERIFIED_REPO` | [track_and_grab.launch.py](../../robot/grape_robot/launch/track_and_grab.launch.py) |
| F-005 | 当前节点支持 `yolo` 与颜色跟踪两类 detector，YOLO 默认目标类别为 `ripe_grape` | `VERIFIED_REPO` | [track_and_grab.py](../../robot/grape_robot/code/track_and_grab.py) |
| F-006 | 当前实现仍以单节点方式混合检测、跟踪、深度计算和抓取动作 | `VERIFIED_REPO` | [track_and_grab.py](../../robot/grape_robot/code/track_and_grab.py) |

## 3. 当前抓取行为事实

| 编号 | 事实 | 状态 | 影响 |
| --- | --- | --- | --- |
| F-101 | 当前多目标逻辑倾向选择画面中最左侧目标，而不是按完整度、深度或可达性综合选择 | `VERIFIED_REPO` | 可能抓错目标或选择边缘目标 |
| F-102 | 当前深度采样使用 `center_y - 40` 附近固定 10×10 区域并取有效像素均值 | `VERIFIED_REPO` | 可能混入叶片、背景或错位深度 |
| F-103 | 当前 RGB 像素到深度像素的空间对齐尚未在本仓库保存完整验证证据 | `UNKNOWN` | 三维目标位置可能偏移 |
| F-104 | 当前抓取闭合夹爪后执行 `position[2] += 0.03` | `VERIFIED_REPO` | 属于向上抬升逻辑，不符合当前悬挂葡萄设想 |
| F-105 | 当前无目标时没有完整的机械臂/摄像头/底盘主动搜索状态机 | `VERIFIED_REPO` | 画面无目标时只能等待 |
| F-106 | 当前正常抓取路径包含夹爪再次设为 pulse 200 的命令，但异常路径没有统一 `finally` 复位保障 | `VERIFIED_REPO` | “未归位”可能来自异常或命令语义未确认 |
| F-107 | 旧农业采摘案例包含底盘预对准、稳定检测、抓前修正、向下约 5cm 脱离、复检和重试思路 | `REFERENCE_ONLY` | 可用于设计状态机，不得直接照搬接口和参数 |

## 4. 已记录的 ROS2 与机械臂事实

以下内容来自已有实机记录，本轮文档整理没有重新连接机器人，因此状态保留为 `DOCUMENTED_ROBOT`。

| 编号 | 事实 | 状态 | 证据 |
| --- | --- | --- | --- |
| F-201 | `/servo_controller` 被记录为高级舵机控制入口，类型为 `servo_controller_msgs/msg/ServosPosition` | `DOCUMENTED_ROBOT` | [机械臂控制接口](../reference/04-机械臂控制接口.md) |
| F-202 | `/servo_controller` 到底层舵机控制链路已记录为验证过 | `DOCUMENTED_ROBOT` | [ROS2 关键节点与话题](../reference/03-ROS2关键节点与话题.md) |
| F-203 | 舵机 id10 被记录为夹爪舵机；300、500、540 曾进行位置测试 | `DOCUMENTED_ROBOT` | [机械臂控制接口](../reference/04-机械臂控制接口.md) |
| F-204 | id10 的 200/300/500/540 分别对应“张开、闭合、保持、归位”的准确物理语义尚未完全确认 | `UNKNOWN` | 当前文档明确保留未知项 |
| F-205 | id1 至 id5 的完整安全 pulse 范围和精确物理关节对应关系尚未形成当前项目合同 | `UNKNOWN` | 当前文档明确保留未知项 |
| F-206 | 当前代码调用 `/kinematics/get_current_pose` 与 `/kinematics/set_pose_target` | `VERIFIED_REPO` | [track_and_grab.py](../../robot/grape_robot/code/track_and_grab.py) |
| F-207 | 上述运动学服务在当前实机上的精确字段、超时和失败行为尚未在本目录保存最新快照 | `UNKNOWN` | 待执行接口快照命令 |

## 5. 当前禁止升级为事实的内容

在获得证据前，不得声称：

- 机械臂“没有完全伸出”就是行程不足；
- RGB 与深度图已经严格对齐；
- `position[2]` 减小在当前世界坐标中一定代表向下；
- id10 某个 pulse 一定对应张开或闭合；
- `/cmd_vel` 或 `/controller/cmd_vel` 中某一个已经确认是本项目底盘唯一控制入口；
- ROS1 农业采摘代码可直接在 ROS2 运行；
- 夹住葡萄后固定下拉 5cm 在当前实车上安全；
- 搜索、脱离复检、失败恢复已经实现。

## 6. 下一批需要采集的证据

在机器人上以只读方式保存到 `docs/evidence/robot-snapshot-YYYYMMDD/`：

```bash
ros2 node list
ros2 topic list -t
ros2 service list -t
ros2 topic info -v /servo_controller
ros2 topic info -v /gemini_camera/rgb/image_raw
ros2 topic info -v /gemini_camera/depth/image_raw
ros2 service type /kinematics/get_current_pose
ros2 service type /kinematics/set_pose_target
ros2 interface show servo_controller_msgs/msg/ServosPosition
ros2 interface show kinematics_msgs/srv/GetRobotPose
ros2 interface show kinematics_msgs/srv/SetRobotPose
ros2 node info /kinematics
```

还需要人工记录：

- 当前小车版本、相机型号和安装位置；
- RGB 与深度分辨率、是否硬件或驱动对齐；
- 相机到末端的实际外参来源；
- id1 至 id5 安全范围；
- id10 的 `open/close/hold/home` 实际值；
- 世界坐标轴方向；
- 假葡萄高度、底盘初始距离和安全下拉空间。

## 7. 更新规则

1. 新事实必须给出证据路径、命令输出或实验记录。
2. 从 `UNKNOWN` 升级时写明日期、设备和验证人。
3. 只在文档中发现的内容最多标为 `DOCUMENTED_ROBOT` 或 `REFERENCE_ONLY`。
4. 修改 ROS2 接口时同步更新 [ROS2 接口合同](ROS2_INTERFACE_CONTRACT.md)。
5. 修改实车安全参数时同步更新 [开发与实车放行关卡](DEVELOPMENT_GATES.md)。
