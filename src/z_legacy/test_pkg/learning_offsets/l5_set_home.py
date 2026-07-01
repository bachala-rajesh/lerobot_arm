"""
LESSON 5 — Compute and write home offsets in one step
======================================================
Combines L3 (compute) and L4 (write) into a single guided workflow.

  Step 1 — Move arm to home pose, press Enter
  Step 2 — Inspect computed offsets, confirm to proceed
  Step 3 — Offsets written to servo EEPROM
  Step 4 — Verification: reads back present positions

Formula used:
    new_offset = present + current_offset - 2048

Column meanings in Step 2 table:
    present  — what register 56 reports right now (target is 2048)
    cur_off  — signed offset currently stored in EEPROM (register 31, decoded)
    new_off  — signed offset that will make present = 2048 at this pose
    encoded  — sign-magnitude encoding of new_off (what physically goes into register 31)
    enc_diff — encoded - new_off (0 for positive offsets; 2048+2*|new_off| for negatives)
               shows how sign-magnitude encoding changes the value before writing
"""

import argparse
import datetime
import os
import time
import scservo_sdk as scs
from ament_index_python.packages import get_package_share_directory

PORTS  = {'leader': '/dev/lerobot_leader', 'follower': '/dev/lerobot_follower'}
JOINTS = {1: 'shoulder_pan', 2: 'shoulder_lift', 3: 'elbow_flex',
          4: 'wrist_flex',   5: 'wrist_roll',    6: 'gripper'}

REG_HOMING_OFFSET = 31
REG_PRESENT_POS   = 56
REG_TORQUE_ENABLE = 40
REG_LOCK          = 55
SIGN_BIT          = 11
PI                = 3.141592653589793
TICKS_PER_DEG     = 4096 / 360.0


def decode_sign_magnitude(raw: int) -> int:
    sign      = (raw >> SIGN_BIT) & 1
    magnitude = raw & ((1 << SIGN_BIT) - 1)
    return -magnitude if sign else magnitude


def encode_sign_magnitude(value: int) -> int:
    if value < 0:
        return (1 << SIGN_BIT) | abs(value)
    return value


def read_joint(pkt, ph, servo_id):
    raw_reg,  _, _ = pkt.read2ByteTxRx(ph, servo_id, REG_HOMING_OFFSET)
    present,   _, _ = pkt.read2ByteTxRx(ph, servo_id, REG_PRESENT_POS)
    cur_off         = decode_sign_magnitude(raw_reg)
    new_off         = present + cur_off - 2048
    encoded         = encode_sign_magnitude(new_off)
    delta           = new_off - cur_off   # ticks the offset will shift; near 0 = no recalibration needed
    return present, cur_off, new_off, encoded, delta


def divider(width=80):
    print('  ' + '─' * width)


parser = argparse.ArgumentParser()
parser.add_argument('--arm', choices=['leader', 'follower'], required=True)
args = parser.parse_args()

ph  = scs.PortHandler(PORTS[args.arm])
pkt = scs.PacketHandler(0)
ph.openPort()
ph.setBaudRate(1_000_000)

# ── Step 1: move arm to home pose ─────────────────────────────────────────────
print()
divider()
print(f'  STEP 1 — SET HOME POSE')
divider()
print(f'  Arm    : {args.arm}')
print(f'  Port   : {PORTS[args.arm]}')
print()
print(f'  ACTION REQUIRED:')
print(f'    Manually move the {args.arm} arm to the home pose.')
print(f'    Hold it firmly — do not let it sag.')
print(f'    Torque will be disabled briefly during the write step.')
print()
input('  Press Enter when the arm is at home pose and you are holding it...')

# ── Step 2: compute offsets and show table (retry loop) ──────────────────────
while True:
    computed = {}
    rows = []
    for servo_id, name in JOINTS.items():
        present, cur_off, new_off, encoded, delta = read_joint(pkt, ph, servo_id)
        computed[servo_id] = (present, cur_off, new_off, encoded)
        rows.append((name, present, cur_off, new_off, encoded, delta))

    print()
    divider()
    print(f'  STEP 2 — COMPUTED OFFSETS  (arm must still be at home pose)')
    divider()
    print(f'  {"Joint":<16}  {"present":>8}  {"cur_off":>8}  {"new_off":>8}  {"encoded":>8}  {"delta":>8}  {"delta_deg":>9}')
    divider()
    for name, present, cur_off, new_off, encoded, delta in rows:
        delta_deg = delta / TICKS_PER_DEG
        print(f'  {name:<16}  {present:>8}  {cur_off:>+8}  {new_off:>+8}  {encoded:>8}  {delta:>+8}  {delta_deg:>+8.2f}°')
    divider()
    print()
    print('  present   — servo reading right now        (target: 2048)')
    print('  cur_off   — signed offset in EEPROM now    (decoded from register 31)')
    print('  new_off   — signed offset to write         = present + cur_off - 2048')
    print('  encoded   — sign-magnitude of new_off      (raw value written to register 31)')
    print('  delta     — new_off - cur_off              (ticks the offset will shift)')
    print('  delta_deg — delta in degrees               (near 0° = no recalibration needed)')
    print()

    choice = input('  Proceed? [y = write / r = reposition and retry / n = abort] : ').strip().lower()
    if choice == 'y':
        break
    elif choice == 'r':
        print()
        divider()
        print('  RETRY — reposition the arm')
        divider()
        print('  Move the arm back to home pose and hold it firmly.')
        input('  Press Enter when ready...')
    else:
        print('  Aborted. Nothing was written.')
        ph.closePort()
        exit(0)

