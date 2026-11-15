"""Ponto de entrada principal para empacotamento (PyInstaller / Nuitka) em Windows e Linux."""

from __future__ import annotations

import multiprocessing
import sys

# Importações explícitas para garantir que empacotadores (PyInstaller/Nuitka)
# incluam os módulos carregados dinamicamente nos subprocessos e os kernels Cython
import optical_networking_gym_v2  # noqa: F401
import optical_networking_gym_v2.heuristics.masked_heuristics  # noqa: F401
import optical_networking_gym_v2.heuristics.runtime_heuristics  # noqa: F401
import optical_networking_gym_v2.optical.kernels.allocation_kernel  # noqa: F401
import optical_networking_gym_v2.optical.kernels.qot_kernel  # noqa: F401
import optical_networking_gym_v2.simulation._request_analysis_kernels  # noqa: F401
from optical_networking_gym_v2.gui import launch_gui


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(launch_gui())
