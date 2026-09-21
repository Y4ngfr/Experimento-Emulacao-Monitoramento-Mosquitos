#!/usr/bin/env python3
"""
Coletor de metricas de REDE por no (roda dentro do namespace do proprio no).

A cada intervalo de --interval segundos:
  - le /proc/net/dev (contadores cumulativos de TODAS as interfaces do no);
  - para cada interface wifi detectada, executa 'iw dev <iface> station dump'
    (quadros tx/rx + retries + failed + beacon loss + rssi + bitrate);
  - grava uma linha CSV com os contadores cumulativos e as taxas do intervalo.

Taxas do intervalo (rx_bps, tx_bps, rx_pps, tx_pps, tx_retries_s, ...) ficam
na mesma linha; totais do experimento = ultimo - primeiro de cada coluna.

Uso:
  python3 coletor_no.py --out /app/dados/metricas/rede_no/sta0.csv [--interval 5]
"""

import argparse
import csv
import os
import re
import signal
import time

import sys

SIGSTOP = False


def _stop(sig, frame):
    global SIGSTOP
    SIGSTOP = True


def ler_dev():
    """Retorna {iface: {'rx_bytes':int,'rx_pkts':int,'rx_drops':int,'tx_bytes':int,'tx_pkts':int}}."""
    out = {}
    with open('/proc/net/dev') as f:
        next(f)
        next(f)
        for line in f:
            if ':' not in line:
                continue
            name, rest = line.split(':', 1)
            v = rest.split()
            out[name.strip()] = {
                'rx_bytes': int(v[0]), 'rx_pkts': int(v[1]), 'rx_drops': int(v[3]),
                'tx_bytes': int(v[8]), 'tx_pkts': int(v[9]),
            }
    return out


def ifaces_wifi():
    """Interfaces wifi no namespace atual (via iw dev)."""
    try:
        import subprocess
        r = subprocess.run(['iw', 'dev'], capture_output=True, text=True).stdout
        return re.findall(r'^\s*Interface\s+(\S+)', r, re.M)
    except Exception:
        return []


def station_dump(iface):
    """Agrega o station dump (soma numericos entre os pares; strings do 1o peer)."""
    import subprocess
    r = subprocess.run(['iw', 'dev', iface, 'station', 'dump'],
                       capture_output=True, text=True).stdout
    peers = []
    cur = None
    for line in r.splitlines():
        m = re.match(r'Station\s+([0-9a-f:]+)\s*\(on', line)
        if m:
            cur = {'mac': m.group(1)}
            peers.append(cur)
        elif cur is not None and ':' in line:
            k, v = line.split(':', 1)
            cur[k.strip()] = v.strip()
    if not peers:
        return {}
    agg = {'n_peers': len(peers)}
    num_keys = ['rx bytes', 'rx packets', 'tx bytes', 'tx packets', 'tx retries',
                'tx failed', 'beacon loss', 'rx drop misc']
    for k in num_keys:
        vals = [float(p.get(k, 0) or 0) for p in peers]
        agg[k.replace(' ', '_')] = int(sum(vals))
    sigs = [float(re.findall(r'-?\d+', p.get('signal avg', ''))[0])
            for p in peers if re.findall(r'-?\d+', p.get('signal avg', ''))]
    if sigs:
        agg['signal_avg'] = round(sum(sigs) / len(sigs), 1)
    else:
        agg['signal_avg'] = ''
    for k in ['tx bitrate', 'expected throughput']:
        agg[k.replace(' ', '_')] = peers[0].get(k, '')
    return agg


def parse_wifi_bitrate(s):
    m = re.findall(r'[\d.]+', s or '')
    return float(m[0]) if m else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--interval', type=float, default=5.0)
    args = ap.parse_args()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    fs = open(args.out, 'w', newline='')
    w = csv.writer(fs)
    header = ['ts', 'iface', 'rx_bytes', 'tx_bytes', 'rx_pkts', 'tx_pkts',
              'rx_bps', 'tx_bps', 'rx_pps', 'tx_pps',
              'peer_rx_bytes', 'peer_rx_pkts', 'peer_tx_pkts',
              'tx_retries_s', 'tx_failed_s', 'beacon_loss_s',
              'rssi_dbm', 'tx_bitrate', 'exp_tp']
    w.writerow(header)
    fs.flush()

    prev = {}
    while not SIGSTOP:
        dev = ler_dev()
        wifi_set = set(ifaces_wifi())
        for iface, c in dev.items():
            if iface == 'lo':
                continue
            prev_c = prev.get(iface)
            dt = args.interval
            rx_bps = tx_bps = rx_pps = tx_pps = ''
            tr_s = tf_s = bl_s = ''
            peer = {}
            if prev_c is not None:
                rx_bps = round((c['rx_bytes'] - prev_c['rx_bytes']) * 8 / dt)
                tx_bps = round((c['tx_bytes'] - prev_c['tx_bytes']) * 8 / dt)
                rx_pps = (c['rx_pkts'] - prev_c['rx_pkts']) / dt
                tx_pps = (c['tx_pkts'] - prev_c['tx_pkts']) / dt
            if iface in wifi_set:
                peer = station_dump(iface)
                if prev_c is not None and 'tx_retries' in peer:
                    tr_s = peer['tx_retries'] - prev_c.get('tx_retries', peer['tx_retries'])
                    tf_s = peer['tx_failed'] - prev_c.get('tx_failed', peer['tx_failed'])
                    bl_s = peer['beacon_loss'] - prev_c.get('beacon_loss', peer['beacon_loss'])
            row = [round(time.time(), 3), iface,
                   c['rx_bytes'], c['tx_bytes'], c['rx_pkts'], c['tx_pkts'],
                   rx_bps, tx_bps, rx_pps, tx_pps,
                   peer.get('rx_bytes', ''), peer.get('rx_packets', ''),
                   peer.get('tx_packets', ''),
                   tr_s, tf_s, bl_s,
                   peer.get('signal_avg', ''),
                   parse_wifi_bitrate(peer.get('tx_bitrate', '')),
                   peer.get('expected_throughput', '')]
            w.writerow(row)
            prev.setdefault(iface, {}).update(c)
            if 'tx_retries' in peer:
                prev[iface]['tx_retries'] = peer['tx_retries']
                prev[iface]['tx_failed'] = peer['tx_failed']
                prev[iface]['beacon_loss'] = peer['beacon_loss']
        fs.flush()
        time.sleep(args.interval)

    fs.close()


if __name__ == '__main__':
    main()