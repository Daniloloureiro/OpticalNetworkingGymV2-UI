from __future__ import annotations

import importlib.util
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[1] / "heuristics" / "judge_heuristics_load_sweep.py"
_SPEC = importlib.util.spec_from_file_location(
    "optical_networking_gym_v2_examples_heuristics_judge_heuristics_load_sweep",
    _MODULE_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"could not load example module at {_MODULE_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

JudgeEpisodeCase = _MODULE.JudgeEpisodeCase
JudgeHeuristicLoadSweepExperiment = _MODULE.JudgeHeuristicLoadSweepExperiment
JudgeHeuristicLoadSweepOutputs = _MODULE.JudgeHeuristicLoadSweepOutputs
POLICY_NAMES = _MODULE.POLICY_NAMES
DEFAULT_LOADS = _MODULE.DEFAULT_LOADS
build_base_scenario = _MODULE.build_base_scenario
build_env = _MODULE.build_env
build_episode_scenario = _MODULE.build_episode_scenario
build_parser = _MODULE.build_parser
main = _MODULE.main
run_episode_case = _MODULE.run_episode_case
run_load_sweep = _MODULE.run_load_sweep
run_single_episode = _MODULE.run_single_episode


__all__ = [
    "DEFAULT_LOADS",
    "JudgeEpisodeCase",
    "JudgeHeuristicLoadSweepExperiment",
    "JudgeHeuristicLoadSweepOutputs",
    "POLICY_NAMES",
    "build_base_scenario",
    "build_env",
    "build_episode_scenario",
    "build_parser",
    "main",
    "run_episode_case",
    "run_load_sweep",
    "run_single_episode",
]


if __name__ == "__main__":
    main()
