#!/usr/bin/env python3
"""
Cientista MQTT subscriber.

Usa o motor compartilhado metricas_app.py (mesmo formato de CSV das
ramificacoes HTTP/CoAP) para, alem do log cru, gravar metricas de aplicacao:
  - latencia fim-a-fim (recepcao - 'ts' embutido pelo publicador);
  - goodput (bytes de payload por segundo);
  - perda na camada de aplicacao (gaps no 'seq') e duplicatas.

Uso:
  python3 cientista_sub.py --broker=11.0.0.10 --id=1 --topic=meta/# --log=X.log
      [--metrics=/app/dados/metricas/app] [--window=20]
"""

import argparse
import os
import sys

import paho.mqtt.client as mqtt

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)

from metricas_app import AppMetricas  # noqa: E402


def parse_args():
    p = argparse.ArgumentParser(description='Cientista MQTT subscriber')
    p.add_argument('--broker', default='11.0.0.10', help='IP do broker MQTT')
    p.add_argument('--port', type=int, default=1883, help='Porta TCP do broker MQTT')
    p.add_argument('--id', default='cient0', help='Client ID do assinante')
    p.add_argument('--topic', default='sensors/#', help='Filtro de tópico')
    p.add_argument('--log', default='/app/dados/mqtt/cient0.log', help='Arquivo de log')
    p.add_argument('--metrics', default=None, help='Dir para o CSV de metricas de app')
    p.add_argument('--window', type=int, default=20, help='Mensagens por linha do CSV de metricas')
    return p.parse_args()


def main():
    args = parse_args()
    m = AppMetricas(name=args.id, log=args.log, metrics_dir=args.metrics,
                    window=args.window)

    def on_connect(client, userdata, flags, reason_code, properties):
        client.subscribe(args.topic, qos=0)

    def on_message(client, userdata, msg):
        m.registrar(msg.payload.decode(errors='replace'), msg.topic)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=args.id)
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(args.broker, args.port, keepalive=30)
    except Exception:
        sys.exit(1)
    client.loop_forever()


if __name__ == '__main__':
    main()