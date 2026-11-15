# Optical Networking Gym v2 — Interface Gráfica e Simulador RMLSA/QoT

Simulador de Redes Ópticas Elásticas (EONs) com camada física de alta performance em Cython (`ASE+NLI` / Modelo GN), interface gráfica em PySide6 (tema claro profissional) e geração padronizada exclusiva dos arquivos `episodes.csv` (28 colunas) e `summary.csv` (45 colunas).

## Estrutura do Projeto

- `OpticalNetworkingGymV2/`: núcleo do simulador (`src/optical_networking_gym_v2`), kernels Cython, heurísticas RMLSA, topologias e interface gráfica (`gui/`).
- `packaging/`: scripts e especificação `PyInstaller` para gerar executáveis nativos para **Linux** e **Windows**.
- `.github/workflows/build-executables.yml`: pipeline automático no GitHub Actions para compilar e testar os executáveis de **Windows (`.exe`)** e **Linux**.
- `parametros_simulacao.json`: perfil pronto de parâmetros para importação em *Arquivo -> Carregar Configuração (.json)*.
- `run_linux.sh`: script para execução direta em desenvolvimento no Linux.

## Execução em Desenvolvimento (Linux)

```bash
./run_linux.sh
```

## Compilação dos Executáveis

### Linux
```bash
./packaging/build_linux.sh
```
Executável gerado em `dist/OpticalNetworkingGymV2/OpticalNetworkingGymV2`.

### Windows
```bat
python -m venv .venv
.venv\Scripts\pip install setuptools wheel Cython numpy
.venv\Scripts\pip install -e .\OpticalNetworkingGymV2[gui,dev] pyinstaller
packaging\build_windows.bat
```
Executável gerado em `dist\OpticalNetworkingGymV2\OpticalNetworkingGymV2.exe`.

## Automação via GitHub Actions

A cada `push` em `main`/`master` (ou disparo manual em *Actions*), o GitHub compila e executa o `--self-test` nos binários **Linux** e **Windows**. Ao criar uma tag `v*` (ex.: `v2.0.0`), os pacotes `OpticalNetworkingGymV2-linux-x86_64.tar.gz` e `OpticalNetworkingGymV2-windows-x86_64.zip` são publicados automaticamente em **GitHub Releases**.
