@echo off
REM ==============================================================================
REM Script de Compilacao do Executavel Windows — Optical Networking Gym v2
REM ==============================================================================
setlocal

cd /d "%~dp0.."

echo ==========================================================
echo   Compilando Executavel Windows — Optical Networking Gym v2
echo ==========================================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual .venv nao encontrado.
    echo Execute:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -e .\OpticalNetworkingGymV2[gui,dev] pyinstaller
    exit /b 1
)

echo [1/3] Compilando extensoes Cython (.pyd)...
pushd OpticalNetworkingGymV2
..\.venv\Scripts\python.exe setup.py build_ext --inplace
if errorlevel 1 exit /b 1
popd

echo [2/3] Verificando PyInstaller...
.venv\Scripts\python.exe -c "import PyInstaller" 2>nul
if errorlevel 1 (
    .venv\Scripts\pip.exe install pyinstaller
)

echo [3/3] Gerando executavel em dist\OpticalNetworkingGymV2\...
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean packaging\ong_gui.spec
if errorlevel 1 exit /b 1

echo ==========================================================
echo   Compilacao concluida com sucesso!
echo   Executavel gerado em: dist\OpticalNetworkingGymV2\OpticalNetworkingGymV2.exe
echo ==========================================================
endlocal
