# ROS2 与外部接口合同

最后整理：2026-07-13

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
| 机器人实际安装包与仓库代码的同步关系 | 尚未形成自动校验 | `UNKNOWN` | 需在机器人工作空间核对 |

## 3. 订阅输入

| 名称 | 类型 | 用途 | 当前证据 | 实车放行要求 |
| --- | --- | --- | --- | --- |
| `/gemini_camera/rgb/image_raw` | `sensor_msgs/msg/Image` | RGB 图像 | `VERIFIED_REPO`；另有实机文档记录 | 核对类型、分辨率、encoding、帧率 |
| `/gemini_camera/depth/image_raw` | `sensor_msgs/msg/Image` | 深度图 | `VERIFIED_REPO`；另有实机文档记录 | 核对类型、encoding、单位、无效值规则 |
| `/gemini_camera/depth/camera_info` | `sensor_msgs/msg/CameraInfo` | 深度相机内参 | `VERIFIED_REPO` | 核对内参与深度图分辨率一致 |

当前通过 `message_filters.ApproximateTimeSynchronizer` 同步三路输入，代码注释与实参的时间容差存在文字差异，后续修改时应以实际参数和测试结果为准。

## 4. 发布输出

| 名称 | 类型 | 用途 | 状态 | 风险说明 |
| --- | --- | --- | --- | --- |
| `/servo_controller` | `servo_controller_msgs/msg/ServosPosition` | 机械臂和夹爪舵机控制 | `VERIFIED_REPO` + `DOCUMENTED_ROBOT` | 真实硬件动作；进入实车前必须重新核对订阅者、单位和限幅 |

代码通过外部函数 `set_servo_position(...)` 向该 publisher 发送命令。不得因为函数名直观就猜测其参数结构，应检查机器人已安装包中的真实定义。

## 5. 服务客户端

| 服务名 | 类型 | 当前用途 | 状态 | 必须补充的证据 |
| --- | --- | --- | --- | --- |
| `/kinematics/get_current_pose` | `kinematics_msgs/srv/GetRobotPose` | 获取末端当前位姿 | `VERIFIED_REPO` | `ros2 service type`、`ros2 interface show`、超时与失败行为 |
| `/kinematics/set_pose_target` | `kinematics_msgs/srv/SetRobotPose` | 将目标位姿转换为舵机 pulse | `VERIFIED_REPO` | 请求/响应字段、单位、IK 无解表现、pulse 数量 |
| `/controller_manager/init_finish` | `std_srvs/srv/Trigger` | 等待控制器初始化 | `VERIFIED_REPO` | 服务提供者、无响应时行为 |
| `/gemini_camera/set_ldp_enable` | `std_srvs/srv/SetBool` | 当前代码初始化时关闭 LDP | `VERIFIED_REPO` | LDP 准确含义及关闭影响 |

当前 `send_request()` 循环没有统一超时。任何重构都应先明确服务合同，再增加可测试的超时和取消处理。

## 6. 本节点提供的服务

| 相对名称 | 类型 | 用途 | 状态 |
| --- | --- | --- | --- |
| `~/start` | `std_srvs/srv/Trigger` | 开始检测/跟踪 | `VERIFIED_REPO` |
| `~/stop` | `std_srvs/srv/Trigger` | 停止并尝试恢复初始姿态 | `VERIFIED_REPO` |
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
| `sdk.pid.PID` | 视觉跟踪 PID | `VERIFIED_REPO` | 在机器人环境定位 `sdk` 包源码 |
| `sdk.common` | 颜色、矩阵与位姿转换 | `VERIFIED_REPO` | 检查实际函数定义和坐标约定 |
| `sdk.fps.FPS` | 帧率统计 | `VERIFIED_REPO` | 检查实际包版本 |
| `kinematics.kinematics_control.set_pose_target` | 构造运动学请求 | `VERIFIED_REPO` | 打开机器人安装源码，确认参数与单位 |
| `servo_controller.bus_servo_control.set_servo_position` | 发布舵机目标 | `VERIFIED_REPO` | 打开机器人安装源码，确认类型、单位和边界 |
| `ultralytics.YOLO` | YOLO 模型加载与推理 | `VERIFIED_REPO` | 记录机器人实际安装版本 |

本仓库当前没有这些机器人厂商 Python 包的完整定义。因此 Codex 可以分析调用点，但不能仅凭本地仓库证明底层行为。

## 8. 参数合同

| 参数 | 默认值 | 状态 | 说明 |
| --- | --- | --- | --- |
| `detector` | `yolo` | `VERIFIED_REPO` | 当前支持 `yolo` 与颜色路径 |
| `model_path` | launch 中为机器人绝对路径 | `VERIFIED_REPO` | 部署环境相关，不能当作跨机器固定路径 |
| `target_class` | `ripe_grape` | `VERIFIED_REPO` | 必须存在于模型类别中 |
| `confidence` | `0.4` | `VERIFIED_REPO` | 需要按现场验证调整 |
| `imgsz` | `320` | `VERIFIED_REPO` | 视觉测试文档另有 416 建议 |
| `enable_arm` | `false` | `VERIFIED_REPO` | 默认安全开关，未分离跟踪/夹取/脱离权限 |

计划中的 `enable_tracking`、`enable_grab`、`enable_detach`、`enable_base_align` 当前只是设计建议，不得写成已经存在。

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
