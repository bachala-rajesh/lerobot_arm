"""
LESSON 1 — Raw encoder readings
================================
The Feetech STS3215 servo has a 12-bit magnetic encoder.
It produces a number from 0 to 4095 for one full revolution (360°).

Register 56 = Present_Position
  - This is what the servo is currently reporting as its position.
  - Range: 0 to 4095
  - One full turn = 4096 steps
  - Resolution: 360 / 4096 ≈ 0.088° per step

At this stage we read the RAW value — no calibration, no offset applied.
Whatever number the encoder physically sees right now is what we print.
"""

import argparse
import scservo_sdk as scs
import time 

PORTS    = {'leader': '/dev/lerobot_leader', 'follower': '/dev/lerobot_follower'}
JOINTS   = {1: 'shoulder_pan', 2: 'shoulder_lift', 3: 'elbow_flex',
            4: 'wrist_flex',   5: 'wrist_roll',    6: 'gripper'}
MAX_TICKS = 4096   # 12-bit encoder: 0 – 4095
DEG_PER_TICK = 360.0 / MAX_TICKS   # ≈ 0.0879°

parser = argparse.ArgumentParser()
parser.add_argument('--arm', choices=['leader', 'follower'], default='leader')
args = parser.parse_args()

ph = scs.PortHandler(PORTS[args.arm])
pkt = scs.PacketHandler(0)
ph.openPort()
ph.setBaudRate(1_000_000)

print(f'\n{"─"*55}')
print(f'  Arm: {args.arm}   (register 56 = Present_Position)')
print(f'{"─"*55}')
print(f'  {"Joint":<16}  {"Raw (0–4095)":>12}  {"Angle (°)":>10}')
print(f'{"─"*55}')


while True:
    for servo_id, name in JOINTS.items():
        raw, _, _ = pkt.read2ByteTxRx(ph, servo_id, 56)
        angle_deg = raw * DEG_PER_TICK
        print(f'  {name:<16}  {raw:>12}  {angle_deg:>9.2f}°')
    print()
    print(f'{"─"*55}')
    time.sleep(0.5)

print(f'{"─"*55}')
print("""
Key things to notice:
  • The raw value has nothing to do with "home" or "zero" yet.
  • Moving the joint changes the raw value by ~11 ticks per degree.
  • The same physical pose can give a very different raw value on two
    different arms because the encoder disc can sit at any position
    when the servo is assembled. That is exactly what homing_offset fixes.
""")

ph.closePort()
