#!/usr/bin/env bash
# ==============================================================================
# Script de Compilação do Executável Linux — Optical Networking Gym v2
# ==============================================================================
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

echo "=========================================================="
echo "  Compilando Executável Linux — Optical Networking Gym v2"
echo "=========================================================="

echo "[1/3] Compilando extensões Cython nativas..."
cd "$PROJECT_DIR/OpticalNetworkingGymV2"
"$VENV_PYTHON" setup.py build_ext --inplace

echo "[2/3] Verificando PyInstaller..."
if ! "$VENV_PYTHON" -c "import PyInstaller" 2>/dev/null; then
    if "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
        "$VENV_PYTHON" -m pip install pyinstaller
    elif command -v uv >/dev/null 2>&1; then
        uv pip install --python "$VENV_PYTHON" pyinstaller
    else
        echo "[ERRO] Nem pip nem uv encontrados para instalar pyinstaller."
        exit 1
    fi
fi

echo "[3/3] Gerando executável em dist/OpticalNetworkingGymV2/..."
cd "$PROJECT_DIR"
"$VENV_PYTHON" -m PyInstaller --noconfirm --clean packaging/ong_gui.spec

echo "=========================================================="
echo "  Compilação concluída com sucesso!"
echo "  Executável gerado em: $PROJECT_DIR/dist/OpticalNetworkingGymV2/OpticalNetworkingGymV2"
echo "=========================================================="
