#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="/home/ubuntu/teams/ctrlteam/grape_robot"
WORKSPACE="/home/ubuntu/ros2_ws"
SRC_DIR="$WORKSPACE/src/example/example/rgbd_function"
MODEL="$PROJECT/models/current.pt"
ROS_SETUP="/opt/ros/humble/setup.bash"
ORBBEC_SETUP="/home/ubuntu/third_party/orbbec_ws/install/setup.bash"

CODE_FILE="$PROJECT/code/track_and_grab.py"
LOCALIZATION_FILE="$PROJECT/code/grape_localization.py"
STABILITY_FILE="$PROJECT/code/target_stability.py"
LAUNCH_FILE="$PROJECT/launch/track_and_grab.launch.py"

for file in \
    "$CODE_FILE" \
    "$LOCALIZATION_FILE" \
    "$STABILITY_FILE" \
    "$LAUNCH_FILE" \
    "$MODEL" \
    "$ROS_SETUP" \
    "$ORBBEC_SETUP"; do
    if [[ ! -e "$file" ]]; then
        echo "缺少文件：$file"
        exit 1
    fi
done

echo "[1/6] 同步项目代码到 ROS2 工作空间"
cp "$CODE_FILE" "$SRC_DIR/track_and_grab.py"
cp "$LOCALIZATION_FILE" "$SRC_DIR/grape_localization.py"
cp "$STABILITY_FILE" "$SRC_DIR/target_stability.py"
cp "$LAUNCH_FILE" "$SRC_DIR/track_and_grab.launch.py"

echo "[2/6] 加载 ROS2 与 Orbbec 消息工作空间"
unset COLCON_CURRENT_PREFIX || true
set +u
source "$ROS_SETUP"
source "$ORBBEC_SETUP"
set -u
python3 -c 'from orbbec_camera_msgs.msg import Extrinsics'

echo "[3/6] 检查 Python 语法"
python3 -m py_compile \
"$SRC_DIR/track_and_grab.py" \
"$SRC_DIR/grape_localization.py" \
"$SRC_DIR/target_stability.py" \
"$SRC_DIR/track_and_grab.launch.py"

echo "[4/6] 编译 example 包"
cd "$WORKSPACE"
colcon build --packages-select example --symlink-install

echo "[5/6] 检查现有 App 提供的 RGB-D 输入"
required_topics=(
    /gemini_camera/rgb/image_raw
    /gemini_camera/depth/image_raw
    /gemini_camera/depth/camera_info
    /gemini_camera/rgb/camera_info
    /gemini_camera/depth_to_color
)
topic_list="$(ros2 topic list)"
for topic in "${required_topics[@]}"; do
    if ! grep -Fxq "$topic" <<<"$topic_list"; then
        echo "缺少 RGB-D 输入：$topic"
        echo "检测-only模式不会自动启动相机或控制器"
        exit 1
    fi
done

echo "[6/6] 启动 YOLO 安全视觉模式"
set +u
source "$WORKSPACE/install/setup.bash"
set -u
export need_compile=False

ros2 launch example track_and_grab.launch.py \
    detector:=yolo \
    model_path:="$MODEL" \
    target_class:="${TARGET_CLASS:-ripe_grape}" \
    confidence:="${CONFIDENCE:-0.4}" \
    imgsz:="${IMGSZ:-320}" \
    depth_scale_m_per_unit:="${DEPTH_SCALE_M_PER_UNIT:-0.001}" \
    stability_required_frames:="${STABILITY_REQUIRED_FRAMES:-3}" \
    stability_max_position_delta_m:="${STABILITY_MAX_POSITION_DELTA_M:-0.03}" \
    stability_max_target_age_s:="${STABILITY_MAX_TARGET_AGE_S:-0.2}" \
    include_bringup:=false \
    enable_arm:=false \
    start:=true
