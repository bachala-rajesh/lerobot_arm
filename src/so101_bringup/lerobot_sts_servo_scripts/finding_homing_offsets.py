import scservo_sdk as scs

ph = scs.PortHandler('/dev/lerobot_follower')
pkt = scs.PacketHandler(0)  # Protocol version 0 for sts/sms series motors
ph.openPort()                                                                            
ph.setBaudRate(1000000)
                                                                                          
names = {1:'shoulder_pan', 2:'shoulder_lift', 3:'elbow_flex',
          4:'wrist_flex',   5:'wrist_roll',    6:'gripper'}                             

for id, name in names.items():
    offset, _, _ = pkt.read2ByteTxRx(ph, id, 31)   # register 31 = homing offset
    pos,    _, _ = pkt.read2ByteTxRx(ph, id, 56)   # register 56 = present position          
    print(f"{name}: EEPROM offset = {offset},  present position = {pos}")                
                                                                                          
ph.closePort() 