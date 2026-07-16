#!/usr/bin/env python3
"""Scan for a Feetech STS servo's current ID and change it.

Connect exactly ONE servo to the bus before running this.
Two servos sharing an ID will both answer and corrupt the scan.

Usage:
    python3 set_servo_id.py --port /dev/ttyUSB0 --new-id 5
    python3 set_servo_id.py --port /dev/ttyUSB0 --new-id 5 --old-id 1  # skip scan
"""

from __future__ import annotations

import argparse
import sys

import scservo_sdk as scs

SMS_STS_ID = 5
SMS_STS_LOCK = 55
PROTOCOL = 0


def scan_for_id(
    packet_handler: scs.PacketHandler, port_handler: scs.PortHandler, id_range: range
) -> int | None:
    for scs_id in id_range:
        model, comm_result, _ = packet_handler.ping(port_handler, scs_id)
        if comm_result == scs.COMM_SUCCESS:
            print(f"found servo: id={scs_id} model={model}")
            return scs_id
    return None


def set_id(
    packet_handler: scs.PacketHandler,
    port_handler: scs.PortHandler,
    old_id: int,
    new_id: int,
) -> None:
    packet_handler.write1ByteTxRx(
        port_handler, old_id, SMS_STS_LOCK, 0
    )  # unlock eeprom
    result, error = packet_handler.write1ByteTxRx(
        port_handler, old_id, SMS_STS_ID, new_id
    )
    if result != scs.COMM_SUCCESS:
        sys.exit(f"write ID failed: {packet_handler.getTxRxResult(result)}")
    packet_handler.write1ByteTxRx(
        port_handler, new_id, SMS_STS_LOCK, 1
    )  # lock eeprom under new id
    print(f"servo {old_id} -> {new_id} done")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port",
        default="/dev/lerobot_follower",
        help="e.g. /dev/ttyUSB0 or /dev/lerobot_follower",
    )
    parser.add_argument("--baud", type=int, default=1_000_000)
    parser.add_argument("--new-id", type=int, required=True)
    parser.add_argument(
        "--old-id", type=int, default=None, help="skip scan if you already know it"
    )
    parser.add_argument("--scan-max", type=int, default=10, help="scan ids 1..scan-max")
    args = parser.parse_args()

    port_handler = scs.PortHandler(args.port)
    packet_handler = scs.PacketHandler(PROTOCOL)

    if not port_handler.openPort():
        sys.exit(f"failed to open port {args.port}")
    if not port_handler.setBaudRate(args.baud):
        sys.exit(f"failed to set baud {args.baud}")

    try:
        old_id = args.old_id
        if old_id is None:
            print(
                f"scanning ids 1..{args.scan_max} (make sure only ONE servo is on the bus)"
            )
            old_id = scan_for_id(
                packet_handler, port_handler, range(1, args.scan_max + 1)
            )
            if old_id is None:
                sys.exit(
                    "no servo found — check wiring/power/baud, or raise --scan-max"
                )

        if old_id == args.new_id:
            print("old id == new id, nothing to do")
            return

        set_id(packet_handler, port_handler, old_id, args.new_id)
    finally:
        port_handler.closePort()


if __name__ == "__main__":
    main()
