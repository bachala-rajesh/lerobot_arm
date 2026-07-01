"""
LESSON 4 — Write homing offsets directly to servo EEPROM
=========================================================
This script writes the offsets computed by L3 into the servo EEPROM.
After writing, run L3 again — every joint should show present ≈ 2048
and new_off ≈ 0 (meaning no further correction needed).

Writing sequence per joint:
  1. Disable torque         (register 40 = 0)
  2. Unlock EEPROM          (register 55 = 0)
  3. Write homing_offset    (register 31, sign-magnitude encoded)
  4. Lock EEPROM            (register 55 = 1)

EEPROM must be unlocked before writing register 31.
Without step 2, the write is silently ignored by the servo.
"""

import argparse
import time
import scservo_sdk as scs

PORTS  = {'leader': '/dev/lerobot_leader', 'follower': '/dev/lerobot_follower'}
JOINTS = {1: 'shoulder_pan', 2: 'shoulder_lift', 3: 'elbow_flex',
          4: 'wrist_flex',   5: 'wrist_roll',    6: 'gripper'}

REG_TORQUE_ENABLE = 40
REG_HOMING_OFFSET = 31
REG_LOCK          = 55
SIGN_BIT          = 11

# ── Edit these values (output of L3) ──────────────────────────────────────────
NEW_OFFSETS = {
    'leader': {
        1: +1902,   # shoulder_pan
        2: +1087,   # shoulder_lift
        3: -1207,   # elbow_flex
        4: -1054,   # wrist_flex
        5: -1690,   # wrist_roll
        6:  +248,   # gripper
    },
    'follower': {
        # paste follower values from L3 here when ready
    },
}
# ──────────────────────────────────────────────────────────────────────────────


def encode_sign_magnitude(value: int, sign_bit: int = SIGN_BIT) -> int:
    """Convert signed int to sign-magnitude for EEPROM write."""
    if value < 0:
        return (1 << sign_bit) | abs(value)
    return value


def decode_sign_magnitude(raw: int, sign_bit: int = SIGN_BIT) -> int:
    """Decode sign-magnitude back to signed int (for verification)."""
    sign      = (raw >> sign_bit) & 1
    magnitude = raw & ((1 << sign_bit) - 1)
    return -magnitude if sign else magnitude


parser = argparse.ArgumentParser()
parser.add_argument('--arm', choices=['leader', 'follower'], default='leader')
args = parser.parse_args()

offsets = NEW_OFFSETS[args.arm]
if not offsets:
    print(f'No offsets defined for {args.arm}. Edit NEW_OFFSETS in this script first.')
    exit(1)

ph  = scs.PortHandler(PORTS[args.arm])
pkt = scs.PacketHandler(0)
ph.openPort()
ph.setBaudRate(1_000_000)

# Show what we are about to write and ask for confirmation
print(f'\n{"─"*55}')
print(f'  About to write to: {args.arm}  ({PORTS[args.arm]})')
print(f'{"─"*55}')
print(f'  {"Joint":<16}  {"new_offset":>10}  {"encoded":>8}')
print(f'{"─"*55}')
for servo_id, name in JOINTS.items():
    if servo_id not in offsets:
        continue
    val     = offsets[servo_id]
    encoded = encode_sign_magnitude(val)
    print(f'  {name:<16}  {val:>+10}  {encoded:>8}')
print(f'{"─"*55}')

confirm = input('\nWrite these offsets to EEPROM? [y/N] ').strip().lower()
if confirm != 'y':
    print('Aborted.')
    ph.closePort()
    exit(0)

# Write
print()
for servo_id, name in JOINTS.items():
    if servo_id not in offsets:
        continue

    val     = offsets[servo_id]
    encoded = encode_sign_magnitude(val)

    pkt.write1ByteTxRx(ph, servo_id, REG_TORQUE_ENABLE, 0)   # disable torque
    pkt.write1ByteTxRx(ph, servo_id, REG_LOCK, 0)            # unlock EEPROM
    pkt.write2ByteTxRx(ph, servo_id, REG_HOMING_OFFSET, encoded)  # write offset
    pkt.write1ByteTxRx(ph, servo_id, REG_LOCK, 1)            # lock EEPROM

    # Servo needs time to finish internal flash write before it can respond
    time.sleep(0.1)

    # Read back and verify
    raw_back, result, _ = pkt.read2ByteTxRx(ph, servo_id, REG_HOMING_OFFSET)
    if result != scs.COMM_SUCCESS:
        print(f'  {name:<16}  written {val:>+6}   readback: FAILED (comm error)')
        continue
    readback = decode_sign_magnitude(raw_back)
    status   = '✓' if readback == val else f'✗ got {readback}'
    print(f'  {name:<16}  written {val:>+6}   readback: {readback:>+6}  {status}')

print(f'\nDone. Now run L3 again — present should be ~2048 for every joint.')
ph.closePort()
