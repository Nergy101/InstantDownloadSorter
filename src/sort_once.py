#!/usr/bin/env python3
"""One-shot, non-interactive sort: classify and move files, print a summary.

No curses/TUI, so it runs in a plain terminal (including cmd.exe on Windows)
and can be invoked from `make sort` or a cron job. Reuses the sorter's model.
"""
import sys
from pathlib import Path

from InstantSorter import load_config, Sorter


def main():
    try:
        location, folders = load_config()
    except FileNotFoundError as e:
        print("ERROR:", e)
        return 1
    except ValueError as e:
        print("ERROR: settings.json is not valid JSON:", e)
        return 1

    if not Path(location).is_dir():
        print("ERROR: folder does not exist:", location)
        return 1
    if not folders:
        print("ERROR: no Folders configured in settings.json")
        return 1

    sorter = Sorter(location, folders)
    sorter.scan()
    moves, errors = sorter.sort()

    print("Sorted %d file(s) in %s" % (len(moves), location))
    if moves:
        by_folder = {}
        for _src, dst in moves:
            by_folder[Path(dst).parent.name] = by_folder.get(Path(dst).parent.name, 0) + 1
        for folder, n in sorted(by_folder.items()):
            print("  %-15s %d" % (folder, n))
    for e in errors:
        print("  !", e)
    if not moves and not errors:
        print("  Nothing to do.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
