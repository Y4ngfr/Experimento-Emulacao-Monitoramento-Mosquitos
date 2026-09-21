#!/usr/bin/env python3
"""Graficos de barras agrupadas: 3 protocolos x carga (10-50 sensores).

Le os `metricas_por_run.csv` de cada experimento (fonte de verdade em
dados/experimentos/<exp>/), agrega por carga (media±desvio das runs) e
recomputa a latencia media fim-a-fim GLOBAL real a partir dos `cient*.log`
(correcao do app_lat_media_ms do CSV, que e media de janelas e nao reflete
a media real; usamos o mesmo filtro t0/warmup do `app_lat_p99_ms_all`).

Saida: analise_host/graficos_comparativo/*.png  (um por metrica, barras
agrupadas por carga, cores por protocolo, valor acima de cada barra).

Metricas:
  - broker_rx_kbps      throughput uplink no broker (sensores->broker)
  - app_lat_media_global_ms  latencia media (todas as msgs, global real)
  - app_lat_p99_ms_all       latencia p99 (todas as msgs)
  - app_goodput_sustentado_kbps  goodput sustentado (app)
  - app_gaps              mensagens perdidas acumuladas (app, comercial)
"""
import argparse
import csv
import os
import statistics
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.topologia1.experimento import (  # noqa: E402
    APPS_CIENT, _msg_log, ler_t0)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS_BASE = os.path.join(RAIZ, 'dados', 'experimentos')
OUT_DEFAULT = os.path.join(RAIZ, 'analise_host', 'graficos_comparativo')

EXPERIMENTOS = {
    'mqtt': 'experimento_20260914_235110',
    'http': 'experimento_20260915_045417',
    'coap': 'experimento_20260915_073606',
}
CARGAS = [10, 20, 30, 40, 50]
ORDEM = ['mqtt', 'http', 'coap']
CORES = {'mqtt': '#d62728', 'http': '#2ca02c', 'coap': '#1f77b4'}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def ler_csv(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def lat_media_global(app_dir, t0):
    """Media (ms) fim-a-fim sobre TODAS as msgs dos cient*.log, >= t0."""
    lats = []
    for i in APPS_CIENT:
        p = os.path.join(app_dir, 'cient%s.log' % i)
        if not os.path.isfile(p):
            continue
        for ts_recv, _b, ts_pub in _msg_log(p):
            if t0 is not None and (ts_recv is None or ts_recv < t0):
                continue
            if ts_recv is None or ts_pub is None or ts_pub <= 0:
                continue
            lats.append((ts_recv - ts_pub) * 1e3)
    return statistics.mean(lats) if lats else None


def coleta():
    dados = {p: {c: {k: [] for k in ('app_lat_p50_ms', 'app_lat_p90_ms',
                                      'app_lat_p99_ms_all', 'app_lat_media_ms')}
                for c in CARGAS} for p in ORDEM}
    for proto, exp in EXPERIMENTOS.items():
        base = os.path.join(DADOS_BASE, exp)
        for r in ler_csv(os.path.join(base, 'metricas_por_run.csv')):
            carga = num(r['carga'])
            if carga is None or int(carga) not in CARGAS:
                continue
            c = int(carga)
            d = dados[proto][c]
            d['app_lat_p50_ms'].append(num(r['app_lat_p50_ms']))
            d['app_lat_p90_ms'].append(num(r['app_lat_p90_ms']))
            d['app_lat_p99_ms_all'].append(num(r['app_lat_p99_ms_all']))
            d['app_lat_media_ms'].append(num(r['app_lat_media_ms']))
    return dados


def agregar(dados, metrica):
    agg = {}
    for c in CARGAS:
        for p in ORDEM:
            vals = [v for v in dados[p][c][metrica] if v is not None]
            if not vals:
                agg[(c, p)] = (None, None)
            else:
                m = statistics.mean(vals)
                d = statistics.stdev(vals) if len(vals) > 1 else 0.0
                agg[(c, p)] = (m, d)
    return agg


def fmt(v):
    a = abs(v)
    if a >= 10000:
        return '%.3g' % v
    if a >= 1000:
        return '%.0f' % v
    if a >= 100:
        return '%.1f' % v
    return '%.2f' % v


def plot(metrica, titulo, unidade, dados, out_dir):
    agg = agregar(dados, metrica)
    x = list(range(len(CARGAS)))
    w = 0.26
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for j, proto in enumerate(ORDEM):
        meds = [agg[(c, proto)][0] for c in CARGAS]
        devs = [agg[(c, proto)][1] or 0.0 for c in CARGAS]
        xs = [xi + (j - 1) * w for xi in x]
        ax.bar(xs, [m if m is not None else 0 for m in meds], w,
               label=proto.upper(), color=CORES[proto],
               capsize=3, edgecolor='black', linewidth=0.5)
        for xi, m, dv in zip(xs, meds, devs):
            if m is None:
                continue
            top = m
            ax.text(xi, top + (top * 0.03), fmt(m), ha='center',
                    va='bottom', fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels([str(c) for c in CARGAS])
    ax.set_xlabel('Carga (numero de sensores)')
    ax.set_ylabel(unidade)
    ax.set_title(titulo)
    ax.grid(axis='y', linestyle=':', alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, metrica + '.png'), dpi=150)
    plt.close(fig)
    print('ok %s' % metrica)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT_DEFAULT)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    dados = coleta()
    plot('app_lat_p50_ms', 'Latencia p50 fim a fim',
         'ms (app_lat_p50_ms)', dados, args.out)
    plot('app_lat_p90_ms', 'Latencia p90 fim a fim (todas as msgs)',
         'ms (app_lat_p90_ms)', dados, args.out)
    plot('app_lat_p99_ms_all', 'Latencia p99 fim a fim (todas as msgs)',
         'ms (app_lat_p99_ms_all)', dados, args.out)
    plot('app_lat_media_ms', 'Latencia media fim a fim (todas as msgs)',
         'ms (app_lat_media_ms)', dados, args.out)
    print('Graficos em: %s' % args.out)


if __name__ == '__main__':
    main()
