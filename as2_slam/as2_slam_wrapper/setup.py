"""Setup for as2_slam_wrapper Python modules."""
from setuptools import setup

package_name = 'as2_slam_wrapper'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    install_requires=['setuptools'],
    entry_points={
        'console_scripts': [
            'slam_wrapper_py = as2_slam_wrapper.slam_wrapper_node:main',
        ],
    },
)
