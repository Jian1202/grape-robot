# SSH 远程接入与安全调试

最后验证：2026-07-14
适用设备：当前 ROSLander 机器人
适用用户：`ubuntu`

本文说明如何从开发电脑通过 SSH 接入机器人，并在不误触发底盘、机械臂或夹爪的前提下进行代码检查和调试。

## 1. 当前验证结论

| 项目 | 当前结论 | 状态 |
| --- | --- | --- |
| 机器人 SSH 用户 | `ubuntu` | `VERIFIED_ROBOT` |
| 本次机器人地址 | `10.248.67.8` | `VERIFIED_ROBOT`，地址可能随网络变化 |
| SSH 端口 | TCP 22 可连接 | `VERIFIED_ROBOT` |
| 机器人主机名 | `ubuntu` | `VERIFIED_ROBOT` |
| 系统架构 | Ubuntu aarch64，Jetson 内核 | `VERIFIED_ROBOT` |
| ROS2 环境 | ROS2 Humble，工作区 `/home/ubuntu/ros2_ws` | `VERIFIED_ROBOT` |
| 项目主目录 | `/home/ubuntu/teams/ctrlteam/grape_robot` | `VERIFIED_ROBOT` |
| SSH 主机 ED25519 指纹 | `SHA256:zru6ibeuztJOPDxB9mSz78mwdZmBwzuC0WsCBGSxTVs` | `VERIFIED_ROBOT`，仅代表 2026-07-14 本次设备 |

`10.248.67.8` 不是永久固定地址。换热点、重新联网或地址租约变化后，必须重新确认机器人 IP，不能直接假设旧地址仍属于机器人。

## 2. 安全边界

SSH 登录本身不等于获得实车动作授权。默认只允许：

- 查看系统、文件和进程；
- 查询 ROS2 node、topic、service 和接口定义；
- 比较本地与机器人文件哈希；
- 执行离线语法检查和不连接执行器的测试；
- 在明确文件白名单、备份和回滚方案后同步代码。

未经用户明确授权和现场人员确认，禁止：

- 启动或重复启动 `bringup`；
- 停止或重启系统服务；
- 发布 `/cmd_vel`、`/controller/cmd_vel` 或 `/servo_controller`；
- 调用会改变相机、运动学、舵机或底盘状态的服务；
- 运行 `enable_arm=true`；
- 重启、升级系统或修改底层硬件配置。

本次检查发现机器人正常启动后已经存在 `bringup`、相机、运动学、舵机控制器和多个 App 节点。远程调试前必须先看现有进程，不能为了“确保环境存在”再次启动一套。

## 3. 网络与机器人 IP

开发电脑和机器人应连接同一个局域网。优先尝试：

```bash
ssh ubuntu@ubuntu.local
```

如果出现：

```text
Could not resolve hostname ubuntu.local
```

说明 mDNS 名称当前不可用，不代表 SSH 服务一定故障。此时在机器人本机执行：

```bash
hostname -I
ip -br addr
nmcli device status
```

选择已连接 Wi-Fi 网卡上的局域网 IPv4 地址。不要使用：

```text
127.0.0.1
127.0.1.1
172.17.0.1
```

本次开发电脑地址为 `10.248.67.100/24`，机器人地址为 `10.248.67.8`。这两个值只记录本次连接事实，后续应重新检查。

可在开发电脑上只读测试 SSH 端口：

```bash
nc -vz 机器人IP 22
```

端口开放后再执行 SSH，不要通过扫描或猜测其他服务替代设备身份确认。

## 4. 使用专用 SSH 密钥

机器人访问密钥应与 GitHub 密钥分开。本项目当前约定使用：

```text
~/.ssh/roslander_ed25519
~/.ssh/roslander_ed25519.pub
```

如果还没有专用密钥，可在开发电脑执行：

```bash
ssh-keygen -t ed25519 -f ~/.ssh/roslander_ed25519 -C roslander-agent
```

不要把私钥、密码或私钥口令发送到聊天、提交到 Git，或复制到项目目录。

