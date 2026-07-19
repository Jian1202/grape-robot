# ROS2 与外部接口合同

最后整理：2026-07-19

本文件集中记录当前代码依赖的 ROS2 接口和外部 Python 符号。它的目的不是证明这些接口在所有机器人版本中都可用，而是防止开发者或 Codex 根据习惯编造名称、类型和字段。

## 1. 使用规则

- 新增外部接口前，先在本文件登记来源和状态。
- `VERIFIED_REPO` 只代表当前代码存在调用，不代表实机服务一定在线。
- 影响硬件动作的接口在进入实车前必须升级为 `VERIFIED_ROBOT`。
- 类型、字段或单位有一个未知，就不能凭经验补全。
- ROS1 名称不能直接写入当前 ROS2 实现。

状态定义见[项目事实基线](PROJECT_FACT_BASE.md)。

## 2. 当前节点

| 项目 | 当前值 | 状态 | 来源 |
| --- | --- | --- | --- |
| 节点实现 | `TrackAndGrabNode` | `VERIFIED_REPO` | `robot/grape_robot/code/track_and_grab.py` |
| 节点名 | `track_and_grab` | `VERIFIED_REPO` | 当前 `main()` |
| launch 中 package | `example` | `VERIFIED_REPO` | `robot/grape_robot/launch/track_and_grab.launch.py` |
| launch 中 executable | `track_and_grab` | `VERIFIED_REPO` | 同上 |
| 当前安全模式 | 定位-only；`enable_arm=true` 拒绝启动 | `VERIFIED_REPO` | `grape_localization.enforce_localization_only` |
| 机器人实际安装包与当前未提交代码的同步关系 | 2026-07-14快照时一致；本轮修改尚未部署 | `UNKNOWN` | [实机只读快照](../evidence/robot-snapshot-20260714/README.md) |

固定工位基本夹取使用独立的 `BasicFixedPickNode`，不解除上述检测-only节点的
动作硬禁用。其默认 `inspect` 模式只读；`execute` 必须经过配置许可、环境令牌、
启动前状态检查和三次人工确认。该执行器目前仅完成仓库实现与离线测试，尚未发送过
实车 action goal，状态为 `VERIFIED_REPO`。

## 3. 订阅输入

| 名称 | 类型 | 用途 | 当前证据 | 实车放行要求 |
| --- | --- | --- | --- | --- |
| `/gemini_camera/rgb/image_raw` | `sensor_msgs/msg/Image` | RGB 图像 | `VERIFIED_REPO`；另有实机文档记录 | 核对类型、分辨率、encoding、帧率 |
| `/gemini_camera/depth/image_raw` | `sensor_msgs/msg/Image` | 深度图 | `VERIFIED_REPO`；另有实机文档记录 | 核对类型、encoding、单位、无效值规则 |
| `/gemini_camera/depth/camera_info` | `sensor_msgs/msg/CameraInfo` | 深度相机内参 | `VERIFIED_REPO` | 核对内参与深度图分辨率一致 |
| `/gemini_camera/rgb/camera_info` | `sensor_msgs/msg/CameraInfo` | RGB相机内参 | `VERIFIED_ROBOT` | 当前代码新增订阅；核对固定样本与本次快照参数一致 |
| `/gemini_camera/depth_to_color` | `orbbec_camera_msgs/msg/Extrinsics` | 深度到RGB外参，translation单位为米 | `VERIFIED_ROBOT` | 驱动`obExtrinsicsToMsg()`定义；当前代码按Reliable + Transient Local订阅 |

当前通过 `message_filters.ApproximateTimeSynchronizer` 只同步 RGB 与深度图；
两路 `CameraInfo` 和外参由独立回调缓存，处理图像对时读取缓存快照。

固定工位基本夹取执行器新增以下只读订阅：

| 名称 | 类型 | 用途 | 当前证据 | 失败语义 |
| --- | --- | --- | --- | --- |
| `/controller_manager/joint_states` | `sensor_msgs/msg/JointState` | 启动前姿态与动作后到位复核，位置单位为rad | `VERIFIED_ROBOT` | 缺失、过期、关节不全或超容差时拒绝/停止后续动作 |
| `/servo_controller` | `servo_controller_msgs/msg/ServosPosition` | 竞争动作通道监视；只订阅、不发布 | `VERIFIED_ROBOT` | 静默期或执行中收到任一消息即取消当前goal，不自动恢复 |

