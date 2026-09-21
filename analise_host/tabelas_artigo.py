#!/usr/bin/env python3
"""Tabelas do artigo, lado a lado num unico PNG (fonte ~3x, negrito).

Esquerda: Latencia media fim-a-fim (ms)         — grade cargas x protocolos
Direita : Throughput uplink no broker (kb/s)    — mesma grade

Le METRICAS_POR_RUN.csv de cada experimento (fonte identica a do relatorio;
sem recompute). Uma unica saida: analise_host/tabelas_artigo.png
"""
import argparse
import csv
import os
import statistics
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS_BASE = os.path.join(_RAIZ, 'dados', 'experimentos')
EXPERIMENTOS = {
    'mqtt': 'experimento_20260914_235110',
    'http': 'experimento_20260915_045417',
    'coap': 'experimento_20260915_073606',
}
CARGAS = [10, 20, 30, 40, 50]
ORDEM = ['mqtt', 'http', 'coap']
_HEADERS = ('app_lat_media_ms', 'broker_rx_kbps')


def numero(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def coleta():
    dados = {p: {c: {k: [] for k in _HEADERS} for c in CARGAS} for p in ORDEM}
    for proto, exp in EXPERIMENTOS.items():
        base = os.path.join(DADOS_BASE, exp)
        with open(os.path.join(base, 'metricas_por_run.csv'), newline='') as f:
            for r in csv.DictReader(f):
                carga = numero(r['carga'])
                if carga is None or int(carga) not in CARGAS:
                    continue
                c = int(carga)
                d = dados[proto][c]
                d['app_lat_media_ms'].append(numero(r['app_lat_media_ms']))
                d['broker_rx_kbps'].append(numero(r['broker_rx_kbps']))
    return dados


def media(vals):
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else float('nan')


def _grade(ax, cx, titulo, chave, fmt, cor, dados):
    ncols = len(ORDEM) + 1
    wc = 0.17
    hc = 0.14
    x0 = cx - ncols * wc / 2
    y0 = 0.58
    ax.text(cx, y0 + 2.2 * hc, titulo, ha='center', va='center',
            fontsize=24, fontweight='bold')
    cab = ['carga'] + [p.upper() for p in ORDEM]
    for j, c in enumerate(cab):
        xc = x0 + j * wc + wc / 2
        ax.add_patch(plt.Rectangle((xc - wc / 2, y0), wc, hc,
                                   facecolor=cor, edgecolor='black'))
        ax.text(xc, y0 + hc / 2, c, ha='center', va='center',
                fontsize=22, fontweight='bold')
    for i, carga in enumerate(CARGAS):
        yi = y0 - (i + 1) * hc
        yc = yi + hc / 2
        ax.add_patch(plt.Rectangle((x0, yi), wc, hc,
                                   facecolor=cor, edgecolor='black'))
        ax.text(x0 + wc / 2, yc, '%d' % carga, ha='center', va='center',
                fontsize=22, fontweight='bold')
        for j, proto in enumerate(ORDEM):
            xc = x0 + (j + 1) * wc + wc / 2
            ax.add_patch(plt.Rectangle((xc - wc / 2, yi), wc, hc,
                                       facecolor='white', edgecolor='black'))
            ax.text(xc, yc, fmt % media(dados[proto][carga][chave]),
                    ha='center', va='center', fontsize=22, fontweight='bold')


def main(out):
    os.makedirs(out, exist_ok=True)
    dados = coleta()
    fig, ax = plt.subplots(figsize=(19, 7.2))
    ax.axis('off')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    _grade(ax, 0.25, 'Latencia media fim-a-fim (ms)', 'app_lat_media_ms',
           '%.1f', '#cfe3fb', dados)
    _grade(ax, 0.75, 'Throughput uplink no broker (kb/s)', 'broker_rx_kbps',
           '%.0f', '#d8f3dc', dados)
    path = os.path.join(out, 'tabelas_artigo.png')
    fig.savefig(path, dpi=180, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('Tabelas: %s' % path)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out',
                    default=os.path.join(_RAIZ, 'analise_host'))
    main(ap.parse_args().out)
