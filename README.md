# grape-robot

基于 ROSLander 移动机械臂平台的葡萄智能视觉夹取系统。

## 项目目标

在教室模拟葡萄架场景中，实现：

- 成熟 / 未成熟葡萄检测
- 葡萄目标中心点输出
- 深度定位
- 移动底盘到达葡萄架附近
- 机械臂与夹爪完成采摘演示

## 当前工程路线

```text
先复现官方示例
↓
整理并理解官方 RGBD 抓取源码
↓
接入 YOLO 葡萄检测
↓
接入深度定位
↓
接入机械臂夹取
↓
接入教室导航
↓
形成现场演示闭环
```

## 目录结构

```text
docs/              项目文档
official_examples/ ROSLander 官方示例源码备份，只读参考
yolo/              YOLO 数据配置、训练脚本、推理脚本
robot/             后续自研 ROS2 机器人端代码
configs/           配置文件
tools/             辅助工具脚本
tests/             测试脚本和测试说明
```

## 当前约定

- 不直接修改 official_examples/ 下的官方示例源码。
- 自研 ROS2 代码后续放入 robot/ros2_ws/src/。
- 大量图片、模型权重、训练输出不直接提交到普通 Git。
- public 仓库中不得提交账号、密码、SSH key、私有资料。

## 文档与资料

- [项目文档入口](docs/README.md)
- [葡萄采摘问题分析与实施建议](docs/reports/2026-07-13-葡萄采摘问题分析与实施建议.md)
- [精选 ROSLander 原始资料索引](docs/source-materials/README.md)

当前问题分析已经确认：通用 `track_and_grab` 尚未包含农业采摘案例中的底盘预对准、抓前修正、向下摘取、结果复检和失败重试。后续开发应优先按分析报告中的阶段路线移植这些能力。
