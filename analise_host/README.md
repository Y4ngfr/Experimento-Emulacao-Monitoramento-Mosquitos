# Análise da campanha

Resultados numéricos, tabelas e figuras usadas no artigo. Esta pasta analisa a
campanha oficial de 45 runs (3 protocolos × 5 cargas × 3 runs) — ver
`RESUMO.md` para o resumo completo e as notas de integridade.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `RESUMO.md` | Reanálise completa da campanha: tabelas por métrica, conclusões e notas de integridade |
| `comparativo_protocolos.py` | Gera `comparativo_protocolos.md`/`.csv` (média ± desvio das 3 runs por carga) |
| `comparativo_protocolos.md` | Tabelas comparativas por métrica (p50/p90/p99/média/goodput/perda/acurácia) |
| `comparativo_protocolos.csv` | Mesmos números em formato utilizável pelo artigo |
| `comparativo_barras.py` | Gera os gráficos de barras agrupadas (p50/p90/p99/média) em `graficos_comparativo/` |
| `artigo_throughput.py` | Gera a figura final do artigo `artigo_throughput.png` (latência média × throughput no broker) |
| `artigo_horizontal.py` | Versão anterior da figura (p99 no painel direito) |
| `tabelas_artigo.py` | Gera `tabelas_artigo.png` (tabelas lado a lado, caso se queira em figura) |
| `debug_lat_media_global.py` | Script de verificação da latência média agregada |
| `experimento_*/graficos/` | Gráficos por protocolo gerados na campanha (p50/p90/p99/média por carga) |

## Fonte dos dados

Os scripts de análise leem `dados/experimentos/<exp_id>/metricas_por_run.csv`
dos três experimentos oficiais:

- **MQTT** → `experimento_20260914_235110`
- **HTTP** → `experimento_20260915_045417`
- **CoAP** → `experimento_20260915_073606`

Os três CSV têm o mesmo esquema (71 colunas, métricas por run); o mapeamento
completo das colunas e as notas de integridade estão em `RESUMO.md`.

## Como gerar os gráficos

```bash
python3 analise_host/comparativo_protocolos.py   # atualiza .md e .csv
python3 analise_host/comparativo_barras.py       # graficos_comparativo/*.png
python3 analise_host/artigo_throughput.py        # artigo_throughput.png
```

## Figuras do artigo

- `artigo_throughput.png` — figura principal: painel esquerdo latência
  fim-a-fim média, painel direito throughput no broker (carga no eixo y).
- `graficos_comparativo/app_lat_{p50,p90,p99_all,media}_ms.png` — barras
  agrupadas por protocolo para cada métrica de latência.

Título sugerido para a figura principal: *Comparação entre MQTT, HTTP e CoAP
quanto à latência fim-a-fim (média) e ao throughput no servidor (broker), para
cargas de 10 a 50 sensores.*