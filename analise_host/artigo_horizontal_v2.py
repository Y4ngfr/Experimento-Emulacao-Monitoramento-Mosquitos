#!/usr/bin/env python3
"""Dois graficos horizontais para o artigo (entregue).

Esquerda : Latencia media fim-a-fim (ms, todas as msgs)
Direita  : Throughput uplink no broker (kb/s)

Eixo Y = carga (10-50), barras na horizontal (mqtt/http/coap).
Fonte das metricas: metricas_por_run.csv (fonte unica identica ao
relatorio, sem recomputo). Saida: analise_host/artigo_horizontal.png
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
    CARGAS, CORES, DADOS_BASE, EXPERIMENTOS, ORDEM, coleta, num)

OUT_DEFAULT = os.path.join(_RAIZ, 'analise_host')


def media(vals):
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else float('nan')


def _painel(ax, dados, chave, titulo, unidade, mostrar_carga=True):
    y = list(range(len(CARGAS)))
    h = 0.265
    for j, proto in enumerate(ORDEM):
        meds = [media(dados[proto][c][chave]) for c in CARGAS]
        ys = [yi + (j - 1) * h for yi in y]
        ax.barh(ys, [m if m == m else 0 for m in meds], h,
                label=proto.upper(), color=CORES[proto], edgecolor='black',
                linewidth=0.6)
        for yi, mi in zip(ys, meds):
            if mi != mi:
                continue
            ax.text(mi + abs(mi) * 0.04, yi, '%.1f' % mi, ha='left',
                    va='center', fontsize=12, fontweight='bold')
    ax.set_yticks(y)
    ax.set_yticklabels([str(c) for c in CARGAS], fontsize=12,
                       fontweight='bold')
    if mostrar_carga:
        ax.set_ylabel('Carga', fontsize=12, fontweight='bold')
    ax.set_xlabel(unidade, fontsize=12)
    ax.set_title(titulo, fontsize=14, fontweight='bold')
    ax.grid(axis='x', linestyle=':', alpha=0.4)
    ax.legend(fontsize=10, loc='lower right')
    ax.invert_yaxis()


def principal(out):
    os.makedirs(out, exist_ok=True)
    dados = coleta()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.5, 4.5))
    _painel(a1, dados, 'app_lat_media_ms',
            'Latencia media fim a fim (todas as msgs)', 'ms (media)')
    _painel(a2, dados, 'broker_rx_kbps',
            'Throughput uplink no broker', 'kb/s (broker_rx_kbps)',
            mostrar_carga=False)
    fig.tight_layout()
    path = os.path.join(out, 'artigo_horizontal.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('Artigo horizontal: %s' % path)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT_DEFAULT)
    principal(ap.parse_args().out)
