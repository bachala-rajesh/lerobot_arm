import scservo_sdk as scs
import time

ph = scs.PortHandler('/dev/lerobot_follower')
pkt = scs.PacketHandler(0)
ph.openPort()
ph.setBaudRate(1000000)

for id in range(1, 7):
    level, _, _ = pkt.read1ByteTxRx(ph, id, 8)
    if level != 2:
        print(f"ID {id}: fixing Return_Level (currently {level})...")
        pkt.write1ByteTxRx(ph, id, 55, 0)   # unlock EEPROM
        time.sleep(0.05)
        pkt.write1ByteTxRx(ph, id, 8, 2)    # Return_Level = 2
        time.sleep(0.05)
        pkt.write1ByteTxRx(ph, id, 55, 1)   # lock EEPROM
        time.sleep(0.05)
        level, _, _ = pkt.read1ByteTxRx(ph, id, 8)
        print(f"ID {id}: Return_Level now = {level}")
    else:
        print(f"ID {id}: already OK (Return_Level=2)")

ph.closePort()