# ── Step 3: write offsets ─────────────────────────────────────────────────────
print()
divider()
print('  STEP 3 — WRITING TO EEPROM  (keep holding the arm)')
divider()
for servo_id, name in JOINTS.items():
    present, cur_off, new_off, encoded = computed[servo_id]

    pkt.write1ByteTxRx(ph, servo_id, REG_TORQUE_ENABLE, 0)       # disable torque
    pkt.write1ByteTxRx(ph, servo_id, REG_LOCK, 0)                # unlock EEPROM
    pkt.write2ByteTxRx(ph, servo_id, REG_HOMING_OFFSET, encoded) # write
    pkt.write1ByteTxRx(ph, servo_id, REG_LOCK, 1)                # lock EEPROM
    time.sleep(0.1)                                               # wait for flash write
    print(f'  {name:<16}  new_off {new_off:>+6}  encoded {encoded:>5}  written ✓')

# ── Step 4: verify ────────────────────────────────────────────────────────────
print()
divider()
print('  STEP 4 — VERIFICATION  (arm must still be at home pose)')
divider()
print(f'  {"Joint":<16}  {"present":>8}  {"offset":>8}  {"err_ticks":>10}  {"err_deg":>8}  {"status":>6}')
divider()

all_ok = True
for servo_id, name in JOINTS.items():
    _, _, new_off_written, _ = computed[servo_id]

    raw_reg, _, _ = pkt.read2ByteTxRx(ph, servo_id, REG_HOMING_OFFSET)
    present,  _, _ = pkt.read2ByteTxRx(ph, servo_id, REG_PRESENT_POS)
    readback       = decode_sign_magnitude(raw_reg)
    err_ticks      = present - 2048
    err_deg        = err_ticks / TICKS_PER_DEG
    status         = '✓ ok' if abs(err_ticks) <= 20 else '! drift'

    if abs(err_ticks) > 20:
        all_ok = False

    print(f'  {name:<16}  {present:>8}  {readback:>+8}  {err_ticks:>+10}  {err_deg:>+7.2f}°  {status:>6}')

divider()

# ── Step 5: save backup to package config directory ───────────────────────────
print()
divider()
print('  STEP 5 — SAVING CALIBRATION BACKUP')
divider()

# ament gives: {workspace}/install/so101_bringup/share/so101_bringup
# 4 levels up  →  workspace root
# then down to: src/so101_bringup/config/calibration_data_backup
pkg_share      = get_package_share_directory('so101_bringup')
workspace_root = os.path.normpath(os.path.join(pkg_share, *(['..'] * 4)))
backup_dir     = os.path.join(workspace_root, 'src', 'so101_bringup', 'config', 'calibration_data_backup')
os.makedirs(backup_dir, exist_ok=True)

now      = datetime.datetime.now()
filename = f'{args.arm}_{now.strftime("%Y-%m-%d_%H-%M-%S")}.yaml'
filepath = os.path.join(backup_dir, filename)

with open(filepath, 'w') as f:
    f.write(f'# Calibration backup\n')
    f.write(f'# Arm  : {args.arm}\n')
    f.write(f'# Date : {now.strftime("%Y-%m-%d %H:%M:%S")}\n')
    f.write('\njoints:\n')
    for servo_id, name in JOINTS.items():
        _, _, new_off, _ = computed[servo_id]
        f.write(f'  {name}:\n')
        f.write(f'    id: {servo_id}\n')
        f.write(f'    homing_offset: {new_off}\n')

print(f'  Saved: {filepath}')
print()

if all_ok:
    print('  All joints within ±20 ticks of 2048. Calibration successful.')
    print()
    print(f'  Next: copy the new_off values into')
    print(f'  src/so101_bringup/config/so101_{args.arm}_calibration.yaml')
    print(f'  then restart ROS2 so the driver writes them on startup.')
else:
    print('  Some joints drifted beyond 20 ticks — arm moved during write.')
    print('  Hold the arm firmly at home pose and run this script again.')

print()
ph.closePort()
