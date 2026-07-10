# frontend

本目录用于保存“葡萄智能视觉夹取系统”的前端界面代码。

当前阶段前端还没有正式实现，本 README 先记录推荐方案、页面功能、后端接口约定和后续开发路线，方便后面按同一思路开工。

## 1. 前端目标

前端主要服务现场调试、比赛展示和答辩演示。

目标不是替代 ROS2 控制程序，而是把机器人当前状态可视化，并提供少量高层控制按钮：

```text
查看相机 / YOLO 实时画面
查看当前检测目标
查看成熟度、置信度和中心点
查看目标三维坐标 X / Y / Z
查看机械臂与夹爪状态
触发开始、停止、复位、急停、保存截图等操作
```

前端应尽量只调用安全的上层接口，不直接操作底层舵机话题。

## 2. 当前项目背景

本项目整体目标是基于 ROSLander 移动机械臂平台，实现葡萄目标识别、深度定位和机械臂夹取演示。

当前仓库中与前端相关的已有信息：

```text
YOLO 模块目标：识别 ripe_grape / unripe_grape
ROS2 环境：Humble
机器人端代码规划目录：robot/ros2_ws/src/
官方 RGBD 抓取示例：official_examples/rgbd_function/
机械臂上层控制入口：/servo_controller
机械臂状态反馈：/controller_manager/servo_states
已观察到网页视频节点：/web_video_server
```

其中 `/web_video_server` 可能可以把 ROS 图像话题转成浏览器视频流，但当前访问方式还没有在本仓库中验证。

## 3. 推荐方案

### 3.1 简单方案：Python 桌面界面

如果时间紧、队伍主要熟悉 Python，可以先做一个本地桌面控制面板。

可选技术：

```text
PySide6
PyQt5 / PyQt6
Tkinter
```

建议界面：

```text
左侧：
  相机画面
  YOLO 检测框
  目标中心点

右侧：
  当前状态：等待目标 / 已发现目标 / 正在靠近 / 正在抓取 / 完成 / 异常
  目标类别：成熟葡萄 / 未成熟葡萄
  置信度：0.92
  空间坐标：X、Y、Z
  机械臂状态：空闲 / 正在靠近 / 已到位 / 异常
  夹爪状态：张开 / 已闭合

底部：
  开始任务
  停止任务
  机械臂复位
  保存截图
```

优点：

```text
Python 可以直接使用 rclpy 订阅 ROS2 话题
不需要额外搭建 Web 后端
适合直接运行在机器人 Ubuntu 图形桌面上
开发成本低，适合快速调试和应急展示
```

缺点：

```text
只能方便地运行在装有程序和 ROS2 环境的电脑或机器人上
手机、平板、其他电脑访问不方便
界面美观和跨设备展示能力弱于网页
```

适合：

```text
时间紧
团队主要会 Python
主要目标是现场调试和最小可演示闭环
```

### 3.2 推荐方案：Web 网页前端

最终展示版本更推荐做网页前端。

整体结构：

```text
ROS2 / YOLO / 机械臂控制后端
        ↓
前端适配程序
FastAPI / Flask
        ↓
REST API + WebSocket + 视频流
        ↓
浏览器网页
电脑 / 平板 / 手机 / 机器人显示屏
```

推荐原因：

```text
任何设备打开浏览器就能查看
更适合比赛展示和答辩讲解
界面容易做得直观、美观
前端和机器人程序可以分开开发
电脑、平板、手机、机器人屏幕可以共用同一套页面
```

代价：

```text
需要写一个 ROS2 到网页的中间层
需要处理视频流、WebSocket 状态推送和控制接口
需要确认 /web_video_server 是否可直接复用
```

## 4. Web 页面建议布局

第一版页面建议做成一个单页控制台。

```text
┌────────────────────────────────────────────┐
│ 葡萄智能视觉夹取系统              系统正常 ● │
├──────────────────────────┬─────────────────┤
│                          │ 当前目标         │
│ YOLO 实时画面             │ 成熟葡萄         │
│ 检测框和中心点            │ 置信度 92%       │
│                          │ X / Y / Z 坐标   │
├──────────────────────────┼─────────────────┤
│ 抓取流程                  │ 控制面板         │
│ 识别 → 定位 → 靠近 → 抓取  │ 开始 停止 复位   │
│                          │ 急停 保存截图    │
└──────────────────────────┴─────────────────┘
```

页面状态建议包括：

```text
系统状态：未连接 / 待机 / 运行中 / 异常 / 急停
视觉状态：无画面 / 检测中 / 已发现目标 / 未发现目标
目标类别：ripe_grape / unripe_grape
目标中文名：成熟葡萄 / 未成熟葡萄
置信度：0.00 ~ 1.00
图像中心点：u, v
空间坐标：x, y, z
机械臂状态：空闲 / 正在靠近 / 已到位 / 复位中 / 异常
夹爪状态：张开 / 闭合 / 未知
任务阶段：等待目标 / 识别 / 定位 / 靠近 / 抓取 / 完成
```

## 5. 前端技术选择

### 5.1 简单 Web 版

适合第一版快速实现：

```text
HTML
CSS
JavaScript
```

建议特点：

