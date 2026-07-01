"""
LESSON 2 — The homing offset register (EEPROM, register 31)
============================================================
What register 56 (Present_Position) actually reports is NOT the raw
magnetic encoder tick.  The servo firmware applies a correction first:

    Present_Position = Raw_Encoder - Homing_Offset

The "Homing_Offset" lives in EEPROM at registers 31 (low byte) and
32 (high byte).  It is a 16-bit sign-magnitude integer:

    • Bit 11  → sign flag  (1 = negative, 0 = positive)
    • Bits 0–10 → magnitude (0 – 2047)

Example:  offset = −1423
    magnitude  = 1423
    sign bit   = 1  → 1 << 11 = 2048
    stored raw = 2048 | 1423 = 3471

Decoding 3471 back:
    bit 11 set? yes  → negative
    magnitude   = 3471 & 2047 = 1423
    decoded     = −1423  ✓

This script:
  1. Reads register 31 (raw 16-bit word) for every joint.
  2. Decodes sign-magnitude → shows the human-readable offset.
  3. Reads register 56 (present position, already offset-corrected).
  4. Back-calculates the raw encoder tick: raw = present + offset.

No writes are made.  This is purely observational.

What to notice when you run it:
  • The "offset" column should match what is in
    src/so101_bringup/config/so101_<arm>_calibration.yaml.
  • "raw_encoder" is the actual magnetic disc position (0–4095).
  • If you move a joint, "present" and "raw_encoder" both change by
    the same amount — the offset itself does not move.
"""

import argparse
import scservo_sdk as scs

PORTS  = {'leader': '/dev/lerobot_leader', 'follower': '/dev/lerobot_follower'}
JOINTS = {1: 'shoulder_pan', 2: 'shoulder_lift', 3: 'elbow_flex',
          4: 'wrist_flex',   5: 'wrist_roll',    6: 'gripper'}

REG_HOMING_OFFSET = 31   # low byte; high byte is 32
REG_PRESENT_POS   = 56
SIGN_BIT          = 11   # bit index used for homing_offset sign


def decode_sign_magnitude(raw: int, sign_bit: int = SIGN_BIT) -> int:
    """Convert the raw 16-bit register value to a signed Python int."""
    sign      = (raw >> sign_bit) & 1
    magnitude = raw & ((1 << sign_bit) - 1)   # lower 11 bits
    return -magnitude if sign else magnitude


parser = argparse.ArgumentParser()
parser.add_argument('--arm', choices=['leader', 'follower'], default='leader')
args = parser.parse_args()

ph  = scs.PortHandler(PORTS[args.arm])
pkt = scs.PacketHandler(0)
ph.openPort()
ph.setBaudRate(1_000_000)

W = 17  # column width

print(f'\n{"─"*75}')
print(f'  Arm: {args.arm}')
print(f'{"─"*75}')
print(f'  {"Joint":<16}  {"raw_reg31":>9}  {"offset":>7}  {"present":>8}  {"raw_encoder":>11}')
print(f'  {"":16}  {"(hex)":>9}  {"(dec)":>7}  {"reg56":>8}  {"=pres+off":>11}')
print(f'{"─"*75}')

for servo_id, name in JOINTS.items():
    raw_reg, _, _  = pkt.read2ByteTxRx(ph, servo_id, REG_HOMING_OFFSET)
    present,  _, _ = pkt.read2ByteTxRx(ph, servo_id, REG_PRESENT_POS)

    offset      = decode_sign_magnitude(raw_reg)
    raw_encoder = (present + offset) % 4096

    print(f'  {name:<16}  {raw_reg:>7} ({raw_reg:#06x})  {offset:>+7}  {present:>8}  {raw_encoder:>11}')

print(f'{"─"*75}')

print("""
Key things to notice:
  • "offset" matches the homing_offset in the calibration YAML.
  • "raw_encoder" is the true magnetic disc position (0–4095).
  • Moving a joint changes both "present" and "raw_encoder" by the
    same amount — the offset stored in EEPROM stays fixed.
  • Two arms with the same PHYSICAL pose will have the same
    "raw_encoder" values but may have different "present" values
    if their offsets differ.  That mismatch is the root cause of
    the leader–follower pose error we are trying to fix.
""")

ph.closePort()
