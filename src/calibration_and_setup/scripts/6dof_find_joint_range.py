#!/usr/bin/env python3
"""Find range_min / range_max for each joint — 6DOF arm (7 servos, wrist_yaw added).

Read-only tool. Move each joint by hand to its two mechanical stops;
script just reads Present_Position (reg 56) at each stop. No EEPROM
write — feetech_ros2_driver pushes range_min/range_max from the yaml
into the servo automatically on every `ros2 launch`, so recording
these numbers in the calibration yaml is enough.

Usage:
    python3 6dof_find_joint_range.py --arm follower
"""
import argparse
import datetime
import os
import scservo_sdk as scs
from ament_index_python.packages import get_package_share_directory

PORTS  = {'leader': '/dev/lerobot_leader', 'follower': '/dev/lerobot_follower'}
JOINTS = {1: 'shoulder_pan', 2: 'shoulder_lift', 3: 'elbow_flex',
          4: 'wrist_flex',   5: 'wrist_yaw',     6: 'wrist_roll', 7: 'gripper'}

REG_PRESENT_POS = 56
TICKS_PER_DEG   = 4096 / 360.0


def read_present(pkt, ph, servo_id):
    present, _, _ = pkt.read2ByteTxRx(ph, servo_id, REG_PRESENT_POS)
    return present


def divider(width=80):
    print('  ' + '─' * width)


parser = argparse.ArgumentParser()
parser.add_argument('--arm', choices=['leader', 'follower'], required=True)
args = parser.parse_args()

ph  = scs.PortHandler(PORTS[args.arm])
pkt = scs.PacketHandler(0)
ph.openPort()
ph.setBaudRate(1_000_000)

print()
divider()
print('  FIND JOINT RANGE  (read-only — no EEPROM write)')
divider()
print(f'  Arm  : {args.arm}')
print(f'  Port : {PORTS[args.arm]}')
print()

results = {}
for servo_id, name in JOINTS.items():
    while True:
        print()
        divider()
        print(f'  JOINT: {name}  (id {servo_id})')
        divider()
        input(f'  Move {name} to its NEGATIVE mechanical stop, then press Enter...')
        neg = read_present(pkt, ph, servo_id)
        input(f'  Now move {name} to its POSITIVE mechanical stop, then press Enter...')
        pos = read_present(pkt, ph, servo_id)

        range_min = min(neg, pos)
        range_max = max(neg, pos)
        span_deg  = (range_max - range_min) / TICKS_PER_DEG

        print(f'  neg={neg}  pos={pos}  ->  range_min={range_min}  range_max={range_max}  span={span_deg:.1f}°')
        choice = input('  Accept? [y = next joint / r = redo this joint / n = abort] : ').strip().lower()
        if choice == 'y':
            results[servo_id] = (range_min, range_max)
            break
        elif choice == 'n':
            print('  Aborted. Nothing was saved.')
            ph.closePort()
            exit(0)
        # 'r' falls through and retries this joint

# ── summary table ──────────────────────────────────────────────────────────
print()
divider()
print('  SUMMARY')
divider()
print(f'  {"Joint":<16}  {"range_min":>10}  {"range_max":>10}  {"span_deg":>9}')
divider()
for servo_id, name in JOINTS.items():
    range_min, range_max = results[servo_id]
    span_deg = (range_max - range_min) / TICKS_PER_DEG
    print(f'  {name:<16}  {range_min:>10}  {range_max:>10}  {span_deg:>8.1f}°')
divider()

# ── save backup ────────────────────────────────────────────────────────────
pkg_share      = get_package_share_directory('calibration_and_setup')
workspace_root = os.path.normpath(os.path.join(pkg_share, *(['..'] * 4)))
backup_dir     = os.path.join(workspace_root, 'src', 'calibration_and_setup', 'config', 'calibration_data_backup')
os.makedirs(backup_dir, exist_ok=True)

now      = datetime.datetime.now()
filename = f'6dof_range_{args.arm}_{now.strftime("%Y-%m-%d_%H-%M-%S")}.yaml'
filepath = os.path.join(backup_dir, filename)

with open(filepath, 'w') as f:
    f.write('# Joint range backup (6DOF)\n')
    f.write(f'# Arm  : {args.arm}\n')
    f.write(f'# Date : {now.strftime("%Y-%m-%d %H:%M:%S")}\n')
    f.write('\njoints:\n')
    for servo_id, name in JOINTS.items():
        range_min, range_max = results[servo_id]
        f.write(f'  {name}:\n')
        f.write(f'    id: {servo_id}\n')
        f.write(f'    range_min: {range_min}\n')
        f.write(f'    range_max: {range_max}\n')

target_file = '6dof_so101_follower_calibration.yaml' if args.arm == 'follower' else 'so101_leader_calibration.yaml'
print()
print(f'  Saved: {filepath}')
print()
print(f'  Next: copy range_min / range_max into')
print(f'  src/calibration_and_setup/config/{target_file}')
print(f'  then restart ROS2 so the driver writes them onto the servos on startup.')
print()

ph.closePort()
