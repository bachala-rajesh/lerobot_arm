from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'so101_control'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'resource'), glob('resource/*.xml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Bachala Rajesh',
    maintainer_email='bachala_rajesh@outlook.com',
    description='ros2_control YAML configs and controller launch files for the SO-101 arm',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
        ],
    },
)
