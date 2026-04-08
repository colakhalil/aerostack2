"""Launch 3D Map Manager node."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory('as2_3d_map_manager')
    default_config = os.path.join(pkg_dir, 'config', 'map_manager_config.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'namespace',
            default_value='drone0',
            description='Drone namespace.'),
        DeclareLaunchArgument(
            'config_file',
            default_value=default_config,
            description='Map manager config file.'),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            choices=['true', 'false'],
            description='Use simulation time.'),

        Node(
            package='as2_3d_map_manager',
            executable='map_manager_py',
            namespace=LaunchConfiguration('namespace'),
            output='screen',
            parameters=[
                LaunchConfiguration('config_file'),
                {'use_sim_time': LaunchConfiguration('use_sim_time')},
            ],
        ),
    ])