将公钥添加到机器人时，应在机器人本机终端或已经可信的登录会话中操作：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
```

把 `~/.ssh/roslander_ed25519.pub` 的完整单行内容追加到：

```text
/home/ubuntu/.ssh/authorized_keys
```

然后执行：

```bash
chmod 600 ~/.ssh/authorized_keys
```

必须确认操作用户是 `ubuntu`。添加到其他用户的家目录不会授权 `ubuntu@机器人IP`。

如果私钥带口令，可在 macOS 本地终端解锁：

```bash
ssh-add --apple-use-keychain ~/.ssh/roslander_ed25519
ssh-add -l
```

口令只在本地终端输入，不要发送给 Codex 或组员。

## 5. SSH 配置建议

可在开发电脑的 `~/.ssh/config` 中配置别名：

```sshconfig
Host roslander
    HostName 10.248.67.8
    User ubuntu
    IdentityFile ~/.ssh/roslander_ed25519
    IdentitiesOnly yes
    AddKeysToAgent yes
    UseKeychain yes
```

随后使用：

```bash
ssh roslander
```

机器人 IP 变化后只更新 `HostName`。不要在仓库内保存包含密码或私钥的 SSH 配置。

## 6. 主机指纹校验

首次连接或机器人地址变化时，先获取公开指纹：

```bash
ssh-keyscan -T 5 -t ed25519,rsa 机器人IP 2>/dev/null \
  | ssh-keygen -lf -
```

本次实机 ED25519 指纹为：

```text
SHA256:zru6ibeuztJOPDxB9mSz78mwdZmBwzuC0WsCBGSxTVs
```

如果出现 `Host key verification failed`，不能直接使用 `StrictHostKeyChecking=no` 绕过校验。应先判断：

1. 机器人是否重装过系统；
2. IP 是否被其他设备占用；
3. 当前公开指纹是否与现场确认的机器人一致；
4. 本地 `known_hosts` 是否以旧主机名保存了同一密钥。

只有完成设备身份确认后，才可以更新对应的 `known_hosts` 记录。

## 7. 登录后的只读校准

每次开始远程调试，先执行：

```bash
hostname
whoami
date
uname -a
pwd
```

确认工作区和项目目录：

```bash
test -d /home/ubuntu/ros2_ws && echo ROS2_WS_PRESENT
test -d /home/ubuntu/teams/ctrlteam/grape_robot && echo PROJECT_PRESENT
```

查看已有 ROS2 进程，避免重复启动：

```bash
ps -eo pid,comm,args \
  | grep -E '[r]os2|[c]omponent_container|[t]rack_and_grab|[s]tart_app_node'
```

加载环境后执行只读 ROS2 查询：

```bash


```

这些命令只查询 ROS2 图，不调用服务、不发布消息。

## 8. 接口取证命令

以下命令用于确认当前代码依赖的真实接口：

```bash
ros2 topic info -v /servo_controller
ros2 topic info -v /gemini_camera/rgb/image_raw
ros2 topic info -v /gemini_camera/depth/image_raw
ros2 topic info -v /gemini_camera/depth/camera_info

ros2 service type /kinematics/get_current_pose
ros2 service type /kinematics/set_pose_target

ros2 interface show servo_controller_msgs/msg/ServosPosition
ros2 interface show kinematics_msgs/srv/GetRobotPose
ros2 interface show kinematics_msgs/srv/SetRobotPose
```

`ros2 interface show` 只显示类型定义。不要为了验证字段而调用动作服务。

本次取证还确认：

- RGB 为 `640×480`、`rgb8`；
- 深度为 `640×400`、`16UC1`；
- RGB 与深度图尺寸不同；
- RGB-D 空间映射是否可靠仍为 `UNKNOWN`。

在完成 RGB-D 对齐验证前，只允许检测和数据显示，不允许根据当前深度结果触发机械臂动作。

## 9. 代码一致性检查

项目主目录是主版本：

```text
/home/ubuntu/teams/ctrlteam/grape_robot
```

ROS2 工作区中的代码是运行副本：

```text
/home/ubuntu/ros2_ws/src/example/example/rgbd_function
```

本地修改或上传前，先比较哈希：

```bash
sha256sum \
  ~/teams/ctrlteam/grape_robot/code/track_and_grab.py \
  ~/teams/ctrlteam/grape_robot/launch/track_and_grab.launch.py \
  ~/teams/ctrlteam/grape_robot/scripts/run_vision.sh \
  ~/ros2_ws/src/example/example/rgbd_function/track_and_grab.py \
  ~/ros2_ws/src/example/example/rgbd_function/track_and_grab.launch.py
