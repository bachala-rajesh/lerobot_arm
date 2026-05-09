import scservo_sdk as scs

PORT = '/dev/lerobot_follower'
SIGN_BIT = 11

ph = scs.PortHandler(PORT)
pkt = scs.PacketHandler(0)
ph.openPort()
ph.setBaudRate(1000000)

joints = {1:'shoulder_pan', 2:'shoulder_lift', 3:'elbow_flex',
        4:'wrist_flex',   5:'wrist_roll',    6:'gripper'}

input("Position ALL joints at HOME (0 rad pose), then press Enter...")

print("\n--- Paste these values into your URDF ---\n")
for id, name in joints.items():
    eeprom_raw, _, _ = pkt.read2ByteTxRx(ph, id, 31)
    present,    _, _ = pkt.read2ByteTxRx(ph, id, 56)

    # decode sign-magnitude (sign bit 11)
    sign      = (eeprom_raw >> SIGN_BIT) & 1
    magnitude = eeprom_raw & ((1 << SIGN_BIT) - 1)
    decoded   = -magnitude if sign else magnitude

    # Feetech formula: present = raw_encoder - eeprom_offset
    raw_home  = (present + decoded) % 4096

    # driver needs servo to report 2048 at home
    new_offset = raw_home - 2048

    print(f'  <param name="id">{id}</param>')
    print(f'  <param name="homing_offset">{new_offset}</param>   <!-- {name} -->')
    print()

ph.closePort()
