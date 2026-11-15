# Optical Networking Gym v2 — Interface Gráfica e Simulador RMLSA/QoT

Simulador de Redes Ópticas Elásticas (EONs) com camada física de alta performance em Cython (`ASE+NLI` / Modelo GN), interface gráfica em PySide6 e geração padronizada dos arquivos `episodes.csv` (28 colunas) e `summary.csv` (45 colunas).

Desenvolvido no âmbito do **Laboratório de Eletromagnetismo Aplicado (LEA-UFPA)**.

---

## Sumário

1. [Instalação Rápida (Executáveis Prontos)](#1-instalação-rápida-executáveis-prontos)
   - [Windows (.exe)](#windows-exe)
   - [Linux](#linux)
2. [Instalação pelo Código-Fonte (Desenvolvimento)](#2-instalação-pelo-código-fonte-desenvolvimento)
   - [Pré-requisitos](#pré-requisitos)
   - [Passo a passo no Linux](#passo-a-passo-no-linux)
   - [Passo a passo no Windows](#passo-a-passo-no-windows)
3. [Compilação dos Executáveis (PyInstaller)](#3-compilação-dos-executáveis-pyinstaller)
4. [Uso Rápido e Arquivos de Saída](#4-uso-rápido-e-arquivos-de-saída)
5. [Estrutura do Projeto](#5-estrutura-do-projeto)
6. [Automação via GitHub Actions](#6-automação-via-github-actions)

---

## 1. Instalação Rápida (Executáveis Prontos)

Se você deseja apenas executar o simulador sem instalar Python ou compilar bibliotecas, baixe o pacote pronto na página de **Releases**:

- **Página de Releases:** https://github.com/LEA-UFPA/OpticalNetworkingGymV2-UI/releases

### Windows (`.exe`)

1. Acesse a [última Release](https://github.com/LEA-UFPA/OpticalNetworkingGymV2-UI/releases/latest) e baixe o arquivo **`OpticalNetworkingGymV2-windows-x86_64.zip`**.
2. Extraia o arquivo `.zip` em uma pasta de sua preferência (por exemplo, `C:\OpticalNetworkingGymV2\`).
3. Abra a pasta extraída `OpticalNetworkingGymV2` e execute **`OpticalNetworkingGymV2.exe`**.

> **Nota:** Mantenha a pasta `_internal` no mesmo diretório de `OpticalNetworkingGymV2.exe` — ela contém o Python embutido, o PySide6 e os kernels Cython compilados. Caso o Windows Defender SmartScreen exiba um aviso por ser um binário não assinado, clique em *Mais informações* e em *Executar assim mesmo*.

### Linux

1. Acesse a [última Release](https://github.com/LEA-UFPA/OpticalNetworkingGymV2-UI/releases/latest) e baixe o arquivo **`OpticalNetworkingGymV2-linux-x86_64.tar.gz`** (ou use o terminal abaixo):
   ```bash
   curl -L -o OpticalNetworkingGymV2-linux-x86_64.tar.gz \
     https://github.com/LEA-UFPA/OpticalNetworkingGymV2-UI/releases/latest/download/OpticalNetworkingGymV2-linux-x86_64.tar.gz
   ```
2. Extraia o pacote e inicie a aplicação:
   ```bash
   tar -xzf OpticalNetworkingGymV2-linux-x86_64.tar.gz
   ./OpticalNetworkingGymV2/OpticalNetworkingGymV2
   ```
3. *(Opcional, Ubuntu/Debian)* Caso falte alguma biblioteca gráfica do Qt/PySide6 no sistema:
   ```bash
   sudo apt-get update
   sudo apt-get install -y libegl1 libxkbcommon0 libdbus-1-3 libxcb-cursor0 libgl1
   ```

---

## 2. Instalação pelo Código-Fonte (Desenvolvimento)

### Pré-requisitos

- **Git**
- **Python 3.11 ou superior** (testado em Python 3.13)
- **Compilador C/C++** para os módulos Cython:
  - **Linux (Ubuntu/Debian):** `build-essential` (`gcc`) + `python3-dev`
  - **Windows:** [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) (carga de trabalho *Desenvolvimento para desktop com C++*)

### Passo a passo no Linux

1. Instale as dependências do sistema (Ubuntu/Debian):
   ```bash
   sudo apt-get update
   sudo apt-get install -y git python3 python3-venv python3-dev build-essential \
     libegl1 libxkbcommon0 libdbus-1-3 libxcb-cursor0 libgl1
   ```
2. Clone o repositório e acesse a pasta do projeto:
   ```bash
   git clone https://github.com/LEA-UFPA/OpticalNetworkingGymV2-UI.git
   cd OpticalNetworkingGymV2-UI
   ```
3. Crie e ative o ambiente virtual `.venv`:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Instale as dependências de build, o simulador e a interface gráfica:
   ```bash
   pip install --upgrade pip setuptools wheel Cython numpy
   pip install -e "./OpticalNetworkingGymV2[gui,dev]"
   ```
5. Compile os kernels Cython nativos (`--inplace`):
   ```bash
   (cd OpticalNetworkingGymV2 && ../.venv/bin/python setup.py build_ext --inplace)
   ```
6. Execute a interface gráfica:
   ```bash
   ./run_linux.sh
   ```

### Passo a passo no Windows

1. Abra o **Prompt de Comando (`cmd`)** ou o **PowerShell** e clone o repositório:
   ```bat
   git clone https://github.com/LEA-UFPA/OpticalNetworkingGymV2-UI.git
   cd OpticalNetworkingGymV2-UI
   ```
2. Crie o ambiente virtual `.venv`:
   ```bat
   python -m venv .venv
   ```
3. Instale as dependências de build, o simulador e a interface gráfica:
   ```bat
   .venv\Scripts\python -m pip install --upgrade pip setuptools wheel Cython numpy
   .venv\Scripts\python -m pip install -e ".\OpticalNetworkingGymV2[gui,dev]"
   ```
4. Compile as extensões Cython (`.pyd`):
   ```bat
   pushd OpticalNetworkingGymV2
   ..\.venv\Scripts\python setup.py build_ext --inplace
   popd
   ```
5. Execute a interface gráfica:
   ```bat
   .venv\Scripts\python -m optical_networking_gym_v2.gui
   ```

---

## 3. Compilação dos Executáveis (PyInstaller)

Com o ambiente virtual `.venv` configurado conforme a seção anterior:

### Linux
```bash
./packaging/build_linux.sh
```
Executável gerado em `dist/OpticalNetworkingGymV2/OpticalNetworkingGymV2`.

### Windows
No Prompt de Comando com o ambiente de compilação MSVC disponível (ex.: *x64 Native Tools Command Prompt for VS*):
```bat
.venv\Scripts\pip install pyinstaller
packaging\build_windows.bat
```
Executável gerado em `dist\OpticalNetworkingGymV2\OpticalNetworkingGymV2.exe`.

### Verificação automática (Self-test)
Para validar o binário compilado em modo headless (executa uma simulação rápida de 50 requisições com `First_Fit` e valida a geração dos CSVs):
```bash
# Linux
QT_QPA_PLATFORM=offscreen ./dist/OpticalNetworkingGymV2/OpticalNetworkingGymV2 --self-test
```
```bat
:: Windows
set QT_QPA_PLATFORM=offscreen
dist\OpticalNetworkingGymV2\OpticalNetworkingGymV2.exe --self-test
```

---

## 4. Uso Rápido e Arquivos de Saída

- **Perfil pronto de parâmetros:** o repositório inclui o arquivo `parametros_simulacao.json`, que pode ser importado diretamente na interface em **Arquivo -> Carregar Configuração (.json)**.
- **Arquivos gerados após a simulação:** ao concluir uma simulação, o simulador exporta exclusivamente os dois arquivos padrão no diretório de saída escolhido:
  - `episodes.csv` (28 colunas com métricas por episódio)
  - `summary.csv` (45 colunas com estatísticas agregadas da simulação)

---

## 5. Estrutura do Projeto

- `OpticalNetworkingGymV2/`: núcleo do simulador (`src/optical_networking_gym_v2`), kernels Cython, heurísticas RMLSA, topologias e interface gráfica (`gui/`).
- `packaging/`: scripts (`build_linux.sh`, `build_windows.bat`) e especificação `PyInstaller` (`ong_gui.spec`).
- `.github/workflows/build-executables.yml`: pipeline automático no GitHub Actions para compilar e testar os executáveis de **Windows (`.exe`)** e **Linux**.
- `parametros_simulacao.json`: arquivo JSON de parâmetros pronto para importação na GUI.
- `run_linux.sh`: script para inicialização rápida em desenvolvimento no Linux.

---

## 6. Automação via GitHub Actions

A cada `push` em `main`/`master` (ou disparo manual em *Actions*), o GitHub compila e executa o `--self-test` nos binários **Linux** e **Windows**. Ao criar e enviar uma tag `v*` (ex.: `v2.0.0`), os pacotes `OpticalNetworkingGymV2-linux-x86_64.tar.gz` e `OpticalNetworkingGymV2-windows-x86_64.zip` são publicados automaticamente em **GitHub Releases**.
