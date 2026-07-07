# rgbd_function 官方示例源码

本目录保存从 ROSLander 机器人官方示例目录拷贝出的 RGBD 追踪与抓取相关源码。

## 文件说明

- `track_and_grab.py`：官方 RGBD 目标追踪与抓取主逻辑
- `track_and_grab.launch.py`：对应 launch 启动文件
- `grape_track_grab.py`：葡萄 / 农业采摘相关示例逻辑
- `grape_track_grab.launch.py`：对应 launch 启动文件

## 使用原则

本目录作为源码参考和备份，不直接在这里开发项目功能。

如需修改或重构，应复制 / 抽象到：

robot/ros2_ws/src/

## 来源

机器人原始路径：

/home/ubuntu/ros2_ws/src/example/example/rgbd_function/

本地整理路径：

official_examples/rgbd_function/

整理日期：2026-07-07

## 注意事项

- 本目录中的源码视为 ROSLander 官方示例参考代码。
- 后续项目自研代码不要直接写在本目录。
- 如果需要修改，应在 `robot/ros2_ws/src/` 下新建自研 ROS2 包。
