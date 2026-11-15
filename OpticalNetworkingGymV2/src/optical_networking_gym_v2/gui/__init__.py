"""
Optical Networking Gym — Interface Gráfica Profissional.

Módulo GUI baseado em PySide6 para configuração, execução e
visualização de simulações de redes ópticas.

Uso:
    python -m optical_networking_gym_v2.gui
    
Ou programaticamente:
    from optical_networking_gym_v2.gui import launch_gui
    launch_gui()
"""

from __future__ import annotations


def launch_gui(argv: list[str] | None = None) -> int:
    """Inicia a interface gráfica do simulador.

    Parameters
    ----------
    argv : list[str] | None
        Argumentos de linha de comando. Se None, usa sys.argv.

    Returns
    -------
    int
        Código de saída da aplicação.
    """
    import multiprocessing
    import sys

    multiprocessing.freeze_support()

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont

    from .app import MainWindow
    from .theme import apply_theme

    if argv is None:
        argv = sys.argv

    # Habilitar High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(argv)
    app.setApplicationName("Optical Networking Gym")
    app.setOrganizationName("UFPA")
    app.setApplicationVersion("2.0.0")

    # Aplicar tema claro profissional por padrão
    apply_theme(app, theme="light")

    # Fonte padrão
    font = QFont("Inter", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)

    window = MainWindow()
    if "--self-test" in argv:
        import tempfile
        from pathlib import Path
        from PySide6.QtCore import QTimer
        from .controllers.simulation_runner import SimulationRunner
        from .controllers.results_manager import ResultsManager
        from .models.run_config import RunConfig, RunMode

        cfg = RunConfig(
            scenario_id="self_test",
            topology_id="nobel-eu",
            episode_length=50,
            episodes_per_point=1,
            seed=10,
            mode=RunMode.SINGLE,
            heuristic_ids=["select_first_fit_action"],
            num_workers=1,
        )
        test_runner = SimulationRunner()
        test_results_mgr = ResultsManager()
        exit_code = {"value": 1}

        def _on_finished(results: list[dict]) -> None:
            try:
                assert len(results) == 1, f"Expected 1 result, got {len(results)}"
                assert results[0].get("status") == "success", results[0].get("error")
                with tempfile.TemporaryDirectory() as tmpdir:
                    test_results_mgr.set_results(results)
                    paths = test_results_mgr.save_pair_in_directory(Path(tmpdir))
                    assert len(paths) == 2
                    assert paths[0].exists() and paths[1].exists()
                exit_code["value"] = 0
                print("SELF-TEST OK:", results[0]["policy"], results[0]["processed"])
            except Exception as exc:
                print(f"SELF-TEST FAILED: {exc}", file=sys.stderr)
                exit_code["value"] = 1
            finally:
                app.quit()

        def _on_error(msg: str) -> None:
            print(f"SELF-TEST RUNNER ERROR: {msg}", file=sys.stderr)
            exit_code["value"] = 1
            app.quit()

        test_runner.sweep_finished.connect(_on_finished)
        test_runner.error_occurred.connect(_on_error)
        QTimer.singleShot(0, lambda: test_runner.start(cfg))
        QTimer.singleShot(30000, lambda: app.quit())
        app.exec()
        return exit_code["value"]

    window.show()

    return app.exec()
