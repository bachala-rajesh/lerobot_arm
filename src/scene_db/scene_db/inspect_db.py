#!/usr/bin/env python3
"""CLI to inspect the scene_db SQLite file.

Usage:
    ros2 run scene_db inspect_db                 # show 20 most recent
    ros2 run scene_db inspect_db --label "door"  # filter by label
    ros2 run scene_db inspect_db --pending       # rows still missing 3D
    ros2 run scene_db inspect_db --count         # total + pending counts
    ros2 run scene_db inspect_db --clear         # delete every row
    ros2 run scene_db inspect_db --db /tmp/x.db  # custom db file
"""
from __future__ import annotations

import argparse
import sys
import time

from scene_db import DEFAULT_DB_PATH, Detection, SceneDB


def _fmt_age(t: float) -> str:
    age = time.time() - t
    if age < 60:
        return f"{age:5.1f}s ago"
    if age < 3600:
        return f"{age/60:5.1f}m ago"
    return f"{age/3600:5.1f}h ago"


def _print_rows(rows: list[Detection]) -> None:
    if not rows:
        print("(no rows)")
        return

    header = (
        f"{'ID':>4}  {'LABEL':<22}  {'BBOX (x1,y1,x2,y2)':<22}  "
        f"{'WORLD (x,y,z)':<28}  {'AGE':>11}  DETECTOR"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        bbox_str = f"({r.bbox[0]},{r.bbox[1]},{r.bbox[2]},{r.bbox[3]})"
        if r.world_xyz is None:
            world_str = "(pending)"
        else:
            wx, wy, wz = r.world_xyz
            world_str = f"({wx:+.3f},{wy:+.3f},{wz:+.3f})"
        print(
            f"{r.id:>4}  {r.label[:22]:<22}  {bbox_str:<22}  "
            f"{world_str:<28}  {_fmt_age(r.detected_at):>11}  "
            f"{r.detector or '-'}"
        )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Inspect the scene_db SQLite file.")
    p.add_argument("--db", default=str(DEFAULT_DB_PATH),
                   help=f"Path to db file (default: {DEFAULT_DB_PATH}).")
    p.add_argument("--limit", type=int, default=20, help="Max rows to print.")
    p.add_argument("--label", type=str, default=None, help="Filter by label.")
    p.add_argument("--pending", action="store_true",
                   help="Show rows that still need 3D localization.")
    p.add_argument("--count", action="store_true",
                   help="Print total and pending counts then exit.")
    p.add_argument("--clear", action="store_true",
                   help="Delete every row. Asks for confirmation.")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    with SceneDB(args.db) as db:
        print(f"DB: {db.path}\n")

        if args.clear:
            total, _ = db.count()
            confirm = input(f"Delete all {total} rows? [y/N] ").strip().lower()
            if confirm == "y":
                db.clear()
                print("Cleared.")
            else:
                print("Aborted.")
            return

        if args.count:
            total, pending = db.count()
            print(f"total rows  : {total}")
            print(f"pending 3D  : {pending}")
            return

        if args.pending:
            rows = db.list_pending(limit=args.limit)
        elif args.label:
            rows = db.query_by_label(args.label, limit=args.limit)
        else:
            rows = db.query_recent(limit=args.limit)

        _print_rows(rows)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
