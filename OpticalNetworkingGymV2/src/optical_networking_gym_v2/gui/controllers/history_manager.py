"""Gerenciador de histórico de simulações.

Armazena, persiste e recupera registros de simulações anteriores,
permitindo ao usuário revisitar resultados, renomear, excluir e
exportar dados em formatos CSV e JSON.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Diretório padrão de persistência do histórico
_HISTORY_DIR = Path.home() / ".optical_networking_gym" / "history"


@dataclass
class SimulationRecord:
    """Registro individual de uma simulação executada.

    Attributes
    ----------
    name : str
        Nome legível do registro (gerado automaticamente ou renomeado).
    timestamp : str
        Data e hora da execução em formato ISO 8601.
    heuristic_ids : list[str]
        Identificadores das heurísticas usadas na simulação.
    config : dict[str, Any]
        Configuração completa utilizada na execução.
    results : list[dict[str, Any]]
        Lista de resultados brutos retornados pelo simulador.
    slot_allocation : list[list[int]] | None
        Matriz de alocação espectral, se disponível.
    """

    name: str
    timestamp: str
    heuristic_ids: list[str]
    config: dict[str, Any]
    results: list[dict[str, Any]]
    slot_allocation: list[list[int]] | None = None


def _sanitize_filename(text: str) -> str:
    """Remove caracteres inválidos para nomes de arquivo.

    Parameters
    ----------
    text : str
        Texto a ser sanitizado.

    Returns
    -------
    str
        Texto seguro para uso como nome de arquivo.
    """
    return re.sub(r'[<>:"/\\|?*]', '_', text)


class HistoryManager:
    """Gerencia o histórico completo de simulações com persistência em disco.

    Os registros são salvos individualmente como arquivos JSON no
    diretório ``~/.optical_networking_gym/history/``, carregados
    automaticamente na inicialização.
    """

    def __init__(self, history_dir: Path | None = None) -> None:
        self._history_dir = history_dir or _HISTORY_DIR
        self._history_dir.mkdir(parents=True, exist_ok=True)

        self._records: list[SimulationRecord] = []
        self.load_history()

    # ── Acesso aos registros ─────────────────────────────────────

    def get_records(self) -> list[SimulationRecord]:
        """Retorna a lista ordenada de registros do histórico.

        Returns
        -------
        list[SimulationRecord]
            Registros ordenados do mais recente ao mais antigo.
        """
        return list(self._records)

    # ── Adição de novos registros ────────────────────────────────

    def add_record(
        self,
        config: dict[str, Any],
        results: list[dict[str, Any]],
        slot_allocation: list[list[int]] | None = None,
    ) -> SimulationRecord:
        """Cria e persiste um novo registro de simulação.

        O nome é gerado automaticamente no formato
        ``{nome_heuristica}_{YYYY-MM-DD_HH-MM-SS}``. Se múltiplas
        heurísticas foram utilizadas, o prefixo será ``multi_heuristica``.

        Parameters
        ----------
        config : dict[str, Any]
            Configuração completa da simulação.
        results : list[dict[str, Any]]
            Lista de dicionários com os resultados brutos.
        slot_allocation : list[list[int]] | None, optional
            Matriz de alocação espectral, por padrão ``None``.

        Returns
        -------
        SimulationRecord
            Registro criado e persistido.
        """
        from optical_networking_gym_v2.gui.models.run_config import HEURISTIC_CATALOG

        heuristic_names_map = {h.id: h.name for h in HEURISTIC_CATALOG}

        # Extrair IDs de heurísticas únicas dos resultados
        heuristic_ids: list[str] = []
        seen: set[str] = set()
        for res in results:
            hid = res.get("heuristic_id", "unknown")
            if hid not in seen:
                heuristic_ids.append(hid)
                seen.add(hid)

        # Gerar nome automático
        now = datetime.now()
        timestamp_str = now.strftime("%Y-%m-%dT%H:%M:%S")
        timestamp_filename = now.strftime("%Y-%m-%d_%H-%M-%S")

        if len(heuristic_ids) == 1:
            heur_label = heuristic_names_map.get(
                heuristic_ids[0], heuristic_ids[0]
            )
            # Converter nome legível para snake_case para o nome do registro
            heur_slug = re.sub(r'\s+', '_', heur_label.lower())
            heur_slug = re.sub(r'[^a-z0-9_]', '', heur_slug)
        else:
            heur_slug = "multi_heuristica"

        name = f"{heur_slug}_{timestamp_filename}"

        record = SimulationRecord(
            name=name,
            timestamp=timestamp_str,
            heuristic_ids=heuristic_ids,
            config=config,
            results=results,
            slot_allocation=slot_allocation,
        )

        self._records.insert(0, record)  # Mais recente primeiro
        self.save_record(record)

        logger.info("Registro de simulação salvo: %s", name)
        return record

    # ── Operações de edição ──────────────────────────────────────

    def rename_record(self, index: int, new_name: str) -> None:
        """Renomeia um registro existente no histórico.

        Remove o arquivo antigo e salva com o novo nome.

        Parameters
        ----------
        index : int
            Índice do registro na lista.
        new_name : str
            Novo nome para o registro.

        Raises
        ------
        IndexError
            Se o índice estiver fora dos limites.
        ValueError
            Se o novo nome estiver vazio.
        """
        if not 0 <= index < len(self._records):
            raise IndexError(f"Índice {index} fora dos limites do histórico.")
        if not new_name.strip():
            raise ValueError("O novo nome não pode ser vazio.")

        record = self._records[index]
        old_path = self._record_filepath(record)

        record.name = new_name.strip()

        # Remove arquivo antigo e salva com o novo nome
        if old_path.exists():
            old_path.unlink()
        self.save_record(record)

    def delete_record(self, index: int) -> None:
        """Remove um registro do histórico e apaga o arquivo correspondente.

        Parameters
        ----------
        index : int
            Índice do registro na lista.

        Raises
        ------
        IndexError
            Se o índice estiver fora dos limites.
        """
        if not 0 <= index < len(self._records):
            raise IndexError(f"Índice {index} fora dos limites do histórico.")

        record = self._records.pop(index)
        filepath = self._record_filepath(record)
        if filepath.exists():
            filepath.unlink()
            logger.info("Arquivo de histórico removido: %s", filepath.name)

    # ── Exportação ───────────────────────────────────────────────

    def export_record_episodes_csv(self, index: int, path: Path) -> None:
        """Exporta episodes.csv (28 colunas) de um registro do histórico."""
        if not 0 <= index < len(self._records):
            raise IndexError(f"Índice {index} fora dos limites do histórico.")

        record = self._records[index]
        results = record.results
        if not results:
            raise ValueError("Registro sem resultados para exportar.")

        from optical_networking_gym_v2.gui.controllers.results_manager import write_episodes_csv
        write_episodes_csv(results, path)
        logger.info("episodes.csv exportado: %s", path)

    def export_record_summary_csv(self, index: int, path: Path) -> None:
        """Exporta summary.csv (45 colunas) de um registro do histórico."""
        if not 0 <= index < len(self._records):
            raise IndexError(f"Índice {index} fora dos limites do histórico.")

        record = self._records[index]
        results = record.results
        if not results:
            raise ValueError("Registro sem resultados para exportar.")

        from optical_networking_gym_v2.gui.controllers.results_manager import write_summary_csv
        write_summary_csv(results, path)
        logger.info("summary.csv exportado: %s", path)

    def export_record_pair(self, index: int, target_dir: Path) -> list[Path]:
        """Exporta o par padrão episodes.csv e summary.csv de um registro em target_dir."""
        if not 0 <= index < len(self._records):
            raise IndexError(f"Índice {index} fora dos limites do histórico.")

        record = self._records[index]
        results = record.results
        if not results:
            raise ValueError("Registro sem resultados para exportar.")

        from optical_networking_gym_v2.gui.controllers.results_manager import (
            write_episodes_csv,
            write_summary_csv,
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        episodes_path = target_dir / "episodes.csv"
        summary_path = target_dir / "summary.csv"
        write_episodes_csv(results, episodes_path)
        write_summary_csv(results, summary_path)
        logger.info("Par CSV exportado em: %s", target_dir)
        return [episodes_path, summary_path]

    def export_record_csv(self, index: int, path: Path) -> None:
        """Exporta os resultados de um registro em CSV (episodes.csv ou summary.csv)."""
        if "episode" in path.stem.lower():
            self.export_record_episodes_csv(index, path)
        else:
            self.export_record_summary_csv(index, path)

    # ── Persistência em disco ────────────────────────────────────

    def save_record(self, record: SimulationRecord) -> None:
        """Salva um registro individual como arquivo JSON no diretório de histórico.

        Parameters
        ----------
        record : SimulationRecord
            Registro a ser persistido.
        """
        filepath = self._record_filepath(record)

        try:
            data = asdict(record)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            logger.exception("Falha ao salvar registro: %s", filepath.name)

    def load_history(self) -> None:
        """Carrega todos os registros salvos do diretório de histórico.

        Os registros são ordenados do mais recente ao mais antigo
        com base no timestamp.
        """
        self._records.clear()

        if not self._history_dir.exists():
            return

        for json_path in sorted(self._history_dir.glob("*.json"), reverse=True):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                record = SimulationRecord(
                    name=data.get("name", json_path.stem),
                    timestamp=data.get("timestamp", ""),
                    heuristic_ids=data.get("heuristic_ids", []),
                    config=data.get("config", {}),
                    results=data.get("results", []),
                    slot_allocation=data.get("slot_allocation"),
                )
                self._records.append(record)
            except Exception:
                logger.exception(
                    "Falha ao carregar registro de histórico: %s", json_path.name
                )

        # Ordenar por timestamp (mais recente primeiro)
        self._records.sort(key=lambda r: r.timestamp, reverse=True)

    # ── Utilitários internos ─────────────────────────────────────

    def _record_filepath(self, record: SimulationRecord) -> Path:
        """Gera o caminho completo do arquivo JSON para um registro.

        Parameters
        ----------
        record : SimulationRecord
            Registro para o qual gerar o caminho.

        Returns
        -------
        Path
            Caminho absoluto do arquivo JSON.
        """
        safe_name = _sanitize_filename(record.name)
        return self._history_dir / f"{safe_name}.json"
