#!/usr/bin/env python3
"""Graficos horizontais lado a lado para o artigo (deliverable 3).

Esquerda : Latencia media fim-a-fim (ms, todas as msgs)  — ylabel "Carga"
Direita  : Throughput uplink no broker (kb/s)            — sem ylabel

Barras na horizontal; eixo Y = carga (10-50); barras = mqtt/http/coap.
Fonte de ambos: metricas_por_run.csv de cada experimento (fonte unica,
identica ao relatorio; sem recomputo). Fontes graúdas em eixos, medidas
e protocolos, valores em negrito.

Saida: analise_host/artigo_throughput.png
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
CORES = {'mqtt': '#d62728', 'http': '#2ca02c', 'coap': '#1f77b4'}
OUT_DEFAULT = os.path.join(_RAIZ, 'analise_host')
COLUNAS = {'app_lat_media_ms': 'Latencia media (ms)',
           'broker_rx_kbps': 'Throughput uplink (kb/s)'}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def media(vals):
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else float('nan')


def carregar():
    dados = {p: {c: {k: [] for k in ('app_lat_media_ms', 'broker_rx_kbps')}
                 for c in CARGAS} for p in ORDEM}
    for proto, exp in EXPERIMENTOS.items():
        with open(os.path.join(DADOS_BASE, exp, 'metricas_por_run.csv'),
                  newline='') as f:
            for r in csv.DictReader(f):
                carga = num(r['carga'])
                if carga is None or int(carga) not in CARGAS:
                    continue
                c = int(carga)
                d = dados[proto][c]
                d['app_lat_media_ms'].append(num(r['app_lat_media_ms']))
                d['broker_rx_kbps'].append(num(r['broker_rx_kbps']))
    return dados


def painel(ax, dados, chave, titulo, unidade, legenda_carga):
    y = [i * 4.2 for i in range(len(CARGAS))]
    h = 0.82
    for j, proto in enumerate(ORDEM):
        meds = [media(dados[proto][c][chave]) for c in CARGAS]
        ys = [yi + (j - 1) * h for yi in y]
        ax.barh(ys, [0 if m != m else m for m in meds], h,
                label=proto.upper(), color=CORES[proto], edgecolor='black',
                linewidth=0.6)
        for yi, mi in zip(ys, meds):
            if mi != mi:
                continue
            ax.text(mi + abs(mi) * 0.05, yi, '%.1f' % mi, ha='left',
                    va='center', fontsize=21, fontweight='bold')
    ax.set_yticks(y)
    ax.set_yticklabels(['%d' % c for c in CARGAS], fontsize=23,
                       fontweight='bold')
    if legenda_carga:
        ax.set_ylabel('Carga', fontsize=23, fontweight='bold')
    ax.set_xlabel(unidade, fontsize=23, fontweight='bold')
    ax.set_title(titulo, fontsize=26, fontweight='bold')
    ax.grid(axis='x', linestyle=':', alpha=0.5)
    ax.tick_params(axis='x', labelsize=21)
    for lbl in ax.get_xticklabels():
        lbl.set_fontweight('bold')
    ax.margins(x=0.18)
    leg = ax.legend(fontsize=20)
    for text in leg.get_texts():
        text.set_fontweight('bold')
    ax.invert_yaxis()


def principal(out):
    os.makedirs(out, exist_ok=True)
    dados = carregar()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(18.4, 13.2))
    painel(a1, dados, 'app_lat_media_ms',
           'Latencia fim-a-fim (media)', 'ms', True)
    painel(a2, dados, 'broker_rx_kbps',
           'Throughput no servidor', 'kb/s', False)
    fig.tight_layout()
    path = os.path.join(out, 'artigo_throughput.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('Grafico: %s' % path)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT_DEFAULT)
    principal(ap.parse_args().out)