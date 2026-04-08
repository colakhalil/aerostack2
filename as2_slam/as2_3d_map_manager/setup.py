"""Setup for as2_3d_map_manager Python modules."""
from setuptools import setup

package_name = 'as2_3d_map_manager'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    install_requires=['setuptools'],
    entry_points={
        'console_scripts': [
            'map_manager_py = as2_3d_map_manager.map_manager_node:main',
            'map_merger_py = as2_3d_map_manager.map_merger_node:main',
        ],
    },
)
