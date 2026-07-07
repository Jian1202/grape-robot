from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='example',
            executable='grape_track_grab',        # 注意：必须和你的 .py 文件名（去掉.py）一致
            name='grape_track_grab_node',
            output='screen',
            emulate_tty=True,                     # 让终端输出彩色日志
            parameters=[
                {'start': True},                  # 启动后自动开始检测
                # {'color': 'purple'}             # 可选：默认颜色（可选）
            ],
            arguments=['--ros-args', '--log-level', 'info']
        )
    ])
