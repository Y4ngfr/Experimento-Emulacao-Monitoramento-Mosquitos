# WSN-WiFi: MQTT, HTTP e CoAP em mininet-wifi

Emulação de uma WSN-WiFi (rede de sensores sobre Wi-Fi) com três protocolos de
aplicação — **MQTT**, **HTTP streaming/long-poll** e **CoAP** — usando
[containernet] + [mininet-wifi]. Cada sensor roda inferência de um modelo
Residual (TensorFlow Lite) na borda e envia apenas o metadado da classificação
ao servidor; a latência fim-a-fim é medida nos cientistas (subscribers).

Campanha executada: 3 protocolos × 5 cargas (10–50 sensores) × 3 runs = **45 runs**
(~300 s cada), análise completa em `analise_host/`.

<div align="center">

| | [como rodar](#como-executar) | [estrutura](#estrutura) | [resultados](analise_host/README.md) |

</div>

## Como executar

### Pré-requisitos

Hospedeiro Linux com Docker. A imagem do experimento é pública em
`yangfr10/mn-wifi:latest` (contém containernet, mininet-wifi, tflite-runtime,
aiocoap, paho-mqtt, mosquitto, numpy, librosa e matplotlib).

```bash
bash up.sh          # cria o container mininet-lab com volumes scripts/config/dados
```

Os **datasets de áudio (≈1,5 GB)** **não** estão neste repositório (ver
[.gitignore](.gitignore)). Eles devem ser montados na tmpfs do host antes do
experimento:

```bash
# 1) prepara o dataset processado (.bin por classe, alvo 10/30/10/50%)
python3 scripts/topologia1/preparar_dataset.py --dataset <bruto> --output scripts/topologia1/Dataset-processado
# 2) monta na RAM do container (copia o Dataset-processado p/ a tmpfs)
docker exec mininet-lab python3 /app/scripts/topologia1/carregar_dataset.py --source /app/scripts/topologia1/Dataset-processado --dest /mnt/dataset-ram
```

### Rodar um experimento

Dentro do container (ou em `docker exec`):

```bash
docker exec mininet-lab python3 /app/scripts/topologia1/experimento.py \
    --app mqtt --runs 3 --tempo 300 --out /app/dados/experimentos \
    --cargas 10,20,30,40,50
```

Argumentos principais de `experimento.py`: `--app {mqtt,http,coap}`, `--runs`,
`--tempo` (duração por run em s), `--cargas`, `--sensores_por_ap`, `--warmup`,
`--out` (base de resultados), além dos parâmetros de rádio/propagação
(`--channel`, `--raio`, `--raio_min`, `--dist_aps`, `--systemloss`, `--exploss`,
`--variance`, `--aptxpower`, `--sensortxpower`).

Cada run grava `dados/experimentos/<exp_id>/` com `metricas_por_run.csv`,
`experimento.log`, `raw/` (logs e CSVs por host) e `graficos/`.

### Análise (fora do container, no host)

```bash
python3 analise_host/comparativo_barras.py        # gráficos p50/p90/p99/média por protocolo
python3 analise_host/comparativo_protocolos.py    # tabela completa média±desvio das runs
python3 analise_host/artigo_throughput.py         # figura do artigo (média × throughput)
```

Os scripts esperam `dados/experimentos/<experimento_*/>` com `metricas_por_run.csv`
para os três protocolos — ver `analise_host/README.md` para a fonte exata dos dados.

## Estrutura

```
├── Dockerfile                 # imagem do experimento (containernet + deps)
├── up.sh                      # cria/sobe o container mininet-lab (volumes, OVS, X11)
├── start.sh                   # fallback que delega para up.sh
├── salvar-imagem.sh           # publica a imagem no registry (Docker Hub)
├── config/                    # configuração (vazia; bind para /app/config)
├── scripts/
│   └── topologia1/            # <-- escopo do repositório
│       ├── experimento.py     # orquestrador da campanha (cargas × runs × protocolo)
│       ├── topologia.py       # constrói a topologia mininet-wifi
│       ├── sensoriamento.py   # leitura de áudio, extração de descritores, metadado
│       ├── preparar_dataset.py / carregar_dataset.py   # dataset → tmpfs
│       ├── metricas_app.py    # motor de métricas compartilhado (latência, goodput, perda)
│       ├── mqtt/  coap/  http/# sensores + servidores/cientistas por protocolo
│       ├── ml/                # classificador Residual + model_float16.tflite
│       └── metricas/          # coletores (no/sys), resumo e gráficos
├── dados/
│   └── experimentos/          # resultados oficiais (CSV + experimento.log por exp.)
├── docs/
│   └── mininet-wifi/          # documentação/referência do mininet-wifi
└── analise_host/              # análise, tabelas e figuras do artigo
    ├── README.md              # guia da análise (ver abaixo)
    ├── RESUMO.md              # reanálise da campanha (45 runs)
    ├── comparativo_protocolos.{py,csv,md}
    ├── comparativo_barras.py  # gráficos p50/p90/p99/média
    ├── artigo_throughput.py   # figura final do artigo
    ├── graficos_comparativo/  # PNGs de barras agrupadas
    └── experimento_*/         # gráficos por protocolo da campanha
```

`scripts/topologia2/` (variante inicial com IPv6/6LoWPAN e coleta por roteamento)
ficou **fora** do versionamento deste repositório: a perspectiva desta campanha
é a topologia 1. Se precisar dela, recupere do histórico local.

## Licença

Sem licença definida (uso acadêmico). Consulte os autores antes de reuse.

[containernet]: https://github.com/containernet/containernet
[mininet-wifi]: https://github.com/intrig-unicamp/mininet-wifi
