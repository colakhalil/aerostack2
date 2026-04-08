"""Launch SLAM wrapper node."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for slam_wrapper_node."""
    pkg_dir = get_package_share_directory('as2_slam_wrapper')
    default_config = os.path.join(pkg_dir, 'config', 'slam_wrapper_config.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'namespace',
            default_value='drone0',
            description='Drone namespace.'),
        DeclareLaunchArgument(
            'config_file',
            default_value=default_config,
            description='SLAM wrapper config file.'),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            choices=['true', 'false'],
            description='Use simulation time.'),

        Node(
            package='as2_slam_wrapper',
            executable='slam_wrapper_py',
            namespace=LaunchConfiguration('namespace'),
            output='screen',
            parameters=[
                LaunchConfiguration('config_file'),
                {'use_sim_time': LaunchConfiguration('use_sim_time')},
            ],
        ),
    ])
