"""Launch Map Merger node."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'drone_namespaces',
            default_value="['drone0', 'drone1']",
            description='List of drone namespaces to merge.'),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            choices=['true', 'false'],
            description='Use simulation time.'),
        DeclareLaunchArgument(
            'voxel_size',
            default_value='0.1',
            description='Voxel size for merged map downsampling.'),
        DeclareLaunchArgument(
            'output_dir',
            default_value='~/aerostack2_maps',
            description='Directory to save merged map files.'),

        Node(
            package='as2_3d_map_manager',
            executable='map_merger_py',
            name='map_merger_node',
            output='screen',
            parameters=[{
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'drone_namespaces': LaunchConfiguration('drone_namespaces'),
                'voxel_size': LaunchConfiguration('voxel_size'),
                'output_dir': LaunchConfiguration('output_dir'),
            }],
        ),
    ])
