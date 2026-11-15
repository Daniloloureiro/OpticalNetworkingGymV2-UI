"""Permite lançar a GUI via: python -m optical_networking_gym_v2.gui"""

from __future__ import annotations

import multiprocessing
import sys

from . import launch_gui

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(launch_gui())

