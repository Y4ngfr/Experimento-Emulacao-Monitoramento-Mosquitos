#!/usr/bin/env python3
"""Comparativo por carga entre os 3 protocolos (mqtt/http/coap).

Le os metricas_por_run.csv de cada experimento e agrega por carga
(media±desvio das runs), gerando:
  - analise_host/comparativo_protocolos.csv
  - analise_host/comparativo_protocolos.md  (tabela markdown por metrica)

Metricas consideradas (camadas app/deteccao/rede/broker).
"""
import argparse
import csv
import os
import statistics

EXPERIMENTOS = {
    'mqtt': 'experimento_20260914_235110',
    'http': 'experimento_20260915_045417',
    'coap': 'experimento_20260915_073606',
}

CARGAS = [10, 20, 30, 40, 50]

APP = ['app_lat_p50_ms', 'app_lat_p90_ms', 'app_lat_p99_ms', 'app_lat_p99_ms_all',
       'app_goodput_media_kbps', 'app_goodput_sustentado_kbps', 'app_msgs_total',
       'app_perda_pct']
DET = ['det_acuracia_pct', 'det_classe_0_taxa_pct', 'det_classe_1_taxa_pct',
       'det_classe_2_taxa_pct', 'det_classe_3_taxa_pct']
REDE = ['sta_rssi_media_dbm', 'sta_bitrate_media_mbps', 'sta_retries',
        'sta_failed', 'sta_beacon_loss']
BROKER = ['broker_clients', 'broker_rx_kbps', 'broker_tx_kbps']


def ler(csv_path):
    with open(csv_path, newline='') as f:
        return list(csv.DictReader(f))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def carga_de(r):
    try:
        return int(r['carga'])
    except (TypeError, ValueError):
        return None


def fmt(v):
    if v is None:
        return '--'
    a = abs(v)
    if a >= 10000 or (0 < a < 0.01):
        return '%.3g' % v
    if a >= 100:
        return '%.1f' % v
    return '%.3g' % v


def agregar(rows, col, carga):
    vals = [num(r[col]) for r in rows if r.get('status') == 'ok'
            and carga_de(r) == carga and num(r[col]) is not None]
    if not vals:
        return None, None, 0
    m = statistics.mean(vals)
    d = statistics.stdev(vals) if len(vals) >= 2 else None
    return m, d, len(vals)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='dados/experimentos')
    ap.add_argument('--out', default='analise_host')
    args = ap.parse_args()

    dados = {}
    for proto, exp in EXPERIMENTOS.items():
        path = os.path.join(args.base, exp, 'metricas_por_run.csv')
        if not os.path.isfile(path):
            print('[erro] csv nao encontrado: %s' % path)
            continue
        dados[proto] = ler(path)

    metricas = []
    for grupo, lista in (('app', APP), ('det', DET), ('rede', REDE), ('broker', BROKER)):
        metricas.extend(lista)

    os.makedirs(args.out, exist_ok=True)
    csv_path = os.path.join(args.out, 'comparativo_protocolos.csv')
    md_path = os.path.join(args.out, 'comparativo_protocolos.md')

    with open(csv_path, 'w', newline='') as ftab:
        w = csv.writer(ftab)
        w.writerow(['metrica', 'grupo', 'carga', 'protocolo', 'media', 'desvio', 'n'])
        for met in metricas:
            for c in CARGAS:
                for proto in EXPERIMENTOS:
                    if proto not in dados:
                        continue
                    m, d, n = agregar(dados[proto], met, c)
                    w.writerow([met, met.split('_')[0], c, proto,
                                '' if m is None else '%.6f' % m,
                                '' if d is None else '%.6f' % d, n])

    lines = ['# Comparativo por protocolo e carga (media±desvio das runs)\n']
    for grupo, lista in (('Aplicacao', APP), ('Deteccao', DET),
                         ('Rede', REDE), ('Broker', BROKER)):
        lines.append('\n## %s\n' % grupo)
        for met in lista:
            cab = '| metrica | carga | ' + ' | '.join(EXPERIMENTOS) + ' |'
            sep = '| ' + ' | '.join(['---'] * (3 + len(EXPERIMENTOS))) + ' |'
            lines.append(cab)
            lines.append(sep)
            for c in CARGAS:
                cel = []
                for proto in EXPERIMENTOS:
                    if proto not in dados:
                        cel.append('--')
                        continue
                    m, d, n = agregar(dados[proto], met, c)
                    cel.append('%s±%s(n=%d)' % (fmt(m), fmt(d), n) if m is not None else '--')
                lines.append('| %s | %d | %s |' % (met, c, ' | '.join(cel)))
            lines.append('')

    with open(md_path, 'w') as f:
        f.write('\n'.join(lines))
    print('CSV : %s' % csv_path)
    print('MD  : %s' % md_path)


if __name__ == '__main__':
    main()