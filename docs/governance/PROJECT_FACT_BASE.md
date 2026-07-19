# 项目事实基线

最后整理：2026-07-19

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
| F-002 | 当前机器人运行 ROS2 Humble，工作区为 `/home/ubuntu/ros2_ws` | `VERIFIED_ROBOT` | [2026-07-14 实机只读快照](../evidence/robot-snapshot-20260714/README.md) |
| F-003 | 当前自研运行代码位于 `robot/grape_robot/`，官方示例备份位于 `official_examples/` | `VERIFIED_REPO` | 当前目录结构 |
| F-004 | 当前 launch 的 `enable_arm` 默认值为 `false`，节点在收到 `enable_arm=true` 时拒绝启动 | `VERIFIED_REPO` | [track_and_grab.launch.py](../../robot/grape_robot/launch/track_and_grab.launch.py)、[grape_localization.py](../../robot/grape_robot/code/grape_localization.py) |
| F-005 | 当前节点支持 `yolo` 与颜色跟踪两类 detector，YOLO 默认目标类别为 `ripe_grape` | `VERIFIED_REPO` | [track_and_grab.py](../../robot/grape_robot/code/track_and_grab.py) |
| F-006 | 当前节点保留旧抓取方法源码，但检测-only构造器不创建执行器 publisher 或运动学 client，动作路径不可达 | `VERIFIED_REPO` | [track_and_grab.py](../../robot/grape_robot/code/track_and_grab.py)、合同测试 |
| F-007 | RGB-D投影、框内稳健深度和失败语义已拆为不依赖ROS2的纯算法模块 | `VERIFIED_REPO` | [grape_localization.py](../../robot/grape_robot/code/grape_localization.py)、[单元测试](../../tests/unit/test_grape_localization.py) |

## 3. 当前抓取行为事实

| 编号 | 事实 | 状态 | 影响 |
| --- | --- | --- | --- |
| F-101 | 当前多目标逻辑倾向选择画面中最左侧目标，而不是按完整度、深度或可达性综合选择 | `VERIFIED_REPO` | 可能抓错目标或选择边缘目标 |
| F-102 | 旧动作路径仍保留 `center_y - 40` 的10×10均值深度代码，但当前安全保护使该路径不可达；检测-only改用显式投影和稳健过滤 | `VERIFIED_REPO` | 后续恢复动作前必须删除或替换旧路径 |
| F-103 | 已实现基于两路内参和 `depth_to_color` 外参的离线映射，驱动发布深度值单位确认为毫米，但实景映射与三维误差尚未验证 | `UNKNOWN` | 默认换算为0.001米/单位，未通过实景验证前不得触发动作 |
| F-104 | 当前抓取闭合夹爪后执行 `position[2] += 0.03` | `VERIFIED_REPO` | 属于向上抬升逻辑，不符合当前悬挂葡萄设想 |
| F-105 | 当前无目标时没有完整的机械臂/摄像头/底盘主动搜索状态机 | `VERIFIED_REPO` | 画面无目标时只能等待 |
| F-106 | 当前正常抓取路径包含夹爪再次设为 pulse 200 的命令，但异常路径没有统一 `finally` 复位保障 | `VERIFIED_REPO` | “未归位”可能来自异常或命令语义未确认 |
| F-107 | 旧农业采摘案例包含底盘预对准、稳定检测、抓前修正、向下约 5cm 脱离、复检和重试思路 | `REFERENCE_ONLY` | 可用于设计状态机，不得直接照搬接口和参数 |

## 4. 已记录的 ROS2 与机械臂事实

以下内容同时引用历史记录与2026-07-14实机只读快照；没有发布动作消息或调用动作服务。

