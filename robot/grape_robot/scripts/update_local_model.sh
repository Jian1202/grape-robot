#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "用法: $0 /path/to/best.pt [model_name.pt]"
    exit 1
fi

SOURCE_MODEL="$1"
PROJECT="/Users/zhoubochun/program/grape_robot/grape-robot/robot/grape_robot"
ARCHIVE_DIR="$PROJECT/models/archive"

if [[ ! -f "$SOURCE_MODEL" ]]; then
    echo "模型文件不存在: $SOURCE_MODEL"
    exit 1
fi

mkdir -p "$ARCHIVE_DIR"

if [[ $# -eq 2 ]]; then
    MODEL_NAME="$2"
else
    STAMP="$(date +%Y%m%d_%H%M%S)"
    MODEL_NAME="grape_${STAMP}.pt"
fi

if [[ "$MODEL_NAME" != *.pt ]]; then
    MODEL_NAME="${MODEL_NAME}.pt"
fi

TARGET_MODEL="$ARCHIVE_DIR/$MODEL_NAME"

if [[ -e "$TARGET_MODEL" ]]; then
    echo "目标模型已存在: $TARGET_MODEL"
    exit 1
fi

cp "$SOURCE_MODEL" "$TARGET_MODEL"
ln -sfn "archive/$MODEL_NAME" "$PROJECT/models/current.pt"

echo "MODEL_UPDATED"
echo "source: $SOURCE_MODEL"
echo "archive: $TARGET_MODEL"
echo "current: $(readlink "$PROJECT/models/current.pt")"
shasum -a 256 "$PROJECT/models/current.pt"
