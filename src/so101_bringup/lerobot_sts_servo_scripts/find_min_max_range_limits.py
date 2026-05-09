import scservo_sdk as scs

PORT = "/dev/lerobot_follower"
ph = scs.PortHandler(PORT)
pkt = scs.PacketHandler(0)
ph.openPort()
ph.setBaudRate(1000000)

joints = {
    1: "shoulder_pan",
    2: "shoulder_lift",
    3: "elbow_flex",
    4: "wrist_flex",
    5: "wrist_roll",
    6: "gripper",
}

print("\n--- Range calibration ---")
for id, name in joints.items():
    input(f"\nMove {name} to its MINIMUM limit, press Enter...")
    mn, _, _ = pkt.read2ByteTxRx(ph, id, 56)

    input(f"Move {name} to its MAXIMUM limit, press Enter...")
    mx, _, _ = pkt.read2ByteTxRx(ph, id, 56)

    print(f'  <param name="range_min">{min(mn, mx)}</param>')
    print(f'  <param name="range_max">{max(mn, mx)}</param>  <!-- {name} -->')

ph.closePort()
