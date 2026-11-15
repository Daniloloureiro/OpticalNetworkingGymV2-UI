# Parâmetros do Simulador (Optical Networking Gym)

Este documento detalha todos os parâmetros disponíveis para a configuração de cenários (`ScenarioConfig`) no simulador Optical Networking Gym, incluindo seus tipos e valores padrão.

## Parâmetros Obrigatórios

Estes parâmetros devem ser definidos ao instanciar ou configurar um cenário, pois não possuem valores padrão predefinidos na classe base:

- **`scenario_id`** (`str`): Identificador único para o cenário.
- **`topology_id`** (`str`): Nome do arquivo da topologia a ser utilizado (ex: `"nsfnet"`).
- **`k_paths`** (`int`): Número de caminhos mais curtos (K-shortest paths) pré-calculados para cada par de nós.
- **`num_spectrum_resources`** (`int`): Número total de slots de espectro (resources) disponíveis por enlace de fibra.

## Parâmetros da Topologia e Física da Fibra

- **`topology_dir`** (`str` | `Path` | `None`): Diretório onde o arquivo de topologia está localizado. Padrão: `None` (usa o diretório embutido).
- **`max_span_length_km`** (`float`): Comprimento máximo de um vão (span) de fibra em km. Padrão: `100.0`.
- **`default_attenuation_db_per_km`** (`float`): Atenuação padrão da fibra em dB/km. Padrão: `0.2`.
- **`default_noise_figure_db`** (`float`): Figura de ruído padrão dos amplificadores (EDFA) em dB. Padrão: `4.5`.
- **`channel_width`** (`float`): Largura de canal. Padrão: `12.5` (GHz).
- **`frequency_start`** (`float`): Frequência inicial do espectro em Hz. Padrão: `(3e8 / 1565e-9)` (~191.69 THz).
- **`frequency_slot_bandwidth`** (`float`): Largura de banda de um slot de frequência em Hz. Padrão: `12.5e9` (12.5 GHz).
- **`launch_power_dbm`** (`float`): Potência de lançamento do sinal em dBm. Padrão: `0.0`.
- **`bandwidth`** (`float` | `None`): Largura de banda total (calculada automaticamente como `num_spectrum_resources * frequency_slot_bandwidth` se for `None`). Padrão: `None`.

## Parâmetros de Tráfego

- **`traffic_mode`** (`TrafficMode`): Modo de geração de tráfego (`STATIC` ou `DYNAMIC`). Padrão: `TrafficMode.DYNAMIC`.
- **`traffic_source`** (`object` | `None`): Fonte do tráfego. Gerado automaticamente se for `None` no tráfego dinâmico. Padrão: `None`.
- **`bit_rates`** (`tuple[int, ...]` | `None`): Taxas de bit das requisições em Gbps. Padrão: `(10, 40, 100, 400)`.
- **`bit_rate_probabilities`** (`tuple[float, ...]` | `None`): Probabilidades associadas a cada taxa de bit. Se `None`, assume-se uma distribuição uniforme. Padrão: `None`.
- **`load`** (`float`): Carga de rede total oferecida (Erlangs). Padrão: `300.0`.
- **`mean_holding_time`** (`float`): Tempo médio de retenção da conexão. Padrão: `100.0`.
- **`mean_inter_arrival_time`** (`float` | `None`): Tempo médio entre a chegada de novas requisições. Se for `None`, é calculado via a Carga (`load`). Padrão: `None`.
- **`static_traffic_path`** (`str` | `Path` | `None`): Caminho para o arquivo que define a matriz de tráfego estático (se aplicável). Padrão: `None`.

## Qualidade de Transmissão (QoT) e Modulações

- **`qot_constraint`** (`str`): Tipo de restrição de QoT (`"ASE+NLI"` ou `"DIST"`). Padrão: `"ASE+NLI"`.
- **`margin`** (`float`): Margem de segurança de OSNR. Padrão: `0.0`.
- **`modulations`** (`tuple[Modulation, ...]`): Conjunto de formatos de modulação disponíveis. Padrão: `()` (Tupla vazia). *Catálogo disponível: BPSK, QPSK, 8QAM, 16QAM, 32QAM, 64QAM.*
- **`modulations_to_consider`** (`int` | `None`): Quantidade de formatos de modulação a serem considerados nas heurísticas e mascaramentos. Padrão: `None` (Usa todos os disponíveis em `modulations`).

## Restrições de Episódio e Monitoramento

- **`episode_length`** (`int`): Duração de um episódio no treinamento/avaliação. Padrão: `1000`.
- **`mask_mode`** (`MaskMode`): Modo de cálculo da máscara de ações (ex: `RESOURCE_AND_QOT`). Padrão: `MaskMode.RESOURCE_AND_QOT`.
- **`reward_profile`** (`RewardProfile`): Perfil de função de recompensa (ex: `BALANCED`). Padrão: `RewardProfile.BALANCED`.
- **`measure_disruptions`** (`bool`): Se interrupções (disruptions) devem ser medidas devido à QoT. Padrão: `False`.
- **`drop_on_disruption`** (`bool`): Se a conexão deve ser removida quando ocorrer interrupção (disruption). Padrão: `False`.
- **`enable_observation`** (`bool`): Ativa a geração de observações para o Agente. Padrão: `True`.
- **`enable_action_mask`** (`bool`): Ativa o filtro/máscara de ações inválidas. Padrão: `True`.
- **`include_mask_in_info`** (`bool`): Inclui a máscara de ação nas informações (info) do estado do Gym. Padrão: `True`.
- **`capture_traffic_table`** (`bool`): Habilita o registro detalhado da tabela de tráfego. Padrão: `False`.
- **`capture_step_trace`** (`bool`): Habilita o registro passo-a-passo (trace) do ambiente de simulação. Padrão: `False`.
- **`seed`** (`int` | `None`): Semente de aleatoriedade para reprodutibilidade. Padrão: `None`.

## Notas Adicionais

Existem também alguns valores padrão globais definidos internamente no simulador (em `defaults.py`):
- `DEFAULT_SEED`: 10
- `DEFAULT_LOAD`: 300.0
- `DEFAULT_MEAN_HOLDING_TIME`: 10800.0
- `DEFAULT_NUM_SPECTRUM_RESOURCES`: 320
- `DEFAULT_K_PATHS`: 3
- `DEFAULT_LAUNCH_POWER_DBM`: 1.0
- `DEFAULT_MODULATIONS_TO_CONSIDER`: 6
