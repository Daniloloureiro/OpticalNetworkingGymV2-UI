#!/usr/bin/env bash
# ==============================================================================
# Script de Inicialização da Bancada Optical Networking Gym v2 (Linux)
# ==============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
SRC_DIR="$PROJECT_DIR/OpticalNetworkingGymV2/src"

echo "=========================================================="
echo "  Iniciando Optical Networking Gym v2 (Ambiente Linux)"
echo "=========================================================="

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Erro: Ambiente virtual nao encontrado em $PROJECT_DIR/.venv"
    echo "Crie o ambiente executando:"
    echo "   cd $PROJECT_DIR"
    echo "   python3 -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -e ./OpticalNetworkingGymV2[gui]"
    exit 1
fi

export PYTHONPATH="$SRC_DIR:$PYTHONPATH"

echo "Executando interface grafica..."
exec "$VENV_PYTHON" -m optical_networking_gym_v2.gui "$@"
