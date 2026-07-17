#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="/home/ubuntu/teams/ctrlteam/grape_robot"
WORKSPACE="/home/ubuntu/ros2_ws"
SRC_DIR="$WORKSPACE/src/example/example/rgbd_function"
MODEL="$PROJECT/models/current.pt"

CODE_FILE="$PROJECT/code/track_and_grab.py"
LOCALIZATION_FILE="$PROJECT/code/grape_localization.py"
STABILITY_FILE="$PROJECT/code/target_stability.py"
LAUNCH_FILE="$PROJECT/launch/track_and_grab.launch.py"

for file in "$CODE_FILE" "$LOCALIZATION_FILE" "$STABILITY_FILE" "$LAUNCH_FILE" "$MODEL"; do
    if [[ ! -e "$file" ]]; then
        echo "缺少文件：$file"
        exit 1
    fi
done

echo "[1/5] 同步项目代码到 ROS2 工作空间"
cp "$CODE_FILE" "$SRC_DIR/track_and_grab.py"
cp "$LOCALIZATION_FILE" "$SRC_DIR/grape_localization.py"
cp "$STABILITY_FILE" "$SRC_DIR/target_stability.py"
cp "$LAUNCH_FILE" "$SRC_DIR/track_and_grab.launch.py"

echo "[2/5] 检查 Python 语法"
python3 -m py_compile \
"$SRC_DIR/track_and_grab.py" \
"$SRC_DIR/grape_localization.py" \
"$SRC_DIR/target_stability.py" \
"$SRC_DIR/track_and_grab.launch.py"

echo "[3/5] 编译 example 包"
set +u
source /opt/ros/humble/setup.bash
set -u
cd "$WORKSPACE"
colcon build --packages-select example --symlink-install

echo "[4/5] 停止可能占用相机的 App 服务"
sudo systemctl stop start_app_node.service

restore_app() {
    echo
    echo "[退出] 恢复 App 服务"
    sudo systemctl start start_app_node.service >/dev/null 2>&1 || true
}
trap restore_app EXIT

echo "[5/5] 启动 YOLO 安全视觉模式"
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
    enable_arm:=false \
    start:=true