```

2026-07-14 本次检查中，本地仓库、机器人项目主目录和 ROS2 运行副本的核心代码哈希一致，因此没有执行上传或覆盖。

## 10. 安全调试流程

推荐顺序：

```text
本地修改和离线测试
-> 显式列出上传文件白名单
-> 上传到机器人 /tmp
-> 比较差异并备份项目主目录旧文件
-> 更新机器人项目主目录
-> Python 语法和导入检查
-> 编译指定 ROS2 包
-> enable_arm=false 检测-only 验证
-> 保存日志和回滚记录
```

禁止直接把临时改动留在 `~/ros2_ws/src/` 中作为最终版本，因为运行脚本可能再次用项目主目录覆盖它。

上传前先使用只显示差异的预演：

```bash
rsync -avhn --itemize-changes \
  本地白名单目录/ \
  ubuntu@机器人IP:/tmp/grape-robot-stage/
```

确认预演只包含白名单文件后，再由任务负责人明确授权实际同步。模型、大型数据集和 rosbag 不应随代码目录批量上传。

## 11. 远程调试停止条件

出现以下任一情况立即停止：

- 机器人身份或主机指纹无法确认；
- 当前运行代码与审查版本哈希不一致；
- 已有多个可能控制同一执行器的节点，且互斥关系未知；
- RGB 与深度尺寸不一致但没有经过验证的映射；
- ROS2 类型、字段、单位或坐标方向为 `UNKNOWN`；
- 需要停止服务、启动节点或写机器人文件，但本轮没有明确授权；
- 现场人员无法立即停止机器人。

停止后保留完整命令、输出、日期、设备地址、Git commit 和未验证项，再决定下一步。

## 12. 故障排查

### `ubuntu.local` 无法解析

在机器人本机查看真实 Wi-Fi 地址，改用 `ssh ubuntu@机器人IP`。

### TCP 22 超时

检查两台设备是否真的处于同一网段、机器人 SSH 服务是否在线，以及 IP 是否已经变化。

### `Permission denied (publickey,password)`

依次检查：

1. 公钥是否完整写入 `/home/ubuntu/.ssh/authorized_keys`；
2. 登录用户是否为 `ubuntu`；
3. `~/.ssh` 权限是否为 `700`；
4. `authorized_keys` 权限是否为 `600`；
5. 本机是否指定了 `roslander_ed25519`；
6. 加密私钥是否已经由 `ssh-add` 解锁。

不要尝试猜密码，也不要把密码或私钥发到聊天中。

### 服务器接受公钥但仍拒绝登录

如果 SSH 调试输出显示 `Server accepts key`，随后仍失败，通常表示本机私钥没有完成签名。先在本地执行：

```bash
ssh-add --apple-use-keychain ~/.ssh/roslander_ed25519
```

然后重新连接。

## 13. 本次未验证内容

- 机器人 IP 是否会长期保持 `10.248.67.8`；
- SSH 服务端完整配置及密码登录策略；
- RGB-D 驱动是否提供已启用的硬件对齐；
- 深度单位和全部无效值规则；
- 多个 `/servo_controller` 发布者之间的互斥机制；
- 任何底盘、机械臂、夹爪或采摘动作。

上述内容在获得新的实机证据前保持 `UNKNOWN`，不得作为实现前提。