## 4. 发布输出

当前检测-only节点和固定工位基本夹取执行器均不创建任何 publisher。

基本夹取执行器通过 ROS2 action client 接触控制器，不向 `/servo_controller`
发布消息。action goal 会导致真实机械臂或夹爪动作，因此只允许在 `execute` 模式及
实车关卡通过后使用。

旧抓取方法仍保留 `set_servo_position(...)` 调用源码，但构造器不创建 `/servo_controller` publisher，且 `enable_arm=true` 会在初始化时被拒绝。恢复任何动作能力前必须另行评审，不得删除安全保护后直接复用旧方法。

## 5. 服务客户端

当前检测-only节点不创建运动学、控制器或相机状态变更客户端，也不调用服务。

旧抓取方法中仍保留 `/kinematics/get_current_pose` 与 `/kinematics/set_pose_target` 的调用源码。实机快照已经确认类型、字段和IK无解行为；恢复客户端前仍必须实现超时、取消、`GetRobotPose.solution`检查和空`pulse`失败退出。

固定工位基本夹取执行器只登记以下客户端：

| 名称 | 类型 | 控制范围/用途 | 状态与来源 |
| --- | --- | --- | --- |
| `/arm_controller/follow_joint_trajectory` | `control_msgs/action/FollowJointTrajectory` | `joint2`–`joint5`，单位rad | `VERIFIED_ROBOT`；2026-07-19 `ros2 action list -t`、`ros2 node info /controller_manager`及控制器配置 |
| `/gripper_controller/follow_joint_trajectory` | `control_msgs/action/FollowJointTrajectory` | `r_joint`，单位rad | `VERIFIED_ROBOT`；同上 |
| `/object_tracking/exit` | `std_srvs/srv/Trigger` | execute前停止现有物体跟踪节点，随后检查动作话题静默 | `VERIFIED_ROBOT`；2026-07-19 `ros2 service type` |

厂商 `JointTrajectoryActionController` 会把rad目标转换为pulse并直接调用servo manager；
它在持续时间结束后报告成功，但源码未核验实际关节误差。因此 action 成功不能单独
证明到位，客户端必须再读取新鲜的 `joint_states` 并执行容差检查。完整证据见
[2026-07-19固定工位基本夹取只读快照](../evidence/basic-fixed-pick-20260719/README.md)。

## 6. 本节点提供的服务

| 相对名称 | 类型 | 用途 | 状态 |
| --- | --- | --- | --- |
| `~/start` | `std_srvs/srv/Trigger` | 开始检测/跟踪 | `VERIFIED_REPO` |
| `~/stop` | `std_srvs/srv/Trigger` | 停止检测并清除节点内状态；当前不发布复位动作 | `VERIFIED_REPO` |
| `~/set_color` | `interfaces/srv/SetString` | 切换颜色跟踪目标 | `VERIFIED_REPO` |
| `~/init_finish` | `std_srvs/srv/Trigger` | 返回节点初始化完成 | `VERIFIED_REPO` |

`~` 名称的最终解析结果受节点名称和 namespace 影响。调用文档不得直接猜测最终绝对名称，应通过：

```bash
ros2 node info /track_and_grab
ros2 service list -t | grep track_and_grab
```

确认。

## 7. 关键外部 Python 符号