```text
不用构建工具
可以直接静态部署
适合快速写出可展示页面
后续再升级为 Vue 或 React
```

### 5.2 漂亮 Web 版

适合最终展示版本：

```text
Vue 3 + Element Plus
```

理由：

```text
组件现成
表格、按钮、标签、状态卡片实现快
中文生态友好
适合比赛展示页面
```

也可以选择：

```text
React
```

如果团队成员更熟悉 React，则可以直接使用 React，不必为了项目强行切换技术栈。

## 6. 后端接口建议

前端不应直接订阅 ROS2 话题。建议在机器人端或同一局域网电脑上提供一个适配后端。

后端可以使用：

```text
FastAPI
Flask
```

推荐 FastAPI，因为它对 REST API 和 WebSocket 支持更直接。

### 6.1 REST API

建议第一版接口：

```http
GET  /api/status
POST /api/start
POST /api/stop
POST /api/reset
POST /api/emergency_stop
POST /api/save_snapshot
```

`GET /api/status` 示例返回：

```json
{
  "system_state": "idle",
  "vision_state": "target_found",
  "task_stage": "locating",
  "target": {
    "class_id": 1,
    "class_name": "ripe_grape",
    "label": "成熟葡萄",
    "confidence": 0.92,
    "center": {
      "u": 328,
      "v": 246
    },
    "position": {
      "x": 0.12,
      "y": -0.03,
      "z": 0.58
    }
  },
  "arm": {
    "state": "approaching"
  },
  "gripper": {
    "state": "closed"
  }
}
```

### 6.2 WebSocket

用于实时推送状态：

```text
WebSocket /ws/status
```

建议推送内容与 `/api/status` 保持同一结构，前端只需要用同一套状态模型渲染。

### 6.3 视频流

可选路径：

```text
/video
```

或者复用 ROS2 中已经观察到的：

```text
/web_video_server
```

待验证内容：

```text
web_video_server 的访问地址
可用的图像话题名
是否支持浏览器直接播放
是否需要在中间层转发或叠加 YOLO 检测框
```

## 7. 建议目录结构

如果采用简单 Web 版：

```text
frontend/
  README.md
  index.html
  styles.css
  app.js
```

如果采用 Vue 3 + Element Plus：

```text
frontend/
  README.md
  package.json
  index.html
  src/
    main.js
    App.vue
    api/
      status.js
    components/
      VideoPanel.vue
      StatusPanel.vue
      ControlPanel.vue
      TaskFlow.vue
```

如果采用 Python 桌面版，建议放到单独子目录，避免和 Web 前端混在一起：

```text
frontend/
  README.md
  desktop_panel/
    README.md
    main.py
  web_panel/
    README.md
    ...
```

## 8. 开发顺序建议

第一阶段：静态页面原型

```text
先写假数据
先把页面布局和状态展示做出来
不连接 ROS2
适合比赛 PPT、答辩截图和团队讨论
```

第二阶段：接入后端状态接口

```text
实现 GET /api/status
前端定时轮询或连接 WebSocket
显示真实目标类别、置信度、坐标和机械臂状态
```

第三阶段：接入视频流

```text
验证 /web_video_server
或者由 FastAPI / Flask 提供 /video
在视频上显示 YOLO 检测框和中心点
```

第四阶段：接入控制按钮

```text
开始任务
停止任务
复位
急停
保存截图
```

控制按钮必须只调用后端提供的安全接口，不在前端写任何底层舵机控制逻辑。

第五阶段：比赛展示优化

```text
适配 1920x1080 屏幕
适配平板横屏
突出当前目标、置信度、坐标和抓取阶段
异常状态要明显
按钮要大，避免现场误触
```

## 9. 安全约定

前端按钮只负责发出高层命令：

```text
start
stop
reset
emergency_stop
save_snapshot
```

不建议前端直接暴露：

```text
单个舵机 ID 控制
任意 pulse 值输入
底层 /ros_robot_controller/bus_servo/set_position 控制
未限幅的机械臂位置输入
```

机械臂控制应优先通过机器人端的安全控制节点完成，并优先使用项目已经确认的上层入口 `/servo_controller`。

## 10. 当前待确认事项

后续开发前需要确认：

```text
最终使用 Python 桌面版还是 Web 网页版
如果做 Web，选择简单 HTML/CSS/JS 还是 Vue 3 + Element Plus
状态后端放在 robot/ros2_ws/src/ 下，还是单独放一个 backend 目录
/web_video_server 的实际访问方式
YOLO 检测结果最终由哪个 ROS2 话题或后端接口输出
目标三维坐标由哪个模块计算并发布
机械臂和夹爪状态是否能从现有话题稳定读取
开始 / 停止 / 复位 / 急停 的后端安全实现方式
```

## 11. 当前建议结论

如果只是快速调试：

```text
优先做 Python 桌面界面。
```

如果目标是最终比赛和答辩展示：

```text
优先做 Web 网页前端。
推荐路线是 Vue 3 + Element Plus + FastAPI + WebSocket + 视频流。
```

第一版可以先从静态页面开始，用假数据把展示效果做出来；等 ROS2 / YOLO / 机械臂状态接口稳定后，再逐步替换成真实数据。
