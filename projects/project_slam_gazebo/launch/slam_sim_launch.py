"""slam_sim_launch.py — Gazebo + drone bridges in a single launch."""

import json
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
import yaml


def _launch_all(context: LaunchContext):
    """Read config at runtime and return simulation + drone bridge launches."""
    config_file = LaunchConfiguration('simulation_config_file').perform(context)

    # Add project worlds/ dir to GZ_SIM_RESOURCE_PATH so AS2 can find our jinja templates
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    worlds_dir = os.path.join(project_dir, 'worlds')
    existing = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    if worlds_dir not in existing:
        os.environ['GZ_SIM_RESOURCE_PATH'] = worlds_dir + (':' + existing if existing else '')

    gazebo_assets_launch = os.path.join(
        get_package_share_directory('as2_gazebo_assets'), 'launch')

    # 1) Launch Gazebo + spawn + world bridges
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_assets_launch, 'launch_simulation.py')),
        launch_arguments={
            'simulation_config_file': LaunchConfiguration('simulation_config_file'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'headless': LaunchConfiguration('headless'),
        }.items())

    # 2) Read config to get drone names
    if config_file.endswith('.json'):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

    # 3) Launch drone bridges for each drone
    drone_bridges = []
    for drone in config.get('drones', []):
        bridge = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(gazebo_assets_launch, 'drone_bridges.py')),
            launch_arguments={
                'simulation_config_file': LaunchConfiguration('simulation_config_file'),
                'namespace': drone['model_name'],
                'use_sim_time': LaunchConfiguration('use_sim_time'),
            }.items())
        drone_bridges.append(bridge)

    return [simulation] + drone_bridges


def generate_launch_description():
    """Launch Gazebo simulation and drone bridges from a single config file."""
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_config = os.path.join(project_dir, 'config', 'slam_single.json')

    return LaunchDescription([
        DeclareLaunchArgument(
            'simulation_config_file',
            default_value=default_config,
            description='Simulation config file (JSON or YAML).'),
        DeclareLaunchArgument(
            'headless',
            default_value='false',
            choices=['true', 'false'],
            description='Launch Gazebo in headless mode.'),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            choices=['true', 'false'],
            description='Use simulation time.'),
        OpaqueFunction(function=_launch_all),
    ])
