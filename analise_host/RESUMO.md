# Reanálise da campanha do host (3 protocolos, 45 runs)

**Data da coleta:** 2026-09-14 a 2026-09-15 (no host, sem o servidor remoto).
**Configuração usada:** cargas 10–50 sensores | APs 1–5 (carga = nº APs) | 3 runs/carga | tempo 300 s/run | sensores:50/AP | raio 60/30 m, dist. APs 150 m, canal 3 | 3 cientistas.

| Protocolo | Experimento | Runs | Status | falhas_assoc |
|---|---|---|---|---|
| MQTT | `experimento_20260914_235110` | 15 | ok | 2 runs com 1 sens. (c30_run1: sta2; c40_run1: sta3) |
| HTTP | `experimento_20260915_045417` | 15 | ok | 0 |
| CoAP | `experimento_20260915_073606` | 15 | ok | 0 |

> **Nota de integridade:** o MQTT foi interrompido no c50 e completado pela fusão do `experimento_20260915_020930` (3 runs c50) — há nota de fusão no `experimento.log`. Descartei `experimento_20260915_044853` (http abortado, sem CSV) e `experimento_20260917_144838` (smoke, 1 run). `dados/{mqtt,http,coap,metricas}` são sobras de teste do host, fora da campanha.

> **Nota falhas de associação:** nos 2 runs mqtt citados, **apenas 1 sensor falhou** (1/30 e 1/40); a `sta` de falha tem CSV zerado e entra na média com 0 (impacto <0,5% no agregado). Runs **mantidas** por decisão do usuário (falha isolada, não compromete o run).

## Qualidade dos dados (verificada)
- `n_stas_csv == carga` em todos os 45 runs; `sta*.csv` completos.
- Nenhum campo vazio nas 71 colunas; `status=ok` em todos.
- Logs de metadados de detecção disponíveis nos 3 protocolos.

## Resultados principais

### Aplicação
| Métrica | Carga | MQTT | HTTP | CoAP |
|---|---|---|---|---|
| Lat. média (p50, ms) | 50 | 1,52 | 3,82 | 6,13 |
| Lat. p99 (ms) | 10 | 3,4 | 13,4 | 18,0 |
| Lat. p99 (ms) | 50 | 463 | 2201 | 1883 |
| Goodput sustentado (kb/s) | 50 | 8,08 | 7,70 | 7,77 |
| Perda app (%) | 10–50 | 0 | 1,3–4,4 | 0 |

- **Perda HTTP (1,3–4,4%) é artefato de medição do long-poll** (1 payload/consulta; cientista inscrito só durante `q.get(timeout=25)`); as mensagens "faltantes" existem no `meta.log` e nos outros cientistas — não é perda real de rede.
- Latência p99 cresce com a carga nos 3 protocolos; MQTT é o mais estável, HTTP/CoAP disparem no p99/p90 a partir de c30 (fila/consulta), já vistos em `app_lat_p99_ms_all` e na tabela completa.
- `app_lat_p99_ms_all` (todas as msgs): HTTP atinge ~4,35 s em c50 vs MQTT ~709 ms.

### Detecção (agregado dos 15 runs por protocolo)
| Protocolo | Acurácia geral | Classe 0 (macho) | Classe 1 (fêmea) | Classe 2 (outros) | Classe 3 (ambiente) |
|---|---|---|---|---|---|
| MQTT | 81,36% (930/1143) | 101/120 | 183/319 | 63/115 | 583/589 |
| HTTP | 81,22% (917/1129) | 98/117 | 183/318 | 62/114 | 574/580 |
| CoAP | 81,37% (926/1138) | 100/119 | 181/316 | 63/115 | 582/588 |

- Acurácia geral estável ≈ **81%**, determinística do modelo (não varia com carga) — confirma as colunas `det_*` do CSV.
- Proporção amostrada ≈ alvo (10%/30%/10%/50%) em todos os protocolos.

### Rede
- `sta_rssi` ≈ −46/47 dBm e `sta_bitrate` 46–51 Mb/s em **todas** as cargas (afição determinística das 3 topologias, mesma posição relativa).
- `sta_retries`/`sta_failed`/`sta_beacon_loss`/`ap_failed` = 0 em todos os runs (sem perda física de enlace).

### Broker
- MQTT: `broker_clients` = carga+4 (sensores+gw+3 cient). HTTP/CoAP registram só 3 clientes (servidores).
- Throughput do broker (rx+tx) escala linearmente com a carga nos 3 protocolos.

## Arquivos gerados
- `analise_host/experimento_<ts>/graficos/*.png` — 51 gráficos por protocolo (média±desvio por carga).
- `analise_host/comparativo_protocolos.csv` e `comparativo_protocolos.md` — tabelas completas (app/det/rede/broker).
- `analise_host/deteccao_experimento_<ts>.log` — saída do `analisar_deteccao.py`.
- `analise_host/grafico_barras_experimento_<ts>.log` — logs/generate de gráficos.