#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="/home/ubuntu/teams/ctrlteam/grape_robot"
WORKSPACE="/home/ubuntu/ros2_ws"
ROS_SETUP="/opt/ros/humble/setup.bash"
WORKSPACE_SETUP="$WORKSPACE/install/setup.bash"
CODE_DIR="$PROJECT/code"
ENTRY="$CODE_DIR/basic_fixed_pick.py"

MODE="${1:-inspect}"
shift || true

if [[ "$MODE" != "inspect" && "$MODE" != "capture" && "$MODE" != "execute" ]]; then
    echo "模式只能是 inspect、capture 或 execute"
    exit 2
fi

for file in "$ROS_SETUP" "$WORKSPACE_SETUP" "$ENTRY" "$CODE_DIR/basic_pick_plan.py"; do
    if [[ ! -e "$file" ]]; then
        echo "缺少文件：$file"
        exit 1
    fi
done

if [[ "$MODE" == "execute" ]]; then
    if [[ -z "${GRAPE_BASIC_PICK_ENABLE:-}" ]]; then
        echo "execute缺少 GRAPE_BASIC_PICK_ENABLE；拒绝动作"
        exit 1
    fi
    if [[ "$#" -lt 2 || "$1" != "--config" ]]; then
        echo "execute必须显式提供 --config 配置文件"
        exit 2
    fi
fi

unset COLCON_CURRENT_PREFIX || true
set +u
source "$ROS_SETUP"
source "$WORKSPACE_SETUP"
set -u

export PYTHONPATH="$CODE_DIR${PYTHONPATH:+:$PYTHONPATH}"
exec python3 "$ENTRY" "$MODE" "$@"
