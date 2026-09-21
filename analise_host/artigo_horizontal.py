#!/usr/bin/env python3
"""Dois graficos horizontais para o artigo — a versao final que voce pediu.

Esquerda : Latencia media fim a fim (ms, todas as msgs)   — ylabel "Carga"
Direita  : Throughput uplink no broker (kb/s)             — SEM ylabel
Barras na horizontal (eixo y = carga 10-50), protocolos coloridos,
valores em negrito, fontes graúdas (fonte dos eixos/medidas/protocolos
aumentada para caber em espaço de artigo).

Fonte: metricas_por_run.csv de cada experimento (fonte identica ao
relatorio; nada recomputado).
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
sys.path.insert(0, _RAIZ)  # noqa: E402

from analise_host.comparativo_barras import (  # noqa: E402
    CARGAS, CORES, EXPERIMENTOS, ORDEM, num)

OUT_DEFAULT = os.path.join(_RAIZ, 'analise_host')


def media(vals):
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else float('nan')


def grafico(ax, dados, chave, titulo, unidade, rotulo_y):
    y = list(range(len(CARGAS)))
    h = 0.27
    for j, proto in enumerate(ORDEM):
        meds = [media(dados[proto][c][chave]) for c in CARGAS]
        ys = [yi + (j - 1) * h for yi in y]
        ax.barh(ys, [0 if m != m else m for m in meds], h,
                label=proto.upper(), color=CORES[proto], edgecolor='black',
                linewidth=0.6)
        for yi, mi in zip(ys, meds):
            if mi != mi:
                continue
            ax.text(mi + abs(mi) * 0.04, yi, '%.1f' % mi, ha='left',
                    va='center', fontsize=13, fontweight='bold')
    ax.set_yticks(y)
    ax.set_yticklabels(['%d' % c for c in CARGAS], fontsize=14,
                       fontweight='bold')
    ax.set_ylabel(rotulo_y, fontsize=14, fontweight='bold')
    ax.set_xlabel(unidade, fontsize=14, fontweight='bold')
    ax.set_title(titulo, fontsize=16, fontweight='bold')
    ax.grid(axis='x', linestyle=':', alpha=0.5)
    ax.legend(fontsize=12)
    ax.invert_yaxis()


def ler():
    dados = {p: {c: {k: [] for k in ('app_lat_media_ms', 'broker_rx_kbps')}
                 for c in CARGAS} for p in ORDEM}
    for proto, exp in EXPERIMENTOS.items():
        base = os.path.join(DADOS_BASE, exp)
        with open(os.path.join(base, 'metricas_por_run.csv'), newline='') as f:
            for r in csv.DictReader(f):
                carga = num(r['carga'])
                if carga is None or int(carga) not in CARGAS:
                    continue
                c = int(carga)
                d = dados[proto][c]
                d['app_lat_media_ms'].append(num(r['app_lat_media_ms']))
                d['broker_rx_kbps'].append(num(r['broker_rx_kbps']))
    return dados


def main(out):
    os.makedirs(out, exist_ok=True)
    dados = ler()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.5, 5.0))
    grafico(a1, dados, 'app_lat_media_ms',
            'Latencia media fim a fim (todas as msgs)',
            'ms (media)', 'Carga')
    grafico(a2, dados, 'broker_rx_kbps',
            'Throughput uplink no broker (kb/s)',
            'kb/s (broker_rx_kbps)', '')
    fig.tight_layout()
    path = os.path.join(out, 'artigo_horizontal.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('Graficos: %s' % path)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT_DEFAULT)
    main(ap.parse_args().out)