| import / 符号 | 当前用途 | 状态 | 验证方式 |
| --- | --- | --- | --- |
| `sdk.pid.PID` | 视觉跟踪 PID | `VERIFIED_ROBOT` | 定义与路径见2026-07-14快照 |
| `sdk.common` | 颜色、矩阵与位姿转换 | `VERIFIED_ROBOT` | 函数定义已取证；物理坐标轴仍未知 |
| `sdk.fps.FPS` | 帧率统计 | `VERIFIED_REPO` | 检查实际包版本 |
| `kinematics.kinematics_control.set_pose_target` | 旧动作方法构造运动学请求 | `VERIFIED_ROBOT` | 实机签名、单位注释和源码哈希已取证 |
| `servo_controller.bus_servo_control.set_servo_position` | 旧动作方法发布舵机目标 | `VERIFIED_ROBOT` | 实机确认固定使用`pulse`并直接发布 |
| `ultralytics.YOLO` | YOLO 模型加载与推理 | `VERIFIED_ROBOT` | 实机版本8.3.182；本轮未重新运行模型 |
| `grape_localization.localize_detection` | RGB-D投影和稳健三维定位 | `VERIFIED_REPO` | 仓库内纯算法定义与离线单元测试 |
| `rclpy.action.ActionClient` | 固定工位机械臂/夹爪action客户端 | `VERIFIED_ROBOT` | 机器人端导入成功；action名称和服务端由2026-07-19只读快照确认 |
| `control_msgs.action.FollowJointTrajectory` | 关节轨迹goal/result | `VERIFIED_ROBOT` | 机器人端`ros2 interface show`及厂商服务端源码 |
| `yaml.safe_load` | 严格读取现场夹取配置 | `VERIFIED_ROBOT` | 机器人端导入成功；配置值仍须现场采集 |

本仓库当前没有这些机器人厂商 Python 包的完整定义。因此 Codex 可以分析调用点，但不能仅凭本地仓库证明底层行为。

## 8. 参数合同

| 参数 | 默认值 | 状态 | 说明 |
| --- | --- | --- | --- |
| `detector` | `yolo` | `VERIFIED_REPO` | 当前支持 `yolo` 与颜色路径 |
| `model_path` | launch 中为机器人绝对路径 | `VERIFIED_REPO` | 部署环境相关，不能当作跨机器固定路径 |
| `target_class` | `ripe_grape` | `VERIFIED_REPO` | 必须存在于模型类别中 |
| `confidence` | `0.4` | `VERIFIED_REPO` | 需要按现场验证调整 |
| `imgsz` | `320` | `VERIFIED_REPO` | 视觉测试文档另有 416 建议 |
| `enable_arm` | `false` | `VERIFIED_REPO` | 当前为硬禁用；传入`true`时节点拒绝启动 |
| `depth_scale_m_per_unit` | `0.001` | `VERIFIED_REPO` | 实机Orbbec驱动源码确认发布深度值单位为毫米；非正值仍失败关闭 |
| `min_valid_points` | `20` | `VERIFIED_REPO` | 框内投影点经过稳健过滤后的最低数量 |
| `min_valid_ratio` | `0.15` | `VERIFIED_REPO` | RGB框收缩区域的最低深度覆盖比例 |
| `box_inset_ratio` | `0.15` | `VERIFIED_REPO` | 排除检测框边缘背景的收缩比例，必须小于0.5 |

计划中的 `enable_tracking`、`enable_grab`、`enable_detach`、`enable_base_align` 当前只是设计建议，不得写成已经存在。

固定工位基本夹取不新增ROS参数；使用
`robot/grape_robot/config/basic_fixed_pick.yaml`。模板中动作许可为false，所有现场
姿态、夹爪开闭位置和参考深度均为null。任何空值、非法类型、非有限值、相邻姿态
单关节变化超过0.20rad都会在创建action goal前失败关闭。0.20rad只是离线保护上限，
不是已经过实车验证的抓取参数。

## 9. 必须在实车保存的接口快照

建议创建：

```text
docs/evidence/robot-snapshot-YYYYMMDD/
├── README.md
├── node-list.txt
├── topic-list-types.txt
├── service-list-types.txt
├── servo-controller-info.txt
├── servo-position-interface.txt
├── get-current-pose-interface.txt
├── set-pose-target-interface.txt
└── kinematics-node-info.txt
```

所有命令优先只读。不要为了“验证接口”顺带发送运动命令。

## 10. 新增接口登记模板

```markdown
### 接口名称

- 类型：
- 方向：发布 / 订阅 / 客户端 / 服务端
- 定义来源：
- 版本或提交：
- 请求/消息字段：
- 单位：
- 超时：
- 失败行为：
- 硬件影响：
- 状态：VERIFIED_REPO / DOCUMENTED_ROBOT / VERIFIED_ROBOT / REFERENCE_ONLY / UNKNOWN
- 验证记录：
```
