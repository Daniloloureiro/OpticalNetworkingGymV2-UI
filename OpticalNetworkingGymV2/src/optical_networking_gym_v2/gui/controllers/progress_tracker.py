"""Rastreador de progresso e estimador de tempo (ETA) para a execução de simulações.

Calcula estatísticas de duração média por tarefa para prever de forma precisa
o tempo restante das varreduras de simulação.
"""

from __future__ import annotations

import time


class ProgressTracker:
    """Rastreador estatístico do andamento de um lote de tarefas de simulação.

    Permite obter a média de execução e prever o tempo restante estimado (ETA).
    """

    def __init__(self, total_tasks: int) -> None:
        """Inicializa o rastreador.

        Parameters
        ----------
        total_tasks : int
            Número total de tarefas no lote.
        """
        self.total_tasks: int = total_tasks
        self.completed_tasks: int = 0
        self.start_time: float = time.time()
        self.task_durations: list[float] = []
        self.last_update_time: float = time.time()

    def reset(self, total_tasks: int) -> None:
        """Reinicia o rastreador com um novo total de tarefas.

        Parameters
        ----------
        total_tasks : int
            Novo total de tarefas.
        """
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.start_time = time.time()
        self.task_durations.clear()
        self.last_update_time = time.time()

    def record_task_completion(self, duration: float) -> None:
        """Registra a conclusão de uma tarefa com sua respectiva duração.

        Parameters
        ----------
        duration : float
            Tempo em segundos gasto na execução da tarefa.
        """
        self.completed_tasks += 1
        self.task_durations.append(duration)
        self.last_update_time = time.time()

    def get_mean_duration(self) -> float:
        """Retorna a duração média por tarefa em segundos.

        Returns
        -------
        float
            Duração média das tarefas concluídas.
        """
        if not self.task_durations:
            return 0.0
        return sum(self.task_durations) / len(self.task_durations)

    def estimate_remaining_time(self) -> float:
        """Estima o tempo restante em segundos para a conclusão das tarefas remanescentes.

        Returns
        -------
        float
            Tempo restante em segundos.
        """
        remaining_tasks = self.total_tasks - self.completed_tasks
        if remaining_tasks <= 0:
            return 0.0

        mean_duration = self.get_mean_duration()
        if mean_duration > 0:
            return mean_duration * remaining_tasks

        # Fallback usando o tempo decorrido total dividido pelo progresso atual
        elapsed = time.time() - self.start_time
        if self.completed_tasks > 0:
            return (elapsed / self.completed_tasks) * remaining_tasks

        return 0.0
