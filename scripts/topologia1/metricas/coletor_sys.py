#!/usr/bin/env python3
"""
Coletor de metricas do PROCESSO CENTRAL do experimento (analogo nas 3
ramificacoes) — grava o mesmo CSV sys/broker.csv nas tres.

O processo central troca com o protocolo de aplicacao, mas o coletor (e o CSV)
nao muda:

  --modo mqtt : assina $SYS/# do broker mosquitto (roda dentro do srv1 para
                alcancar o broker local);
  --modo http : GET /stats do servidor_http (contadores do POST /meta e do
                stream long-poll);
  --modo coap : GET /stats do servidor_coap (contadores do POST /meta e dos
                observers do /stream).

A cada intervalo grava uma linha CSV com o snapshot dos contadores cumulativos
e as taxas do intervalo (throughput do processo central).

Uso:
  python3 coletor_sys.py --modo mqtt --broker 127.0.0.1 --out .../sys/broker.csv
  python3 coletor_sys.py --modo http --url http://127.0.0.1:8000/stats --out .../sys/broker.csv
  python3 coletor_sys.py --modo coap --url coap://127.0.0.1:5683/stats --out .../sys/broker.csv
"""

import argparse
import csv
import json
import os
import signal
import threading
import time

import paho.mqtt.client as mqtt

SIGSTOP = False
SEEN = {}
CONECTADO = False

_KEYS = {
    'bytes_recv': '$SYS/broker/bytes/received',
    'bytes_sent': '$SYS/broker/bytes/sent',
    'msg_recv': '$SYS/broker/messages/received',
    'msg_sent': '$SYS/broker/messages/sent',
    'pub_sent': '$SYS/broker/publish/messages/sent',
    'pub_bytes': '$SYS/broker/publish/bytes/sent',
    'clients': '$SYS/broker/clients/connected',
    'subs': '$SYS/broker/subscriptions/count',
    'load_recv_1m': '$SYS/broker/load/messages/received/1min',
    'load_sent_1m': '$SYS/broker/load/messages/sent/1min',
}


def _stop(sig, frame):
    global SIGSTOP
    SIGSTOP = True


def _on_connect(client, userdata, flags, reason_code, properties):
    global CONECTADO
    CONECTADO = reason_code == 0
    if reason_code == 0:
        client.subscribe('$SYS/#', qos=0)


def _on_message(client, userdata, msg):
    SEEN[msg.topic] = msg.payload.decode()


def _on_disconnect(client, userdata, flags, reason_code, properties):
    global CONECTADO
    CONECTADO = False


def _snapshot_mqtt():
    snap = {}
    for alias, t in _KEYS.items():
        v = SEEN.get(t)
        try:
            snap[alias] = float(v)
        except (TypeError, ValueError):
            snap[alias] = None
    return snap


def _snapshot_http(url):
    import urllib.request
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read().decode('utf-8'))


async def _coap_get(url):
    import aiocoap
    ctx = await aiocoap.Context.create_client_context()
    try:
        req = aiocoap.Message(code=aiocoap.GET, uri=url)
        resp = await ctx.request(req).response
        if not resp.code.is_successful():
            return None
        return json.loads(resp.payload.decode('utf-8'))
    finally:
        await ctx.shutdown()


def _snapshot_coap(url):
    import asyncio
    return asyncio.run(_coap_get(url))


def _snapshot(modo, url):
    """Snapshot dos contadores do processo central; None se indisponivel."""
    if modo == 'mqtt':
        return _snapshot_mqtt()
    try:
        if modo == 'http':
            return _snapshot_http(url)
        if modo == 'coap':
            return _snapshot_coap(url)
    except Exception:
        return None
    return None


def _v(x):
    """Load* podem nao existir fora do mqtt -> grava vazio em vez de None."""
    return x if x is not None else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--modo', choices=['mqtt', 'http', 'coap'], default='mqtt',
                    help='Processo central a medir (default mqtt)')
    ap.add_argument('--broker', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=1883)
    ap.add_argument('--url', default='',
                    help='Endpoint de stats (http://.../stats ou coap://.../stats)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--interval', type=float, default=5.0)
    args = ap.parse_args()

    if args.modo == 'mqtt':
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='sys_coletor')
        client.on_connect = _on_connect
        client.on_message = _on_message
        client.on_disconnect = _on_disconnect
        client.connect(args.broker, args.port, keepalive=30)
        threading.Thread(target=client.loop_forever, daemon=True).start()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    fs = open(args.out, 'w', newline='')
    w = csv.writer(fs)
    w.writerow(['ts', 'bytes_recv', 'bytes_sent', 'msg_recv', 'msg_sent', 'pub_sent',
                'pub_bytes', 'clients', 'subs', 'load_recv_1m', 'load_sent_1m',
                'brx_bps', 'btx_bps', 'bmsg_rx_pps', 'bmsg_tx_pps', 'bpub_bps'])
    fs.flush()

    snaps = {}
    while not SIGSTOP:
        time.sleep(args.interval)
        snap = _snapshot(args.modo, args.url)
        if snap is None:
            continue

        def dr(a):
            va = snap.get(a)
            vb = snaps.get(a) if snaps else None
            if va is not None and vb is not None:
                return (va - vb) / args.interval
            return ''

        if snaps:
            row = [round(time.time(), 3),
                   int(snap.get('bytes_recv') or 0), int(snap.get('bytes_sent') or 0),
                   int(snap.get('msg_recv') or 0), int(snap.get('msg_sent') or 0),
                   int(snap.get('pub_sent') or 0), int(snap.get('pub_bytes') or 0),
                   int(snap.get('clients') or 0), int(snap.get('subs') or 0),
                   _v(snap.get('load_recv_1m')), _v(snap.get('load_sent_1m')),
                   dr('bytes_recv') * 8 if dr('bytes_recv') != '' else '',
                   dr('bytes_sent') * 8 if dr('bytes_sent') != '' else '',
                   dr('msg_recv'), dr('msg_sent'),
                   dr('pub_bytes') * 8 if dr('pub_bytes') != '' else '']
            w.writerow(row)
            fs.flush()
        snaps = snap

    fs.close()


if __name__ == '__main__':
    main()