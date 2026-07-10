import os
from ament_index_python.packages import get_package_share_directory

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch import LaunchDescription, LaunchService
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, OpaqueFunction

def launch_setup(context):
    compiled = os.environ['need_compile']
    start = LaunchConfiguration('start', default='true')
    start_arg = DeclareLaunchArgument('start', default_value=start)
    color = LaunchConfiguration('color', default='green')
    color_arg = DeclareLaunchArgument('color', default_value=color)

    detector = LaunchConfiguration('detector', default='yolo')
    detector_arg = DeclareLaunchArgument('detector', default_value=detector)
    model_path = LaunchConfiguration(
        'model_path',
        default='/home/ubuntu/grape-yolo/models/grape_v2_best.pt'
    )
    model_path_arg = DeclareLaunchArgument('model_path', default_value=model_path)
    target_class = LaunchConfiguration('target_class', default='ripe_grape')
    target_class_arg = DeclareLaunchArgument('target_class', default_value=target_class)
    confidence = LaunchConfiguration('confidence', default='0.4')
    confidence_arg = DeclareLaunchArgument('confidence', default_value=confidence)
    imgsz = LaunchConfiguration('imgsz', default='320')
    imgsz_arg = DeclareLaunchArgument('imgsz', default_value=imgsz)
    enable_arm = LaunchConfiguration('enable_arm', default='false')
    enable_arm_arg = DeclareLaunchArgument('enable_arm', default_value=enable_arm)
    if compiled == 'True':
        controller_package_path = get_package_share_directory('controller')
        peripherals_package_path = get_package_share_directory('peripherals')
    else:
        controller_package_path = '/home/ubuntu/ros2_ws/src/driver/controller'
        peripherals_package_path = '/home/ubuntu/ros2_ws/src/peripherals'
    depth_camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(peripherals_package_path, 'launch/depth_camera.launch.py')),
    )
    controller_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(controller_package_path, 'launch/controller.launch.py')),
    )

    track_and_grab_node = Node(
        package='example',
        executable='track_and_grab',
        output='screen',
        parameters=[
            {'color': color},
            {'start': ParameterValue(start, value_type=bool)},
            {'detector': detector},
            {'model_path': model_path},
            {'target_class': target_class},
            {'confidence': ParameterValue(confidence, value_type=float)},
            {'imgsz': ParameterValue(imgsz, value_type=int)},
            {'enable_arm': ParameterValue(enable_arm, value_type=bool)},
        ]
    )

    return [start_arg,
            color_arg,
            detector_arg,
            model_path_arg,
            target_class_arg,
            confidence_arg,
            imgsz_arg,
            enable_arm_arg,
            depth_camera_launch,
            controller_launch,
            track_and_grab_node,
            ]

def generate_launch_description():
    return LaunchDescription([
        OpaqueFunction(function = launch_setup)
    ])

if __name__ == '__main__':
    # 创建一个LaunchDescription对象(create a LaunchDescription object)
    ld = generate_launch_description()

    ls = LaunchService()
    ls.include_launch_description(ld)
    ls.run()
