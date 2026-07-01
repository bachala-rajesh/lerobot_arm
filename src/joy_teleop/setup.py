import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'joy_teleop'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Bachala Rajesh',
    maintainer_email='bachala_rajesh@outlook.com',
    description='Joystick teleop node for the SO-101 arm — maps gamepad input to TwistStamped delta commands',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'joy_teleop_node = joy_teleop.joy_teleop_node:main',
        ],
    },
)
