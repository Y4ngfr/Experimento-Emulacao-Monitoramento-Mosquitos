#!/usr/bin/env python3
"""
Resumo offline das metricas coletadas durante o experimento.

Le os CSVs gerados por coletor_no.py / coletor_sys.py / cientista_sub.py e
imprime um relatorio consolidado:

  - por no/interface: total de bytes e quadros rx/tx, throughput medio,
    quadros/s medio; no wifi: retries, falhas, perda de beacon, rssi, bitrate;
  - broker: mensagens e bytes totais, throughput medio;
  - aplicacao: goodput, msgs, perda (gaps/seq), duplicatas,
    latencia fim-a-fim (media/min/max/p50/p99).

Uso:
  python3 resumo_metricas.py --dir /app/dados/metricas
"""

import argparse
import csv
import json
import os
import statistics


def ler_csv(path):
    rows = []
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


NOISE = ('br-', 'docker0', 'veth', 'lo', 'wlp', 'hwsim', 'ovs-system', 'eth0@')


def eh_relevante(iface):
    return not any(iface.startswith(p) for p in NOISE)


def resumo_rede(d):
    print('=' * 70)
    print('REDE (por no / interface)')
    print('=' * 70)
    for path in sorted(os.listdir(os.path.join(d, 'rede_no'))):
        if not path.endswith('.csv'):
            continue
        rows = ler_csv(os.path.join(d, 'rede_no', path))
        node = path[:-4]
        print('\n-- %s --' % node)
        if not rows:
            print('  (sem amostras)')
            continue
        by_if = {}
        for r in rows:
            by_if.setdefault(r['iface'], []).append(r)
        for iface, rr in by_if.items():
            if not eh_relevante(iface):
                continue
            if len(rr) < 2:
                continue
            first, last = rr[0], rr[-1]
            dur = max(0.001, num(last['ts']) - num(first['ts']))
            rx_b = num(last['rx_bytes']) - num(first['rx_bytes'])
            tx_b = num(last['tx_bytes']) - num(first['tx_bytes'])
            rx_p = num(last['rx_pkts']) - num(first['rx_pkts'])
            tx_p = num(last['tx_pkts']) - num(first['tx_pkts'])
            bps_rx = [num(r['rx_bps']) for r in rr]
            bps_tx = [num(r['tx_bps']) for r in rr]
            pps_rx = [num(r['rx_pps']) for r in rr]
            pps_tx = [num(r['tx_pps']) for r in rr]
            f = lambda vs: statistics.mean([x for x in vs if x is not None]) if any(x is not None for x in vs) else float('nan')
            extra = ''
            if num(rr[-1].get('peer_tx_pkts')) is not None:
                peer_rx = num(last['peer_rx_bytes']) - num(first['peer_rx_bytes'])
                peer_txp = num(last['peer_tx_pkts']) - num(first['peer_tx_pkts'])
                ret = sum(x for x in (num(r['tx_retries_s']) for r in rr) if x is not None)
                fail = sum(x for x in (num(r['tx_failed_s']) for r in rr) if x is not None)
                beac = sum(x for x in (num(r['beacon_loss_s']) for r in rr) if x is not None)
                rssi = [num(r['rssi_dbm']) for r in rr]
                bit = [num(r['tx_bitrate']) for r in rr]
                extra = ('  |  wifi: rx=%.0fMB peer_tx_pkts=%d retries=%d failed=%d ' % (peer_rx / 1e6, peer_txp, ret, fail)
                         + 'beacon_loss=%d rssi=%.0fdBm bitrate=%.1fMbps' % (beac, statistics.mean([x for x in rssi if x is not None]) if any(x is not None for x in rssi) else float('nan'), statistics.mean([x for x in bit if x is not None]) if any(x is not None for x in bit) else float('nan')))
            print('  %-14s rx=%.1fMB(%d) tx=%.1fMB(%d) thru_rx=%.0fkbps thru_tx=%.0fkbps '
                  'pps_rx=%.1f pps_tx=%.1f%s'
                  % (iface, rx_b / 1e6, rx_p, tx_b / 1e6, tx_p,
                     f(bps_rx) / 1e3, f(bps_tx) / 1e3, f(pps_rx), f(pps_tx), extra))


def resumo_sys(d):
    path = os.path.join(d, 'sys', 'broker.csv')
    if not os.path.isfile(path):
        return
    rows = ler_csv(path)
    print('\n' + '=' * 70)
    print('PROCESSO CENTRAL (broker MQTT via $SYS | servidor HTTP/CoAP via /stats)')
    print('=' * 70)
    if len(rows) < 2:
        print('  (sem amostras)')
        return
    first, last = rows[0], rows[-1]
    mp = lambda k: num(last[k]) - num(first[k])
    print('  mensagens recebidas: %d | enviadas: %d | publicadas: %d'
          % (mp('msg_recv'), mp('msg_sent'), mp('pub_sent')))
    print('  bytes recebidos: %.1f MB | enviados: %.1f MB'
          % (mp('bytes_recv') / 1e6, mp('bytes_sent') / 1e6))
    print('  throughput medio (broker): rx=%.0fkbps tx=%.0fkbps | msgs/s rx=%.1f tx=%.1f'
          % (statistics.mean([num(r['brx_bps']) for r in rows if num(r['brx_bps']) is not None]) / 1e3,
             statistics.mean([num(r['btx_bps']) for r in rows if num(r['btx_bps']) is not None]) / 1e3,
             statistics.mean([num(r['bmsg_rx_pps']) for r in rows if num(r['bmsg_rx_pps']) is not None]),
             statistics.mean([num(r['bmsg_tx_pps']) for r in rows if num(r['bmsg_tx_pps']) is not None])))


def resumo_app(d):
    dd = os.path.join(d, 'app')
    print('\n' + '=' * 70)
    print('APLICACAO (fim-a-fim, por cientista)')
    print('=' * 70)
    for path in sorted(os.listdir(dd)):
        if not path.endswith('.csv'):
            continue
        rows = ler_csv(os.path.join(dd, path))
        name = path[:-4]
        if not rows:
            print('\n-- %s --\n  (sem amostras)' % name)
            continue
        ult = rows[-1]
        msgs = int(ult['msgs'])
        gaps = int(ult['gaps'])
        dups = int(ult['dups'])
        f = lambda vs: statistics.mean([x for x in vs if x is not None]) if any(x is not None for x in vs) else float('nan')
        gbps = [num(r['goodput_bps']) for r in rows]
        medias = [num(r['lat_media_us']) for r in rows]
        lmin = [num(r['lat_min_us']) for r in rows]
        lmax = [num(r['lat_max_us']) for r in rows]
        p99 = [num(r['lat_p99_us']) for r in rows]
        perda = [num(r['perda_app_%']) for r in rows]
        print('\n-- %s --\n  msgs=%d (janelas=%d) gaps=%d dups=%d'
              % (name, msgs, len(rows), gaps, dups))
        print('  goodput medio=%.1f kbps | perda_app media=%.2f%%'
              % (f(gbps) / 1e3, f(perda)))
        if medias:
            print('  latencia fim-a-fim: media=%.0fus min=%.0fus max=%.0fus p50=%.0fus p99=%.0fus'
                  % (f(medias), min(lmin), max(lmax),
                     statistics.median(medias) if len(medias) > 1 else medias[0],
                     f(p99)))
        else:
            print('  latencia: sem amostras')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='/app/dados/metricas')
    args = ap.parse_args()
    resumo_rede(args.dir)
    resumo_sys(args.dir)
    resumo_app(args.dir)


if __name__ == '__main__':
    main()