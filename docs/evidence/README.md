# 实机证据目录

本目录用于保存能够被组员和 Codex重复核对的实机接口快照、环境版本和实验记录。

当前已保存一份实机只读快照：

- [2026-07-14 ROSLander 实机只读接口与源码快照](robot-snapshot-20260714/README.md)
- [2026-07-14 RGB-D葡萄定位验证方案与过程记录](rgbd-localization-validation-20260714/README.md)

快照只证明其中列出的命令和取证时刻；未列出的坐标方向、硬件参数和动作安全性仍保持 `UNKNOWN`。

## 推荐目录命名

```text
docs/evidence/
└── robot-snapshot-YYYYMMDD/
    ├── README.md
    ├── environment.txt
    ├── node-list.txt
    ├── topic-list-types.txt
    ├── service-list-types.txt
    ├── servo-controller-info.txt
    ├── servo-position-interface.txt
    ├── get-current-pose-interface.txt
    ├── set-pose-target-interface.txt
    └── kinematics-node-info.txt
```

同一天对多台设备采集时增加设备代号，例如：

```text
robot-snapshot-20260713-car-a/
```

## 首轮只读采集命令

在机器人 ROS2 环境已经正确 `source` 后执行：

```bash
ros2 node list
ros2 topic list -t
ros2 service list -t
ros2 topic info -v /servo_controller
ros2 service type /kinematics/get_current_pose
ros2 service type /kinematics/set_pose_target
ros2 interface show servo_controller_msgs/msg/ServosPosition
ros2 interface show kinematics_msgs/srv/GetRobotPose
ros2 interface show kinematics_msgs/srv/SetRobotPose
ros2 node info /kinematics
```

这些命令只读取系统状态。不要在证据采集任务中加入 `ros2 topic pub`、底盘速度或舵机运动命令。

## 每份快照的 README

至少记录：

```text
采集日期和时区
设备代号
机器人系统版本
ROS_DISTRO
Git commit
执行账号与工作空间路径（脱敏后）
每个文件对应的完整命令
采集过程中的报错
哪些结论可以升级
哪些内容仍然 UNKNOWN
```

## 脱敏规则

提交前删除或替换：

- 密码、token、SSH 私钥和 cookie；
- 不需要公开的公网 IP、热点名称和个人目录；
- 厂商授权码、比赛私密材料和个人信息；
- 与接口验证无关的环境变量。

不要把脱敏后的值伪装成真实值，应使用 `<REDACTED>`。

## 大文件

完整 rosbag、长视频和大量图片不提交普通 Git。仓库记录：

```text
文件名
大小
SHA-256
采集日期
用途
保存位置或组内获取方式
对应 Git commit 与配置
```

## 事实升级

采集完成后：

1. 对照[项目事实基线](../governance/PROJECT_FACT_BASE.md)；
2. 将能够直接证明的项目升级为 `VERIFIED_ROBOT`；
3. 更新[ROS2 接口合同](../governance/ROS2_INTERFACE_CONTRACT.md)；
4. 保留命令和原始输出，不只保存人工总结；
5. 无法证明的内容继续保留为 `UNKNOWN`。
