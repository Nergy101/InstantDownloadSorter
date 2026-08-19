#!/usr/bin/env python3
"""
Cross-platform helper used by the Makefile.

The Makefile recipes are thin wrappers that invoke this script so that all
platform differences (Python launcher name, missing POSIX tools like grep/sed,
Windows' missing curses module) are handled in Python rather than in shell.
Pure stdlib -- no third-party dependencies required to run this file.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SORTER = os.path.join(ROOT, "src", "InstantSorter.py")
SORT_ONCE = os.path.join(ROOT, "src", "sort_once.py")
REQUIREMENTS = os.path.join(ROOT, "requirements.txt")

TARGETS = {
    "help": "Show this help",
    "run": "Run the sorter (interactive TUI)",
    "sort": "Sort now, non-interactively (no TUI)",
    "install": "Install dependencies (windows-curses on Windows; requirements.txt if present)",
}


def print_help():
    print("Instant Download Sorter -- available targets:\n")
    for name, desc in TARGETS.items():
        print(f"  {name:<8} {desc}")
    print("\nRun any of these with 'make <target>' (macOS, or Git Bash/MSYS2/WSL")
    print("on Windows) or directly with 'python make.py <target>'.")


def install():
    # Install windows-curses on Windows: the curses module used by the app is
    # not bundled with native Windows Python.
    if sys.platform.startswith("win"):
        rc = subprocess.call([sys.executable, "-m", "pip", "install", "windows-curses"])
        if rc != 0:
            return rc
    if not os.path.exists(REQUIREMENTS):
        if not sys.platform.startswith("win"):
            print("No requirements.txt and not on Windows -- no dependencies to install.")
        return 0
    return subprocess.call([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS])


def main():
    cmd = next((a for a in sys.argv[1:] if not a.startswith("-")), "help")
    if cmd == "help":
        print_help()
        return 0
    if cmd == "run":
        os.execv(sys.executable, [sys.executable, SORTER])
        return 0  # not reached
    if cmd == "sort":
        os.execv(sys.executable, [sys.executable, SORT_ONCE])
        return 0  # not reached
    if cmd == "install":
        return install()
    print(f"Unknown target: {cmd}", file=sys.stderr)
    print("Available: help, run, install", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
