#!/usr/bin/env python3
"""
Cientista (assinante HTTP) — ramificacao HTTP.

Usa o motor compartilhado metricas_app.py (mesmo CSV de aplicacao das outras
ramificacoes). Em vez de assinar um topico, faz long-poll em GET /stream no
servidor, que entrega os metadados dos sensores conforme chegam.

Uso:
  python3 cientista_stream.py --url http://11.0.0.10:8000/stream --id cient1 \
      --log /app/dados/http/cient1.log [--metrics=/app/dados/metricas/app]
"""

import argparse
import json
import os
import sys
import time
import urllib.request

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)

from metricas_app import AppMetricas  # noqa: E402

MAX_ERROS = 5
ERRO_SLEEP = 2.0


def parse_args():
    p = argparse.ArgumentParser(description='Cientista HTTP subscriber (long-poll)')
    p.add_argument('--url', default='http://11.0.0.10:8000/stream',
                   help='Endpoint de stream (/stream)')
    p.add_argument('--id', default='cient0', help='ID do cientista')
    p.add_argument('--log', default='/app/dados/http/cient0.log', help='Arquivo de log')
    p.add_argument('--metrics', default=None, help='Dir para o CSV de metricas de app')
    p.add_argument('--window', type=int, default=20, help='Mensagens por linha do CSV de metricas')
    return p.parse_args()


def _receber(url):
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def main():
    args = parse_args()
    m = AppMetricas(name=args.id, log=args.log, metrics_dir=args.metrics,
                    window=args.window)

    erros = 0
    while True:
        try:
            metas = _receber(args.url)
            erros = 0
            for meta in metas:
                sensor = meta.get('sensor', '?')
                m.registrar(json.dumps(meta), sensor)
        except OSError:
            erros += 1
            if erros >= MAX_ERROS:
                return
            time.sleep(ERRO_SLEEP)


if __name__ == '__main__':
    main()