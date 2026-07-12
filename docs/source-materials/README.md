# 精选原始资料索引

本目录保存与当前葡萄采摘问题最相关、体积适合进入 GitHub 的 ROSLander 原始教学资料。

> 这些文件主要用于项目内部学习、方案追溯和硬件调试。资料版权归原作者或设备厂商所有；仓库仅保留当前项目需要的精选文件，没有上传完整教学资料包、模型、安装程序和大体积第三方源码。

## 1. 农业采摘资料

| 文件 | 重点内容 | 建议阅读人群 |
| --- | --- | --- |
| [场地组装实验](agriculture/01-场地组装实验.pdf) | 果树高度约 36cm，果实水平与垂直间距，收纳盒安装 | 场地组、机械臂调试人员 |
| [农业采摘实验](agriculture/02-农业采摘实验.pdf) | 任务流程、果树类型、自动校准、XYZ 偏差、导航点 | 控制组、系统集成人员 |
| [机械臂偏差调节](agriculture/03-机械臂偏差调节.pdf) | 舵机中位标准、夹爪 2-3cm 中位、ID10 范围和机械限位 | 机械臂实车调试人员 |

## 2. 移动抓取资料

| 文件 | 重点内容 | 建议阅读人群 |
| --- | --- | --- |
| [机器人移动抓取准备](mobile-grab/01-机器人移动抓取准备.pdf) | 场地与障碍物准备 | 导航与场地组 |
| [机器人移动抓取实现步骤](mobile-grab/02-机器人移动抓取实现步骤.pdf) | 停止像素校准、导航到点、视觉微调、抓取与放置 | 导航与控制组 |
| [navigation_transport.zip](mobile-grab/navigation_transport.zip) | ROS1 移动抓取编排与视觉校准源码 | 负责底盘对准逻辑的组员 |

## 3. 课程资料

| 文件 | 可参考内容 | 当前用途 |
| --- | --- | --- |
| [基于深度的颜色追踪实验](courses/10-01-基于深度的颜色追踪实验.docx) | 目标 ROI 内深度统计、目标中心跟踪 | 改造深度采样与底盘调距 |
| [基于深度点云的目标追踪实验](courses/10-04-基于深度点云的目标追踪实验.docx) | RGB-D 转点云、根据最近点控制底盘 | 评估后续点云方案；当前不建议直接全量接入 |
| [机械臂逆运动学实验](courses/22-02-机械臂逆运动学实验.docx) | 无解判断、关节范围、脉宽转换 | 补充 IK 失败保护与可达性检查 |
| [机械臂三维空间目标抓取实验](courses/24-02-机械臂三维空间目标抓取实验.docx) | 手眼矩阵、分方向补偿、目标稳定判断、按形状抓取 | 参考抓前修正与多解选择 |

## 4. 未上传的大文件

农业采摘完整功能包没有上传：

```text
文件：agripicking.zip
大小：约 470.79MiB
本地原始位置：
E:\葡萄比赛\ROSLander多模态机器人-Jetson Nano（实验资料）
  \03 综合实践案例\02 复合机器人农业采摘综合实践案例
  \2 功能包程序\agripicking.zip
```

未上传原因：

- 超过 GitHub 普通单文件 100MB 限制；
- 内含完整 Git 历史、模型引擎、Ultralytics/TensorRT 和大量第三方源码；
- 当前真正需要阅读的农业采摘代码只占其中很小一部分。

由资料持有人私发压缩包后，优先查看：

```text
agripicking/config/config.yaml
agripicking/scripts/agripicking/mission_start.py
agripicking/scripts/agripicking/mission_start.launch
agripicking/scripts/agripicking/track_and_grab/agricultural_picking.py
agripicking/scripts/agripicking/track_and_grab/agricultural_picking.launch
agripicking/scripts/yolov8/yolov8_node.py
```

不要优先研究压缩包里的整套 `tensorrtx-master`、Ultralytics 源码、模型引擎和历史缓存。

## 5. 版本与使用提醒

- 精选资料大多基于 Ubuntu 18.04 + ROS Melodic（ROS1）。
- 当前仓库机器人端使用 ROS2，话题、服务、消息和启动方式不同。
- 可以移植状态机、参数体系、校准方法和动作策略，不能直接复制整个节点运行。
- 资料中出现的舵机 pulse、XYZ offset 和导航点均是示例或特定机器实测值，必须在当前小车上重新校准。