| 编号 | 事实 | 状态 | 证据 |
| --- | --- | --- | --- |
| F-201 | `/servo_controller` 当前存在，类型为 `servo_controller_msgs/msg/ServosPosition`，订阅者为 `/controller_manager`，快照时有7个发布端点 | `VERIFIED_ROBOT` | [2026-07-14 实机只读快照](../evidence/robot-snapshot-20260714/README.md) |
| F-202 | `/servo_controller` 到底层舵机控制链路已记录为验证过 | `DOCUMENTED_ROBOT` | [ROS2 关键节点与话题](../reference/03-ROS2关键节点与话题.md) |
| F-203 | 舵机 id10 被记录为夹爪舵机；300、500、540 曾进行位置测试 | `DOCUMENTED_ROBOT` | [机械臂控制接口](../reference/04-机械臂控制接口.md) |
| F-204 | id10 的 200/300/500/540 分别对应“张开、闭合、保持、归位”的准确物理语义尚未完全确认 | `UNKNOWN` | 当前文档明确保留未知项 |
| F-205 | id1 至 id5 的完整安全 pulse 范围和精确物理关节对应关系尚未形成当前项目合同 | `UNKNOWN` | 当前文档明确保留未知项 |
| F-206 | 当前检测-only节点不创建运动学客户端；旧抓取方法中仍保留两个运动学服务调用表达式 | `VERIFIED_REPO` | [track_and_grab.py](../../robot/grape_robot/code/track_and_grab.py) |
| F-207 | 两个运动学服务的类型、字段和服务端“无解时 pulse为空但success仍为true”行为已确认 | `VERIFIED_ROBOT` | [2026-07-14 实机只读快照](../evidence/robot-snapshot-20260714/README.md) |
| F-208 | Gemini RGB为`640×480 rgb8`，深度为`640×400 16UC1`，`depth_registration=false`；深度值为毫米，`depth_to_color.translation`为米 | `VERIFIED_ROBOT` | [2026-07-14 实机只读快照](../evidence/robot-snapshot-20260714/README.md) |
| F-209 | 运动学服务网络等待、调用超时和取消行为尚未形成合同 | `UNKNOWN` | 当前客户端已禁用，恢复前必须取证并实现 |
| F-210 | `/controller_manager`提供机械臂、夹爪和joint1三个`FollowJointTrajectory` action；机械臂action控制`joint2`–`joint5`，夹爪action控制`r_joint` | `VERIFIED_ROBOT` | [2026-07-19固定工位基本夹取只读快照](../evidence/basic-fixed-pick-20260719/README.md) |
| F-211 | 厂商action服务端把rad转换为pulse后直接调用servo manager，支持执行期间取消，但结束时不检查实际到位误差 | `VERIFIED_ROBOT` | 同上，厂商源码SHA-256及摘录 |
| F-212 | 当前新增的固定工位夹取执行器不创建publisher，不使用旧运动学/舵机调用；默认inspect只读，execute需要三重许可。2026-07-19续查后，仓库实现已改为在每步后通过总线状态服务读取真实pulse并复核，不再把joint_states当作实际到位证据 | `VERIFIED_REPO`（修正后的动作路径）/ `VERIFIED_ROBOT`（旧版只读inspect） | `basic_fixed_pick.py`、纯算法和合同测试、[2026-07-19只读部署及续查记录](../evidence/basic-fixed-pick-20260719/README.md) |
| F-213 | 2026-07-19快照时`/servo_controller`有7个发布端点，6秒观察窗口没有收到消息；发布者之间不存在可证明的系统级互斥 | `VERIFIED_ROBOT`（端点与本次窗口）/ `UNKNOWN`（长期互斥） | [2026-07-19只读快照](../evidence/basic-fixed-pick-20260719/README.md) |
| F-214 | 固定工位的pregrasp/grasp/lift关节姿态、`r_joint`开闭方向和位置、葡萄接触后的安全夹持量尚未采集和动作验证 | `UNKNOWN` | 配置模板保持null，禁止从旧pulse值推算 |
| F-215 | 厂商`ServoManager.get_position()`返回缓存的最近命令目标，`/controller_manager/joint_states`不是舵机总线实测位置，不能证明实际到位 | `VERIFIED_ROBOT` | 机器人端厂商源码续查、同一时刻joint_states与总线状态服务结果对比，见2026-07-19续查记录 |
| F-216 | `/ros_robot_controller/bus_servo/get_state`可用`GetBusServoState`只读查询ID1–5、10的实际position pulse；本次两次读取间仅有ID1、ID10各1 pulse波动 | `VERIFIED_ROBOT` | `ros2 service type/interface show/call`与机器人端消息导入，见2026-07-19续查记录 |
| F-217 | 现场曾同时发现两套同名ROS控制图；另一Ubuntu设备MAC为`f8:3d:c6:1f:8f:55`，当前机器人MAC为`f8:3d:c6:57:25:91`。现场人员已把前者加入热点黑名单；动作前仍须重新确认控制图唯一 | `VERIFIED_ROBOT`（当时发现与MAC）/ `DOCUMENTED_ROBOT`（热点黑名单操作） | 2026-07-19现场续查；网络隔离不是程序内永久互斥 |
| F-218 | 现场小步试验确认ID10从499递增到504、509时夹爪继续小幅闭合，未观察到顶死或异常声音；真实葡萄安全夹持位置仍未知 | `VERIFIED_ROBOT`（方向与本次小步）/ `UNKNOWN`（负载夹持量） | 2026-07-19 NoMachine现场观察与人工确认 |

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

首轮只读快照已保存到 `docs/evidence/robot-snapshot-20260714/`。下一批重点不是重复列接口，而是补充：

- 一组同步RGB、深度、两路CameraInfo和外参固定样本；
- 已知距离标定物的映射与三维误差；
- 多个`/servo_controller`发布者的互斥机制。
- 固定工位pregrasp、grasp、lift姿态和相邻姿态安全间隔；
- `r_joint`张开/闭合方向、空载安全位置及接触葡萄时的可接受行程。

还需要人工记录：

- 当前小车版本、相机型号和安装位置；
- RGB-D映射在真实目标上的误差；
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
