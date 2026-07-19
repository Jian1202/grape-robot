# 2026-07-19 固定工位基本夹取只读快照

## 结论与边界

本次在ROSLander机器人上只读确认了基本夹取所需的标准action、关节状态、
`/object_tracking/exit`服务和厂商控制器实现。没有发送action goal，没有调用
`/object_tracking/exit`，没有发布topic，也没有移动机械臂、夹爪或底盘。

这些证据只允许离线实现和后续分级验证，不证明任何夹取姿态或夹爪位置安全。
K4仍为“未通过，仅工程上暂按通过继续”，不得写成 `VERIFIED_ROBOT`。

- 采集时间：2026-07-19 15:17（Asia/Shanghai）
- 设备主机名：`ubuntu`
- ROS发行版：Humble
- 本地分支：`codex/rgbd-localization-validation-20260714`
- 本地起始提交：`07b1dd6`
- 实机动作：无

## 执行的只读命令

ROS环境加载前清除了远端遗留的 `COLCON_CURRENT_PREFIX`，随后执行：

```bash
ros2 action list -t
ros2 action info /arm_controller/follow_joint_trajectory
ros2 action info /gripper_controller/follow_joint_trajectory
ros2 service type /object_tracking/exit
ros2 topic info -v /controller_manager/joint_states
ros2 topic echo --once /controller_manager/joint_states sensor_msgs/msg/JointState
ros2 topic info -v /servo_controller
ros2 node info /controller_manager
ros2 interface show control_msgs/action/FollowJointTrajectory
systemctl is-active start_app_node.service
timeout 6 ros2 topic hz /servo_controller
sha256sum /home/ubuntu/ros2_ws/src/driver/servo_controller/servo_controller/servo_controller/joint_trajectory_action_controller.py
sed -n '1,280p' /home/ubuntu/ros2_ws/src/driver/servo_controller/servo_controller/servo_controller/joint_trajectory_action_controller.py
sed -n '1,280p' /home/ubuntu/ros2_ws/src/driver/servo_controller/servo_controller/config/servo_controller.yaml
```

还在机器人Python环境只导入了以下符号：`yaml`、`ActionClient`、
`FollowJointTrajectory`、`GoalStatus`、`Duration`、`JointState`、
`ServosPosition`、`Trigger`和`JointTrajectoryPoint`。结果为 `OK`；导入不会创建节点
或发送动作。

## 接口结果

`ros2 action list -t`返回：

```text
/arm_controller/follow_joint_trajectory [control_msgs/action/FollowJointTrajectory]
/gripper_controller/follow_joint_trajectory [control_msgs/action/FollowJointTrajectory]
/not_arm_controller/follow_joint_trajectory [control_msgs/action/FollowJointTrajectory]
```

`ros2 node info /controller_manager`确认三个action server均由
`/controller_manager`提供。单独的`ros2 action info`在同一时刻却显示server为0，
属于CLI发现结果不一致；执行器仍必须在运行时调用`wait_for_server()`，不可只依赖
静态快照。

控制器配置SHA-256：

```text
979eaf6a09ad1d8ad32a366468ec1e6ee362c0ad936a5d4ef986e6d607e2d423
```

其关节集合为：

```text
not_arm_controller: joint1
arm_controller: joint2, joint3, joint4, joint5
gripper_controller: r_joint
```

`/controller_manager/joint_states`类型为`sensor_msgs/msg/JointState`，发布者为
`/controller_manager`。本次单帧包含`joint1`–`joint5`和`r_joint`，position为rad。
此单帧只证明接口格式，不得复制为夹取姿态。

`/object_tracking/exit`类型为`std_srvs/srv/Trigger`。`start_app_node.service`
在快照时为`active`。

`/servo_controller`类型为`servo_controller_msgs/msg/ServosPosition`，订阅者为
`/controller_manager`，快照时有7个发布端点。6秒`ros2 topic hz`窗口没有收到消息
并因timeout以124退出；这只证明该短窗口静默，不证明发布端点互斥或长期静默。

## 厂商action服务端行为

取证文件：

```text
/home/ubuntu/ros2_ws/src/driver/servo_controller/servo_controller/servo_controller/joint_trajectory_action_controller.py
SHA-256: 1a47432fd86bfcb1f9be061d36a59dd6e02f06d5e9b6f17c49681261838f70ee
```

源码直接证明：

1. goal中必须包含控制器配置的全部关节名；
2. `trajectory.header.stamp`为零时使用当前ROS时间；
3. 目标位置通过`pos_rad_to_pulse()`从rad转换为pulse；
4. 转换后直接调用`servo_manager.set_position(duration, ...)`；
5. 等待持续时间期间检查`goal_handle.is_cancel_requested`；
6. 持续时间结束后直接`succeed()`，没有读取实际位置或执行目标容差判断。

因此新客户端即使收到action成功，也必须再用新鲜`joint_states`检查实际关节位置。

## UNKNOWN与后续关卡

- `UNKNOWN`：pregrasp、grasp、lift的安全关节姿态；
- `UNKNOWN`：`r_joint`在本机上的张开/闭合方向和安全位置；
- `UNKNOWN`：夹住真实葡萄后的最小/最大安全行程；
- `UNKNOWN`：7个`/servo_controller`发布端点的系统级互斥；
- `UNKNOWN`：动作取消后实际舵机停止延迟；
- 未验证：新执行器尚未部署，尚未进行inspect/capture或任何action动作测试；
- 未验证：基本夹取、抬升和重复性；
- 不在本轮：向下脱离、底盘对准、视觉自动闭环、自动重试和自动归位。
