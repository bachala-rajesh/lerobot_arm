"""
LESSON 3 — Compute the correct homing offset at home pose
==========================================================
BEFORE RUNNING THIS SCRIPT:
  • Physically move the arm to your defined home pose and hold it still.
  • The arm must not move while this script reads the servos.

The formula (derived from two equations):

    Formula 1:  present  = raw_encoder - current_offset
    Formula 2:  2048     = raw_encoder - new_offset

    Solving:    new_offset = present + current_offset - 2048

Where:
    present        = register 56  (what the servo reports right now)
    current_offset = register 31  (decoded from sign-magnitude)
    2048           = the value we want the servo to report at home
                     so that the driver sees 0 radians

This script does NOT write anything to the servo.
It only reads and computes.  Output it ready to paste into the YAML.
"""

import argparse
import scservo_sdk as scs

PORTS  = {'leader': '/dev/lerobot_leader', 'follower': '/dev/lerobot_follower'}
JOINTS = {1: 'shoulder_pan', 2: 'shoulder_lift', 3: 'elbow_flex',
          4: 'wrist_flex',   5: 'wrist_roll',    6: 'gripper'}

REG_HOMING_OFFSET = 31
REG_PRESENT_POS   = 56
SIGN_BIT          = 11


def decode_sign_magnitude(raw: int) -> int:
    sign      = (raw >> SIGN_BIT) & 1
    magnitude = raw & ((1 << SIGN_BIT) - 1)
    return -magnitude if sign else magnitude


parser = argparse.ArgumentParser()
parser.add_argument('--arm', choices=['leader', 'follower'], required=True,
                    help='Which arm to compute offsets for')
args = parser.parse_args()

ph  = scs.PortHandler(PORTS[args.arm])
pkt = scs.PacketHandler(0)
ph.openPort()
ph.setBaudRate(1_000_000)

print(f'\n{"─"*65}')
print(f'  Arm: {args.arm}   — arm must be at home pose right now')
print(f'{"─"*65}')
print(f'  {"Joint":<16}  {"present":>8}  {"cur_off":>8}  {"new_off":>8}')
print(f'{"─"*65}')

results = {}
for servo_id, name in JOINTS.items():
    raw_reg,  _, _ = pkt.read2ByteTxRx(ph, servo_id, REG_HOMING_OFFSET)
    present,  _, _ = pkt.read2ByteTxRx(ph, servo_id, REG_PRESENT_POS)

    current_offset = decode_sign_magnitude(raw_reg)
    new_offset     = present + current_offset - 2048

    results[name] = new_offset
    print(f'  {name:<16}  {present:>8}  {current_offset:>+8}  {new_offset:>+8}')

print(f'{"─"*65}')

print(f'\nPaste this into src/so101_bringup/config/so101_{args.arm}_calibration.yaml:\n')
print('joints:')
for name, new_off in results.items():
    servo_id = [k for k, v in JOINTS.items() if v == name][0]
    print(f'  {name}:')
    print(f'    id: {servo_id}')
    print(f'    homing_offset: {new_off}')

ph.closePort()
